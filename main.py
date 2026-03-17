import sys
print("START", flush=True); sys.stdout.flush()
print("importing concerts...", flush=True)
from concerts import get_upcoming_concerts
print("importing spotify...", flush=True)
from spotify import (
    get_spotify_client,
    get_taste_profile,
    find_artist_on_spotify,
    get_top_tracks_for_artist,
    update_discovery_playlist,
)
print("importing matching...", flush=True)
from matching import filter_artists_by_taste
print("ALL IMPORTS OK", flush=True)

import sys
print("START", flush=True); sys.stdout.flush()

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import requests as req


def get_spotify_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-top-read playlist-modify-public playlist-modify-private",
    )
    token_info = auth_manager.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
    return spotipy.Spotify(auth=token_info["access_token"])


def get_taste_profile(sp: spotipy.Spotify, top_n: int = 30) -> dict:
    profile = {
        "top_artists": [],
        "top_genres": [],
        "top_tracks": [],
    }
    seen_artists = set()
    for time_range in ["short_term", "medium_term", "long_term"]:
        results = sp.current_user_top_artists(limit=20, time_range=time_range)
        for artist in results["items"]:
            if artist["name"] not in seen_artists:
                profile["top_artists"].append(artist["name"])
                profile["top_genres"].extend(artist.get("genres", []))
                seen_artists.add(artist["name"])
    from collections import Counter
    genre_counts = Counter(profile["top_genres"])
    profile["top_genres"] = [g for g, _ in genre_counts.most_common(20)]
    results = sp.current_user_top_tracks(limit=top_n, time_range="medium_term")
    profile["top_tracks"] = [
        f"{t['name']} by {t['artists'][0]['name']}" for t in results["items"]
    ]
    return profile


def find_artist_on_spotify(sp: spotipy.Spotify, artist_name: str) -> dict | None:
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
    token = sp._auth
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    response = req.get(url, headers=headers)
    if response.status_code != 200:
        return []
    tracks = response.json().get("tracks", [])[:n]
    return [t["uri"] for t in tracks]


def update_discovery_playlist(sp: spotipy.Spotify, track_uris: list[str],
                               playlist_name: str = "🎸 Local Discovery") -> str:
    user_id = sp.current_user()["id"]
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
    sp.playlist_replace_items(playlist_id, [])
    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i:i+100])
    return f"https://open.spotify.com/playlist/{playlist_id}"
