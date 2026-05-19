# GreenCare Backend

GreenCare is a smart golf course management system built for Daejung Golf Engineering. This is the backend API service.

## Features

- JWT auth (access + refresh tokens)
- Role-based access (`worker`, `admin`, `manager`)
- **Work reports** (`/api/v1/work-reports/`): field work tracking with before/after photos
- **Disease detection** (`/api/v1/detections/`): multi-angle uploads and mock AI analysis
- **Golf courses** (`/api/v1/courses/`): course catalog
- **Work areas / map zones** (`/api/v1/work-areas/`): mapped polygons per course
- Legacy `reports` table retained in the database for older migrations; public API uses work reports above
- PostgreSQL + SQLAlchemy async + Alembic migrations
- Static file serving for uploaded images

## API Documentation

- Swagger UI: `http://localhost:8000/docs` (or your `DEV_API_PUBLIC_URL` + `/docs` on a phone)
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

Create `.env` from `.env.example`.

- `APP_NAME`: FastAPI app name
- `DEBUG`: debug mode toggle (`True/False`)
- `SECRET_KEY`: JWT signing secret
- `ACCESS_TOKEN_EXPIRE_MINUTES`: access token lifetime
- `REFRESH_TOKEN_EXPIRE_DAYS`: refresh token lifetime
- `DATABASE_URL`: async PostgreSQL URL (`postgresql+asyncpg://...`)
- `NAS_STORAGE_PATH`: reserved for NAS storage setup
- `LOCAL_STORAGE_PATH`: local image storage root (default `./storage/images`)
- `MAX_IMAGE_SIZE_MB`: upload limit in MB
- `ALLOWED_HOSTS`: allowed hosts (project-specific use)
- `API_BIND_HOST`: uvicorn bind address (default `0.0.0.0` for LAN devices)
- `API_PORT`: dev server port (default `8000`)
- `DEV_API_PUBLIC_URL`: optional stable base URL, e.g. `http://192.168.0.61:8000` — set once and use the **same** value in the mobile app `EXPO_PUBLIC_API_URL`. Reserve that IP in your router’s DHCP settings if your PC’s address keeps changing.

## Run with Docker

1. Ensure Docker Desktop is installed and running.
2. Build and start services:
   - `docker compose up --build`
3. API available at:
   - `http://localhost:8000`

## Run Locally

1. Create and activate virtual environment (recommended).
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Ensure PostgreSQL is running and `.env` is configured.
4. Run migrations:
   - `python -m alembic upgrade head`
5. Start server (recommended — reads `API_BIND_HOST`, `API_PORT`, `DEV_API_PUBLIC_URL` from `.env`):
   - `python run_dev.py`
   - Or manually: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

## Database Migration Commands

- Create migration:
  - `python -m alembic revision --autogenerate -m "your_message"`
- Apply latest migrations:
  - `python -m alembic upgrade head`
- Roll back one revision:
  - `python -m alembic downgrade -1`

## Health Check

- `GET /health` returns `status`, `version`, `modules`, and `database` connectivity (`connected` / `disconnected`).
