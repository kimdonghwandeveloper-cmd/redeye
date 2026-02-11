import os
from datasets import load_dataset, Value
from transformers import (
    RobertaTokenizer, 
    RobertaForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    DataCollatorWithPadding
)
import numpy as np
import evaluate

# 1. Configuration
MODEL_NAME = "microsoft/codebert-base"
OUTPUT_DIR = "./redeye-detection-model"
MAX_LENGTH = 512  # CodeBERT context window
EPOCHS = 3
BATCH_SIZE = 8

def compute_metrics(eval_pred):
    load_accuracy = evaluate.load("accuracy")
    load_f1 = evaluate.load("f1")
    
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    
    accuracy = load_accuracy.compute(predictions=predictions, references=labels)["accuracy"]
    f1 = load_f1.compute(predictions=predictions, references=labels)["f1"]
    
    return {"accuracy": accuracy, "f1": f1}

def train():
    print(f"🚀 Preparing to fine-tune {MODEL_NAME} on CodeXGLUE (Devign)...")
    
    # 2. Load Dataset (Using a small subset for demo if needed, but here we load full train/test)
    # devign is a subset of code_x_glue_cc_defect_detection
    try:
        dataset = load_dataset("code_x_glue_cc_defect_detection", trust_remote_code=True)
    except ValueError:
        print("⚠️ trust_remote_code failed, trying without it...")
        dataset = load_dataset("code_x_glue_cc_defect_detection")
    
    # 3. Preprocessing
    # Rename target column to labels for Trainer compatibility
    if "target" in dataset["train"].column_names:
        dataset = dataset.rename_column("target", "labels")
    
    # Ensure labels are integers for CrossEntropyLoss
    # Use cast_column to enforce int64 schema
    try:
        dataset = dataset.cast_column("labels", Value("int64"))
    except Exception as e:
        print(f"⚠️ cast_column failed: {e}. Trying manual map...")
        dataset = dataset.map(lambda x: {"labels": int(x["labels"])})
        
    print(f"✅ Dataset Loaded: {dataset}")
    print(f"📊 Columns: {dataset['train'].column_names}")
    print(f"🔍 Sample Label: {dataset['train'][0]['labels']}")

    tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)

    def tokenize_function(examples):
        # The column name is 'func' for the code snippet
        return tokenizer(
            examples["func"], 
            padding="max_length", 
            truncation=True, 
            max_length=MAX_LENGTH
        )

    print("⏳ Tokenizing dataset...")
    tokenized_datasets = dataset.map(tokenize_function, batched=True)
    
    # Select small subset for quick verification if getting Started
    # tokenized_datasets["train"] = tokenized_datasets["train"].select(range(1000)) 
    # tokenized_datasets["test"] = tokenized_datasets["test"].select(range(100))

    # 4. Model Setup
    model = RobertaForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=2,
        problem_type="single_label_classification" # Force CrossEntropyLoss
    )
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=EPOCHS,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        # fp16=True, # Enable if GPU supports it
        # push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )

    # 5. Train
    print("🔥 Starting Training...")
    trainer.train()
    
    # 6. Save
    print(f"💾 Saving model to {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("✅ Training Complete!")

if __name__ == "__main__":
    train()
