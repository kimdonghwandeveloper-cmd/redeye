from datasets import load_dataset

DATASET_NAME = "CyberNative/Code_Vulnerability_Security_DPO"
print(f"🔍 Inspecting dataset: {DATASET_NAME}")

ds = load_dataset(DATASET_NAME, split="train", streaming=True)

# For streaming dataset, we can't get length without iterating, but we can check info.
# Or load first N to guess structure.
print("Dataset loaded in streaming mode.")
# Try to get dataset info from HF Hub metadata if available
try:
    info = load_dataset(DATASET_NAME, split="train", streaming=False).num_rows
    print(f"Total Rows (Train): {info}")
except Exception as e:
    print(f"Could not key total rows directly: {e}")

example = next(iter(ds))
print("Keys found:", example.keys())
