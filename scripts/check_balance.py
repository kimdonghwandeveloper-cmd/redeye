from datasets import load_dataset
import pandas as pd
from collections import Counter

def check_balance():
    print("⏳ Loading dataset...")
    try:
        dataset = load_dataset("code_x_glue_cc_defect_detection", trust_remote_code=True)
    except:
        dataset = load_dataset("code_x_glue_cc_defect_detection")
        
    print("✅ Dataset loaded.")
    
    train_labels = dataset["train"]["target"]
    test_labels = dataset["test"]["target"]
    
    print("\n📊 Training Set Balance:")
    print(Counter(train_labels))
    
    print("\n📊 Test Set Balance:")
    print(Counter(test_labels))
    
    # Check what 0 and 1 represent (usually documented, but let's check a sample)
    print("\n🔍 Sample Inspection:")
    for i in range(5):
        print(f"Label: {train_labels[i]} | Code Snippet: {dataset['train'][i]['func'][:50]}...")

if __name__ == "__main__":
    check_balance()
