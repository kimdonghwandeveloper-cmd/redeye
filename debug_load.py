import torch
from transformers import RobertaForSequenceClassification, RobertaTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer, AutoConfig
import os

# Config
DETECTION_LOCAL_PATH = "./quantized_models/redeye-detection-quantized"
REPAIR_LOCAL_PATH = "./quantized_models/redeye-repair-quantized"

def load_quantized_local(model_class, local_path, is_seq2seq=False):
    print(f"Testing load from {local_path}...")
    try:
        # 1. Load Config
        config = AutoConfig.from_pretrained(local_path)
        
        # 2. Init Base Model (CPU)
        print("Initialzing base model...")
        if "AutoModel" in model_class.__name__:
             model = model_class.from_config(config)
        else:
             model = model_class(config)
        
        # 3. Apply Quantization Structure
        print("Applying quantization structure...")
        model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        # 4. Load State Dict
        print("Loading state dict...")
        bin_path = os.path.join(local_path, "pytorch_model.bin")
        state_dict = torch.load(bin_path, map_location="cpu")
        
        model.load_state_dict(state_dict)
        print("✅ Load Success!")
        
    except Exception as e:
        print(f"❌ Load Failed: {e}")
        # Debug: Print keys if it's the repair model failure
        if "scale" in str(e) and "state_dict" in locals():
            print("\n🔍 Debugging Keys for failing layer...")
            search_key = "encoder.block.0.layer.0.SelfAttention.q"
            found_keys = [k for k in state_dict.keys() if search_key in k]
            print(f"Keys found for {search_key}:")
            for k in found_keys:
                print(f" - {k}")
            
            # Check module type
            try:
                layer = model.encoder.block[0].layer[0].SelfAttention.q
                print(f"Module Type: {type(layer)}")
            except:
                pass
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("--- Detection Model Test ---")
    if os.path.exists(DETECTION_LOCAL_PATH):
        load_quantized_local(RobertaForSequenceClassification, DETECTION_LOCAL_PATH)
    else:
        print(f"Skipping Detection (path not found: {DETECTION_LOCAL_PATH})")

    print("\n--- Repair Model Test ---")
    if os.path.exists(REPAIR_LOCAL_PATH):
        load_quantized_local(AutoModelForSeq2SeqLM, REPAIR_LOCAL_PATH, is_seq2seq=True)
    else:
        print(f"Skipping Repair (path not found: {REPAIR_LOCAL_PATH})")
