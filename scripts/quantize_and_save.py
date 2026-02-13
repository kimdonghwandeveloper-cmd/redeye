import os
import torch
import shutil
from transformers import RobertaForSequenceClassification, RobertaTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer
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
    print(f"🚀 Loading Repair Model from {REPAIR_MODEL_PATH}...")
    try:
        model = AutoModelForSeq2SeqLM.from_pretrained(REPAIR_MODEL_PATH, token=HF_TOKEN)
        tokenizer = AutoTokenizer.from_pretrained("t5-small", token=HF_TOKEN) # T5 base tokenizer
        
        print("📉 Quantizing Repair Model (Dynamic Int8)...")
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        save_path = f"{OUTPUT_DIR}/redeye-repair-quantized"
        os.makedirs(save_path, exist_ok=True)
        
        print(f"💾 Saving to {save_path}...")
        torch.save(quantized_model.state_dict(), f"{save_path}/pytorch_model.bin")
        model.config.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        print("✅ Repair Model Quantized & Saved!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if not HF_TOKEN:
        print("⚠️ Warning: HF_TOKEN not found in env. Private models might fail.")
    
    quantize_detection()
    quantize_repair()
    print("\n✨ All Done. Now you can upload the 'quantized_models' folder to Hugging Face.")
