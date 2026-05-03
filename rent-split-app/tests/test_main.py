import pytest
from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

# Clean up test data file before/after tests
@pytest.fixture(autouse=True)
def clean_data():
    if os.path.exists("data.json"):
        os.remove("data.json")
    yield
    if os.path.exists("data.json"):
        os.remove("data.json")

# ── Health Check ──────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

# ── Flatmates ─────────────────────────────────────────────────────────────────

def test_add_flatmate():
    res = client.post("/api/flatmates", json={"name": "Harjot", "email": "h@flat.com"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Harjot"
    assert "id" in data

def test_get_flatmates():
    client.post("/api/flatmates", json={"name": "Arjun"})
    res = client.get("/api/flatmates")
    assert res.status_code == 200
    assert len(res.json()) == 1

def test_duplicate_flatmate():
    client.post("/api/flatmates", json={"name": "Riya"})
    res = client.post("/api/flatmates", json={"name": "Riya"})
    assert res.status_code == 400

def test_remove_flatmate():
    r = client.post("/api/flatmates", json={"name": "Priya"})
    fid = r.json()["id"]
    res = client.delete(f"/api/flatmates/{fid}")
    assert res.status_code == 200
    assert len(client.get("/api/flatmates").json()) == 0

# ── Expenses ──────────────────────────────────────────────────────────────────

def _setup_flatmates():
    r1 = client.post("/api/flatmates", json={"name": "Arjun"})
    r2 = client.post("/api/flatmates", json={"name": "Neha"})
    return r1.json()["id"], r2.json()["id"]

def test_add_expense():
    id1, id2 = _setup_flatmates()
    res = client.post("/api/expenses", json={
        "description": "Rent",
        "amount": 12000,
        "paid_by": id1,
        "split_among": [id1, id2],
        "category": "Rent"
    })
    assert res.status_code == 201
    assert res.json()["amount"] == 12000

def test_invalid_expense_amount():
    id1, id2 = _setup_flatmates()
    res = client.post("/api/expenses", json={
        "description": "Groceries",
        "amount": -500,
        "paid_by": id1,
        "split_among": [id1, id2]
    })
    assert res.status_code == 400

def test_delete_expense():
    id1, id2 = _setup_flatmates()
    r = client.post("/api/expenses", json={
        "description": "Internet",
        "amount": 800,
        "paid_by": id1,
        "split_among": [id1, id2]
    })
    eid = r.json()["id"]
    res = client.delete(f"/api/expenses/{eid}")
    assert res.status_code == 200

# ── Balances ──────────────────────────────────────────────────────────────────

def test_balances():
    id1, id2 = _setup_flatmates()
    client.post("/api/expenses", json={
        "description": "Groceries",
        "amount": 1000,
        "paid_by": id1,
        "split_among": [id1, id2]
    })
    res = client.get("/api/balances")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "transactions" in data
    # id1 paid 1000 split 2 ways, so id2 owes id1 500
    assert len(data["transactions"]) == 1
    t = data["transactions"][0]
    assert t["from"] == id2
    assert t["to"] == id1
    assert t["amount"] == 500.0

# ── Settle Up ─────────────────────────────────────────────────────────────────

def test_settle_payment():
    id1, id2 = _setup_flatmates()
    client.post("/api/expenses", json={
        "description": "Electricity",
        "amount": 600,
        "paid_by": id1,
        "split_among": [id1, id2]
    })
    res = client.post("/api/settle", json={"from_id": id2, "to_id": id1, "amount": 300})
    assert res.status_code == 201
    # After settling, transactions should be empty
    bal = client.get("/api/balances").json()
    assert len(bal["transactions"]) == 0

# ── Stats ──────────────────────────────────────────────────────────────────────

def test_stats():
    id1, id2 = _setup_flatmates()
    client.post("/api/expenses", json={
        "description": "Rent",
        "amount": 15000,
        "paid_by": id1,
        "split_among": [id1, id2],
        "category": "Rent"
    })
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_expenses"] == 15000
    assert data["num_expenses"] == 1
    assert "Rent" in data["by_category"]