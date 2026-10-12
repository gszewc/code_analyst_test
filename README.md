# Code Analyst

Repository for the code_analyst project.

## Project Structure

```text
code_analyst/
├── codeminer/                  # Core application modules
│   ├── parsing/                # Multi-language parsing framework
│   │   ├── interfaces.py       #   LanguageParser & CrossFileResolverBase ABCs
│   │   ├── registry.py         #   ParserRegistry — language/extension dispatch
│   │   ├── discovery.py        #   FileDiscovery — multi-language file scanning
│   │   ├── models.py           #   Shared data models (ASTNode, ASTResult, etc.)
│   │   ├── types.py            #   Node/relationship type definitions
│   │   ├── security.py         #   Path validation & security checks
│   │   └── python/             #   Python language plugin
│   │       ├── parser.py       #     PythonParser (LanguageParser adapter)
│   │       ├── ast_parser.py   #     Core AST parsing engine
│   │       ├── cross_file_resolver.py  # Cross-file dependency resolution
│   │       ├── nodes_visitor.py        # AST node extraction
│   │       ├── relationship_detector.py # Relationship detection
│   │       └── ...             #     node_builder, metrics, module_registry, etc.
│   ├── database/               # Storage layer (SQLite + Neo4j)
│   ├── api/                    # FastAPI REST API (versioned under /api/v1/)
│   ├── services/               # Business logic services
│   ├── components/             # Orchestrators (AnalysisOrchestrator, etc.)
│   └── models/                 # API request/response models
├── tests/                      # Test suite
│   ├── parsing/                # Parsing framework tests
│   │   └── python/             #   Python parser tests
│   ├── database/               # Database layer tests
│   └── api/                    # API tests
├── frontend/                   # Vue 3 + TypeScript SPA
├── docker/                     # Docker/Podman configuration
├── data/                       # SQLite database storage
├── uploads/                    # Uploaded ZIP files
└── logs/                       # Application logs
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Podman + `podman-compose`

### Setup

```bash
# Create python venv 
python3 -m venv .venv
# Activate virtual environment
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm ci
cd ..

# Create data directories
mkdir -p data uploads logs

# Copy environment file
cp .env.example .env

# Start the backend API and Neo4j with Podman Compose
podman-compose -f docker/docker-compose.yml up -d --build
```

### Run API Server

```bash
# Development mode (with hot reload)
uvicorn codeminer.api.main:app --reload --host 0.0.0.0 --port 8080

# Production mode
uvicorn codeminer.api.main:app --host 0.0.0.0 --port 8080

# Or run the backend with Podman Compose
podman-compose -f docker/docker-compose.yml up -d backend
```

### Run Frontend

```bash
cd frontend

# Development mode (Vite dev server on http://localhost:3000)
npm run dev
```

The frontend talks to the backend at `http://localhost:8080` by default. To point it at a different API URL, set `VITE_API_BASE_URL` before starting Vite:

```bash
cd frontend
VITE_API_BASE_URL=http://localhost:8080 npm run dev
```

### Build Frontend

```bash
cd frontend

# Create a production build in frontend/dist
npm run build

# Optional: serve the production build locally
npm run preview
```

### Rebuild Backend Docker Image After Source Changes

```bash
docker/update-backend-image.sh
```

The rebuild utility prefers `podman-compose` and falls back to `podman compose` or `docker compose` if needed.

The backend container now waits for Neo4j to accept Bolt connections before it starts `uvicorn`, which makes startup more reliable under `podman-compose`.

### Access API Documentation

- Swagger UI: <http://localhost:8080/docs>
- ReDoc: <http://localhost:8080/redoc>
- Health Check: <http://localhost:8080/api/v1/health>

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run Unit 3 API tests
pytest tests/api/ -v

# Run with coverage
pytest tests/ -v --cov=codeminer --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Run AST Parser CLI

```bash
# Parse Python code
python -m codeminer.parsing.python.cli parse /path/to/python/code
```

## API Endpoints

### Projects

- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Files

- `POST /api/v1/projects/{id}/upload` - Upload ZIP file
- `GET /api/v1/projects/{id}/files` - List files
- `GET /api/v1/projects/{id}/files/*filepath` - Get file content
- `POST /api/v1/projects/{id}/folders` - Create folder

### Analysis

- `POST /api/v1/analysis/projects/{id}/analyze` - Start analysis (supports `languages` and `folders` filters)
- `GET /api/v1/analysis/jobs/{id}` - Get job status
- `GET /api/v1/analysis/projects/{id}/jobs` - List jobs
- `GET /api/v1/analysis/defaults` - Get analysis defaults

### Languages

- `GET /api/v1/languages` - List registered languages and type definitions
- `GET /api/v1/languages/projects/{id}/detected-languages` - Detect languages in a project

### Graph

- `GET /api/v1/projects/{id}/nodes` - Get nodes (supports `language` filter)
- `GET /api/v1/projects/{id}/nodes/{node_id}` - Get node by ID
- `GET /api/v1/projects/{id}/nodes/{node_id}/relationships` - Get relationships
- `GET /api/v1/projects/{id}/search` - Search nodes
- `GET /api/v1/projects/{id}/stats` - Get project stats

## Environment Variables

See `.env.example` for all available options:

```ini
# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Database Configuration
SQLITE_PATH=data/projects.sqlite
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Development

```bash
# Format code
black codeminer/ tests/

# Lint code
ruff check codeminer/ tests/

# Run tests
pytest tests/ -v
```

## License

See LICENSE file.
