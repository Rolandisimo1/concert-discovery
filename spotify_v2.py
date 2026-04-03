import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import requests as req
from collections import Counter


def get_spotify_client():
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-top-read playlist-modify-public playlist-modify-private",
    )
    token_info = auth_manager.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
    return spotipy.Spotify(auth=token_info["access_token"])


def get_taste_profile(sp, top_n=30):
    profile = {"top_artists": [], "top_genres": [], "top_tracks": []}
    seen_artists = set()
    for time_range in ["short_term", "medium_term", "long_term"]:
        results = sp.current_user_top_artists(limit=20, time_range=time_range)
        for artist in results["items"]:
            if artist["name"] not in seen_artists:
                profile["top_artists"].append(artist["name"])
                profile["top_genres"].extend(artist.get("genres", []))
                seen_artists.add(artist["name"])
    genre_counts = Counter(profile["top_genres"])
    profile["top_genres"] = [g for g, _ in genre_counts.most_common(20)]
    results = sp.current_user_top_tracks(limit=top_n, time_range="medium_term")
    profile["top_tracks"] = [
        f"{t['name']} by {t['artists'][0]['name']}" for t in results["items"]
    ]
    return profile


def find_artist_on_spotify(sp, artist_name):
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


def get_top_tracks_for_artist(sp, artist_id, artist_name, offset=0, n=3):
    """
    Gets n tracks for an artist starting at offset, for weekly rotation.
    Falls back to search if offset exceeds available tracks.
    """
    try:
        # Get more tracks than we need so offset works
        results = sp.search(q=f"artist:{artist_name}", type="track", limit=50)
        tracks = results.get("tracks", {}).get("items", [])

        # Filter to only tracks actually by this artist (search can return loose matches)
        tracks = [
            t for t in tracks
            if any(a["id"] == artist_id for a in t.get("artists", []))
        ]

        if not tracks:
            # Fallback: just search by name without strict artist filter
            results = sp.search(q=f"artist:{artist_name}", type="track", limit=n)
            tracks = results.get("tracks", {}).get("items", [])
            return [t["uri"] for t in tracks[:n]]

        # Use offset to rotate, wrap around if needed
        total = len(tracks)
        start = offset % total if total > 0 else 0
        # Wrap-around slice
        rotated = (tracks[start:] + tracks[:start])[:n]
        return [t["uri"] for t in rotated]

    except Exception as e:
        print(f"   Warning: could not get tracks for {artist_name}: {e}", flush=True)
        return []


def update_discovery_playlist(sp, track_uris, playlist_name="🎸 Local Discovery"):
    user_id = sp.current_user()["id"]
    playlist_id = None
    playlists = sp.current_user_playlists(limit=50)
    for p in playlists["items"]:
        if p["name"] == playlist_name:
            playlist_id = p["id"]
            break
    if not playlist_id:
        print(f"Creating new playlist: {playlist_name}")
        playlist = sp._post("me/playlists", payload={
            "name": playlist_name,
            "public": False,
            "description": "Artists playing near Raleigh - curated weekly by Claude",
        })
        playlist_id = playlist["id"]
    else:
        print(f"Updating existing playlist: {playlist_name}")
    sp.playlist_replace_items(playlist_id, [])
    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i:i+100])
    return f"https://open.spotify.com/playlist/{playlist_id}"
