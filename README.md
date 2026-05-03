# FlatMate

A flatmate expense manager built with FastAPI. Track shared costs, calculate who owes whom, and settle dues — all from a clean web interface.

---

## Features

- Add flatmates and manage your flat roster
- Log expenses by category with flexible splitting
- Auto-calculates net balances using debt simplification
- One-click settlement to mark payments as done
- Spending breakdown by category with visual progress bars

---

## Tech Stack

- **Backend** — FastAPI, Pydantic, Uvicorn
- **Frontend** — HTML, CSS, Vanilla JS
- **Storage** — JSON file (no database required)
- **Container** — Docker, Docker Compose
- **CI/CD** — GitHub Actions

---

## Getting Started

### Run locally

```bash
git clone https://github.com/YOUR_USERNAME/splitnest.git
cd splitnest
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000`

### Run with Docker

```bash
docker compose up --build
```

Open `http://localhost:8000`

---

## Running Tests

```bash
pytest tests/ -v
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI |
| GET | `/health` | Health check |
| GET | `/api/flatmates` | List all flatmates |
| POST | `/api/flatmates` | Add a flatmate |
| DELETE | `/api/flatmates/{id}` | Remove a flatmate |
| GET | `/api/expenses` | List all expenses |
| POST | `/api/expenses` | Add an expense |
| DELETE | `/api/expenses/{id}` | Delete an expense |
| GET | `/api/balances` | Net balances and settlement transactions |
| POST | `/api/settle` | Record a payment |
| GET | `/api/stats` | Spending stats and category breakdown |

---

## CI/CD Pipeline

The pipeline runs automatically on every push to `main` or `develop`.

```
push
 │
 ├── lint.yml          flake8 code linting
 ├── docker-lint.yml   hadolint Dockerfile linting
 │
 └── test.yml          pytest (11 tests)
      │
      └── docker-build.yml    build image + container health check
           │
           ├── trivy.yml        image vulnerability scan (CRITICAL, HIGH)
           └── health-check.yml API smoke test (5 endpoints)
                │
                └── summary     pass / fail report
```

Each workflow file is independently reusable via `workflow_call`. The main `pipeline.yml` orchestrates them in order using `needs`.

---

## Project Structure

```
splitnest/
├── .github/
│   └── workflows/
│       ├── pipeline.yml
│       ├── lint.yml
│       ├── docker-lint.yml
│       ├── test.yml
│       ├── docker-build.yml
│       ├── trivy.yml
│       └── health-check.yml
├── .vscode/
│   └── settings.json
├── templates/
│   └── index.html
├── tests/
│   └── test_main.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── main.py
├── requirements.txt
└── README.md
```

---

## License

MIT
