"""Handles Spotify API queries and automated playlist generation."""
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

MOODS_QUERY_MAP = {
    "Energetic ⚡": "workout high energy electronic",
    "Relaxed 🍃": "chill lofi acoustic ambient",
    "Stressed / Focus 💻": "deep focus instrumental study",
    "Happy 🎉": "feel good indie pop upbeat"
}

def get_spotify_client():
    """Initialize Spotipy with standard OAuth token caching."""
    auth_manager = SpotifyOAuth(
        scope="playlist-modify-public playlist-modify-private user-read-private",
        cache_path=".cache"
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def recommend_tracks(mood: str, limit: int = 5) -> list:
    """Searches Spotify tracks based on mood, creates a playlist, and returns the added tracks."""
    sp = get_spotify_client()
    user_info = sp.current_user()

    query = MOODS_QUERY_MAP.get(mood, "pop hits")

    # 1. Search for Spotify catalog
    search_results = sp.search(q=query, type="track", limit=limit)
    tracks = search_results["tracks"]["items"]

    track_uris = [t["uri"] for t in tracks]
    track_data = [
        {
            "name": t["name"],
            "artist": t["artists"][0]["name"],
            "url": t["external_urls"]["spotify"]
        }
        for t in tracks
    ]

    # 2. Create a new playlist on the authenticated user's account
    playlist_name = f"AI Vibe Check: {mood}"
    new_playlist = sp.user_playlist_create(
        user=user_info["id"],
        name=playlist_name,
        public=True,
        description=f"Generated via real-time webcam emotion detection using query: '{query}'"
    )

    # 3. Insert tracks into the newly created playlist
    sp.playlist_add_items(new_playlist["id"], track_uris)
    
    return track_data