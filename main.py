import sys
import traceback
import os
from datetime import datetime

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
        api_key=os.environ["TICKETMASTER_API_KEY"],
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

    # Sort by show date - furthest date first so newest picks are at top
    # (next week the close ones will have been heard many times already)
    def parse_date(a):
        try:
            return datetime.strptime(a["date"], "%Y-%m-%d")
        except Exception:
            return datetime.min

    matched_artists.sort(key=parse_date, reverse=True)
    print(f"Claude selected {len(matched_artists)} artists (sorted furthest date first)", flush=True)

    # Use week number to rotate which tracks we pick per artist
    # Week 1: tracks 0-2, Week 2: tracks 3-5, Week 3: tracks 6-8, etc.
    week_number = datetime.now().isocalendar()[1]
    track_offset = (week_number % 10) * 3  # cycles every 10 weeks
    print(f"Week {week_number} — track offset: {track_offset}", flush=True)

    print("Looking up artists on Spotify...", flush=True)
    all_track_uris = []
    seen_uris = set()  # for deduplication within this playlist
    final_artists = []

    for artist_info in matched_artists[:25]:
        spotify_artist = find_artist_on_spotify(sp, artist_info["artist"])
        if not spotify_artist:
            print(f"  Not found on Spotify: {artist_info['artist']}", flush=True)
            continue

        tracks = get_top_tracks_for_artist(
            sp,
            spotify_artist["id"],
            artist_info["artist"],
            offset=track_offset,
            n=3,
        )

        # Deduplicate — skip any track already in this playlist
        new_tracks = [t for t in tracks if t not in seen_uris]
        if new_tracks:
            all_track_uris.extend(new_tracks)
            seen_uris.update(new_tracks)
            final_artists.append({**artist_info, "spotify": spotify_artist})
            print(f"  OK: {artist_info['artist']} ({artist_info['date']}) score {artist_info['score']}/10", flush=True)
        else:
            print(f"  Skipped (duplicate tracks): {artist_info['artist']}", flush=True)

    print(f"Adding {len(all_track_uris)} tracks to playlist...", flush=True)
    playlist_url = update_discovery_playlist(sp, all_track_uris)

    print("\n" + "="*60, flush=True)
    print("LOCAL DISCOVERY - THIS WEEK'S PICKS (furthest shows first)", flush=True)
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
