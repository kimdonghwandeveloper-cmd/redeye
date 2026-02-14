from typing import Dict, Optional, Tuple, Any, Union
from transformers import RobertaForSequenceClassification, RobertaTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import torch.nn.functional as F
from .config import settings
import logging

# Configure Logging
logger = logging.getLogger(__name__)

class ExpertModel:
    """
    ExpertModel serves as the central AI engine for RedEye.
    It manages the loading and inference of two specialized models:
    1. Detection Model (CodeBERT): Classifies code as SAFE or VULNERABLE.
    2. Repair Model (T5-Small + LoRA): Generates fixes for vulnerable code.
    
    Resource Management:
    - Uses lazy loading to save memory (models are loaded only when requested).
    - Uses dynamic 8-bit quantization to reduce RAM usage.
    """
    def __init__(self):
        # Detection Model (CodeBERT)
        self.detect_model: Optional[RobertaForSequenceClassification] = None
        self.detect_tokenizer: Optional[RobertaTokenizer] = None
        
        # Repair Model (T5-Small + LoRA)
        self.repair_model: Optional[AutoModelForSeq2SeqLM] = None
        self.repair_tokenizer: Optional[AutoTokenizer] = None
        
        # Hardware Acceleration
        # IMPORTANT: Dynamic quantization does NOT support CUDA!
        # Quantized models MUST run on CPU
        self.device = torch.device("cpu")
        logger.info(f"🖥️ Using device: {self.device} (Quantized models require CPU)")
        self.load_error: Optional[str] = None

    def _load_quantized_model(self, model_class: Any, model_name_or_path: str, is_seq2seq: bool = False) -> Tuple[Any, Any]:
        """
        Helper to load a quantized model (Linear layers quantized to Int8).
        
        Strategy:
        1. Load Config & Tokenizer (Fast & Lightweight)
        2. Initialize Base Model Structure (Float32) on CPU without weights
        3. Apply Dynamic Quantization Structure (Float32 -> Int8 structure)
        4. Load Quantized State Dict (The actual weights)
        """
        try:
            print(f"[DEBUG] Step 1: Starting to load model from: {model_name_or_path}")
            logger.info(f"🚀 Loading Quantized Model from {model_name_or_path}...")
            logger.debug(f"HF_TOKEN set: {bool(settings.HF_TOKEN)}")
            
            # Prepare token (None if empty string)
            hf_token = settings.HF_TOKEN if settings.HF_TOKEN else None
            print(f"[DEBUG] Step 2: Token prepared, HF_TOKEN exists: {bool(hf_token)}")
            
            # 1. Load Config
            from transformers import AutoConfig
            print(f"[DEBUG] Step 3: Loading config from {model_name_or_path}")
            config = AutoConfig.from_pretrained(model_name_or_path, token=hf_token)
            print(f"[DEBUG] Step 4: Config loaded successfully")
            
            # 2. Load Tokenizer
            print(f"[DEBUG] Step 5: Loading tokenizer, is_seq2seq={is_seq2seq}")
            if is_seq2seq:
                tokenizer = AutoTokenizer.from_pretrained("t5-small", token=hf_token) 
            else:
                # Use microsoft/codebert-base tokenizer (stable, well-tested)
                # The custom tokenizer.json in the repo is corrupted
                print(f"[DEBUG] Step 5.5: Using microsoft/codebert-base tokenizer")
                tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base", token=hf_token, use_fast=True)
            print(f"[DEBUG] Step 6: Tokenizer loaded")

            # 3. Init Base Model (Empty/Random weights)
            # This is lightweight because we don't load the full float32 weights from hub.
            print(f"[DEBUG] Step 7: Initializing base model structure")
            with torch.device("meta"):
                 pass # Meta device optimization (skip for now to ensure compatibility)
            
            if "AutoModel" in model_class.__name__:
                 model = model_class.from_config(config)
            else:
                 model = model_class(config)
            print(f"[DEBUG] Step 8: Base model initialized")
            
            # 4. Apply Quantization Structure
            # We must apply the EXACT same quantization as we did during saving
            print(f"[DEBUG] Step 9: Applying quantization")
            model = torch.quantization.quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8
            )
            print(f"[DEBUG] Step 10: Quantization applied")
            
            # 5. Load State Dict
            import os
            print(f"[DEBUG] Step 11: Checking if path is directory: {os.path.isdir(model_name_or_path)}")
            if os.path.isdir(model_name_or_path):
                 bin_path = os.path.join(model_name_or_path, "pytorch_model.bin")
                 print(f"[DEBUG] Step 12a: Using local path: {bin_path}")
            else:
                 from huggingface_hub import hf_hub_download
                 print(f"[DEBUG] Step 12b: Downloading from HuggingFace: {model_name_or_path}")
                 logger.info(f"📥 Downloading from HuggingFace: {model_name_or_path}")
                 bin_path = hf_hub_download(
                     repo_id=model_name_or_path, 
                     filename="pytorch_model.bin", 
                     token=hf_token
                 )
                 print(f"[DEBUG] Step 13: Downloaded to: {bin_path}")
            
            print(f"[DEBUG] Step 14: Loading weights from: {bin_path}")
            logger.info(f"📂 Loading weights from: {bin_path}")
            state_dict = torch.load(bin_path, map_location="cpu")
            print(f"[DEBUG] Step 15: Weights loaded, loading into model")
            model.load_state_dict(state_dict)
            
            model.to(self.device)
            model.eval()
            logger.info(f"✅ Quantized Model Loaded: {model_name_or_path}")
            return model, tokenizer

        except Exception as e:
            logger.error(f"❌ Failed to load Quantized Model {model_name_or_path}: {e}")
            raise e

    def load_detection_model(self):
        """Lazy load the detection model (Quantized)."""
        if self.detect_model and self.detect_tokenizer:
            return 

        try:
            self.detect_model, self.detect_tokenizer = self._load_quantized_model(
                RobertaForSequenceClassification, 
                settings.DETECTION_MODEL_PATH
            )
        except Exception as e:
             self.load_error = f"Detection Model Error: {str(e)}"
             self.detect_model = None

    def load_repair_model(self):
        """Lazy load the repair model (Quantized)."""
        if self.repair_model and self.repair_tokenizer:
            return 

        try:
            self.repair_model, self.repair_tokenizer = self._load_quantized_model(
                AutoModelForSeq2SeqLM, 
                settings.REPAIR_MODEL_PATH,
                is_seq2seq=True
            )
        except Exception as e:
            self.load_error = f"Repair Model Error: {str(e)}"
            self.repair_model = None

    def verify(self, code_snippet: str) -> Dict[str, Union[str, float]]:
        """
        [API Endpoint Helper]
        Analyzes a code snippet to detect security vulnerabilities.

        Args:
            code_snippet (str): The source code to analyze.

        Returns:
            dict: {
                "label": "SAFE" | "VULNERABLE" | "ERROR",
                "confidence": float (0.0 - 1.0),
                "error": str (optional)
            }
        """
        # Lazy Load
        if not self.detect_model or not self.detect_tokenizer:
            self.load_detection_model()
            
        if not self.detect_model or not self.detect_tokenizer:
            return {"label": "ERROR", "confidence": 0.0, "error": f"Model load failed: {self.load_error}"}

        try:
            # Tokenize & Move to Device
            inputs = self.detect_tokenizer(
                code_snippet, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512
            ).to(self.device)
            
            # Inference
            with torch.no_grad():
                logits = self.detect_model(**inputs).logits
                probs = F.softmax(logits, dim=-1)
                prediction = torch.argmax(probs, dim=-1).item()
                
            label = "VULNERABLE" if prediction == 1 else "SAFE"
            confidence = probs[0][prediction].item()
            
            return {
                "label": label,
                "confidence": round(confidence, 4)
            }
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return {"label": "ERROR", "confidence": 0.0, "error": f"Inference failed: {str(e)}"}

    def repair(self, vulnerable_code: str) -> Dict[str, str]:
        """
        [API Endpoint Helper]
        Generates a secure fix for the provided vulnerable code.

        Args:
            vulnerable_code (str): The code that needs fixing.

        Returns:
            dict: {
                "fixed_code": str,
                "error": str (optional)
            }
        """
        # Lazy Load
        if not self.repair_model or not self.repair_tokenizer:
            self.load_repair_model()
            
        if not self.repair_model or not self.repair_tokenizer:
            return {"fixed_code": "", "error": f"Model load failed: {self.load_error}"}

        try:
            input_text = f"fix vulnerability: {vulnerable_code}"
            inputs = self.repair_tokenizer(
                input_text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512
            ).to(self.device)

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
            return {"fixed_code": fix}
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {"fixed_code": "", "error": f"Generation failed: {str(e)}"}

expert_model = ExpertModel()
