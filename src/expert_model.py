from transformers import RobertaForSequenceClassification, RobertaTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import torch.nn.functional as F
from .config import settings

class ExpertModel:
    def __init__(self):
        # Detection Model (CodeBERT)
        self.detect_model = None
        self.detect_tokenizer = None
        
        # Repair Model (T5-Small + LoRA)
        self.repair_model = None
        self.repair_tokenizer = None
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.load_error = None

    def _load_quantized_model(self, model_class, model_name_or_path, is_seq2seq=False):
        """
        Helper to load a quantized model (Linear layers quantized to Int8).
        Strategy:
        1. Load Config & Tokenizer (Normal)
        2. Initialize Base Model (Float32) on CPU
        3. Apply Dynamic Quantization Structure (Float32 -> Int8 structure, still empty weights)
        4. Load Quantized State Dict
        """
        try:
            print(f"🚀 Loading Quantized Model from {model_name_or_path}...")
            
            # 1. Download/Cache model if it's a Repo ID
            # We use the tokenizer loading to ensure the folder is cached or use snapshot_download
            # But simpler: use from_pretrained to get config, then init model
            
            # Load Config
            from transformers import AutoConfig
            config = AutoConfig.from_pretrained(model_name_or_path, token=settings.HF_TOKEN)
            
            # Load Tokenizer
            if is_seq2seq:
                tokenizer = AutoTokenizer.from_pretrained("t5-small", token=settings.HF_TOKEN) 
            else:
                tokenizer = RobertaTokenizer.from_pretrained(model_name_or_path, token=settings.HF_TOKEN)

            # 2. Init Base Model (Empty/Random weights)
            # This is lightweight because we don't load the full float32 weights from hub, just init structure
            # Note: We can't use from_pretrained because it tries to load weights. We use from_config.
            with torch.device("meta"):
                 # Meta device avoids allocating memory for initial weights, but quantize_dynamic might need real CPU tensors
                 # Let's stick to CPU for safety, it's small enough (skeleton)
                 pass
            
            model = model_class(config)
            
            # 3. Apply Quantization Structure
            # We must apply the EXACT same quantization as we did during saving
            torch.quantization.quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8, inplace=True
            )
            
            # 4. Load State Dict
            # We need to find the local path of the pytorch_model.bin
            from huggingface_hub import hf_hub_download
            bin_path = hf_hub_download(repo_id=model_name_or_path, filename="pytorch_model.bin", token=settings.HF_TOKEN)
            
            state_dict = torch.load(bin_path, map_location="cpu")
            model.load_state_dict(state_dict)
            
            model.to(self.device)
            model.eval()
            print(f"✅ Quantized Model Loaded: {model_name_or_path}")
            return model, tokenizer

        except Exception as e:
            print(f"❌ Failed to load Quantized Model {model_name_or_path}: {e}")
            raise e

    def load_detection_model(self):
        """Load the detection model (Quantized)."""
        if self.detect_model and self.detect_tokenizer:
            return 

        try:
            self.detect_model, self.detect_tokenizer = self._load_quantized_model(
                RobertaForSequenceClassification, 
                settings.DETECTION_MODEL_PATH
            )
        except Exception as e:
             self.load_error = f"Detection: {str(e)}"
             self.detect_model = None

    def load_repair_model(self):
        """Load the repair model (Quantized)."""
        if self.repair_model and self.repair_tokenizer:
            return 

        try:
            self.repair_model, self.repair_tokenizer = self._load_quantized_model(
                AutoModelForSeq2SeqLM, 
                settings.REPAIR_MODEL_PATH,
                is_seq2seq=True
            )
        except Exception as e:
            self.load_error = f"Repair: {str(e)}"
            self.repair_model = None

    def verify(self, code_snippet: str) -> dict:
        """
        Verify if code is SAFE or VULNERABLE.
        """
        # Lazy Load
        if not self.detect_model or not self.detect_tokenizer:
            self.load_detection_model()
            
        if not self.detect_model or not self.detect_tokenizer:
            return {"label": "ERROR", "confidence": 0.0, "error": f"Model load failed: {self.load_error}"}

        try:
            inputs = self.detect_tokenizer(code_snippet, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            
            with torch.no_grad():
                logits = self.detect_model(**inputs).logits
                probs = F.softmax(logits, dim=-1)
                prediction = torch.argmax(probs, dim=-1).item()
                
            label = "VULNERABLE" if prediction == 1 else "SAFE"
            confidence = probs[0][prediction].item()
            
            return {
                "label": label,
                "confidence": confidence
            }
        except Exception as e:
            return {"label": "ERROR", "confidence": 0.0, "error": f"Inference failed: {str(e)}"}

    def repair(self, vulnerable_code: str) -> str:
        """
        Generate a fix for vulnerable code.
        """
        # Lazy Load
        if not self.repair_model or not self.repair_tokenizer:
            self.load_repair_model()
            
        if not self.repair_model or not self.repair_tokenizer:
            return f"Error: Repair model not loaded. Reason: {self.load_error}"

        try:
            input_text = f"fix vulnerability: {vulnerable_code}"
            inputs = self.repair_tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512).to(self.device)

            with torch.no_grad():
                outputs = self.repair_model.generate(
                    **inputs,
                    max_length=128,
                    num_beams=5,
                    early_stopping=True,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=2
                )
            
            fix = self.repair_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return fix
        except Exception as e:
            return f"Error during generation: {str(e)}"

expert_model = ExpertModel()
