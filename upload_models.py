
import os
from huggingface_hub import HfApi, login

def upload_models():
    print("🚀 RedEye Model Uploader")
    print("This script will upload your local models to Hugging Face.")
    
    # 1. Login Logic
    # Use HF_TOKEN env var if available, otherwise try to load from local cache
    token = os.getenv("HF_TOKEN")
    if token:
        print("🔑 Using HF_TOKEN from environment variable.")
        login(token=token)
    else:
        print("ℹ️ No HF_TOKEN env var found. Trying to use local credentials...")
        # HfApi() will automatically use stored token if available

    try:
        api = HfApi()
        user_info = api.whoami(token=token)
        username = user_info['name']
        print(f"✅ Logged in as: {username}")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("👉 Please run 'huggingface-cli login' in your terminal or set HF_TOKEN environment variable.")
        return

    # 2. Define Models to Upload
    models = [
        # Full Models
        {
            "local_path": "./redeye-detection-model-v2",
            "repo_name": "redeye-detection-model-v2",
            "type": "model"
        },
        {
            "local_path": "./redeye-repair-model-v4",
            "repo_name": "redeye-repair-model-v4",
            "type": "model"
        },
        # Quantized Models
        {
            "local_path": "./quantized_models/redeye-detection-quantized-v2",
            "repo_name": "redeye-detection-quantized-v2",
            "type": "model"
        },
        {
            "local_path": "./quantized_models/redeye-repair-quantized-v2",
            "repo_name": "redeye-repair-quantized-v2",
            "type": "model"
        }
    ]

    # 3. Upload Loop
    for model in models:
        repo_id = f"{username}/{model['repo_name']}"
        local_path = model['local_path']
        
        if not os.path.exists(local_path):
            print(f"⚠️ Skipping {repo_id}: Local path '{local_path}' not found.")
            continue

        print(f"\n📦 Uploading {local_path} -> {repo_id}...")
        
        try:
            # Create Repo if not exists
            api.create_repo(repo_id=repo_id, exist_ok=True, repo_type=model['type'])
            
            # Upload Folder
            api.upload_folder(
                folder_path=local_path,
                repo_id=repo_id,
                repo_type=model['type'],
                ignore_patterns=["checkpoint-*", "*.git*", "__pycache__"]
            )
            print(f"✅ Successfully uploaded to: https://huggingface.co/{repo_id}")
        except Exception as e:
            print(f"❌ Failed to upload {repo_id}: {e}")

    print("\n🎉 All done! Now update your REDEYE backend config.")
    print(f"Originals:")
    print(f"  DETECTION_MODEL = {username}/redeye-detection-model-v2")
    print(f"  REPAIR_MODEL = {username}/redeye-repair-model-v4")
    print(f"Quantized (for Production):")
    print(f"  DETECTION_MODEL_QUANTIZED = {username}/redeye-detection-quantized-v2")
    print(f"  REPAIR_MODEL_QUANTIZED = {username}/redeye-repair-quantized-v2")

if __name__ == "__main__":
    upload_models()
