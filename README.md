# Moodtrack: AI Emotion-to-Playlist Generator

A web app that reads your facial expression through the webcam, detects your emotion with a pretrained vision model, and recommends 5 Spotify tracks that match how you feel. You can save them as a playlist.

```
Webcam ─▶ Face crop (OpenCV) ─▶ Emotion model (ViT) ─▶ Mood ─▶ Spotify search ─▶ 5 tracks
```

**Tech stack:** Python, Flask, Hugging Face `transformers` ([`trpakov/vit-face-expression`](https://huggingface.co/trpakov/vit-face-expression)), OpenCV, Spotify Web API (`spotipy`), plain HTML/CSS/JS.

## Setup

1. **Install dependencies** (Python 3.10+):
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Create a Spotify app** in the [Developer Dashboard](https://developer.spotify.com/dashboard) and add this redirect URI:
   ```
   http://127.0.0.1:8888/callback
   ```
   Don't use port 5000. That's the app's own port, and the login would break.
3. **Set environment variables** (PowerShell):
   ```powershell
   $env:SPOTIPY_CLIENT_ID = "your-client-id"
   $env:SPOTIPY_CLIENT_SECRET = "your-client-secret"
   $env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
   ```
4. **Run** `python app.py`. Complete the Spotify login in the browser the first time, then open **http://127.0.0.1:5000**.

Without the Spotify variables, emotion detection still works; only the playlist features are disabled.

## Usage

Click **Enable camera**, then **Capture mood** and hold an expression during the countdown. You'll get your mood and 5 tracks. Use **Shuffle again** for a new set, or **Save to Spotify** to create a private playlist. You can also pick a mood manually.

## Mood mapping

| Emotion | Mood | Spotify search query |
|---|---|---|
| happy | Happy 😄 | feel good happy upbeat pop |
| sad | Sad 😢 | sad heartbreak acoustic ballad |
| angry, disgust | Angry 😠 | angry rage hard rock metal |
| surprise | Surprised 😲 | euphoric hype dance electronic |
| fear | Fearful 😨 | dark tense cinematic suspense |
| neutral | Neutral 😐 | chill lofi instrumental focus |

To change the music for a mood, edit `MOODS_QUERY_MAP` in `music_service.py`.

## Project structure

```
app.py             Flask server and API routes
emotion_model.py   Face cropping, emotion inference, emotion → mood mapping
music_service.py   Spotify login, track search, playlist creation
templates/         Page layout
static/            Frontend JS and CSS
```

## Troubleshooting

- **Camera error:** close other apps or tabs that use the camera (e.g. a VS Code preview tab), and open the app at `http://127.0.0.1:5000` in a regular browser.
- **"Not logged in to Spotify":** restart `python app.py` and complete the browser login.
- **Spotify 403 errors:** in Development Mode, the app owner's account needs Premium, and your account must be added under **User Management** in the dashboard.

## Limitations

The model reads facial expressions, not inner feelings, so subtle expressions often come out as *Neutral*. Spotify's search matches the query words against track, artist and album names, not how a song sounds, so an occasional track may not fit the mood.
