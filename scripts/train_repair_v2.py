"""
Repair Model v2 학습 스크립트
CIRCL/vulnerability-cwe-patch 전처리 데이터 사용
GTX 1070 (8GB VRAM) 최적화

기존 CyberNative DPO (2000개) → CIRCL 실제 패치 데이터로 업그레이드
"""

import os
import torch

# Windows 호환성: torch.distributed.tensor 이 없으면 peft가 크래시
# → dummy 모듈 + dummy 클래스 주입으로 우회
import types
if not hasattr(torch.distributed, 'tensor'):
    torch.distributed.tensor = types.ModuleType('torch.distributed.tensor')
    class _DummyDTensor:
        pass
    torch.distributed.tensor.DTensor = _DummyDTensor

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback
)
from peft import get_peft_model, LoraConfig, TaskType

# === Configuration (GTX 1070 최적화) ===
BASE_MODEL = "t5-small"
DATA_PATH = "./data/circl_processed/repair.jsonl"
OUTPUT_DIR = "./redeye-repair-model-v2"
MAX_LENGTH = 256         # 1070에선 512는 OOM 위험
BATCH_SIZE = 4           # Seq2Seq은 메모리 더 사용
GRAD_ACCUM = 4           # 실효 배치 = 16
EPOCHS = 5
LEARNING_RATE = 1e-3     # LoRA는 높은 lr 사용 가능
EVAL_SPLIT = 0.1


def train():
    print(f"🚀 Repair Model v2 학습 시작")
    print(f"  Base: {BASE_MODEL}")
    print(f"  Data: {DATA_PATH}")
    print(f"  GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    
    # 1. 데이터 로드
    print("📥 Loading preprocessed repair data...")
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    print(f"  Total samples: {len(dataset)}")
    
    # Train/Eval 분할
    split = dataset.train_test_split(test_size=EVAL_SPLIT, seed=42)
    print(f"  Train: {len(split['train'])}, Eval: {len(split['test'])}")
    
    # 2. Tokenizer & Model
    print("📝 Loading tokenizer & model...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL)
    
    # 3. LoRA 설정
    peft_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        inference_mode=False,
        r=8,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q", "v"]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # 4. Tokenize
    def preprocess_function(examples):
        model_inputs = tokenizer(
            examples["input"],
            max_length=MAX_LENGTH,
            truncation=True,
            padding="max_length"
        )
        labels = tokenizer(
            examples["output"],
            max_length=MAX_LENGTH,
            truncation=True,
            padding="max_length"
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs
    
    print("⏳ Tokenizing...")
    tokenized = split.map(preprocess_function, batched=True, remove_columns=["input", "output", "language"])
    
    # 5. Training Arguments (GTX 1070 최적화)
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        gradient_accumulation_steps=GRAD_ACCUM,
        num_train_epochs=EPOCHS,
        weight_decay=0.01,
        warmup_ratio=0.1,
        logging_dir='./logs/repair_v2',
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=torch.cuda.is_available(),
        dataloader_num_workers=2,
        report_to="none",
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )
    
    # 6. Train
    print("🔥 Training started...")
    trainer.train()
    
    # 7. Save (LoRA adapter만 저장 → 용량 절약)
    print(f"💾 Saving LoRA adapter to {OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # 8. 테스트 추론
    print("\n🧪 Test inference:")
    test_inputs = [
        "fix vulnerability: query = 'SELECT * FROM users WHERE id = ' + user_input",
        "fix vulnerability: password = request.args.get('password')\nopen('log.txt').write(password)",
    ]
    
    model.eval()
    for test_input in test_inputs:
        inputs = tokenizer(test_input, return_tensors="pt", max_length=MAX_LENGTH, truncation=True)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
            model = model.cuda()
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=MAX_LENGTH, num_beams=5, early_stopping=True)
        
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"  Input:  {test_input[:60]}...")
        print(f"  Output: {result}")
        print()
    
    print("✅ Repair Model v2 학습 완료!")


if __name__ == "__main__":
    train()
