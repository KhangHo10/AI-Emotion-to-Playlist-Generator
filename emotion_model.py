"""Handles loading the Hugging Face Vision Transformer model and running emotion inference."""
from transformers import pipeline 

MOODS = ["Energetic ⚡", "Relaxed 🍃", "Stressed / Focus 💻", "Happy 🎉"]

print("Loading facial emotion recognition model...")
emotion_pipeline = pipeline("image-classification", model="abhilash88/face-emotion-detection")

def predict_emotion(image) -> dict:
    """Takes a PIL image, run inference, and maps the model's output to app moods."""
    predictions = emotion_pipeline(image)

    if not predictions:
        return {"detected": None, "confidence": 0.0, "raw_predictions": []}


    # Example prediction format from pipeline: [{'label': 'Happy', 'score': 0.92}, ...]

    top_pred = predictions[0]
    raw_label = top_pred["label"].lower()
    confidence = float(top_pred["score"])

    if raw_label in ["happy", "surprise"]:
            mapped_mood = "Happy 🎉"
    elif raw_label in ["angry", "fear"]:
        mapped_mood = "Energetic ⚡"
    elif raw_label == "sad":
        mapped_mood = "Relaxed 🍃"
    else:  # Neutral, Disgust, etc.
        mapped_mood = "Stressed / Focus 💻"

    return {
        "detected": mapped_mood,
        "raw_label": top_pred["label"],
        "confidence": round(confidence, 2),
        "raw_predictions": predictions[:3], # Top 3 for UI debugging
    }
