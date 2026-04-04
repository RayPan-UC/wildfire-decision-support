# Wildfire Spread AI — Local Setup (Without Docker)

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| PostgreSQL | 16+ | Must include PostGIS extension |
| Python | 3.11+ | |
| pip | latest | |

**Install PostGIS:**
- **Windows**: Download PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/) and select PostGIS in the Stack Builder during installation
- **Mac**: `brew install postgresql postgis`
- **Ubuntu**: `sudo apt install postgresql postgresql-contrib postgis`

---

## Step 1: Configure Environment Variables

Copy the example file and update your credentials:

```bash
# Run from the project root (wildfire-spread-ai/)
cp .env.example .env
```

For local development, ensure `DB_HOST=localhost` in your `.env`:

```env
# Flask Backend
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wildfire_db
DB_USER=postgres
DB_PASSWORD=your_password

# PostgreSQL Container (not used locally, can be left as-is)
POSTGRES_DB=wildfire_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

---

## Step 2: Create the Database

```bash
psql -U postgres -c "CREATE DATABASE wildfire_db;"
```

---

## Step 3: Run init.sql

This creates the PostGIS extension, all tables, and inserts test data:

```bash
# Run from the project root (wildfire-spread-ai/)
psql -U postgres -d wildfire_db -f docker/init.sql
```

Verify tables were created:

```bash
psql -U postgres -d wildfire_db -c "\dt"
```

You should see `users` and `fire_events`.

---

## Step 4: Install Python Dependencies

```bash
# Run from the project root (wildfire-spread-ai/)
pip install -r requirements.txt
```

---

## Step 5: Run Flask

```bash
cd backend
python main.py
```

Flask will start at `http://localhost:5000`.  
`debug=True` is enabled — the server auto-reloads on file changes.

---

## Common Commands

```bash
# Open database shell
psql -U postgres -d wildfire_db

# Reset database (drop and recreate)
psql -U postgres -c "DROP DATABASE wildfire_db;"
psql -U postgres -c "CREATE DATABASE wildfire_db;"
psql -U postgres -d wildfire_db -f docker/init.sql
```

---

## Troubleshooting

**`could not load library "postgis"` or `extension "postgis" is not available`**  
PostGIS is not installed or not linked to this PostgreSQL instance. Reinstall PostgreSQL with PostGIS via Stack Builder (Windows) or `brew install postgis` (Mac).

**`psql: command not found`**  
Add PostgreSQL `bin/` to your PATH.  
Windows example: `C:\Program Files\PostgreSQL\16\bin`

**`password authentication failed`**  
Check that `DB_PASSWORD` in `.env` matches your local PostgreSQL password.

**`Port 5000 already in use`**  
Another process is using port 5000. Change the port in `backend/main.py`:
```python
app.run(host='0.0.0.0', debug=True, port=5001)
```
