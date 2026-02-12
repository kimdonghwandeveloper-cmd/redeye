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

    def load_models(self):
        """Load both detection and repair models from disk."""
        # 1. Load Detection Model
        try:
            print(f"🚀 Loading Detection Model from {settings.DETECTION_MODEL_PATH}...")
            self.detect_model = RobertaForSequenceClassification.from_pretrained(settings.DETECTION_MODEL_PATH)
            self.detect_tokenizer = RobertaTokenizer.from_pretrained(settings.DETECTION_MODEL_PATH)
            self.detect_model.to(self.device)
            self.detect_model.eval()
            print("✅ Detection Model Loaded")
        except Exception as e:
            print(f"❌ Failed to load Detection Model: {e}")

        # 2. Load Repair Model
        try:
            print(f"🚀 Loading Repair Model from {settings.REPAIR_MODEL_PATH}...")
            # T5-small adapter
            self.repair_model = AutoModelForSeq2SeqLM.from_pretrained(settings.REPAIR_MODEL_PATH)
            self.repair_tokenizer = AutoTokenizer.from_pretrained(settings.REPAIR_BASE_MODEL)
            self.repair_model.to(self.device)
            self.repair_model.eval()
            print("✅ Repair Model Loaded")
        except Exception as e:
            print(f"❌ Failed to load Repair Model: {e}")

    def verify(self, code_snippet: str) -> dict:
        """
        Verify if code is SAFE or VULNERABLE.
        """
        if not self.detect_model:
            self.load_models()
            if not self.detect_model:
                return {"label": "ERROR", "confidence": 0.0}

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

    def repair(self, vulnerable_code: str) -> str:
        """
        Generate a fix for vulnerable code.
        """
        if not self.repair_model:
            self.load_models()
            if not self.repair_model:
                return "Error: Repair model not loaded."

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

expert_model = ExpertModel()
