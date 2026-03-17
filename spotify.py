"""
Handles all Spotify interactions:
- Auth via refresh token (no browser needed in CI)
- Fetching user's top artists and tracks to build a taste profile
- Searching for artists from the concert list
- Creating/updating the discovery playlist
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os


def get_spotify_client() -> spotipy.Spotify:
    """
    Auth using refresh token stored in environment (GitHub Secrets).
    No browser interaction needed.
    """
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-top-read playlist-modify-public playlist-modify-private",
    )

    # Inject the refresh token directly — bypasses browser auth
    token_info = auth_manager.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
    return spotipy.Spotify(auth=token_info["access_token"])


def get_taste_profile(sp: spotipy.Spotify, top_n: int = 30) -> dict:
    """
    Fetches user's top artists and tracks across short/medium/long term.
    Returns a structured profile for Claude to reason about.
    """
    profile = {
        "top_artists": [],
        "top_genres": [],
        "top_tracks": [],
    }

    # Get top artists across time ranges for a richer picture
    seen_artists = set()
    for time_range in ["short_term", "medium_term", "long_term"]:
        results = sp.current_user_top_artists(limit=20, time_range=time_range)
        for artist in results["items"]:
            if artist["name"] not in seen_artists:
                profile["top_artists"].append(artist["name"])
                profile["top_genres"].extend(artist.get("genres", []))
                seen_artists.add(artist["name"])

    # Deduplicate and rank genres by frequency
    from collections import Counter
    genre_counts = Counter(profile["top_genres"])
    profile["top_genres"] = [g for g, _ in genre_counts.most_common(20)]

    # Top tracks (medium term)
    results = sp.current_user_top_tracks(limit=top_n, time_range="medium_term")
    profile["top_tracks"] = [
        f"{t['name']} by {t['artists'][0]['name']}" for t in results["items"]
    ]

    return profile

def find_artist_on_spotify(sp: spotipy.Spotify, artist_name: str) -> dict | None:
    """Search for an artist and return their Spotify info if found."""
    results = sp.search(q=f"artist:{artist_name}", type="artist", limit=3)
    artists = results.get("artists", {}).get("items", [])
    if not artists:
        return None
    best = max(artists, key=lambda a: a.get("popularity", 0))
    return {
        "id": best["id"],
        "name": best["name"],
        "genres": best.get("genres", []),
        "popularity": best.get("popularity", 0),
        "url": best.get("external_urls", {}).get("spotify", ""),
    }

    def get_top_tracks_for_artist(sp: spotipy.Spotify, artist_id: str, n: int = 3) -> list[str]:
    """Returns Spotify track URIs for an artist's top tracks."""
    token = sp.auth_manager.get_access_token(as_dict=False) if hasattr(sp.auth_manager, 'get_access_token') else sp._auth
    headers = {"Authorization": f"Bearer {sp.auth_manager.get_cached_token()['access_token']}"}
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    import requests as req
    response = req.get(url, headers=headers)
    if response.status_code != 200:
        return []
    tracks = response.json().get("tracks", [])[:n]
    return [t["uri"] for t in tracks]


def update_discovery_playlist(sp: spotipy.Spotify, track_uris: list[str],
                               playlist_name: str = "🎸 Local Discovery") -> str:
    """
    Creates the playlist if it doesn't exist, then replaces its tracks.
    Returns the playlist URL.
    """
    user_id = sp.current_user()["id"]

    # Find existing playlist or create new one
    playlist_id = None
    playlists = sp.current_user_playlists(limit=50)
    for p in playlists["items"]:
        if p["name"] == playlist_name:
            playlist_id = p["id"]
            break

    if not playlist_id:
        print(f"Creating new playlist: {playlist_name}")
        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description="Artists playing near Raleigh in the next few months — curated weekly by Claude 🤖",
        )
        playlist_id = playlist["id"]
    else:
        print(f"Updating existing playlist: {playlist_name}")

    # Replace all tracks (Spotify limits to 100 per request)
    sp.playlist_replace_items(playlist_id, [])
    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i:i+100])

    return f"https://open.spotify.com/playlist/{playlist_id}"
