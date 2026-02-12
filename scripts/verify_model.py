from transformers import RobertaForSequenceClassification, RobertaTokenizer
import torch
import torch.nn.functional as F
from datasets import load_dataset
import random

MODEL_PATH = "./redeye-detection-model"

def verify():
    print(f"🚀 Loading model from {MODEL_PATH}...")
    try:
        model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
        tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        print(f"✅ Model loaded on {device}")
        
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return

    print("⏳ Loading dataset (to get REAL samples)...")
    try:
        dataset = load_dataset("code_x_glue_cc_defect_detection", trust_remote_code=True)
    except:
        dataset = load_dataset("code_x_glue_cc_defect_detection")

    test_data = dataset["test"]

    # Pick 2 Safe (False) and 2 Vulnerable (True) samples
    safe_samples = [x for x in test_data if x["target"] == False][:2]
    vuln_samples = [x for x in test_data if x["target"] == True][:2]
    
    samples = safe_samples + vuln_samples

    print("\n🔍 Running Verification on REAL Dataset Samples...\n")
    
    for i, sample in enumerate(samples):
        code = sample["func"]
        true_label = "🔴 VULNERABLE" if sample["target"] else "🟢 SAFE"
        
        inputs = tokenizer(code, return_tensors="pt", truncation=True, max_length=512).to(device)
        
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = F.softmax(logits, dim=-1)
            prediction = torch.argmax(probs, dim=-1).item()
            
        pred_label = "🔴 VULNERABLE" if prediction == 1 else "🟢 SAFE"
        confidence = probs[0][prediction].item() * 100
        
        # Check if correct
        status = "✅ CORRECT" if true_label == pred_label else "❌ WRONG"
        
        print(f"📝 Sample {i+1} (True: {true_label})")
        print(f"🔹 Code Start: {code[:100].replace(chr(10), ' ')}...")
        print(f"🤖 Prediction: {pred_label} (Confidence: {confidence:.2f}%) -> {status}")
        print("-" * 30)

if __name__ == "__main__":
    verify()
