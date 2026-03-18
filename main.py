import sys
import traceback
print("START", flush=True)

from concerts import get_upcoming_concerts
from spotify import (
    get_spotify_client,
    get_taste_profile,
    find_artist_on_spotify,
    get_top_tracks_for_artist,
    update_discovery_playlist,
)
from matching import filter_artists_by_taste

print("ALL IMPORTS OK", flush=True)


def main():
    print("Fetching concerts...", flush=True)
    concerts = get_upcoming_concerts(
        api_key=__import__("os").environ["TICKETMASTER_API_KEY"],
        city="Raleigh",
        state="NC",
        radius_miles=50,
        months_ahead=4,
    )

    if not concerts:
        print("No concerts found. Exiting.")
        return

    print(f"Found {len(concerts)} concerts", flush=True)
    print("Building Spotify taste profile...", flush=True)
    sp = get_spotify_client()
    taste_profile = get_taste_profile(sp)
    print(f"Top genres: {', '.join(taste_profile['top_genres'][:8])}", flush=True)
    print(f"Top artists: {', '.join(taste_profile['top_artists'][:5])}", flush=True)

    print("Asking Claude to filter artists...", flush=True)
    matched_artists = filter_artists_by_taste(concerts, taste_profile)

    if not matched_artists:
        print("No matching artists found.")
        return

    print(f"Claude selected {len(matched_artists)} artists", flush=True)
    print("Looking up artists on Spotify...", flush=True)
    all_track_uris = []
    final_artists = []

    for artist_info in matched_artists[:25]:
        spotify_artist = find_artist_on_spotify(sp, artist_info["artist"])
        if not spotify_artist:
            print(f"  Not found on Spotify: {artist_info['artist']}", flush=True)
            continue
        tracks = get_top_tracks_for_artist(sp, spotify_artist["id"], n=3)
        if tracks:
            all_track_uris.extend(tracks)
            final_artists.append({**artist_info, "spotify": spotify_artist})
            print(f"  OK: {artist_info['artist']} (score {artist_info['score']}/10)", flush=True)

    print(f"Adding {len(all_track_uris)} tracks to playlist...", flush=True)
    playlist_url = update_discovery_playlist(sp, all_track_uris)

    print("\n" + "="*60, flush=True)
    print("LOCAL DISCOVERY - THIS WEEK'S PICKS", flush=True)
    print("="*60, flush=True)
    for a in final_artists:
        print(f"\n  {a['artist']}", flush=True)
        print(f"  Venue: {a['venue']} - {a['date']}", flush=True)
        print(f"  Tickets: {a['url']}", flush=True)
        print(f"  Why: {a['reason']}", flush=True)

    print(f"\nPlaylist: {playlist_url}", flush=True)
    print(f"Total: {len(final_artists)} artists, {len(all_track_uris)} tracks", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRASHED: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
