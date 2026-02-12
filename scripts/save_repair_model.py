import torch
from peft import PeftModel, PeftConfig
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os

BASE_MODEL_NAME = "t5-small"
ADAPTER_DIR = "./redeye-repair-model"
MERGED_OUTPUT_DIR = "./redeye-repair-model-merged"

def save_repair_model():
    print("🔄 Loading Base Model and Adapter for verification...")
    
    # 1. Load Base Model
    base_model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
    
    # 2. Load Adapter
    if not os.path.exists(os.path.join(ADAPTER_DIR, "adapter_model.safetensors")) and \
       not os.path.exists(os.path.join(ADAPTER_DIR, "adapter_model.bin")):
        print(f"❌ Adapter not found in {ADAPTER_DIR}. Training might have failed.")
        return

    model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    
    print("✅ Adapter loaded successfully!")
    
    # Option: Merge and Save (If we want a standalone model, but sticking to Adapter saves space)
    # User wanted "Add-on", so keeping it as Adapter is best for disk space (8GB limit).
    # We just verify it works.
    
    test_input = "fix vulnerability: user_input = request.args.get('id'); query = 'SELECT * FROM users WHERE id = ' + user_input"
    inputs = tokenizer(test_input, return_tensors="pt")
    
    print(f"🧪 Testing generation with input: {test_input}")
    # Use better generation parameters to avoid repetition
    outputs = model.generate(
        **inputs, 
        max_length=128,
        num_beams=5,
        early_stopping=True,
        repetition_penalty=1.2,
        no_repeat_ngram_size=2
    )
    print(f"✨ Generated Output: {tokenizer.decode(outputs[0], skip_special_tokens=True)}")
    
    print("✅ Repair Model (LoRA) is ready for use!")

if __name__ == "__main__":
    save_repair_model()
