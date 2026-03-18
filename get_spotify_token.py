"""
Run this ONCE locally to get your Spotify refresh token.
Then store the refresh token as a GitHub Secret.

Usage:
    pip install spotipy
    python auth/get_spotify_token.py
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Paste your Spotify app credentials here (from developer.spotify.com)
CLIENT_ID = "YOUR_SPOTIFY_CLIENT_ID"
CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = [
    "user-top-read",
    "playlist-modify-public",
    "playlist-modify-private",
    "playlist-read-private",
]

def main():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        open_browser=True,
    ))

    # Trigger auth flow - browser will open
    user = sp.current_user()
    print(f"\n✅ Authenticated as: {user['display_name']} ({user['id']})")

    # Grab the cached token info
    token_info = sp.auth_manager.get_cached_token()
    print(f"\n🔑 Your refresh token (save this as a GitHub Secret named SPOTIFY_REFRESH_TOKEN):")
    print(f"\n{token_info['refresh_token']}\n")
    print("Also save your CLIENT_ID and CLIENT_SECRET as GitHub Secrets.")

if __name__ == "__main__":
    main()
