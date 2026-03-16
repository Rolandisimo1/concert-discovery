"""
Uses Claude API to evaluate which local artists match the user's music taste.
Batches artists to minimize API calls.
"""

import anthropic
import json
import os


def filter_artists_by_taste(
    artists: list[dict],
    taste_profile: dict,
    batch_size: int = 30,
) -> list[dict]:
    """
    Given a list of artists playing locally and the user's Spotify taste profile,
    returns a filtered + scored list of artists Claude thinks the user will like.

    Each artist dict should have: name, venue, date, genre
    Returns same dicts with added: score (1-10), reason
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    taste_summary = f"""
User's top Spotify artists: {', '.join(taste_profile['top_artists'][:20])}

Top genres they listen to: {', '.join(taste_profile['top_genres'][:15])}

Sample top tracks: {', '.join(taste_profile['top_tracks'][:10])}
"""

    matched = []

    # Process in batches to stay within token limits
    for i in range(0, len(artists), batch_size):
        batch = artists[i:i + batch_size]
        artist_list = "\n".join([
            f"- {a['artist']} | Genre: {a['genre']} | Venue: {a['venue']} | Date: {a['date']}"
            for a in batch
        ])

        prompt = f"""You are helping a music fan discover local concerts that match their taste.

Here is their Spotify listening profile:
{taste_summary}

Here are artists playing near Denver in the next few months:
{artist_list}

For each artist, decide if this person would likely enjoy seeing them live.
Consider genre fit, similar artist vibes, and variety.
Prefer smaller/indie venues and lesser-known artists for discovery value.
Skip obvious stadium acts they've certainly heard of already.

Respond ONLY with a JSON array. Each element:
{{
  "artist": "<exact artist name from list>",
  "score": <1-10, where 7+ means recommend>,
  "reason": "<one sentence why they'd like or skip this>"
}}

Include all artists in your response, even low scores. No other text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            text = response.content[0].text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            scored = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Warning: Could not parse Claude response for batch {i}: {e}")
            continue

        # Merge scores back into original artist dicts
        score_map = {s["artist"]: s for s in scored}
        for artist in batch:
            score_data = score_map.get(artist["artist"], {})
            if score_data.get("score", 0) >= 7:
                matched.append({
                    **artist,
                    "score": score_data.get("score", 0),
                    "reason": score_data.get("reason", ""),
                })

    # Sort by score descending
    matched.sort(key=lambda a: a["score"], reverse=True)
    print(f"Claude selected {len(matched)} artists from {len(artists)} playing locally")
    return matched
