"""Handles Spotify API queries and playlist creation.

Uses the post-February-2026 Web API endpoints (POST /me/playlists and
/playlists/{id}/items). spotipy's user_playlist_create / playlist_add_items
still call the removed /users/{id}/playlists and /playlists/{id}/tracks routes,
so those two calls go through the raw client instead.
"""
import random
from functools import lru_cache

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Genres whose sound mirrors each emotion (sad -> sad music). Broad genres like "pop" mix
# every mood, so these are narrow, mood-specific Spotify genres. Each request tries them in
# random order, so "Shuffle again" also rotates genres. Names must be Spotify genre strings;
# one Spotify doesn't recognise just returns nothing and the next is tried.
MOOD_GENRES = {
    "Happy 😄": ["dance pop", "disco", "motown", "funk", "bubblegum pop"],
    "Sad 😢": ["sad rap", "slowcore", "sadcore", "emo", "melancholia"],
    "Angry 😠": ["nu metal", "rap metal", "hardcore punk", "thrash metal", "metalcore"],
    "Surprised 😲": ["big room", "electro house", "hyperpop", "drum and bass"],
    "Fearful 😨": ["dark ambient", "darkwave", "witch house", "drone"],
    "Neutral 😐": ["lo-fi beats", "chillhop", "chillwave", "ambient"],
}

# Keyword fallback, used only if a genre search returns nothing.
MOODS_QUERY_MAP = {
    "Happy 😄": "feel good happy upbeat pop",
    "Sad 😢": "sad heartbreak acoustic ballad",
    "Angry 😠": "angry rage hard rock metal",
    "Surprised 😲": "euphoric hype dance electronic",
    "Fearful 😨": "dark tense cinematic suspense",
    "Neutral 😐": "chill lofi instrumental focus",
}

# Each search reads one page from a random point within the top MAX_SEARCH_DEPTH results and
# samples tracks from it, so "Shuffle again" gives a different set. Depth is kept small:
# results are ranked by popularity, and deep results in niche genres fit the genre less well.
SEARCH_PAGE_SIZE = 10  # Development Mode maximum for search
MAX_SEARCH_DEPTH = 60


class SpotifyNotLoggedIn(Exception):
    """No valid Spotify token yet; the login must happen at startup, not inside a web request."""


@lru_cache(maxsize=1)
def get_auth_manager() -> SpotifyOAuth:
    """OAuth manager with token caching in .cache.

    Reads SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET and SPOTIPY_REDIRECT_URI from the environment.
    """
    return SpotifyOAuth(
        scope="playlist-modify-public playlist-modify-private user-read-private",
        cache_path=".cache",
    )


def login() -> str:
    """Run the interactive browser login (if no cached token) and return the user's display name.

    Call this once from the terminal before serving requests. spotipy's login blocks while it
    waits for the browser redirect, which would freeze any web request that triggered it.
    """
    get_auth_manager().get_access_token(as_dict=False)
    user = spotipy.Spotify(auth_manager=get_auth_manager()).current_user()
    return user.get("display_name") or user["id"]


def is_logged_in() -> bool:
    """True if a cached token exists (refreshing it if expired). Never opens a browser."""
    auth = get_auth_manager()
    return auth.validate_token(auth.cache_handler.get_cached_token()) is not None


def get_spotify_client() -> spotipy.Spotify:
    if not is_logged_in():
        raise SpotifyNotLoggedIn(
            "Not logged in to Spotify. Stop the app, then restart `python app.py` "
            "and complete the login in your browser."
        )
    return spotipy.Spotify(auth_manager=get_auth_manager())


def _search_tracks(sp: spotipy.Spotify, query: str, limit: int) -> list[dict]:
    """Return `limit` tracks sampled from a random page of the query's top results."""
    first = sp.search(q=query, type="track", limit=SEARCH_PAGE_SIZE)["tracks"]
    items = first["items"]

    # Pick the page from the real result count, so the offset never runs past the end.
    depth = min(first["total"], MAX_SEARCH_DEPTH)
    if depth > SEARCH_PAGE_SIZE:
        offset = random.randint(0, depth - SEARCH_PAGE_SIZE)
        if offset > 0:
            # Spotify's total can overestimate; keep the first page if this one comes back empty.
            items = sp.search(q=query, type="track", limit=SEARCH_PAGE_SIZE, offset=offset)["tracks"]["items"] or items

    items = [t for t in items if t]  # search pages can contain null entries
    return random.sample(items, k=min(limit, len(items)))


def recommend_tracks(mood: str, limit: int = 5) -> list[dict]:
    """Search Spotify for tracks in a genre matching the mood. Does not create a playlist."""
    sp = get_spotify_client()

    genres = MOOD_GENRES.get(mood, ["pop"])
    tracks = []
    for genre in random.sample(genres, k=len(genres)):
        tracks = _search_tracks(sp, f'genre:"{genre}"', limit)
        if tracks:
            print(f"[spotify] {mood}: genre {genre!r} -> {len(tracks)} tracks")
            break
        print(f"[spotify] {mood}: genre {genre!r} returned nothing, trying next")
    if not tracks:
        # No genre matched or genre filter unavailable: fall back to a keyword search.
        query = MOODS_QUERY_MAP.get(mood, "pop hits")
        tracks = _search_tracks(sp, query, limit)
        print(f"[spotify] {mood}: all genres empty, keyword fallback {query!r} -> {len(tracks)} tracks")

    return [
        {
            "name": t["name"],
            "artist": ", ".join(a["name"] for a in t["artists"]),
            "url": t["external_urls"]["spotify"],
            "uri": t["uri"],
            "album_art": t["album"]["images"][-1]["url"] if t["album"]["images"] else None,
        }
        for t in tracks
    ]


def save_playlist(mood: str, track_uris: list[str]) -> dict:
    """Create a private playlist on the user's account with the given tracks."""
    sp = get_spotify_client()
    genres = ", ".join(MOOD_GENRES.get(mood, ["pop"]))

    playlist = sp._post(
        "me/playlists",
        payload={
            "name": f"AI Vibe Check: {mood}",
            "public": False,
            "description": f"Generated via real-time webcam emotion detection. Genres: {genres}",
        },
    )
    sp._post(f"playlists/{playlist['id']}/items", payload={"uris": track_uris})

    return {"id": playlist["id"], "url": playlist["external_urls"]["spotify"]}
