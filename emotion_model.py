"""Handles loading the Hugging Face Vision Transformer model and running emotion inference."""
import cv2
import numpy as np
from PIL import Image
from transformers import pipeline

MOODS = ["Happy 😄", "Sad 😢", "Angry 😠", "Surprised 😲", "Fearful 😨", "Neutral 😐"]

MODEL_ID = "trpakov/vit-face-expression"

# Fallback for models whose config only exposes LABEL_0..LABEL_6 (e.g. abhilash88/face-emotion-detection,
# whose model card gives this order). trpakov/vit-face-expression already returns named labels.
FER_LABELS = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

# Each emotion maps to its own mood so the music mirrors how the user feels.
# Disgust is folded into Angry: it is rare in FER training data (~1.5%), unreliable,
# and most often confused with angry.
FER_TO_MOOD = {
    "happy": "Happy 😄",
    "sad": "Sad 😢",
    "angry": "Angry 😠",
    "disgust": "Angry 😠",
    "surprise": "Surprised 😲",
    "fear": "Fearful 😨",
    "neutral": "Neutral 😐",
}

print("Loading facial emotion recognition model...")
emotion_pipeline = pipeline("image-classification", model=MODEL_ID)
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def decode_label(label: str) -> str:
    """Turn 'LABEL_3' into 'Happy' and 'happy' into 'Happy'."""
    if label.upper().startswith("LABEL_"):
        return FER_LABELS[int(label.split("_")[1])]
    return label.capitalize()


def crop_face(image: Image.Image, margin: float = 0.25) -> tuple[Image.Image, bool]:
    """Crop to the largest detected face (plus some margin). Falls back to the full frame."""
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return image, False

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    pad_w, pad_h = int(w * margin), int(h * margin)
    box = (
        max(x - pad_w, 0),
        max(y - pad_h, 0),
        min(x + w + pad_w, image.width),
        min(y + h + pad_h, image.height),
    )
    return image.crop(box), True


def predict_emotion(image: Image.Image) -> dict:
    """Takes a PIL image, crops the face, runs inference, and maps the model's output to app moods."""
    face, face_found = crop_face(image)
    predictions = emotion_pipeline(face)

    if not predictions:
        return {"detected": None, "confidence": 0.0, "raw_predictions": [], "face_detected": face_found}

    # Pipeline output is sorted by score: [{'label': 'LABEL_3', 'score': 0.92}, ...]
    predictions = [{"label": decode_label(p["label"]), "score": float(p["score"])} for p in predictions]
    top_pred = predictions[0]

    return {
        "detected": FER_TO_MOOD.get(top_pred["label"].lower(), "Neutral 😐"),
        "raw_label": top_pred["label"],
        "confidence": round(top_pred["score"], 2),
        "raw_predictions": predictions[:3],  # Top 3 for UI debugging
        "face_detected": face_found,
    }
