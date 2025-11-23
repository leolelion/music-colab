.PHONY: help setup start-all stop-all status test-all clean-all backend-dev frontend-dev full-dev

help:
	@echo "🎵 Music Colab - Full Stack Project Management"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  setup          - Complete project setup (install deps, start Neo4j, ingest data)"
	@echo "  start-all      - Start all services (Neo4j, Backend, Frontend)"
	@echo "  full-dev       - Start development mode with auto-reload"
	@echo "  stop-all       - Stop all services"
	@echo ""
	@echo "📊 Status & Info:"
	@echo "  status         - Check status of all services"
	@echo "  test-all       - Run all tests (backend + frontend)"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean-all      - Clean all build artifacts and dependencies"
	@echo ""
	@echo "🔧 Individual Services:"
	@echo "  backend-dev    - Start only backend in dev mode"
	@echo "  frontend-dev   - Start only frontend in dev mode"
	@echo ""
	@echo "📖 Service URLs:"
	@echo "  • Frontend:      http://localhost:3000"
	@echo "  • Backend API:   http://localhost:8000"
	@echo "  • GraphQL:       http://localhost:8000/graphql"
	@echo "  • Neo4j Browser: http://localhost:7474"

setup:
	@echo "🎯 Setting up Music Colab project..."
	@echo ""
	@echo "1️⃣  Installing backend dependencies..."
	cd backend && make install-deps
	@echo ""
	@echo "2️⃣  Installing frontend dependencies..."
	cd frontend && make install
	@echo ""
	@echo "3️⃣  Starting Neo4j database..."
	cd backend && make start-neo4j
	@echo ""
	@echo "4️⃣  Ingesting test data..."
	cd backend && make ingest-data
	@echo ""
	@echo "🎉 Setup complete! Run 'make start-all' to start all services"

start-all:
	@echo "🚀 Starting all Music Colab services..."
	@echo ""
	@trap 'echo "🛑 Shutting down all services..."; kill %1 %2 2>/dev/null; cd backend && make stop-neo4j; exit' INT; \
	echo "1️⃣  Starting Neo4j (if not running)..."; \
	cd backend && make start-neo4j; \
	echo "2️⃣  Starting backend server..."; \
	(cd backend && make dev) & \
	echo "3️⃣  Starting frontend server..."; \
	sleep 3; \
	(cd frontend && make start) & \
	echo ""; \
	echo "✅ All services started!"; \
	echo "🌐 Frontend: http://localhost:3000"; \
	echo "🔌 Backend: http://localhost:8000"; \
	echo "📊 GraphQL: http://localhost:8000/graphql"; \
	echo ""; \
	echo "Press Ctrl+C to stop all services"; \
	wait

full-dev: start-all

backend-dev:
	@echo "🔧 Starting backend in development mode..."
	cd backend && make start-neo4j && make dev

frontend-dev:
	@echo "🔧 Starting frontend in development mode..."
	cd frontend && make start

stop-all:
	@echo "🛑 Stopping all services..."
	@pkill -f "uvicorn main:app" 2>/dev/null || echo "Backend not running"
	@pkill -f "react-scripts start" 2>/dev/null || echo "Frontend not running"
	cd backend && make stop-neo4j
	@echo "✅ All services stopped"

status:
	@echo "📊 Service Status Check:"
	@echo ""
	@echo "🗃️  Neo4j Database:"
	@if docker ps | grep -q neo4j; then \
		echo "   ✅ Running"; \
		cd backend && make check-neo4j 2>/dev/null | grep -E "(✅|📊|❌)" || echo "   ❌ Connection failed"; \
	else \
		echo "   ❌ Not running"; \
	fi
	@echo ""
	@echo "🔌 Backend API (port 8000):"
	@if curl -s http://localhost:8000/graphql >/dev/null 2>&1; then \
		echo "   ✅ Running"; \
	else \
		echo "   ❌ Not running"; \
	fi
	@echo ""
	@echo "🌐 Frontend (port 3000):"
	@if curl -s http://localhost:3000 >/dev/null 2>&1; then \
		echo "   ✅ Running"; \
	else \
		echo "   ❌ Not running"; \
	fi

test-all:
	@echo "🧪 Running all tests..."
	@echo ""
	@echo "1️⃣  Backend tests:"
	cd backend && make test
	@echo ""
	@echo "2️⃣  Frontend tests:"
	cd frontend && make test --watchAll=false
	@echo ""
	@echo "✅ All tests complete!"

clean-all:
	@echo "🧹 Cleaning all build artifacts..."
	cd backend && rm -rf __pycache__ .pytest_cache htmlcov .coverage
	cd frontend && make clean
	@echo "✅ Cleanup complete!"
