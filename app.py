"""Flask entry point: serves the UI and exposes the emotion + recommendation APIs."""
import base64
import io

from flask import Flask, jsonify, render_template, request
from PIL import Image

from emotion_model import MOODS, predict_emotion
from music_service import recommend_tracks

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload cap


def decode_data_url(data_url: str) -> Image.Image:
    """Turn a 'data:image/jpeg;base64,...' string from the browser into a PIL image."""
    _, _, encoded = data_url.partition(",")
    return Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")


@app.get("/")
def index():
    return render_template("index.html", moods=MOODS)


@app.post("/api/detect-emotion")
def detect_emotion():
    payload = request.get_json(silent=True) or {}
    if "image" not in payload:
        return jsonify(error="Missing 'image' field"), 400
    try:
        image = decode_data_url(payload["image"])
    except Exception:
        return jsonify(error="Could not decode image"), 400

    result = predict_emotion(image)
    return jsonify(result)


@app.post("/api/recommend")
def recommend():
    payload = request.get_json(silent=True) or {}
    mood = payload.get("mood")
    if mood not in MOODS:
        return jsonify(error=f"Unknown mood. Expected one of {MOODS}"), 400

    tracks = recommend_tracks(mood, limit=5)
    return jsonify(mood=mood, tracks=tracks)


if __name__ == "__main__":
    # localhost counts as a secure context, so the browser will allow webcam access.
    app.run(debug=True, use_reloader=False, port=5000)
