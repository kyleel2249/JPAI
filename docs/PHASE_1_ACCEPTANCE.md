# Phase 1 Acceptance Criteria

## Scope
Establish a runnable repository foundation with backend health API, responsive frontend shell, typed configuration, test harness and baseline documentation.

## Acceptance checklist
- [x] Repository identity and Phase 1 scope documented.
- [x] FastAPI application entry point created.
- [x] Versioned health endpoint created.
- [x] Safe local host and CORS defaults defined.
- [x] React + TypeScript + Vite shell created.
- [x] Frontend displays backend connection state.
- [x] Backend test cases authored.
- [x] Architecture, constitution, gateway, registry and roadmap documents created.
- [ ] Backend dependencies installed and tests executed in a supported runtime.
- [ ] Frontend dependencies installed and production build/test executed in a supported runtime.
- [ ] Security and recovery review completed.

## Verification commands

Backend:
```bash
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
pytest
ruff check backend
uvicorn jpai_api.main:app --reload --app-dir backend
```

Frontend:
```bash
cd frontend
npm install
npm run build
npm test
```

## Completion status
Application and documentation files have been authored in the repository. Runtime test execution and full phase certification remain pending until the project is run in a Python/Node environment. Do not label Phase 1 fully certified until those checks pass.
