"""
Tests for GraphQL API endpoints
"""
import pytest
import json
from fastapi.testclient import TestClient

class TestGraphQLAPI:
    """Test class for GraphQL API operations"""
    
    def test_graphql_endpoint_exists(self, client):
        """Test that GraphQL endpoint is accessible"""
        response = client.get("/graphql")
        # GraphQL endpoint should respond (even if it's a GET request)
        assert response.status_code in [200, 405]  # 405 = Method Not Allowed is OK for GraphQL
    
    def test_artist_network_query_structure(self, client, setup_test_data):
        """Test the structure of artist network GraphQL query"""
        query = """
        query {
            artistNetwork(artistName: "Test Miles Davis") {
                nodes {
                    id
                    name
                    mbid
                    isMainArtist
                    connectionCount
                }
                edges {
                    source
                    target
                    weight
                    sharedAlbums
                }
                stats
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "data" in data
        assert "artistNetwork" in data["data"]
        
        network_data = data["data"]["artistNetwork"]
        assert "nodes" in network_data
        assert "edges" in network_data
        assert "stats" in network_data
        
        # Verify nodes structure
        if network_data["nodes"]:
            node = network_data["nodes"][0]
            required_node_fields = ["id", "name", "mbid", "isMainArtist", "connectionCount"]
            for field in required_node_fields:
                assert field in node
        
        # Verify edges structure
        if network_data["edges"]:
            edge = network_data["edges"][0]
            required_edge_fields = ["source", "target", "weight", "sharedAlbums"]
            for field in required_edge_fields:
                assert field in edge
    
    def test_artist_network_with_test_data(self, client, setup_test_data):
        """Test artist network query with known test data"""
        query = """
        query {
            artistNetwork(artistName: "Test Miles Davis") {
                nodes {
                    id
                    name
                    isMainArtist
                }
                edges {
                    source
                    target
                    sharedAlbums
                }
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        network_data = data["data"]["artistNetwork"]
        
        # Should have Miles Davis as main artist
        main_artists = [node for node in network_data["nodes"] if node["isMainArtist"]]
        assert len(main_artists) == 1
        assert main_artists[0]["name"] == "Test Miles Davis"
        
        # Should have collaborators
        collaborators = [node for node in network_data["nodes"] if not node["isMainArtist"]]
        assert len(collaborators) >= 2
        
        # Should have edges connecting artists
        assert len(network_data["edges"]) >= 2
        
        # All edges should involve Miles Davis
        miles_davis_edges = [
            edge for edge in network_data["edges"] 
            if edge["source"] == "Test Miles Davis" or edge["target"] == "Test Miles Davis"
        ]
        assert len(miles_davis_edges) >= 2
    
    def test_artist_query(self, client, setup_test_data):
        """Test individual artist query"""
        query = """
        query {
            artist(name: "Test Miles Davis") {
                id
                name
                mbid
                isMainArtist
                connectionCount
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        artist_data = data["data"]["artist"]
        assert artist_data is not None
        assert artist_data["name"] == "Test Miles Davis"
        assert artist_data["mbid"] == "test-miles-mbid"
    
    def test_artist_not_found(self, client):
        """Test querying for non-existent artist"""
        query = """
        query {
            artist(name: "Non Existent Artist") {
                id
                name
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return null for non-existent artist
        assert data["data"]["artist"] is None
    
    def test_network_query_with_nonexistent_artist(self, client):
        """Test network query for non-existent artist"""
        query = """
        query {
            artistNetwork(artistName: "Non Existent Artist") {
                nodes {
                    id
                    name
                }
                edges {
                    source
                    target
                }
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        network_data = data["data"]["artistNetwork"]
        
        # Should return empty or minimal data for non-existent artist
        assert len(network_data["nodes"]) == 0
        assert len(network_data["edges"]) == 0
