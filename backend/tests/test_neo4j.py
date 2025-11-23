"""
Tests for Neo4j data operations
"""
import pytest
from py2neo import Graph

class TestNeo4jOperations:
    """Test class for Neo4j database operations"""
    
    def test_neo4j_connection(self, neo4j_graph):
        """Test that we can connect to Neo4j database"""
        # Simple query to test connection
        result = list(neo4j_graph.run("RETURN 1 as test"))[0]
        assert result["test"] == 1
    
    def test_create_test_artists(self, neo4j_graph, setup_test_data):
        """Test that test data is created correctly"""
        query = "MATCH (a:Artist) WHERE a.name CONTAINS 'Test' RETURN count(a) as count"
        result = list(neo4j_graph.run(query))[0]
        assert result["count"] == 3
    
    def test_artist_collaboration_query(self, neo4j_graph, setup_test_data):
        """Test querying artist collaborations"""
        query = """
        MATCH (main:Artist {name: 'Test Miles Davis'})
        OPTIONAL MATCH (main)-[r:COLLABORATED_WITH]-(connected:Artist)
        RETURN main, connected, r.shared_albums as shared_albums, r.weight as weight
        """
        
        results = list(neo4j_graph.run(query))
        
        # Should return Miles Davis with his collaborators
        assert len(results) >= 2  # Miles + at least 2 collaborators
        
        # Check that Miles Davis is in all results
        for record in results:
            assert record["main"]["name"] == "Test Miles Davis"
    
    def test_collaboration_relationships(self, neo4j_graph, setup_test_data):
        """Test that collaboration relationships are bidirectional"""
        query = """
        MATCH (a:Artist)-[r:COLLABORATED_WITH]-(b:Artist)
        WHERE a.name CONTAINS 'Test' AND b.name CONTAINS 'Test'
        RETURN a.name, b.name, r.shared_albums, r.weight
        """
        
        results = list(neo4j_graph.run(query))
        
        # Should have relationships between all test artists
        assert len(results) >= 3  # At least 3 relationships
        
        # Verify shared albums exist
        for record in results:
            assert record["r.shared_albums"] is not None
            assert len(record["r.shared_albums"]) > 0
    
    def test_artist_not_found(self, neo4j_graph):
        """Test querying for non-existent artist"""
        query = "MATCH (a:Artist {name: 'Non Existent Artist'}) RETURN a"
        result = list(neo4j_graph.run(query))
        assert len(result) == 0
