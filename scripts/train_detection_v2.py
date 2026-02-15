"""
Detection Model v2 학습 스크립트
CIRCL/vulnerability-cwe-patch 전처리 데이터 사용
GTX 1070 (8GB VRAM) 최적화

기존 CodeXGLUE (C/C++만) → 다중 언어 지원으로 업그레이드
"""

import os
import torch
import numpy as np
import evaluate
from datasets import load_dataset
from transformers import (
    RobertaTokenizer,
    RobertaForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
    EarlyStoppingCallback
)

# === Configuration (GTX 1070 최적화) ===
BASE_MODEL = "microsoft/codebert-base"
DATA_PATH = "./data/circl_processed/detection.jsonl"
OUTPUT_DIR = "./redeye-detection-model-v2"
MAX_LENGTH = 256         # 1070에선 512는 OOM 위험 → 256 사용
BATCH_SIZE = 8           # 8GB VRAM에 맞춤
GRAD_ACCUM = 2           # 실효 배치 = 16
EPOCHS = 5
LEARNING_RATE = 2e-5
EVAL_SPLIT = 0.1         # 10% validation


def compute_metrics(eval_pred):
    """Accuracy + F1 계산."""
    load_accuracy = evaluate.load("accuracy")
    load_f1 = evaluate.load("f1")
    
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    
    accuracy = load_accuracy.compute(predictions=predictions, references=labels)["accuracy"]
    f1 = load_f1.compute(predictions=predictions, references=labels)["f1"]
    
    return {"accuracy": accuracy, "f1": f1}


def train():
    print(f"🚀 Detection Model v2 학습 시작")
    print(f"  Base: {BASE_MODEL}")
    print(f"  Data: {DATA_PATH}")
    print(f"  GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    
    # 1. 데이터 로드 (JSONL)
    print("📥 Loading preprocessed detection data...")
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    print(f"  Total samples: {len(dataset)}")
    
    # Label 분포 확인
    labels = dataset["label"]
    print(f"  SAFE: {labels.count(0)}, VULNERABLE: {labels.count(1)}")
    
    # Train/Eval 분할
    split = dataset.train_test_split(test_size=EVAL_SPLIT, seed=42)
    print(f"  Train: {len(split['train'])}, Eval: {len(split['test'])}")
    
    # 2. Tokenizer
    print("📝 Loading tokenizer...")
    tokenizer = RobertaTokenizer.from_pretrained(BASE_MODEL)
    
    def tokenize_function(examples):
        return tokenizer(
            examples["code"],
            padding="max_length",
            truncation=True,
            max_length=MAX_LENGTH
        )
    
    print("⏳ Tokenizing...")
    tokenized = split.map(tokenize_function, batched=True, remove_columns=["code", "language"])
    
    # 3. Model
    print("🧠 Loading model...")
    model = RobertaForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=2,
        problem_type="single_label_classification"
    )
    
    # 4. Training Arguments (GTX 1070 최적화)
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
        logging_dir='./logs/detection_v2',
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        fp16=torch.cuda.is_available(),  # GTX 1070: FP16 지원
        dataloader_num_workers=2,
        report_to="none",  # wandb 등 비활성화
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )
    
    # 5. Train
    print("🔥 Training started...")
    trainer.train()
    
    # 6. Save
    print(f"💾 Saving model to {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # 7. Final eval
    results = trainer.evaluate()
    print(f"\n📊 Final Results:")
    print(f"  Accuracy: {results['eval_accuracy']:.4f}")
    print(f"  F1 Score: {results['eval_f1']:.4f}")
    print("✅ Detection Model v2 학습 완료!")


if __name__ == "__main__":
    train()
