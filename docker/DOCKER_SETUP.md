# Wildfire Spread AI — Docker Setup Guide

## Prerequisites

- Install [Docker Desktop](https://www.docker.com/products/docker-desktop) (Windows/Mac)
- Launch Docker Desktop and confirm the icon in the system tray shows **Running** (green)

---

## Step 1: Configure Environment Variables

The `.env` file must be in the **project root** (not inside `docker/`).  
Copy the example file to create your own:

```bash
# Run from the project root (wildfire-spread-ai/)
cp .env.example .env
```

Open `.env` and update as needed:

```env
# Flask Backend
DB_NAME=wildfire_db
DB_USER=postgres
DB_PASSWORD=your_password        # change this
SECRET_KEY=some_long_random_str  # always change for production

# PostgreSQL Container (must match DB_* above)
POSTGRES_DB=wildfire_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password  # must be identical to DB_PASSWORD
```

---

## Step 2: First-Time Startup

`docker-compose.yml` is inside the `docker/` folder. Run all commands from there:

```bash
cd docker
docker compose up --build
```

> `--build` is required the first time. Subsequent restarts don't need it unless you change `Dockerfile` or `requirements.txt`.

On first startup, Docker will:
1. Download `postgis/postgis:16-3.4` and `python:3.11-slim` (~500 MB, requires internet)
2. Run `init.sql` to create the users table automatically
3. Start 2 services: `db` / `backend`

When everything is ready you should see:
```
backend-1  |  * Running on http://0.0.0.0:5000
```

---

## Step 3: Accessing the Services

| Service | URL |
|---|---|
| Flask backend | http://localhost:5000 |
| PostgreSQL | localhost:5432 (credentials from `.env`) |

### API Examples (curl or Postman)

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"123456"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"123456"}'
```

---

## Common Commands

> All commands run from `wildfire-spread-ai/docker/`

```bash
# Run in background (detached mode)
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs -f backend        # backend only

# Stop all services
docker compose down

# Stop and delete all data (full reset)
docker compose down -v

# Reset database and rebuild from scratch (e.g. after changing .env)
docker compose down -v && docker compose up --build

# Rebuild a single service (e.g. after editing Dockerfile)
docker compose up --build backend

# Open a database shell
docker compose exec db psql -U postgres -d wildfire_db
```

---

## Troubleshooting

**`docker compose: command not found`**  
Older Docker versions use `docker-compose` (with hyphen). Try: `docker-compose up --build`

**`Port 5432 already in use`**  
A local PostgreSQL instance is running on the same port. Stop it, or change the host port in `docker-compose.yml`:
```yaml
ports: "5433:5432"
```

**`backend: Connection refused (cannot reach db)`**  
The DB may still be initializing. Wait a few seconds — the backend will retry. Check: `docker compose logs db`

**`users table does not exist (init.sql not executed)`**  
PostgreSQL skips `init.sql` when a volume already exists. Run:
```bash
docker compose down -v && docker compose up --build
```
