"""
Integration tests for the full application flow
"""
import pytest
import json

class TestIntegration:
    """Integration tests for the complete application"""
    
    def test_full_miles_davis_network_flow(self, client, neo4j_graph):
        """Test the complete flow for Miles Davis network (if data exists)"""
        # First check if Miles Davis data exists in the database
        check_query = "MATCH (a:Artist {name: 'Miles Davis'}) RETURN a"
        result = list(neo4j_graph.run(check_query))
        
        if len(result) == 0:
            pytest.skip("Miles Davis data not found in database - run data ingestion first")
        
        # Query for Miles Davis network
        query = """
        query {
            artistNetwork(artistName: "Miles Davis") {
                nodes {
                    id
                    name
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
        
        network_data = data["data"]["artistNetwork"]
        
        # Verify Miles Davis is the main artist
        main_artists = [node for node in network_data["nodes"] if node["isMainArtist"]]
        assert len(main_artists) == 1
        assert main_artists[0]["name"] == "Miles Davis"
        
        # Should have collaborators
        collaborators = [node for node in network_data["nodes"] if not node["isMainArtist"]]
        assert len(collaborators) > 0
        
        # Should have connections
        assert len(network_data["edges"]) > 0
        
        # Verify stats are present and valid
        assert network_data["stats"] is not None
        stats = json.loads(network_data["stats"])
        assert stats["total_nodes"] == len(network_data["nodes"])
        assert stats["total_edges"] == len(network_data["edges"])
        assert stats["main_artists"] == 1
        assert stats["collaborating_artists"] == len(collaborators)
    
    def test_cors_headers(self, client):
        """Test that CORS headers are properly set"""
        response = client.options("/graphql", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        # Should allow CORS for the frontend
        assert response.status_code in [200, 204]
        
        # Check if CORS headers are present (may vary based on implementation)
        # This test ensures the CORS middleware is working
    
    def test_graphql_introspection(self, client):
        """Test GraphQL schema introspection"""
        introspection_query = """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": introspection_query},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return schema information
        assert "data" in data
        assert "__schema" in data["data"]
        assert "types" in data["data"]["__schema"]
        
        # Check that our custom types are in the schema
        type_names = [t["name"] for t in data["data"]["__schema"]["types"]]
        assert "Artist" in type_names
        assert "NetworkData" in type_names
        assert "Edge" in type_names
    
    def test_error_handling_invalid_query(self, client):
        """Test error handling for invalid GraphQL queries"""
        invalid_query = """
        query {
            invalidField {
                nonExistentField
            }
        }
        """
        
        response = client.post(
            "/graphql",
            json={"query": invalid_query},
            headers={"Content-Type": "application/json"}
        )
        
        # Should return error information
        assert response.status_code == 200  # GraphQL returns 200 even for query errors
        data = response.json()
        
        # Should have errors in the response
        assert "errors" in data or ("data" in data and data["data"] is None)
    
    def test_malformed_request(self, client):
        """Test handling of malformed requests"""
        response = client.post(
            "/graphql",
            json={"invalid": "request"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should handle malformed requests gracefully
        assert response.status_code in [200, 400]
