from neo4j import GraphDatabase
import json
import os
from dotenv import load_dotenv
from album_musicians import extract_album_musicians, find_artist_id

# Load environment variables from .env file
load_dotenv(dotenv_path='.env')

class MusicCollabDatabase:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_constraints(self):
        """Create unique constraints and indexes for better performance"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT artist_mbid IF NOT EXISTS FOR (a:Artist) REQUIRE a.mbid IS UNIQUE",
                "CREATE CONSTRAINT album_mbid IF NOT EXISTS FOR (al:Album) REQUIRE al.mbid IS UNIQUE",
                "CREATE CONSTRAINT track_title_album IF NOT EXISTS FOR (t:Track) REQUIRE (t.title, t.album_mbid) IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"✅ Created constraint")
                except Exception as e:
                    print(f"⚠️  Constraint may already exist")

    def create_or_update_artist(self, session, artist_name, mbid=None, is_main_artist=False):
        """Create or update an artist node"""
        query = """
        MERGE (a:Artist {name: $name})
        ON CREATE SET a.created_at = datetime()
        ON MATCH SET a.updated_at = datetime()
        SET a.mbid = COALESCE(a.mbid, $mbid),
            a.performance_name = $name,
            a.is_main_artist = COALESCE(a.is_main_artist, $is_main_artist)
        RETURN a
        """
        return session.run(query, 
                          name=artist_name,
                          mbid=mbid or f"generated-{artist_name.lower().replace(' ', '-')}",
                          is_main_artist=is_main_artist)

    def create_or_update_album(self, session, album_info, main_artist_name):
        """Create or update an album node and link to main artist"""
        # Parse date
        release_date = album_info.get('date', 'Unknown')
        if release_date == 'Unknown' or not release_date:
            release_date = '1900-01-01'
        elif len(release_date) == 4:  # Just year
            release_date = f"{release_date}-01-01"
        elif len(release_date) == 7:  # Year-month
            release_date = f"{release_date}-01"

        query = """
        MERGE (al:Album {title: $title, main_artist: $main_artist})
        ON CREATE SET
            al.created_at = datetime(),
            al.mbid = $mbid,
            al.release_date = date($release_date)
        ON MATCH SET
            al.updated_at = datetime()

        /* Link to main artist */
        WITH al
        MATCH (a:Artist {name: $main_artist})
        MERGE (a)-[:RELEASED]->(al)

        RETURN al
        """

        
        album_mbid = f"album-{album_info['title'].lower().replace(' ', '-')}-{main_artist_name.lower().replace(' ', '-')}"
        
        return session.run(query,
                          title=album_info['title'],
                          main_artist=main_artist_name,
                          mbid=album_mbid,
                          release_date=release_date)

    def create_track(self, session, track_title, album_title, main_artist, track_number=1):
        """Create a track and link to album"""
        query = """
        MATCH (al:Album {title: $album_title, main_artist: $main_artist})
        MERGE (t:Track {title: $track_title, album_mbid: al.mbid})
        ON CREATE SET
            t.created_at = datetime(),
            t.track_number = $track_number
        ON MATCH SET
            t.updated_at = datetime(),
            t.track_number = $track_number

        /* Link track to album */
        MERGE (al)-[:CONTAINS]->(t)

        RETURN t
        """

        return session.run(query,
                        track_title=track_title,
                        album_title=album_title,
                        main_artist=main_artist,
                        track_number=track_number)


    def create_collaboration(self, session, musician_name, role, track_title, album_title, main_artist):
        """Create collaboration relationships between artist and track/album"""
        
        # Create the collaborating artist if not exists
        self.create_or_update_artist(session, musician_name, is_main_artist=False)
        
        # Create relationship to track
        track_collab_query = """
        MATCH (artist:Artist {name: $musician_name})
        MATCH (album:Album {title: $album_title, main_artist: $main_artist})
        MATCH (track:Track {title: $track_title, album_mbid: album.mbid})

        MERGE (artist)-[r:PERFORMED_ON]->(track)
        ON CREATE SET
            r.created_at = datetime(),
            r.role = $role,
            r.instrument = $role
        ON MATCH SET
            r.updated_at = datetime(),
            r.role = $role,
            r.instrument = $role

        RETURN r
        """

        
        # Create aggregated relationship to album
        album_collab_query = """
        MATCH (artist:Artist {name: $musician_name})
        MATCH (album:Album {title: $album_title, main_artist: $main_artist})

        MERGE (artist)-[r:COLLABORATED_ON]->(album)
        ON CREATE SET
            r.roles = [$role],
            r.track_count = 1,
            r.created_at = datetime()
        ON MATCH SET
            r.roles = CASE
                WHEN $role IN r.roles THEN r.roles
                ELSE r.roles + $role
            END,
            r.track_count = r.track_count + 1,
            r.updated_at = datetime()

        RETURN r
        """
        
        session.run(track_collab_query, 
                   musician_name=musician_name,
                   role=role,
                   track_title=track_title,
                   album_title=album_title,
                   main_artist=main_artist)
        
        session.run(album_collab_query,
                   musician_name=musician_name,
                   role=role,
                   album_title=album_title,
                   main_artist=main_artist)

    def ingest_artist_albums(self, artist_name, album_title=None, num_albums=5):
        """Main function to ingest an artist and their albums with all collaborators"""
        print(f"\n🎵 Starting Neo4j ingestion for: {artist_name}")
        
        with self.driver.session() as session:
            # Create main artist with MBID
            try:
                artist_mbid = find_artist_id(artist_name)
                self.create_or_update_artist(session, artist_name, artist_mbid, is_main_artist=True)
                print(f"✅ Created main artist: {artist_name}")
            except Exception as e:
                print(f"⚠️  Could not find MBID for {artist_name}, using generated ID")
                self.create_or_update_artist(session, artist_name, is_main_artist=True)
            
            # Extract album musicians using your existing function
            results = extract_album_musicians(artist_name, album_title, num_albums)
            
            if not results:
                print("❌ No album data to ingest")
                return
            
            # Process each album
            for result in results:
                album_info = result['album_info']
                musicians_data = result['musicians']
                
                print(f"\n📀 Ingesting album: {album_info['title']}")
                
                # Create album
                self.create_or_update_album(session, album_info, artist_name)
                
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
                    self.create_track(session, track_title, album_info['title'], artist_name, track_number)
                    
                    # Add all musicians for this track
                    for musician in track_musicians:
                        self.create_collaboration(
                            session,
                            musician['name'],
                            musician['role'],
                            track_title,
                            album_info['title'],
                            artist_name
                        )
                    
                    track_number += 1
                
                print(f"✅ Completed album: {album_info['title']}")
        
        print(f"\n🎉 Finished Neo4j ingestion for {artist_name}!")

    def get_collaboration_stats(self):
        """Get some basic stats about the ingested data"""
        with self.driver.session() as session:
            queries = {
                "Total Artists": "MATCH (a:Artist) RETURN count(a) as count",
                "Total Albums": "MATCH (al:Album) RETURN count(al) as count", 
                "Total Tracks": "MATCH (t:Track) RETURN count(t) as count",
                "Total Collaborations": "MATCH ()-[r:COLLABORATED_ON]->() RETURN count(r) as count",
                "Most Collaborative Artist": """
                    MATCH (a:Artist)-[r:COLLABORATED_ON]->(al:Album)
                    RETURN a.name, count(al) as albums_collaborated_on
                    ORDER BY albums_collaborated_on DESC LIMIT 1
                """,
                "Most Common Instruments": """
                    MATCH ()-[r:PERFORMED_ON]->()
                    RETURN r.role, count(*) as frequency
                    ORDER BY frequency DESC LIMIT 5
                """
            }
            
            print("\n📊 DATABASE STATISTICS:")
            for stat_name, query in queries.items():
                result = session.run(query)
                if stat_name in ["Most Collaborative Artist", "Most Common Instruments"]:
                    records = result.data()
                    print(f"   • {stat_name}:")
                    for record in records:
                        if stat_name == "Most Collaborative Artist":
                            print(f"     - {record['a.name']}: {record['albums_collaborated_on']} albums")
                        else:
                            print(f"     - {record['r.role']}: {record['frequency']} times")
                else:
                    count = result.single()['count']
                    print(f"   • {stat_name}: {count}")

    def create_artist_connections(self):
        """Create direct COLLABORATED_WITH relationships between artists for faster visualization"""
        print("🔗 Creating direct artist-to-artist connections...")
        
        with self.driver.session() as session:
            # Create direct artist connections based on shared albums
            query = """
            MATCH (a1:Artist)-[:COLLABORATED_ON]->(album)<-[:COLLABORATED_ON]-(a2:Artist)
            WHERE a1.name < a2.name
            WITH a1, a2, count(album) as collaboration_count, collect(album.title) as shared_albums
            
            MERGE (a1)-[r:COLLABORATED_WITH]-(a2)
            ON CREATE SET r.created_at = datetime()
            ON MATCH SET r.updated_at = datetime()
            SET r.strength = collaboration_count,
                r.shared_albums = shared_albums
            
            RETURN count(r) as connections_created
            """
            
            result = session.run(query)
            connections = result.single()["connections_created"]
            print(f"✅ Created {connections} direct artist connections")
            
            return connections

    def get_artist_network(self, artist_name=None, limit=50):
        """Get artist network data optimized for frontend visualization"""
        with self.driver.session() as session:
            if artist_name:
                # Get network centered on specific artist
                query = """
                MATCH (center:Artist {name: $artist_name})
                OPTIONAL MATCH (center)-[r:COLLABORATED_WITH]-(connected:Artist)
                WITH center, collect({
                    artist: connected.name,
                    strength: r.strength,
                    shared_albums: r.shared_albums
                }) as connections
                RETURN {
                    center_artist: center.name,
                    connections: connections,
                    total_connections: size(connections)
                } as network
                """
                result = session.run(query, artist_name=artist_name)
                return [record["network"] for record in result]
            else:
                # Get full network (limited for performance)
                query = """
                MATCH (a1:Artist)-[r:COLLABORATED_WITH]-(a2:Artist)
                RETURN {
                    artist1: a1.name,
                    artist2: a2.name,
                    strength: r.strength,
                    shared_albums: r.shared_albums
                } as connection
                LIMIT $limit
                """
                result = session.run(query, limit=limit)
                return [record["connection"] for record in result]

    def get_visualization_data(self):
        """Get all data needed for frontend network visualization"""
        with self.driver.session() as session:
            # Get all artists with their connection counts (for node sizing)
            nodes_query = """
            MATCH (a:Artist)
            OPTIONAL MATCH (a)-[r:COLLABORATED_WITH]-()
            WITH a, count(r) as connection_count
            RETURN {
                id: a.name,
                name: a.name,
                is_main_artist: a.is_main_artist,
                connection_count: connection_count,
                mbid: a.mbid
            } as node
            ORDER BY a.is_main_artist DESC, a.name
            """
            
            # Get all connections (for edges)  
            edges_query = """
            MATCH (a1:Artist)-[r:COLLABORATED_WITH]-(a2:Artist)
            WHERE a1.name < a2.name
            RETURN {
                source: a1.name,
                target: a2.name,
                weight: r.strength,
                shared_albums: r.shared_albums
            } as edge
            """
            
            nodes = [record["node"] for record in session.run(nodes_query)]
            edges = [record["edge"] for record in session.run(edges_query)]
            
            return {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "main_artists": len([n for n in nodes if n["is_main_artist"]]),
                    "collaborating_artists": len([n for n in nodes if not n["is_main_artist"]])
                }
            }

def main():
    # Load Neo4j credentials from environment variables
    NEO4J_URI = os.getenv('NEO4J_BOLT_URL')
    NEO4J_USER = os.getenv('NEO4J_USER')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    
    if not NEO4J_PASSWORD:
        print("❌ Error: NEO4J_PASSWORD not found in environment variables!")
        print("   Please check your .env file contains NEO4J_PASSWORD=your_password")
        return
    
    print(f"🔧 Connecting to Neo4j at: {NEO4J_URI}")
    print(f"🔧 Using user: {NEO4J_USER}")
    
    try:
        # Create database connection
        db = MusicCollabDatabase(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        # Create constraints for better performance
        print("🔧 Setting up database constraints...")
        db.create_constraints()
        
        # Ingest artist data - you can modify these parameters
        print("🎵 Starting data ingestion...")
        # db.ingest_artist_albums("Miles Davis", num_albums=3)
        
        # You can add more artists here
        # db.ingest_artist_albums("Neil Young", num_albums=2)
        db.ingest_artist_albums("John Coltrane", num_albums=2)
        # db.ingest_artist_albums("Charlie Parker", num_albums=2)
        
        # CREATE OPTIMIZED ARTIST CONNECTIONS FOR FRONTEND
        print("\n🔗 Creating optimized artist connections for frontend...")
        connections_created = db.create_artist_connections()
        
        # Test the network query
        print("\n🕸️  Testing artist network queries...")
        network = db.get_artist_network("Miles Davis")
        if network and network[0]['total_connections'] > 0:
            print(f"✅ Miles Davis connected to {network[0]['total_connections']} artists")
            print("🔗 Top connections:")
            for conn in network[0]['connections'][:5]:
                albums_str = ', '.join(conn['shared_albums'][:2])
                if len(conn['shared_albums']) > 2:
                    albums_str += f" (+{len(conn['shared_albums'])-2} more)"
                print(f"   • {conn['artist']}: {conn['strength']} albums ({albums_str})")
        else:
            print("⚠️  No connections found for Miles Davis")
        
        # Get full visualization data
        print("\n📊 Getting visualization data...")
        viz_data = db.get_visualization_data()
        print(f"✅ Visualization data ready:")
        print(f"   • {viz_data['stats']['total_nodes']} nodes ({viz_data['stats']['main_artists']} main artists)")
        print(f"   • {viz_data['stats']['total_edges']} edges")
        
        # Show some example connections
        if viz_data['edges']:
            print(f"\n🔗 Sample connections:")
            for edge in viz_data['edges'][:5]:
                print(f"   • {edge['source']} ↔ {edge['target']} (strength: {edge['weight']})")
        
        # Show basic statistics
        db.get_collaboration_stats()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            db.close()
        except:
            pass

if __name__ == "__main__":
    main()
