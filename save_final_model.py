from transformers import RobertaForSequenceClassification, RobertaTokenizer
import os
import shutil

CHECKPOINT_PATH = "./redeye-detection-model/checkpoint-8196"
OUTPUT_DIR = "./redeye-detection-model"

def finalize_save():
    print(f"📥 Loading model from {CHECKPOINT_PATH}...")
    try:
        model = RobertaForSequenceClassification.from_pretrained(CHECKPOINT_PATH)
        tokenizer = RobertaTokenizer.from_pretrained(CHECKPOINT_PATH)
        
        print(f"💾 Saving final model to {OUTPUT_DIR}...")
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        
        print("✅ Success! Model saved to root output directory.")
        
    except Exception as e:
        print(f"❌ Failed to save model: {e}")

if __name__ == "__main__":
    if os.path.exists(CHECKPOINT_PATH):
        finalize_save()
    else:
        print(f"❌ Checkpoint not found at {CHECKPOINT_PATH}")
