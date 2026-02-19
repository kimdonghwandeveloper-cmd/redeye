"""
CIRCL/vulnerability-cwe-patch 데이터셋 전처리 스크립트

이 스크립트는 CIRCL 데이터셋의 패치 diff를 파싱하여:
1. Detection Model용: 취약/안전 코드 스니펫 + 라벨 데이터 생성
2. Repair Model용: 취약 코드 → 수정 코드 쌍 생성

v2: 메모리 절약을 위해 JSONL로 스트리밍 저장 + 샘플링
"""

import base64
import json
import os
import re
import random
from collections import Counter

# Configuration
OUTPUT_DIR = "./data/circl_processed"
MAX_CONTEXT_LINES = 5    # diff context 라인 수
MIN_CODE_LENGTH = 20     # 너무 짧은 코드 제외
MAX_CODE_LENGTH = 2000   # 너무 긴 코드 제외 (토큰 초과 방지)
MAX_DETECTION_SAMPLES = 50000  # Detection 최대 샘플 수 (밸런싱)
MAX_REPAIR_SAMPLES = 20000    # Repair 최대 샘플 수

# 지원 언어 확장자 매핑
LANG_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".cs": "csharp", ".cpp": "cpp", ".c": "c",
    ".go": "go", ".rs": "rust", ".swift": "swift", ".kt": "kotlin",
    ".php": "php", ".rb": "ruby", ".sql": "sql"
}


def detect_language(patch_url: str, diff_text: str) -> str:
    """패치 URL 또는 diff 파일명에서 언어 추론."""
    # diff 헤더에서 파일명 추출: --- a/path/to/file.py
    file_match = re.findall(r'--- a/(.+)', diff_text)
    if file_match:
        filename = file_match[0].strip()
        ext = os.path.splitext(filename)[1].lower()
        if ext in LANG_EXTENSIONS:
            return LANG_EXTENSIONS[ext]
    
    # URL에서 추론
    for ext, lang in LANG_EXTENSIONS.items():
        if ext in patch_url.lower():
            return lang
    
    return "unknown"


def parse_diff_for_detection(diff_text: str, language: str) -> list:
    """
    diff에서 Detection Model용 데이터 추출.
    
    - 라인(취약 코드): label = 1 (VULNERABLE)
    + 라인(수정 코드): label = 0 (SAFE)
    
    주변 컨텍스트도 포함하여 더 정확한 학습 데이터 생성.
    """
    samples = []
    current_hunk_context = []
    vuln_lines = []
    safe_lines = []
    
    for line in diff_text.split('\n'):
        # 메타데이터 라인 무시 (index, mode 등)
        if line.startswith('index ') or line.startswith('old mode ') or line.startswith('new mode ') or line.startswith('similarity index') or line.startswith('deleted file mode') or line.startswith('new file mode'):
            continue

        # 파일 경계 또는 diff 헤더 발견 시 컨텍스트 리셋
        if line.startswith('diff --git') or line.startswith('--- a/') or line.startswith('+++ b/'):
             # 이전 hunk 처리 (있다면)
            if vuln_lines or safe_lines:
                context = '\n'.join(current_hunk_context[-MAX_CONTEXT_LINES:])
                
                if vuln_lines:
                    vuln_code = '\n'.join(vuln_lines)
                    if MIN_CODE_LENGTH <= len(vuln_code) <= MAX_CODE_LENGTH:
                        full_code = f"{context}\n{vuln_code}" if context else vuln_code
                        samples.append({
                            "code": full_code.strip(),
                            "label": 1,
                            "language": language
                        })
                
                if safe_lines:
                    safe_code = '\n'.join(safe_lines)
                    if MIN_CODE_LENGTH <= len(safe_code) <= MAX_CODE_LENGTH:
                        full_code = f"{context}\n{safe_code}" if context else safe_code
                        samples.append({
                            "code": full_code.strip(),
                            "label": 0,
                            "language": language
                        })

            # 리셋 (단, --- / +++ 는 같은 파일 내 hunk가 아님. diff --git으로만 파일 구분)
            # 보통 ---/+++는 diff --git 뒤에 나오지만, 확실히 하기 위해 diff --git에서만 리셋하도록 수정
            if line.startswith('diff --git'):
                current_hunk_context = []
                vuln_lines = []
                safe_lines = []
            continue

        if line.startswith('@@'):
            # 이전 hunk 처리
            if vuln_lines or safe_lines:
                context = '\n'.join(current_hunk_context[-MAX_CONTEXT_LINES:])
                
                if vuln_lines:
                    vuln_code = '\n'.join(vuln_lines)
                    if MIN_CODE_LENGTH <= len(vuln_code) <= MAX_CODE_LENGTH:
                        full_code = f"{context}\n{vuln_code}" if context else vuln_code
                        samples.append({
                            "code": full_code.strip(),
                            "label": 1,
                            "language": language
                        })
                
                if safe_lines:
                    safe_code = '\n'.join(safe_lines)
                    if MIN_CODE_LENGTH <= len(safe_code) <= MAX_CODE_LENGTH:
                        full_code = f"{context}\n{safe_code}" if context else safe_code
                        samples.append({
                            "code": full_code.strip(),
                            "label": 0,
                            "language": language
                        })
            
            current_hunk_context = []
            vuln_lines = []
            safe_lines = []
            
        elif line.startswith('-'):
            vuln_lines.append(line[1:])
        elif line.startswith('+'):
            safe_lines.append(line[1:])
        else:
            # Context line (unchanged)
            current_hunk_context.append(line.lstrip(' '))
    
    # 마지막 hunk 처리
    if vuln_lines or safe_lines:
        context = '\n'.join(current_hunk_context[-MAX_CONTEXT_LINES:])
        if vuln_lines:
            vuln_code = '\n'.join(vuln_lines)
            if MIN_CODE_LENGTH <= len(vuln_code) <= MAX_CODE_LENGTH:
                full_code = f"{context}\n{vuln_code}" if context else vuln_code
                samples.append({"code": full_code.strip(), "label": 1, "language": language})
        if safe_lines:
            safe_code = '\n'.join(safe_lines)
            if MIN_CODE_LENGTH <= len(safe_code) <= MAX_CODE_LENGTH:
                full_code = f"{context}\n{safe_code}" if context else safe_code
                samples.append({"code": full_code.strip(), "label": 0, "language": language})
    
    return samples


def parse_diff_for_repair(diff_text: str, language: str) -> list:
    """
    diff에서 Repair Model용 데이터 추출.
    취약 코드(- 라인) → 수정 코드(+ 라인) 쌍 생성.
    """
    pairs = []
    vuln_lines = []
    safe_lines = []
    
    for line in diff_text.split('\n'):
        if line.startswith('@@'):
            # 이전 hunk에서 쌍 생성
            if vuln_lines and safe_lines:
                vuln_code = '\n'.join(vuln_lines)
                safe_code = '\n'.join(safe_lines)
                if MIN_CODE_LENGTH <= len(vuln_code) <= MAX_CODE_LENGTH and \
                   MIN_CODE_LENGTH <= len(safe_code) <= MAX_CODE_LENGTH:
                    pairs.append({
                        "input": f"fix vulnerability: {vuln_code}",
                        "output": safe_code,
                        "language": language
                    })
            vuln_lines = []
            safe_lines = []
        elif line.startswith('---') or line.startswith('+++'):
            continue
        elif line.startswith('-'):
            vuln_lines.append(line[1:])
        elif line.startswith('+'):
            safe_lines.append(line[1:])
    
    # 마지막 hunk
    if vuln_lines and safe_lines:
        vuln_code = '\n'.join(vuln_lines)
        safe_code = '\n'.join(safe_lines)
        if MIN_CODE_LENGTH <= len(vuln_code) <= MAX_CODE_LENGTH and \
           MIN_CODE_LENGTH <= len(safe_code) <= MAX_CODE_LENGTH:
            pairs.append({
                "input": f"fix vulnerability: {vuln_code}",
                "output": safe_code,
                "language": language
            })
    
    return pairs


def save_jsonl(data: list, filepath: str):
    """JSONL 형식으로 저장 (메모리 효율적)."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  💾 Saved {len(data)} samples → {filepath} ({size_mb:.1f} MB)")


def balance_detection_samples(samples: list, max_total: int) -> list:
    """Detection 샘플을 라벨 밸런싱하여 샘플링."""
    vuln = [s for s in samples if s["label"] == 1]
    safe = [s for s in samples if s["label"] == 0]
    
    half = max_total // 2
    random.seed(42)
    
    if len(vuln) > half:
        vuln = random.sample(vuln, half)
    if len(safe) > half:
        safe = random.sample(safe, half)
    
    # 적은 쪽에 맞추기
    min_count = min(len(vuln), len(safe))
    vuln = vuln[:min_count]
    safe = safe[:min_count]
    
    combined = vuln + safe
    random.shuffle(combined)
    return combined


def main():
    from datasets import load_dataset
    
    print("📥 Loading CIRCL/vulnerability-cwe-patch dataset...")
    dataset = load_dataset("CIRCL/vulnerability-cwe-patch", split="train")
    print(f"✅ Loaded {len(dataset)} entries")
    
    all_detection = []
    all_repair = []
    lang_counter = Counter()
    skipped = 0
    
    for i, entry in enumerate(dataset):
        if i % 5000 == 0:
            print(f"  Processing {i}/{len(dataset)}... (det={len(all_detection)}, rep={len(all_repair)})")
        
        patches = entry.get("patches", [])
        if not patches:
            skipped += 1
            continue
        
        for patch in patches:
            patch_b64 = patch.get("patch_text_b64", "")
            patch_url = patch.get("url", "")
            
            if not patch_b64:
                continue
            
            try:
                diff_text = base64.b64decode(patch_b64).decode("utf-8", errors="replace")
            except Exception:
                continue
            
            language = detect_language(patch_url, diff_text)
            
            # TOP 10 언어만 필터링
            if language == "unknown":
                continue
            
            lang_counter[language] += 1
            
            # Detection용
            det_samples = parse_diff_for_detection(diff_text, language)
            all_detection.extend(det_samples)
            
            # Repair용
            rep_samples = parse_diff_for_repair(diff_text, language)
            all_repair.extend(rep_samples)
    
    # 결과 통계 (샘플링 전)
    print(f"\n📊 전처리 결과 (샘플링 전):")
    print(f"  - 전체 엔트리: {len(dataset)}")
    print(f"  - 스킵됨 (패치 없음): {skipped}")
    print(f"  - Detection 샘플: {len(all_detection)}")
    print(f"  - Repair 샘플: {len(all_repair)}")
    print(f"\n🌐 언어별 분포:")
    for lang, count in lang_counter.most_common():
        print(f"  {lang}: {count}")
    
    # 샘플링 (메모리 절약 + 학습 효율)
    print(f"\n✂️ 샘플링 시작...")
    det_sampled = balance_detection_samples(all_detection, MAX_DETECTION_SAMPLES)
    print(f"  Detection: {len(all_detection)} → {len(det_sampled)} (밸런싱됨)")
    
    random.seed(42)
    if len(all_repair) > MAX_REPAIR_SAMPLES:
        rep_sampled = random.sample(all_repair, MAX_REPAIR_SAMPLES)
    else:
        rep_sampled = all_repair
    print(f"  Repair: {len(all_repair)} → {len(rep_sampled)}")
    
    # JSONL로 저장 (메모리 효율적!)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    det_path = os.path.join(OUTPUT_DIR, "detection.jsonl")
    save_jsonl(det_sampled, det_path)
    
    rep_path = os.path.join(OUTPUT_DIR, "repair.jsonl")
    save_jsonl(rep_sampled, rep_path)
    
    # Label 분포 확인
    det_labels = [s["label"] for s in det_sampled]
    det_langs = Counter(s["language"] for s in det_sampled)
    rep_langs = Counter(s["language"] for s in rep_sampled)
    
    print(f"\n🏷️ Detection Label 분포: SAFE={det_labels.count(0)}, VULNERABLE={det_labels.count(1)}")
    print(f"\n🌐 Detection 언어별:")
    for lang, count in det_langs.most_common():
        print(f"  {lang}: {count}")
    print(f"\n🌐 Repair 언어별:")
    for lang, count in rep_langs.most_common():
        print(f"  {lang}: {count}")
    
    print("\n✅ 전처리 완료!")


if __name__ == "__main__":
    main()
