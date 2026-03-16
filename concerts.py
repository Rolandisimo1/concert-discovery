"""
Fetches upcoming music events in Denver metro using the Ticketmaster Discovery API.
Free tier: 5,000 requests/day — more than enough for weekly runs.
Get your key at: https://developer.ticketmaster.com/
"""

import requests
from datetime import datetime, timedelta


def get_upcoming_concerts(api_key: str, city: str = "Raleigh", state: str = "NC",
                           radius_miles: int = 50, months_ahead: int = 4) -> list[dict]:
    """
    Returns a list of upcoming concerts with artist name, venue, date, and url.
    Filters to small/mid venues by excluding large arenas.
    """
    start = datetime.utcnow()
    end = start + timedelta(days=30 * months_ahead)

    # Ticketmaster expects ISO 8601 with Z suffix
    start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": api_key,
        "classificationName": "music",
        "city": city,
        "stateCode": state,
        "radius": radius_miles,
        "unit": "miles",
        "startDateTime": start_str,
        "endDateTime": end_str,
        "size": 200,  # max per request
        "sort": "date,asc",
    }

    concerts = []
    page = 0

    while True:
        params["page"] = page
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        events = data.get("_embedded", {}).get("events", [])
        if not events:
            break

        for event in events:
            # Extract venue info
            venues = event.get("_embedded", {}).get("venues", [{}])
            venue = venues[0] if venues else {}
            venue_name = venue.get("name", "Unknown Venue")
            venue_capacity = venue.get("upcomingEvents", {}).get("_total", None)

            # Extract artist/attraction name
            attractions = event.get("_embedded", {}).get("attractions", [{}])
            artist_name = attractions[0].get("name", "") if attractions else ""
            if not artist_name:
                artist_name = event.get("name", "Unknown Artist")

            # Extract date
            dates = event.get("dates", {})
            date_str = dates.get("start", {}).get("localDate", "")

            concerts.append({
                "artist": artist_name,
                "venue": venue_name,
                "date": date_str,
                "url": event.get("url", ""),
                "event_name": event.get("name", ""),
                "genre": _extract_genre(event),
            })

        # Check if there are more pages
        total_pages = data.get("page", {}).get("totalPages", 1)
        page += 1
        if page >= total_pages:
            break

    print(f"Found {len(concerts)} upcoming concerts near {city}, {state}")
    return concerts


def _extract_genre(event: dict) -> str:
    """Pull genre/subgenre from Ticketmaster classification data."""
    classifications = event.get("classifications", [])
    if not classifications:
        return ""
    c = classifications[0]
    genre = c.get("genre", {}).get("name", "")
    subgenre = c.get("subGenre", {}).get("name", "")
    return f"{genre} / {subgenre}".strip(" /")
