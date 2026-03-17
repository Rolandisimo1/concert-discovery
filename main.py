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


def main():
    print("🎵 Starting Local Concert Discovery...\n")

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

    print("\n📊 Building Spotify taste profile...")
    sp = get_spotify_client()
    taste_profile = get_taste_profile(sp)
    print(f"   Top genres: {', '.join(taste_profile['top_genres'][:8])}")
    print(f"   Top artists sample: {', '.join(taste_profile['top_artists'][:5])}")

    print("\n🤖 Asking Claude to pick artists you'll like...")
    matched_artists = filter_artists_by_taste(concerts, taste_profile)

    if not matched_artists:
        print("No matching artists found this week.")
        return

    print("\n🔍 Looking up artists on Spotify...")
    all_track_uris = []
    final_artists = []

    for artist_info in matched_artists[:25]:
        spotify_artist = find_artist_on_spotify(sp, artist_info["artist"])
        if not spotify_artist:
            print(f"   ⚠️  Not found on Spotify: {artist_info['artist']}")
            continue

        tracks = get_top_tracks_for_artist(sp, spotify_artist["id"], n=3)
        if tracks:
            all_track_uris.extend(tracks)
            final_artists.append({**artist_info, "spotify": spotify_artist})
            print(f"   ✅ {artist_info['artist']} — score {artist_info['score']}/10")

    print(f"\n🎧 Adding {len(all_track_uris)} tracks to playlist...")
    playlist_url = update_discovery_playlist(sp, all_track_uris)

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
