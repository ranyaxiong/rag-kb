# Repository Guidelines

## Project Structure & Module Organization
- `app/`: FastAPI backend. `api/` (routes like `qa.py`, `documents.py`), `core/` (processing, vector store, config), `models/` (Pydantic schemas), entry `app/main.py`.
- `frontend/`: Streamlit UI. Entry `frontend/streamlit_app.py` with `components/` and `utils/`.
- `tests/`: Pytest suite and fixtures (`tests/conftest.py`). Config in `pytest.ini`.
- `scripts/`: Utilities (`setup-keyring.py`, `setup-cors.py`, `start.sh`, `stop.sh`).
- `docker/`: Compose files and Dockerfiles. Runtime data in `data/`, logs in `logs/`, optional secrets in `secrets/` (do not commit keys).

## Build, Test, and Development Commands
- `make install`: Install Python deps and create runtime directories.
- `make dev` / `make run`: Start backend (Uvicorn on `:8000`) and UI (Streamlit on `:8501`).
- `make test` / `make test-html`: Run tests with coverage; HTML report in `htmlcov/`.
- `make lint` / `make format`: Run `flake8`, `black`, and `isort`.
- `make docker-build` / `make docker-run` / `make docker-stop`: Containerize and run locally.
Examples: `uvicorn app.main:app --reload`, `streamlit run frontend/streamlit_app.py`.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indent, `black` (88 cols), `isort` for imports, `flake8` (ignore `E203,W503`).
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Prefer docstrings and type hints for public APIs in `app/api` and `app/core`.

## Testing Guidelines
- Framework: `pytest`. Files `tests/test_*.py`; functions `test_*`.
- Coverage: enforced ≥70% (`pytest.ini` via `--cov-fail-under=70`).
- Run subsets with `pytest -k "vector_store"`; HTML report via `make test-html`.

## Commit & Pull Request Guidelines
- Commits: imperative and concise; bilingual allowed (EN/中文). Optional scope tags (e.g., `fix(api): async upload race`).
- PRs include: summary, linked issues, test plan (commands run), screenshots for UI changes, and notes on security/config changes.
- Before pushing: `make format && make lint && make test` must pass.

## Security & Configuration Tips
- Never commit API keys or `.env`. Prefer `OPENAI_API_KEY` env var or `scripts/setup-keyring.py`; sample config in `.env.secure.example`.
- Validate with `make check-security`. Configure CORS via `scripts/setup-cors.py` or env (`ALLOWED_ORIGINS`, etc.). See `SECURITY.md` for details.

