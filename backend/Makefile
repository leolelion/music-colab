.PHONY: help install-deps test test-neo4j test-graphql test-integration test-verbose test-coverage start-server start-neo4j stop-neo4j check-neo4j ingest-data dev setup

help:
	@echo "🎵 Music Colab Backend - Available Commands:"
	@echo ""
	@echo "📦 Setup & Dependencies:"
	@echo "  setup           - Complete setup (install deps + start Neo4j + ingest data)"
	@echo "  install-deps    - Install Python dependencies"
	@echo ""
	@echo "🗃️  Database Management:"
	@echo "  start-neo4j     - Start Neo4j database (Docker)"
	@echo "  stop-neo4j      - Stop Neo4j database"
	@echo "  check-neo4j     - Check Neo4j connection and data"
	@echo "  ingest-data     - Load Miles Davis test data into Neo4j"
	@echo ""
	@echo "🚀 Server Management:"
	@echo "  start-server    - Start FastAPI GraphQL server (port 8000)"
	@echo "  dev            - Start development mode (server with auto-reload)"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-neo4j     - Run Neo4j tests only"
	@echo "  test-graphql   - Run GraphQL tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-verbose   - Run tests with verbose output"
	@echo "  test-coverage  - Run tests with coverage report"

install-deps:
	pip install -r requirements.txt

test: install-deps
	pytest tests/ -v

test-neo4j: install-deps
	pytest tests/test_neo4j.py -v

test-graphql: install-deps
	pytest tests/test_graphql.py -v

test-integration: install-deps
	pytest tests/test_integration.py -v

test-verbose: install-deps
	pytest tests/ -v -s

test-coverage: install-deps
	pip install coverage
	coverage run -m pytest tests/
	coverage report
	coverage html

# Database Management
start-neo4j:
	@echo "🗃️  Starting Neo4j database..."
	cd .. && docker-compose up neo4j -d
	@echo "⏳ Waiting for Neo4j to be ready..."
	sleep 10
	@echo "✅ Neo4j should be ready at bolt://localhost:7687"

stop-neo4j:
	@echo "🛑 Stopping Neo4j database..."
	cd .. && docker-compose down

check-neo4j:
	@echo "🔍 Checking Neo4j connection and data..."
	@python3 -c "\
from py2neo import Graph; \
graph = Graph('bolt://localhost:7687', auth=('neo4j', 'password')); \
result = list(graph.run('MATCH (a:Artist {name: \"Miles Davis\"}) RETURN a LIMIT 1')); \
artist_count = list(graph.run('MATCH (a:Artist) RETURN count(a) as count'))[0]['count']; \
rel_count = list(graph.run('MATCH ()-[r:COLLABORATED_WITH]->() RETURN count(r) as count'))[0]['count']; \
print('✅ Neo4j connection successful'); \
print(f'📊 Database stats: {artist_count} artists, {rel_count} collaborations'); \
print('✅ Miles Davis data found' if result else '❌ Miles Davis data missing - run make ingest-data')"

ingest-data:
	@echo "📥 Ingesting Miles Davis collaboration data..."
	cd ../scripts && python3 ingest_real_data.py
	@echo "✅ Data ingestion complete!"

# Server Management  
start-server: install-deps
	@echo "🚀 Starting FastAPI GraphQL server on http://localhost:8000..."
	@echo "📊 GraphQL Playground: http://localhost:8000/graphql"
	python3 main.py

dev: install-deps
	@echo "🔄 Starting FastAPI server in development mode (auto-reload)..."
	@echo "📊 GraphQL Playground: http://localhost:8000/graphql"
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Complete Setup
setup: install-deps start-neo4j ingest-data
	@echo "🎉 Setup complete! You can now:"
	@echo "   • Run 'make start-server' to start the API server"
	@echo "   • Run 'make test' to run tests"
	@echo "   • Visit http://localhost:8000/graphql for GraphQL playground"
