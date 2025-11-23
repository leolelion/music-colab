from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL
import strawberry
from py2neo import Graph
from typing import List, Optional
import os

app = FastAPI()

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Neo4j connection
NEO4J_BOLT_URL = os.getenv("NEO4J_BOLT_URL", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

graph = Graph(NEO4J_BOLT_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))

@strawberry.type
class Artist:
    id: str
    name: str
    mbid: Optional[str]
    is_main_artist: bool
    connection_count: int
    primary_instruments: List[str]  # Most common instruments/roles

@strawberry.type
class Edge:
    source: str
    target: str
    weight: int
    shared_albums: List[str]
    collaboration_roles: List[str]  # Roles they played together

@strawberry.type
class NetworkData:
    nodes: List[Artist]
    edges: List[Edge]
    stats: Optional[str]  # JSON string for stats

@strawberry.type
class Query:
    @strawberry.field
    def artist_network(self, artist_name: str = "Miles Davis") -> NetworkData:
        """Get the collaboration network for a specific artist"""
        
        # Query to get all artists in the network (main artist + collaborators + their interconnections)
        artist_query = """
        // First, get all artists directly connected to the main artist
        MATCH (main:Artist {name: $artist_name})
        OPTIONAL MATCH (main)-[r1:COLLABORATED_WITH]-(collaborator:Artist)
        WITH main, collect(DISTINCT collaborator) as collaborators
        
        // Then get all connections within this network (main + collaborators)
        UNWIND (collaborators + [main]) as artist1
        UNWIND (collaborators + [main]) as artist2
        MATCH (artist1)-[r:COLLABORATED_WITH]-(artist2)
        WHERE ID(artist1) < ID(artist2)  // Avoid duplicate edges
        
        // Get instrument data for each artist
        OPTIONAL MATCH (artist1)-[perf1:PERFORMED_ON]->()
        OPTIONAL MATCH (artist2)-[perf2:PERFORMED_ON]->()
        
        WITH artist1, artist2, r, 
             collect(DISTINCT perf1.role) as artist1_roles,
             collect(DISTINCT perf2.role) as artist2_roles
        
        RETURN artist1 as source_artist, artist2 as target_artist, 
               r.shared_albums as shared_albums, r.strength as weight,
               artist1_roles, artist2_roles,
               [role IN r.roles WHERE role IS NOT NULL] as collaboration_roles
        """
        
        result = graph.run(artist_query, artist_name=artist_name)
        
        nodes = {}
        edges = []
        
        for record in result:
            source_artist = record["source_artist"]
            target_artist = record["target_artist"]
            shared_albums = record["shared_albums"] or []
            weight = record["weight"] or len(shared_albums)
            artist1_roles = [r for r in (record["artist1_roles"] or []) if r]
            artist2_roles = [r for r in (record["artist2_roles"] or []) if r]
            collaboration_roles = [r for r in (record["collaboration_roles"] or []) if r]
            
            # Add source artist
            source_id = source_artist["name"]
            if source_id not in nodes:
                # Get top 3 most common instruments for this artist
                top_instruments = artist1_roles[:3] if artist1_roles else []
                nodes[source_id] = Artist(
                    id=source_id,
                    name=source_artist["name"],
                    mbid=source_artist.get("mbid"),
                    is_main_artist=(source_id == artist_name),
                    connection_count=0,  # Will calculate later
                    primary_instruments=top_instruments
                )
            
            # Add target artist
            target_id = target_artist["name"]
            if target_id not in nodes:
                # Get top 3 most common instruments for this artist
                top_instruments = artist2_roles[:3] if artist2_roles else []
                nodes[target_id] = Artist(
                    id=target_id,
                    name=target_artist["name"],
                    mbid=target_artist.get("mbid"),
                    is_main_artist=(target_id == artist_name),
                    connection_count=0,  # Will calculate later
                    primary_instruments=top_instruments
                )
            
            # Add edge
            edges.append(Edge(
                source=source_id,
                target=target_id,
                weight=weight,
                shared_albums=shared_albums,
                collaboration_roles=collaboration_roles
            ))
        
        # Calculate connection counts
        for node_id in nodes:
            connection_count = len([e for e in edges if e.source == node_id or e.target == node_id])
            nodes[node_id].connection_count = connection_count
        
        # Create stats
        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "main_artists": 1,
            "collaborating_artists": len(nodes) - 1
        }
        
        import json
        return NetworkData(
            nodes=list(nodes.values()),
            edges=edges,
            stats=json.dumps(stats)  # Convert to proper JSON string
        )
    
    @strawberry.field
    def full_network(self) -> NetworkData:
        """Get the complete collaboration network (all artists and their connections)"""
        
        # Query to get all artists and all their connections
        full_network_query = """
        MATCH (a1:Artist)-[r:COLLABORATED_WITH]-(a2:Artist)
        WHERE ID(a1) < ID(a2)  // Avoid duplicate edges
        
        // Get instrument data for each artist
        OPTIONAL MATCH (a1)-[perf1:PERFORMED_ON]->()
        OPTIONAL MATCH (a2)-[perf2:PERFORMED_ON]->()
        
        WITH a1, a2, r, 
             collect(DISTINCT perf1.role) as artist1_roles,
             collect(DISTINCT perf2.role) as artist2_roles
        
        RETURN a1 as source_artist, a2 as target_artist, 
               r.shared_albums as shared_albums, r.strength as weight,
               artist1_roles, artist2_roles,
               [role IN r.roles WHERE role IS NOT NULL] as collaboration_roles
        """
        
        result = graph.run(full_network_query)
        
        nodes = {}
        edges = []
        
        for record in result:
            source_artist = record["source_artist"]
            target_artist = record["target_artist"]
            shared_albums = record["shared_albums"] or []
            weight = record["weight"] or len(shared_albums)
            artist1_roles = [r for r in (record["artist1_roles"] or []) if r]
            artist2_roles = [r for r in (record["artist2_roles"] or []) if r]
            collaboration_roles = [r for r in (record["collaboration_roles"] or []) if r]
            
            # Add source artist
            source_id = source_artist["name"]
            if source_id not in nodes:
                # Get top 3 most common instruments for this artist
                top_instruments = artist1_roles[:3] if artist1_roles else []
                nodes[source_id] = Artist(
                    id=source_id,
                    name=source_artist["name"],
                    mbid=source_artist.get("mbid"),
                    is_main_artist=source_artist.get("is_main_artist", False),
                    connection_count=0,
                    primary_instruments=top_instruments
                )
            
            # Add target artist
            target_id = target_artist["name"]
            if target_id not in nodes:
                # Get top 3 most common instruments for this artist
                top_instruments = artist2_roles[:3] if artist2_roles else []
                nodes[target_id] = Artist(
                    id=target_id,
                    name=target_artist["name"],
                    mbid=target_artist.get("mbid"),
                    is_main_artist=target_artist.get("is_main_artist", False),
                    connection_count=0,
                    primary_instruments=top_instruments
                )
            
            # Add edge
            edges.append(Edge(
                source=source_id,
                target=target_id,
                weight=weight,
                shared_albums=shared_albums,
                collaboration_roles=collaboration_roles
            ))
        
        # Calculate connection counts
        for node_id in nodes:
            connection_count = len([e for e in edges if e.source == node_id or e.target == node_id])
            nodes[node_id].connection_count = connection_count
        
        # Create stats
        main_artist_count = len([n for n in nodes.values() if n.is_main_artist])
        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "main_artists": main_artist_count,
            "collaborating_artists": len(nodes) - main_artist_count
        }
        
        import json
        return NetworkData(
            nodes=list(nodes.values()),
            edges=edges,
            stats=json.dumps(stats)
        )
    
    @strawberry.field
    def artist(self, name: str) -> Optional[Artist]:
        """Get details for a specific artist"""
        query = """
        MATCH (a:Artist {name: $name})
        OPTIONAL MATCH (a)-[perf:PERFORMED_ON]->()
        WITH a, collect(DISTINCT perf.role) as roles
        RETURN a, [role IN roles WHERE role IS NOT NULL][..3] as top_instruments
        """
        result = graph.run(query, name=name)
        record = result.data()
        
        if record:
            artist_data = record[0]["a"]
            top_instruments = [r for r in (record[0]["top_instruments"] or []) if r]
            return Artist(
                id=artist_data["name"],
                name=artist_data["name"],
                mbid=artist_data.get("mbid"),
                is_main_artist=artist_data.get("is_main_artist", False),
                connection_count=0,
                primary_instruments=top_instruments
            )
        return None
    
    @strawberry.field
    def main_artists(self) -> List[Artist]:
        """Get all main artists in the database"""
        query = """
        MATCH (a:Artist {is_main_artist: true})
        OPTIONAL MATCH (a)-[r:COLLABORATED_WITH]-()
        OPTIONAL MATCH (a)-[perf:PERFORMED_ON]->()
        WITH a, count(DISTINCT r) as connection_count, collect(DISTINCT perf.role) as roles
        RETURN a, connection_count, [role IN roles WHERE role IS NOT NULL][..3] as top_instruments
        ORDER BY a.name
        """
        result = graph.run(query)
        
        artists = []
        for record in result:
            artist_data = record["a"]
            connection_count = record["connection_count"]
            top_instruments = [r for r in (record["top_instruments"] or []) if r]
            artists.append(Artist(
                id=artist_data["name"],
                name=artist_data["name"],
                mbid=artist_data.get("mbid"),
                is_main_artist=True,
                connection_count=connection_count,
                primary_instruments=top_instruments
            ))
        
        return artists
    
    @strawberry.field
    def search_artists(self, query: str, limit: int = 20) -> List[Artist]:
        """Search for artists by name"""
        search_query = """
        MATCH (a:Artist)
        WHERE toLower(a.name) CONTAINS toLower($query)
        OPTIONAL MATCH (a)-[r:COLLABORATED_WITH]-()
        OPTIONAL MATCH (a)-[perf:PERFORMED_ON]->()
        WITH a, count(DISTINCT r) as connection_count, collect(DISTINCT perf.role) as roles
        RETURN a, connection_count, [role IN roles WHERE role IS NOT NULL][..3] as top_instruments
        ORDER BY a.is_main_artist DESC, connection_count DESC, a.name
        LIMIT $limit
        """
        result = graph.run(search_query, query=query, limit=limit)
        
        artists = []
        for record in result:
            artist_data = record["a"]
            connection_count = record["connection_count"]
            top_instruments = [r for r in (record["top_instruments"] or []) if r]
            artists.append(Artist(
                id=artist_data["name"],
                name=artist_data["name"],
                mbid=artist_data.get("mbid"),
                is_main_artist=artist_data.get("is_main_artist", False),
                connection_count=connection_count,
                primary_instruments=top_instruments
            ))
        
        return artists

schema = strawberry.Schema(query=Query)
app.add_route("/graphql", GraphQL(schema))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)