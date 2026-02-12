# REPAIR MODEL TRAINING SCRIPT (Phase 2)
# Strategy: Hybrid (Curation + LoRA)
# Model: Salesforce/codet5-small (Encoder-Decoder for Code Generation)
# Dataset: CyberNative/Code_Vulnerability_Security_DPO (Filtered for Top 10 Languages)

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import get_peft_config, PeftModel, PeftConfig, get_peft_model, LoraConfig, TaskType

# Configuration
BASE_MODEL_NAME = "t5-small" # Very stable, standard T5 (similar size) used as fallback
OUTPUT_DIR = "./redeye-repair-model"
DATASET_NAME = "CyberNative/Code_Vulnerability_Security_DPO"
TARGET_LANGUAGES = ["python", "javascript", "java", "cpp", "csharp", "c", "typescript", "php", "go", "rust"] # Top 10ish

def filter_fn(example):
    return True 

def train():
    print(f"🚀 Starting Repair Model Training...")
    print(f"model: {BASE_MODEL_NAME}")
    print(f"dataset: {DATASET_NAME} (Streaming Mode)")

    # 1. Load Tokenizer & Model
    # Use standard AutoTokenizer for T5
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME) 
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL_NAME)

    # 2. Configure LoRA (Low-Rank Adaptation)
    # Target modules for T5: q, v (attention)
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

    # 3. Load Dataset (Streaming)
    # We use the DPO dataset but treat it as SFT (Supervised Fine-Tuning)
    # Input: 'prompt' (Vulnerable Code) -> Output: 'chosen' (Fixed Code)
    dataset = load_dataset(DATASET_NAME, split="train", streaming=True)
    
    # Take a sample for training to respect disk/time (Curated Subset Strategy)
    # Let's take 10,000 examples
    dataset = dataset.take(2000) 

    def preprocess_function(examples):
        inputs = examples["question"] # Contains description + vulnerable code
        targets = examples["chosen"]  # Contains fixed code
        
        # Format for T5: "fix vulnerability: <code...>"
        model_inputs = tokenizer(
            ["fix vulnerability: " + inp for inp in inputs], 
            max_length=512, 
            truncation=True,
            padding="max_length"
        )
        labels = tokenizer(
            targets, 
            max_length=512, 
            truncation=True, 
            padding="max_length"
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    # Apply processing
    # Note: 'map' with batched=True on streaming dataset returns an iterable
    # We need to wrap it specifically for Trainer or use a custom loop.
    # For simplicity with Trainer, we might need a non-streaming subset if possible,
    # OR use `max_steps` with an IterableDataset.
    
    # Let's convert the streamed subset to a standard dataset for Trainer compatibility
    # since 2000 examples is small enough for RAM (~5MB).
    print("📥 Downloading 2000 examples to memory...")
    data_list = list(dataset)
    from datasets import Dataset
    train_dataset = Dataset.from_list(data_list)
    
    tokenized_dataset = train_dataset.map(preprocess_function, batched=True)

    # 4. Training Arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        learning_rate=1e-3,
        per_device_train_batch_size=4, # Adjust based on VRAM
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        weight_decay=0.01,
        save_strategy="epoch",
        logging_steps=10,
        fp16=torch.cuda.is_available(), # Use Mixed Precision if GPU
        push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
    )

    # 5. Train
    print("🔥 Training started...")
    trainer.train()

    # 6. Save Adapter
    print(f"💾 Saving adapter to {OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)

if __name__ == "__main__":
    train()
