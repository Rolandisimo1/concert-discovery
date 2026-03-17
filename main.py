"""
Main entry point for the Local Concert Discovery pipeline.

Flow:
1. Fetch upcoming Denver concerts from Ticketmaster
2. Build taste profile from Spotify listening history
3. Claude filters artists to ones the user will likely enjoy
4. Look up each matched artist on Spotify, grab top tracks
5. Update the discovery playlist
6. Print a summary of what's coming up
"""

import os
from concerts import get_upcoming_concerts
from spotify import (
    get_spotify_client,
    get_taste_profile,
    find_artist_on_spotify,
    get_top_tracks_for_artist,
    update_discovery_playlist,
)
from matching import filter_artists_by_taste
```

**Fix 2 — docstring** (line 5), change:
```
1. Fetch upcoming Denver concerts from Ticketmaster
```
to:
```
1. Fetch upcoming Raleigh, NC concerts from Ticketmaster


def main():
    print("🎵 Starting Local Concert Discovery...\n")

    # --- 1. Fetch concerts ---
    concerts = get_upcoming_concerts(
        api_key=os.environ["TICKETMASTER_API_KEY"],
        city="Raleigh",
        state="NC",
        radius_miles=50,
        months_ahead=4,
    )

    if not concerts:
        print("No concerts found. Exiting.")
        return

    # --- 2. Spotify taste profile ---
    print("\n📊 Building Spotify taste profile...")
    sp = get_spotify_client()
    taste_profile = get_taste_profile(sp)
    print(f"   Top genres: {', '.join(taste_profile['top_genres'][:8])}")
    print(f"   Top artists sample: {', '.join(taste_profile['top_artists'][:5])}")

    # --- 3. Claude filtering ---
    print("\n🤖 Asking Claude to pick artists you'll like...")
    matched_artists = filter_artists_by_taste(concerts, taste_profile)

    if not matched_artists:
        print("No matching artists found this week.")
        return

    # --- 4. Build playlist tracks ---
    print("\n🔍 Looking up artists on Spotify...")
    all_track_uris = []
    final_artists = []

    for artist_info in matched_artists[:25]:  # cap at 25 artists
        spotify_artist = find_artist_on_spotify(sp, artist_info["artist"])
        if not spotify_artist:
            print(f"   ⚠️  Not found on Spotify: {artist_info['artist']}")
            continue

        tracks = get_top_tracks_for_artist(sp, spotify_artist["id"], n=3)
        if tracks:
            all_track_uris.extend(tracks)
            final_artists.append({**artist_info, "spotify": spotify_artist})
            print(f"   ✅ {artist_info['artist']} — score {artist_info['score']}/10")

    # --- 5. Update playlist ---
    print(f"\n🎧 Adding {len(all_track_uris)} tracks to playlist...")
    playlist_url = update_discovery_playlist(sp, all_track_uris)

    # --- 6. Summary ---
    print("\n" + "="*60)
    print("🎸 LOCAL DISCOVERY — THIS WEEK'S PICKS")
    print("="*60)
    for a in final_artists:
        print(f"\n  {a['artist']}")
        print(f"  📍 {a['venue']} — {a['date']}")
        print(f"  🎟️  {a['url']}")
        print(f"  💬 {a['reason']}")

    print(f"\n🎵 Playlist updated: {playlist_url}")
    print(f"\nTotal: {len(final_artists)} artists, {len(all_track_uris)} tracks\n")


if __name__ == "__main__":
    main()
