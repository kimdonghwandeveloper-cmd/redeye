import os
import torch
import shutil
from transformers import RobertaForSequenceClassification, RobertaTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Config (Should match your .env or paths)
DETECTION_MODEL_PATH = os.getenv("DETECTION_MODEL_PATH", "./redeye-detection-model")
REPAIR_MODEL_PATH = os.getenv("REPAIR_MODEL_PATH", "./redeye-repair-model")
HF_TOKEN = os.getenv("HF_TOKEN")

OUTPUT_DIR = "./quantized_models"

def quantize_detection():
    print(f"🚀 Loading Detection Model from {DETECTION_MODEL_PATH}...")
    try:
        model = RobertaForSequenceClassification.from_pretrained(DETECTION_MODEL_PATH, token=HF_TOKEN)
        tokenizer = RobertaTokenizer.from_pretrained(DETECTION_MODEL_PATH, token=HF_TOKEN)
        
        print("📉 Quantizing Detection Model (Dynamic Int8)...")
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        save_path = f"{OUTPUT_DIR}/redeye-detection-quantized"
        os.makedirs(save_path, exist_ok=True)
        
        print(f"💾 Saving to {save_path}...")
        torch.save(quantized_model.state_dict(), f"{save_path}/pytorch_model.bin")
        model.config.save_pretrained(save_path) # Save config
        tokenizer.save_pretrained(save_path)    # Save tokenizer
        print("✅ Detection Model Quantized & Saved!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def quantize_repair():
    print(f"🚀 Loading Repair Model (Adapter) from {REPAIR_MODEL_PATH}...")
    try:
        # 1. Load Base Model (T5-small)
        # We assume the base model is t5-small as per project specs.
        # This gives us a clean slate without any "Unexpected key" warnings.
        print("   - Loading Base Model (t5-small)...")
        base_model = AutoModelForSeq2SeqLM.from_pretrained("t5-small", token=HF_TOKEN)
        tokenizer = AutoTokenizer.from_pretrained("t5-small", token=HF_TOKEN)

        # 2. Load Adapter & Merge
        # Load the adapter from the local path which contains the LoRA weights
        print(f"   - Loading Adapter and Merging from {REPAIR_MODEL_PATH}...")
        try:
             model = PeftModel.from_pretrained(base_model, REPAIR_MODEL_PATH, token=HF_TOKEN)
             model = model.merge_and_unload()
             print("   - ✅ Merge Complete! Model is now standard T5.")
        except Exception as peft_err:
             print(f"   - ⚠️  Merge Failed: {peft_err}")
             print("   - Trying fallback: Loading as standard model...")
             model = AutoModelForSeq2SeqLM.from_pretrained(REPAIR_MODEL_PATH, token=HF_TOKEN)

        # 3. Quantize
        print("📉 Quantizing Repair Model (Dynamic Int8)...")
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        save_path = f"{OUTPUT_DIR}/redeye-repair-quantized"
        # Clear previous directory to ensure no artifacts like adapter_config.json remain
        if os.path.exists(save_path):
            shutil.rmtree(save_path)
        os.makedirs(save_path, exist_ok=True)
        
        print(f"💾 Saving to {save_path}...")
        torch.save(quantized_model.state_dict(), f"{save_path}/pytorch_model.bin")
        model.config.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        print("✅ Repair Model Quantized & Saved!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not HF_TOKEN:
        print("⚠️ Warning: HF_TOKEN not found in env. Private models might fail.")
    
    quantize_detection()
    quantize_repair()
    print("\n✨ All Done. Now you can upload the 'quantized_models' folder to Hugging Face.")
