from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import uuid
from datetime import datetime
from pathlib import Path

app = FastAPI(title="FlatMate — Rent Split Calculator", version="1.0.0")

DATA_FILE = "data.json"

# ─── Data Persistence ────────────────────────────────────────────────────────

def load_data():
    if not Path(DATA_FILE).exists():
        return {"flatmates": [], "expenses": [], "settlements": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── Models ──────────────────────────────────────────────────────────────────

class Flatmate(BaseModel):
    name: str
    email: Optional[str] = ""

class Expense(BaseModel):
    description: str
    amount: float
    paid_by: str          # flatmate id
    split_among: List[str]  # list of flatmate ids
    category: Optional[str] = "General"

class Settlement(BaseModel):
    from_id: str
    to_id: str
    amount: float

# ─── Flatmates ────────────────────────────────────────────────────────────────

@app.get("/api/flatmates")
def get_flatmates():
    return load_data()["flatmates"]

@app.post("/api/flatmates", status_code=201)
def add_flatmate(flatmate: Flatmate):
    data = load_data()
    # Prevent duplicate names
    names = [f["name"].lower() for f in data["flatmates"]]
    if flatmate.name.lower() in names:
        raise HTTPException(status_code=400, detail="Flatmate with this name already exists.")
    new = {
        "id": str(uuid.uuid4())[:8],
        "name": flatmate.name,
        "email": flatmate.email,
        "joined": datetime.now().strftime("%Y-%m-%d")
    }
    data["flatmates"].append(new)
    save_data(data)
    return new

@app.delete("/api/flatmates/{flatmate_id}")
def remove_flatmate(flatmate_id: str):
    data = load_data()
    data["flatmates"] = [f for f in data["flatmates"] if f["id"] != flatmate_id]
    save_data(data)
    return {"message": "Removed successfully"}

# ─── Expenses ─────────────────────────────────────────────────────────────────

@app.get("/api/expenses")
def get_expenses():
    data = load_data()
    flatmates = {f["id"]: f["name"] for f in data["flatmates"]}
    expenses = data["expenses"]
    for e in expenses:
        e["paid_by_name"] = flatmates.get(e["paid_by"], "Unknown")
        e["split_among_names"] = [flatmates.get(i, "Unknown") for i in e["split_among"]]
    return expenses

@app.post("/api/expenses", status_code=201)
def add_expense(expense: Expense):
    data = load_data()
    if expense.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")
    if not expense.split_among:
        raise HTTPException(status_code=400, detail="Select at least one person to split with.")
    new = {
        "id": str(uuid.uuid4())[:8],
        "description": expense.description,
        "amount": round(expense.amount, 2),
        "paid_by": expense.paid_by,
        "split_among": expense.split_among,
        "category": expense.category,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    data["expenses"].append(new)
    save_data(data)
    return new

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: str):
    data = load_data()
    data["expenses"] = [e for e in data["expenses"] if e["id"] != expense_id]
    save_data(data)
    return {"message": "Deleted successfully"}

# ─── Balances ─────────────────────────────────────────────────────────────────

@app.get("/api/balances")
def get_balances():
    data = load_data()
    flatmates = {f["id"]: f["name"] for f in data["flatmates"]}

    # net[person] = amount they are owed (positive) or owe (negative)
    net = {fid: 0.0 for fid in flatmates}

    for expense in data["expenses"]:
        paid_by = expense["paid_by"]
        split_among = expense["split_among"]
        amount = expense["amount"]
        if not split_among:
            continue
        share = round(amount / len(split_among), 2)
        for person in split_among:
            if person != paid_by:
                net[paid_by] = round(net.get(paid_by, 0) + share, 2)
                net[person] = round(net.get(person, 0) - share, 2)

    # Apply settlements
    for s in data["settlements"]:
        net[s["to_id"]] = round(net.get(s["to_id"], 0) - s["amount"], 2)
        net[s["from_id"]] = round(net.get(s["from_id"], 0) + s["amount"], 2)

    # Simplify into "who owes whom" transactions
    creditors = sorted([(fid, amt) for fid, amt in net.items() if amt > 0.005], key=lambda x: -x[1])
    debtors = sorted([(fid, -amt) for fid, amt in net.items() if amt < -0.005], key=lambda x: -x[1])

    transactions = []
    i, j = 0, 0
    cred = list(creditors)
    debt = list(debtors)
    while i < len(cred) and j < len(debt):
        creditor_id, cred_amt = cred[i]
        debtor_id, debt_amt = debt[j]
        settle = round(min(cred_amt, debt_amt), 2)
        transactions.append({
            "from": debtor_id,
            "from_name": flatmates.get(debtor_id, "Unknown"),
            "to": creditor_id,
            "to_name": flatmates.get(creditor_id, "Unknown"),
            "amount": settle
        })
        cred[i] = (creditor_id, round(cred_amt - settle, 2))
        debt[j] = (debtor_id, round(debt_amt - settle, 2))
        if cred[i][1] < 0.005:
            i += 1
        if debt[j][1] < 0.005:
            j += 1

    summary = [
        {"id": fid, "name": flatmates[fid], "balance": round(net[fid], 2)}
        for fid in flatmates
    ]
    return {"summary": summary, "transactions": transactions}

# ─── Settle Up ────────────────────────────────────────────────────────────────

@app.post("/api/settle", status_code=201)
def settle_payment(settlement: Settlement):
    data = load_data()
    flatmate_ids = [f["id"] for f in data["flatmates"]]
    if settlement.from_id not in flatmate_ids or settlement.to_id not in flatmate_ids:
        raise HTTPException(status_code=400, detail="Invalid flatmate ID.")
    record = {
        "id": str(uuid.uuid4())[:8],
        "from_id": settlement.from_id,
        "to_id": settlement.to_id,
        "amount": round(settlement.amount, 2),
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    data["settlements"].append(record)
    save_data(data)
    return record

# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    data = load_data()
    expenses = data["expenses"]
    total = round(sum(e["amount"] for e in expenses), 2)
    by_category = {}
    for e in expenses:
        cat = e.get("category", "General")
        by_category[cat] = round(by_category.get(cat, 0) + e["amount"], 2)
    top_spender = None
    spender_totals = {}
    for e in expenses:
        spender_totals[e["paid_by"]] = round(spender_totals.get(e["paid_by"], 0) + e["amount"], 2)
    if spender_totals:
        top_id = max(spender_totals, key=spender_totals.get)
        flatmates = {f["id"]: f["name"] for f in data["flatmates"]}
        top_spender = {"name": flatmates.get(top_id, "?"), "amount": spender_totals[top_id]}
    return {
        "total_expenses": total,
        "num_expenses": len(expenses),
        "num_flatmates": len(data["flatmates"]),
        "by_category": by_category,
        "top_spender": top_spender
    }

# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "app": "FlatMate Rent Split Calculator"}

# ─── Serve Frontend ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html", "r") as f:
        return f.read()
