
import os
from huggingface_hub import HfApi, login

def upload_models():
    print("🚀 RedEye Model Uploader")
    print("This script will upload your local models to Hugging Face.")
    
    # 1. Login
    token = input("Enter your Hugging Face Write Token (get it from https://huggingface.co/settings/tokens): ").strip()
    if not token:
        print("❌ Token is required.")
        return

    try:
        login(token=token)
        api = HfApi()
        user_info = api.whoami(token=token)
        username = user_info['name']
        print(f"✅ Logged in as: {username}")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # 2. Define Models to Upload
    # 2. Define Models to Upload
    models = [
        {
            "local_path": "./quantized_models/redeye-detection-quantized",
            "repo_name": "redeye-detection-quantized",
            "type": "model"
        },
        {
            "local_path": "./quantized_models/redeye-repair-quantized",
            "repo_name": "redeye-repair-quantized",
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

    print("\n🎉 All done! Now update your Railway variables with these Repo IDs.")
    print(f"1. DETECTION_MODEL_PATH = {username}/redeye-detection-v2")
    print(f"2. REPAIR_MODEL_PATH = {username}/redeye-repair-v2")

if __name__ == "__main__":
    upload_models()
