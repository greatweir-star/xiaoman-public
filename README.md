# Xiaoman

Xiaoman is a companion AI system designed for long-term, emotionally-aware interactions.

## Architecture

The project consists of three main parts:

- **web/** — Frontend client (Vite + TypeScript)
- **backend/** — Node.js/TypeScript gateway and service layer
- **backend-py/** — Python core engine (memory, emotion, dialogue, world system)

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- Docker (optional)

### Backend (Python)

```bash
cd backend-py
pip install -r requirements.txt
python start_server.py
```

### Backend (Node.js)

```bash
cd backend
npm install
npm run dev
```

### Frontend

```bash
cd web
npm install
npm run dev
```

### Docker Compose

```bash
docker-compose up --build
```

## Project Structure

```
.
├── backend/          # TypeScript gateway layer
│   └── src/
├── backend-py/       # Python core engine
│   ├── xiaoman/      # Core modules
│   └── config/       # Linkage configurations
├── web/              # Frontend
│   └── src/
├── tools/            # Utility scripts
└── docker-compose.yml
```

## License

MIT
