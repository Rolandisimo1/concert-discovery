# 🎸 Local Concert Discovery

Automatically finds upcoming concerts near Denver, filters them to your taste using Claude AI, and builds a Spotify playlist — every Sunday.

## How it works

1. **Ticketmaster API** → upcoming shows within 40 miles of Raleigh, next 4 months
2. **Spotify API** → reads your top artists, tracks, and genres
3. **Claude AI** → picks the artists you'll likely enjoy from the local lineup
4. **Spotify API** → builds/updates your "🎸 Local Discovery" playlist
5. **GitHub Actions** → runs automatically every Sunday morning

---

## Setup (one time)

### 1. Get API Keys

| Service | Where to get it | Cost |
|---|---|---|
| Ticketmaster | https://developer.ticketmaster.com/ | Free |
| Spotify | https://developer.spotify.com/dashboard | Free |
| Anthropic | https://console.anthropic.com/ | Pay per use (~cents/week) |

**For Spotify**, create an app at the dashboard and set the Redirect URI to:
```
http://localhost:8888/callback
```

### 2. Get your Spotify Refresh Token (one-time, local)

```bash
pip install spotipy
# Edit auth/get_spotify_token.py with your CLIENT_ID and CLIENT_SECRET
python auth/get_spotify_token.py
```

A browser will open, you'll log in, and the script will print your refresh token.

### 3. Fork this repo on GitHub

Then go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Value |
|---|---|
| `SPOTIFY_CLIENT_ID` | Your Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Your Spotify app client secret |
| `SPOTIFY_REFRESH_TOKEN` | From step 2 above |
| `TICKETMASTER_API_KEY` | Your Ticketmaster API key |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

### 4. Test it manually

Go to **Actions → Weekly Concert Discovery → Run workflow** to trigger a manual run and verify everything works.

After that, it runs automatically every Sunday at 9am MT.

---

## Output

- A Spotify playlist called **"🎸 Local Discovery"** updated weekly
- GitHub Actions log shows each selected artist, venue, date, and Claude's reason for picking them

## Customization

Edit `main.py` to change:
- `city` / `state` / `radius_miles` — for different locations
- `months_ahead` — how far out to search (default: 4)
- `top_n` in `get_taste_profile()` — how many artists to sample from your history
- Playlist name in `update_discovery_playlist()`

Edit the Claude prompt in `src/matching.py` to adjust filtering preferences — e.g., "prefer artists under 10k monthly listeners" or "weight toward artists I've never heard of."
