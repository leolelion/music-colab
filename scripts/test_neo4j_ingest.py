#!/usr/bin/env python3
"""
Test script for Neo4j ingestion - Tests the data processing logic without requiring Neo4j
"""

import json
from album_musicians import extract_album_musicians, find_artist_id

class MockNeo4jDatabase:
    """Mock database for testing the ingestion logic"""
    
    def __init__(self):
        self.artists = {}
        self.albums = {}
        self.tracks = {}
        self.collaborations = []
    
    def create_artist(self, artist_name, mbid=None, is_main_artist=False):
        """Mock artist creation"""
        artist_id = f"artist-{len(self.artists)}"
        self.artists[artist_name] = {
            'id': artist_id,
            'name': artist_name,
            'mbid': mbid or f"generated-{artist_name.lower().replace(' ', '-')}",
            'is_main_artist': is_main_artist
        }
        return artist_id
    
    def create_album(self, album_info, main_artist_name):
        """Mock album creation"""
        album_id = f"album-{len(self.albums)}"
        self.albums[album_info['title']] = {
            'id': album_id,
            'title': album_info['title'],
            'date': album_info.get('date', 'Unknown'),
            'main_artist': main_artist_name
        }
        return album_id
    
    def create_track(self, track_title, album_title, track_number=1):
        """Mock track creation"""
        track_id = f"track-{len(self.tracks)}"
        self.tracks[f"{album_title}-{track_title}"] = {
            'id': track_id,
            'title': track_title,
            'album': album_title,
            'track_number': track_number
        }
        return track_id
    
    def add_collaboration(self, musician_name, role, track_title, album_title, main_artist):
        """Mock collaboration creation"""
        self.collaborations.append({
            'musician': musician_name,
            'role': role,
            'track': track_title,
            'album': album_title,
            'main_artist': main_artist
        })
    
    def process_artist_data(self, artist_name, album_title=None, num_albums=3):
        """Process artist data and simulate Neo4j ingestion"""
        print(f"\n🧪 Testing data processing for: {artist_name}")
        
        # Create main artist
        try:
            artist_mbid = find_artist_id(artist_name)
            self.create_artist(artist_name, artist_mbid, is_main_artist=True)
            print(f"✅ Created main artist: {artist_name}")
        except Exception as e:
            print(f"⚠️  Could not find MBID for {artist_name}, using generated ID")
            self.create_artist(artist_name, is_main_artist=True)
        
        # Extract album musicians using existing function
        results = extract_album_musicians(artist_name, album_title, num_albums)
        
        if not results:
            print("❌ No album data to process")
            return
        
        # Process each album
        for result in results:
            album_info = result['album_info']
            musicians_data = result['musicians']
            
            print(f"\n📀 Processing album: {album_info['title']}")
            
            # Create album
            self.create_album(album_info, artist_name)
            
            # Group musicians by track
            tracks_musicians = {}
            for musician in musicians_data['all_musicians']:
                track = musician['song']
                if track not in tracks_musicians:
                    tracks_musicians[track] = []
                tracks_musicians[track].append(musician)
            
            # Process each track and its musicians
            track_number = 1
            for track_title, track_musicians in tracks_musicians.items():
                # Create track
                self.create_track(track_title, album_info['title'], track_number)
                
                # Add all musicians for this track
                unique_musicians = set()
                for musician in track_musicians:
                    musician_key = f"{musician['name']}-{musician['role']}"
                    if musician_key not in unique_musicians:
                        self.add_collaboration(
                            musician['name'],
                            musician['role'],
                            track_title,
                            album_info['title'],
                            artist_name
                        )
                        unique_musicians.add(musician_key)
                
                track_number += 1
            
            print(f"✅ Processed album: {album_info['title']}")
        
        print(f"\n🎉 Finished processing {artist_name}!")
    
    def get_stats(self):
        """Get statistics about processed data"""
        from collections import Counter
        
        print(f"\n📊 PROCESSING STATISTICS:")
        print(f"   • Total Artists: {len(self.artists)}")
        print(f"   • Total Albums: {len(self.albums)}")
        print(f"   • Total Tracks: {len(self.tracks)}")
        print(f"   • Total Collaborations: {len(self.collaborations)}")
        
        # Most common instruments
        roles = [collab['role'] for collab in self.collaborations]
        role_counts = Counter(roles)
        print(f"\n🎼 Most Common Instruments/Roles:")
        for role, count in role_counts.most_common(5):
            print(f"   • {role}: {count} times")
        
        # Most collaborative musicians (excluding main artist)
        musicians = [collab['musician'] for collab in self.collaborations 
                    if not self.artists.get(collab['musician'], {}).get('is_main_artist', False)]
        musician_counts = Counter(musicians)
        print(f"\n🤝 Most Collaborative Musicians:")
        for musician, count in musician_counts.most_common(5):
            print(f"   • {musician}: {count} collaborations")
        
        # Albums with most collaborators
        album_collaborators = {}
        for collab in self.collaborations:
            album = collab['album']
            if album not in album_collaborators:
                album_collaborators[album] = set()
            album_collaborators[album].add(collab['musician'])
        
        print(f"\n📀 Albums with Most Collaborators:")
        for album, collaborators in sorted(album_collaborators.items(), 
                                         key=lambda x: len(x[1]), reverse=True)[:3]:
            print(f"   • {album}: {len(collaborators)} collaborators")
    
    def export_for_neo4j(self, filename="neo4j_data.json"):
        """Export processed data in a format ready for Neo4j ingestion"""
        data = {
            'artists': list(self.artists.values()),
            'albums': list(self.albums.values()),
            'tracks': list(self.tracks.values()),
            'collaborations': self.collaborations
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Exported data to {filename} (ready for Neo4j ingestion)")
        return filename

def main():
    """Test the data processing pipeline"""
    try:
        # Create mock database
        mock_db = MockNeo4jDatabase()
        
        # Process artist data
        mock_db.process_artist_data("Miles Davis", num_albums=2)
        
        # Show statistics
        mock_db.get_stats()
        
        # Export data for actual Neo4j ingestion later
        mock_db.export_for_neo4j()
        
        print(f"\n✅ Test completed successfully!")
        print(f"\n💡 Next steps:")
        print(f"   1. Set up Neo4j database (Docker or Neo4j Desktop)")
        print(f"   2. Update NEO4J_PASSWORD in neo4j_ingest.py")
        print(f"   3. Run: python neo4j_ingest.py")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
