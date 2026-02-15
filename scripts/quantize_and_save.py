import os
import torch
import shutil
from transformers import (
    RobertaForSequenceClassification, 
    RobertaTokenizer, 
    AutoModelForSeq2SeqLM, 
    AutoTokenizer,
    T5Tokenizer
)
from peft import PeftModel
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Config (Force Local Paths for safety)
DETECTION_LOCAL = "./redeye-detection-model-v2"
REPAIR_LOCAL = "./redeye-repair-model-v4"
HF_TOKEN = os.getenv("HF_TOKEN")
OUTPUT_DIR = "./quantized_models"

def quantize_detection():
    print(f"\n🚀 [Detection Model] Loading from {DETECTION_LOCAL}...")
    try:
        # 1. Load Model
        model = RobertaForSequenceClassification.from_pretrained(DETECTION_LOCAL, token=HF_TOKEN)
        
        # 2. Load Tokenizer (Robust fallback to base model name)
        print("   - Loading Tokenizer...")
        try:
            # Try loading from local first
            tokenizer = RobertaTokenizer.from_pretrained(DETECTION_LOCAL, token=HF_TOKEN)
        except Exception:
            print("   - ⚠️ Local tokenizer load failed, falling back to 'microsoft/codebert-base'")
            tokenizer = RobertaTokenizer.from_pretrained("microsoft/codebert-base", token=HF_TOKEN)
        
        # 3. Quantize
        print("📉 Quantizing (Dynamic Int8)...")
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        save_path = f"{OUTPUT_DIR}/redeye-detection-quantized-v2"
        os.makedirs(save_path, exist_ok=True)
        
        print(f"💾 Saving to {save_path}...")
        torch.save(quantized_model.state_dict(), f"{save_path}/pytorch_model.bin")
        model.config.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        print("✅ Detection Model Quantized & Saved!")
        
    except Exception as e:
        print(f"❌ Detection Error: {e}")

def quantize_repair():
    print(f"\n🚀 [Repair Model] Loading Adapter from {REPAIR_LOCAL}...")
    try:
        # 1. Load Base Model (CodeT5-small)
        print("   - Loading Base Model (Salesforce/codet5-small)...")
        base_model = AutoModelForSeq2SeqLM.from_pretrained("Salesforce/codet5-small", token=HF_TOKEN)
        
        # 2. Load Tokenizer (Multiple fallbacks for TypeErrors/SentencePiece issues)
        print("   - Loading Tokenizer...")
        tokenizer = None
        try:
            # Try RobertaTokenizer directly (CodeT5 uses this)
            tokenizer = RobertaTokenizer.from_pretrained("Salesforce/codet5-small", token=HF_TOKEN)
        except Exception:
            try:
                # Try AutoTokenizer with fast disabled
                tokenizer = AutoTokenizer.from_pretrained("Salesforce/codet5-small", token=HF_TOKEN, use_fast=False)
            except Exception:
                # Global fallback to t5-small if all else fails
                print("   - ⚠️ CodeT5 tokenizer failed, using 't5-small' fallback")
                tokenizer = T5Tokenizer.from_pretrained("t5-small", token=HF_TOKEN)

        # 3. Load Adapter & Merge
        print(f"   - Merging Adaptor weights...")
        model = PeftModel.from_pretrained(base_model, REPAIR_LOCAL, token=HF_TOKEN)
        model = model.merge_and_unload()
        print("   - ✅ Merge Complete!")

        # 4. Quantize
        print("📉 Quantizing (Dynamic Int8)...")
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        save_path = f"{OUTPUT_DIR}/redeye-repair-quantized-v2"
        if os.path.exists(save_path):
            shutil.rmtree(save_path)
        os.makedirs(save_path, exist_ok=True)
        
        print(f"💾 Saving to {save_path}...")
        torch.save(quantized_model.state_dict(), f"{save_path}/pytorch_model.bin")
        model.config.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        print("✅ Repair Model Quantized & Saved!")

    except Exception as e:
        print(f"❌ Repair Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    quantize_detection()
    quantize_repair()
    print("\n✨ All Done. Now you can use upload_models.py to upload the 'quantized_models' folder.")
