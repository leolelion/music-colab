"""
Test configuration and fixtures
"""
import pytest
import os
from py2neo import Graph
from fastapi.testclient import TestClient
from main import app, schema
from strawberry.asgi import GraphQL

# Test Neo4j configuration
TEST_NEO4J_URI = os.getenv("TEST_NEO4J_URI", "bolt://localhost:7687")
TEST_NEO4J_USER = os.getenv("TEST_NEO4J_USER", "neo4j")
TEST_NEO4J_PASSWORD = os.getenv("TEST_NEO4J_PASSWORD", "password")

@pytest.fixture
def neo4j_graph():
    """Fixture to provide Neo4j graph connection for testing"""
    graph = Graph(TEST_NEO4J_URI, auth=(TEST_NEO4J_USER, TEST_NEO4J_PASSWORD))
    return graph

@pytest.fixture
def client():
    """Fixture to provide FastAPI test client"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def graphql_client():
    """Fixture to provide GraphQL test client"""
    from strawberry.test import BaseGraphQLTestClient
    
    class GraphQLTestClient(BaseGraphQLTestClient):
        def request(self, body, headers=None):
            # This is a simple implementation for testing
            return {"data": None}
    
    return GraphQLTestClient(schema)

@pytest.fixture(scope="function")
def setup_test_data(neo4j_graph):
    """Fixture to set up test data and clean up after test"""
    # Clean up any existing test data
    neo4j_graph.run("MATCH (n:Artist) WHERE n.name CONTAINS 'Test' DELETE n")
    
    # Create test data
    test_data_query = """
    CREATE (miles:Artist {name: 'Test Miles Davis', mbid: 'test-miles-mbid'})
    CREATE (coltrane:Artist {name: 'Test John Coltrane', mbid: 'test-coltrane-mbid'})
    CREATE (evans:Artist {name: 'Test Bill Evans', mbid: 'test-evans-mbid'})
    
    CREATE (miles)-[:COLLABORATED_WITH {shared_albums: ['Test Kind of Blue'], weight: 1}]->(coltrane)
    CREATE (miles)-[:COLLABORATED_WITH {shared_albums: ['Test Kind of Blue'], weight: 1}]->(evans)
    CREATE (coltrane)-[:COLLABORATED_WITH {shared_albums: ['Test Kind of Blue'], weight: 1}]->(evans)
    
    RETURN miles, coltrane, evans
    """
    
    neo4j_graph.run(test_data_query)
    
    yield
    
    # Clean up after test
    neo4j_graph.run("MATCH (n:Artist) WHERE n.name CONTAINS 'Test' DETACH DELETE n")
