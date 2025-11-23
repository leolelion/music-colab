import musicbrainzngs
import time
import os
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../.env')

# Set up MusicBrainz user agent with email from environment
MUSICBRAINZ_EMAIL = os.getenv('MUSICBRAINZ_EMAIL', 'you@example.com')
musicbrainzngs.set_useragent("MusicColabApp", "0.1", MUSICBRAINZ_EMAIL)

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

# --- 2. Get a specific album's releases
def get_album_releases(artist_id, album_title=None, limit=50):
    """Get releases for a specific album or first few albums"""
    res = safe_request(
        musicbrainzngs.browse_release_groups,
        artist=artist_id,
        includes=[],
        limit=limit
    )
    
    release_groups = res.get("release-group-list", [])
    albums = []
    
    for rg in release_groups:
        if rg.get("primary-type", "").lower() == "album":
            title = rg["title"]
            date = rg.get("first-release-date", "Unknown")
            rg_id = rg["id"]
            
            # If looking for specific album, filter (more flexible matching)
            if album_title and album_title.lower() not in title.lower():
                continue
            
            albums.append({
                "title": title,
                "date": date,
                "release_group_id": rg_id
            })
    
    return albums

# --- 3. Get actual releases from release group
def get_releases_from_group(release_group_id):
    """Get actual release IDs from a release group"""
    res = safe_request(
        musicbrainzngs.browse_releases,
        release_group=release_group_id,
        includes=["artist-credits"],
        limit=10
    )
    
    releases = res.get("release-list", [])
    # Filter for official releases
    official_releases = [
        rel for rel in releases 
        if rel.get("status", "").lower() == "official"
    ]
    
    return official_releases[:1] if official_releases else releases[:1]  # Take first official or first available

# --- 4. Get detailed recording information for an album
def get_album_recordings(release_id):
    """Get detailed recording information including musicians"""
    print(f"  📀 Fetching detailed recordings for release: {release_id}")
    
    try:
        release_data = safe_request(
            musicbrainzngs.get_release_by_id,
            release_id,
            includes=["recordings", "artist-credits"]
        )
        return release_data["release"]
    except Exception as e:
        print(f"    ❌ Error fetching release details: {e}")
        return None

# --- 4b. Get detailed recording with all relationships
def get_detailed_recording(recording_id):
    """Get detailed recording information with all artist relationships"""
    try:
        recording_data = safe_request(
            musicbrainzngs.get_recording_by_id,
            recording_id,
            includes=["artist-rels", "artist-credits"]
        )
        return recording_data["recording"]
    except Exception as e:
        print(f"    ❌ Error fetching detailed recording: {e}")
        return None

# --- 5. Extract musicians from a single song/recording
def extract_song_musicians(recording):
    """Extract all musicians and roles from a single recording"""
    song_title = recording.get("title", "Unknown")
    musicians = []
    
    # Artist credits (primary performers)
    for credit in recording.get("artist-credit", []):
        if isinstance(credit, dict) and "artist" in credit:
            musicians.append({
                "name": credit["artist"]["name"],
                "role": "performer",
                "song": song_title
            })
    
    # Recording relationships (detailed roles)
    for rel in recording.get("artist-relation-list", []):
        role = rel.get("type", "")
        artist = rel.get("artist", {})
        
        if artist and role:
            # Handle attributes - they can be strings or objects
            instrument_role = role  # Default to the relationship type
            
            for attr in rel.get("attribute-list", []):
                if isinstance(attr, str):
                    # For instrument relationships, use the instrument name as the role
                    if role.lower() == "instrument":
                        instrument_role = attr
                elif isinstance(attr, dict):
                    attr_value = attr.get("value", attr.get("attribute", ""))
                    # For instrument relationships, use the instrument name as the role
                    if role.lower() == "instrument":
                        instrument_role = attr_value
            
            musicians.append({
                "name": artist.get("name"),
                "role": instrument_role,
                "song": song_title
            })
    
    return song_title, musicians

# --- 6. Process all musicians from an album
def process_album_musicians(release_data):
    """Process all musicians from an album"""
    album_title = release_data.get("title", "Unknown Album")
    all_musicians = []
    
    # Handle medium-list (tracks/discs)
    for medium in release_data.get("medium-list", []):
        for track in medium.get("track-list", []):
            recording = track.get("recording", {})
            if recording:
                # Get detailed recording information with artist relationships
                recording_id = recording.get("id")
                if recording_id:
                    detailed_recording = get_detailed_recording(recording_id)
                    if detailed_recording:
                        # Merge the detailed data back into the original recording
                        recording.update(detailed_recording)
                
                song_title, musicians = extract_song_musicians(recording)
                all_musicians.extend(musicians)
    
    return {
        "album": album_title,
        "all_musicians": all_musicians
    }

# --- 7. Aggregate musicians by role and individual
def aggregate_album_musicians(album_data):
    """Create aggregated view of all album contributors"""
    role_counts = defaultdict(set)
    musician_contributions = defaultdict(list)
    
    for musician in album_data["all_musicians"]:
        name = musician["name"]
        role = musician["role"]
        song = musician["song"]
        
        role_counts[role].add(name)
        musician_contributions[name].append({
            "role": role,
            "song": song,
            "attributes": musician.get("attributes", [])
        })
    
    return {
        "by_role": {role: list(musicians) for role, musicians in role_counts.items()},
        "by_musician": dict(musician_contributions),
        "total_unique_musicians": len(musician_contributions),
        "total_roles": len(role_counts)
    }

# --- 8. Display album musicians by role
def display_album_musicians(album_data, summary_data):
    """Display album musicians organized by role"""
    print(f"\n📀 Album: {album_data['album']}")
    print(f"� Musicians by Role:")
    
    for role, musicians_list in summary_data['by_role'].items():
        print(f"   • {role}: {', '.join(musicians_list)}")

# --- 9. Process a single album
def process_single_album(album):
    """Process a single album and return musician data"""
    print(f"\n📀 Processing album: {album['title']} ({album['date']})")
    
    # Get releases for this album
    releases = get_releases_from_group(album['release_group_id'])
    
    if not releases:
        print("❌ No releases found for this album")
        return None
    
    release_id = releases[0]['id']
    
    # Get detailed recording data
    release_data = get_album_recordings(release_id)
    
    if not release_data:
        print("❌ Could not fetch recording details")
        return None
    
    # Extract musicians
    album_musicians = process_album_musicians(release_data)
    summary = aggregate_album_musicians(album_musicians)
    
    # Display results
    display_album_musicians(album_musicians, summary)
    
    return {
        "album_info": album,
        "musicians": album_musicians,
        "summary": summary
    }

# --- 10. Main function to extract musicians from multiple albums
def extract_album_musicians(artist_name, album_title=None, num_albums=5):
    """Main function to extract all musicians from multiple albums"""
    print(f"🎤 Analyzing musician data for: {artist_name}")
    
    # Find artist
    artist_id = find_artist_id(artist_name)
    
    # Get albums
    albums = get_album_releases(artist_id, album_title, limit=1 if album_title else num_albums)
    
    if not albums:
        print("❌ No albums found")
        return
    
    results = []
    
    # Process each album
    for album in albums[:num_albums]:
        result = process_single_album(album)
        if result:
            results.append(result)
    
    print(f"\n✅ Successfully processed {len(results)} albums")
    return results

# --- 11. Example usage
if __name__ == "__main__":
    # Extract musicians from multiple albums
    artist_name = "Miles Davis"
    album_title = None  # Set to None to get first available albums, or specify like "Kind of Blue"
    
    results = extract_album_musicians(artist_name, album_title, num_albums=5)
    
    if not results:
        print("❌ Failed to extract musician data")
