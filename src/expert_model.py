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

    def load_detection_model(self):
        """Load only the detection model."""
        if self.detect_model and self.detect_tokenizer:
            return # Already loaded

        try:
            print(f"🚀 Loading Detection Model from {settings.DETECTION_MODEL_PATH}...")
            self.detect_model = RobertaForSequenceClassification.from_pretrained(settings.DETECTION_MODEL_PATH, token=settings.HF_TOKEN)
            self.detect_tokenizer = RobertaTokenizer.from_pretrained(settings.DETECTION_MODEL_PATH, token=settings.HF_TOKEN)
            
            # Dynamic Quantization (Float32 -> Int8) to save memory
            print("📉 Quantizing Detection Model (Dynamic Int8)...")
            self.detect_model = torch.quantization.quantize_dynamic(
                self.detect_model, {torch.nn.Linear}, dtype=torch.qint8
            )
            
            self.detect_model.to(self.device)
            # self.detect_model.eval() # Quantized model is already in eval mode mostly, but good practice.
            print("✅ Detection Model Loaded & Quantized")
        except Exception as e:
            print(f"❌ Failed to load Detection Model: {e}")
            self.load_error = f"Detection: {str(e)}"
            self.detect_model = None
            self.detect_tokenizer = None

    def load_repair_model(self):
        """Load only the repair model."""
        if self.repair_model and self.repair_tokenizer:
            return # Already loaded

        try:
            print(f"🚀 Loading Repair Model from {settings.REPAIR_MODEL_PATH}...")
            # T5-small adapter
            self.repair_model = AutoModelForSeq2SeqLM.from_pretrained(settings.REPAIR_MODEL_PATH, token=settings.HF_TOKEN)
            self.repair_tokenizer = AutoTokenizer.from_pretrained(settings.REPAIR_BASE_MODEL, token=settings.HF_TOKEN)
            
            # Dynamic Quantization (Float32 -> Int8) to save memory
            print("📉 Quantizing Repair Model (Dynamic Int8)...")
            self.repair_model = torch.quantization.quantize_dynamic(
                self.repair_model, {torch.nn.Linear}, dtype=torch.qint8
            )
            
            self.repair_model.to(self.device)
            # self.repair_model.eval()
            print("✅ Repair Model Loaded & Quantized")
        except Exception as e:
            print(f"❌ Failed to load Repair Model: {e}")
            self.load_error = f"Repair: {str(e)}"
            self.repair_model = None
            self.repair_tokenizer = None

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
