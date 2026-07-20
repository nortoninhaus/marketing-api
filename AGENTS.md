# AGENTS.md

## Developer Commands
- **Backend (FastAPI):**
  - Install: `pip install -r requirements.txt`
  - Run: `uvicorn app.main:app --reload` (Note: `app/main.py` is the likely entrypoint)
  - Test: `pytest`
- **Dashboard (Streamlit):**
  - Run: `streamlit run dashboard.py`
- **Frontend (Flutter Web):**
  - Path: `web_ui/`
  - Commands: `flutter pub get`, `flutter run -d chrome`

## Project Structure
- `app/`: FastAPI backend implementation.
  - `connectors/`: Multi-platform marketing API integrations (Meta, Google, TikTok, etc.).
  - `routers/`: API endpoints.
  - `models/`: Pydantic schemas for requests/responses.
- `dashboard.py`: Streamlit-based data visualization.
- `web_ui/`: Flutter web application.
- `tests/`: Extensive pytest suite for connectors and API.

## Core Logic & Conventions
- **Connectors:** All platforms inherit from `app/connectors/base.py`. Follow this pattern when adding new integrations.
- **Environment:** Requires a `.env` file (see `.env.example`).
- **Deployment:** Uses Docker (`Dockerfile`, `Dockerfile.dashboard`) and Google Cloud (`.gcloudignore`, `deploy.sh`).

## Testing Quirks
- Tests cover specific OAuth flows and API validations for multiple social platforms.
- `tests/conftest.py` contains shared fixtures for API mocking.
