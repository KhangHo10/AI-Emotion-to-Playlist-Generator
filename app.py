"""Flask entry point: serves the UI and exposes the emotion + recommendation APIs."""
import base64
import io
import os
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request
from PIL import Image
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError

from emotion_model import MOODS, predict_emotion
from music_service import SpotifyNotLoggedIn, login, recommend_tracks, save_playlist

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload cap

PORT = 5000
MAX_PLAYLIST_TRACKS = 10


def decode_data_url(data_url: str) -> Image.Image:
    """Turn a 'data:image/jpeg;base64,...' string from the browser into a PIL image."""
    _, _, encoded = data_url.partition(",")
    return Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")


def spotify_error(err: Exception):
    """Return Spotify failures as JSON so the frontend can show the real message."""
    if isinstance(err, SpotifyNotLoggedIn):
        app.logger.warning(str(err))
        return jsonify(error=str(err)), 401
    if isinstance(err, SpotifyOauthError):
        message = f"Spotify login failed. Are SPOTIPY_CLIENT_ID/SECRET/REDIRECT_URI set? ({err})"
    elif isinstance(err, SpotifyException):
        message = f"Spotify API error {err.http_status}: {err.msg}"
    else:
        message = f"Spotify request failed: {err}"
    app.logger.exception(message)
    return jsonify(error=message), 502


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

    return jsonify(predict_emotion(image))


@app.post("/api/recommend")
def recommend():
    payload = request.get_json(silent=True) or {}
    mood = payload.get("mood")
    if mood not in MOODS:
        return jsonify(error=f"Unknown mood. Expected one of {MOODS}"), 400

    try:
        tracks = recommend_tracks(mood, limit=5)
    except Exception as err:
        return spotify_error(err)
    return jsonify(mood=mood, tracks=tracks)


@app.post("/api/save-playlist")
def save():
    payload = request.get_json(silent=True) or {}
    mood = payload.get("mood")
    uris = payload.get("uris")
    if mood not in MOODS:
        return jsonify(error=f"Unknown mood. Expected one of {MOODS}"), 400
    if (
        not isinstance(uris, list)
        or not 0 < len(uris) <= MAX_PLAYLIST_TRACKS
        or not all(isinstance(u, str) and u.startswith("spotify:track:") for u in uris)
    ):
        return jsonify(error="'uris' must be a list of 1-10 Spotify track URIs"), 400

    try:
        playlist = save_playlist(mood, uris)
    except Exception as err:
        return spotify_error(err)
    return jsonify(playlist=playlist)


def spotify_startup_login():
    """Log in to Spotify in the terminal before serving, so no web request ever blocks on it."""
    if not os.environ.get("SPOTIPY_CLIENT_ID"):
        print("SPOTIPY_* env vars not set: emotion detection works, playlist features are disabled.")
        return

    redirect = urlparse(os.environ.get("SPOTIPY_REDIRECT_URI", ""))
    if redirect.port == PORT:
        print(
            f"SPOTIPY_REDIRECT_URI uses port {PORT}, the same port as this app, so the login "
            f"redirect lands on the app instead of spotipy. Use another port, e.g. "
            f"http://127.0.0.1:8888/callback (in both the env var and the Spotify dashboard). "
            f"Playlist features are disabled."
        )
        return

    try:
        print("Logging in to Spotify (a browser tab may open the first time)...")
        print(f"Logged in to Spotify as {login()}")
    except Exception as err:
        print(f"Spotify login failed, playlist features are disabled: {err}")


if __name__ == "__main__":
    spotify_startup_login()
    # 127.0.0.1 counts as a secure context, so the browser will allow webcam access.
    app.run(debug=True, use_reloader=False, port=PORT)
