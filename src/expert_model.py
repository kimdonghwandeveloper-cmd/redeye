from transformers import RobertaForSequenceClassification, RobertaTokenizer
import torch
import torch.nn.functional as F

MODEL_PATH = "./redeye-detection-model"

class ExpertModel:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load_model(self):
        """Load the trained model from disk."""
        print(f"🚀 Loading Expert Model from {MODEL_PATH}...")
        try:
            self.model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
            self.tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
            self.model.to(self.device)
            self.model.eval() # Set to evaluation mode
            print(f"✅ Expert Model loaded on {self.device}")
        except Exception as e:
            print(f"❌ Failed to load Expert Model: {e}")

    def predict(self, code_snippet: str) -> dict:
        """
        Analyze a code snippet and return prediction.
        Returns: { "label": "VULNERABLE"|"SAFE", "confidence": float }
        """
        if not self.model:
            self.load_model()
            if not self.model:
                return {"label": "ERROR", "confidence": 0.0}

        inputs = self.tokenizer(code_snippet, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        
        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = F.softmax(logits, dim=-1)
            prediction = torch.argmax(probs, dim=-1).item()
            
        label = "VULNERABLE" if prediction == 1 else "SAFE"
        confidence = probs[0][prediction].item()
        
        return {
            "label": label,
            "confidence": confidence
        }

expert_model = ExpertModel()
