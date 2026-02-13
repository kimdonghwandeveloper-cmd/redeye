import json
import os
from typing import Dict, List, Any

class TrainingMetricsService:
    def __init__(self, model_checkpoint_path: str):
        self.trainer_state_path = os.path.join(model_checkpoint_path, "trainer_state.json")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Reads trainer_state.json and formats it for frontend visualization.
        """
        if not os.path.exists(self.trainer_state_path):
            return {"error": "Model training logs not found.", "path": self.trainer_state_path}

        try:
            with open(self.trainer_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            log_history = data.get("log_history", [])
            
            # Process history: Separate training loss from eval metrics
            formatted_history = []
            
            # We want to align training loss and eval metrics by epoch or step
            # HuggingFace logs them separately usually.
            
            # Strategy: Create a dictionary keyed by epoch (rounded) or step to merge them
            # But simpler for charts: Just return the raw list and let frontend filter?
            # Better: Return two separate series or a merged series if steps align.
            
            # Let's return a clean list of data points
            # Each point: { step, epoch, loss, eval_loss, eval_accuracy, eval_f1 }
            
            metrics_by_step = {}

            for entry in log_history:
                step = entry.get("step")
                if step not in metrics_by_step:
                    metrics_by_step[step] = {"step": step, "epoch": entry.get("epoch")}
                
                if "loss" in entry:
                    metrics_by_step[step]["loss"] = entry["loss"]
                
                if "eval_loss" in entry:
                    metrics_by_step[step]["eval_loss"] = entry["eval_loss"]
                    metrics_by_step[step]["eval_accuracy"] = entry["eval_accuracy"]
                    metrics_by_step[step]["eval_f1"] = entry["eval_f1"]

            # Sort by step
            sorted_history = sorted(metrics_by_step.values(), key=lambda x: x["step"])

            return {
                "history": sorted_history,
                "best_metric": data.get("best_metric"),
                "total_epochs": data.get("num_train_epochs")
            }

        except Exception as e:
            return {"error": str(e)}

# Determine path relative to this file
# src/services/training_metrics.py -> src/data/trainer_state.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # src/
DEFAULT_CHECKPOINT_PATH = os.path.join(BASE_DIR, "data")
training_metrics_service = TrainingMetricsService(DEFAULT_CHECKPOINT_PATH)
