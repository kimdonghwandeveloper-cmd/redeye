from datasets import load_dataset
import pandas as pd

def inspect_codexglue():
    print("\n" + "="*50)
    print("🔍 PHASE 1: Detection Dataset (CodeXGLUE/Devign)")
    print("="*50)
    try:
        # CodeXGLUE Defect Detection (Devign subset)
        dataset = load_dataset("code_x_glue_cc_defect_detection", split="train[:3]", trust_remote_code=True)
        
        for item in dataset:
            print(f"\n[Label]: {'🔴 VULNERABLE' if item['target'] == 1 else 'mj SAFE'}")
            print(f"[Code Snippet]:\n{item['func'][:200]}...") # Show first 200 chars
            print("-"*30)
    except Exception as e:
        print(f"Error loading CodeXGLUE: {e}")

def inspect_cybernative():
    print("\n" + "="*50)
    print("🛠️ PHASE 2: Repair Dataset (CyberNative DPO)")
    print("="*50)
    try:
        # CyberNative DPO
        dataset = load_dataset("CyberNative/Code_Vulnerability_Security_DPO", split="train[:2]")
        
        for item in dataset:
            print(f"\n[Question]: {item['question']}")
            print(f"[❌ Rejected (Vulnerable)]:\n{item['rejected'][:200]}...")
            print(f"[✅ Chosen (Fixed)]:\n{item['chosen'][:200]}...")
            print("-"*30)
    except Exception as e:
        print(f"Error loading CyberNative: {e}")

if __name__ == "__main__":
    # Install check is assumed or handled by user
    print("🚀 Loading Datasets for Inspection...\n")
    inspect_codexglue()
    inspect_cybernative()
