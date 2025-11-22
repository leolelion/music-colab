import musicbrainzngs
import time

musicbrainzngs.set_useragent("MusicColabApp", "0.1", "you@example.com")

# --- Helper: safe MusicBrainz request with retry + delay
def safe_request(func, *args, **kwargs):
    for attempt in range(3):
        try:
            time.sleep(1)  # be nice to their API
            return func(*args, **kwargs)
        except musicbrainzngs.WebServiceError as e:
            print(f"Error: {e}, retrying ({attempt+1}/3)...")
            time.sleep(2)
    raise Exception("Failed after 3 retries")

# --- 1. Search artist and get their MBID
def find_artist_id(name):
    res = safe_request(musicbrainzngs.search_artists, name, limit=1)
    if not res["artist-list"]:
        raise Exception("Artist not found")
    artist = res["artist-list"][0]
    print(f"Found artist: {artist['name']} (ID: {artist['id']})")
    return artist["id"]

# --- 2. Fetch *all* releases (albums) for the artist
def get_all_albums(artist_id, max_albums=None):
    offset = 0
    limit = 100
    all_groups = []

    while True:
        res = safe_request(
            musicbrainzngs.browse_release_groups,
            artist=artist_id,
            includes=[],
            limit=limit,
            offset=offset
        )

        groups = res.get("release-group-list", [])
        if not groups:
            break

        all_groups.extend(groups)
        print(f"Fetched {len(groups)} release-groups (total: {len(all_groups)})")

        if max_albums and len(all_groups) >= max_albums:
            all_groups = all_groups[:max_albums]
            break

        if len(groups) < limit:
            break
        offset += limit

    # Keep only official albums
    albums = [
        {"title": g["title"], "first-release-date": g.get("first-release-date", "Unknown")}
        for g in all_groups
        if g.get("primary-type", "").lower() == "album"
    ]
    return albums


# --- 3. Filter only official albums (skip singles, etc.)
def filter_albums(releases):
    albums = {}
    for rel in releases:
        if rel.get("status", "").lower() != "official":
            continue
        rg = rel.get("release-group", {})
        if rg.get("primary-type", "").lower() != "album":
            continue

        title = rel["title"]
        date = rel.get("date", "Unknown")
        albums[title] = date  # deduplicate by title

    return [{"title": t, "release_date": d} for t, d in albums.items()]

# --- 4. Example usage
if __name__ == "__main__":
    artist_name = "Miles Davis"
    artist_id = find_artist_id(artist_name)
    artist_id = "561d854a-6a28-4aa7-8c99-323e6ce46c2a"  # Miles Davis MBID

    albums = get_all_albums(artist_id, max_albums=10)
    #albums = filter_albums(all_albums)

    print(f"\n🎶 {artist_name} — {len(albums)} official albums found:\n")
    for a in sorted(albums, key=lambda x: x["first-release-date"]):
        print(f"  - {a['title']} ({a['first-release-date']})")
