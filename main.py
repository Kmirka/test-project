import os
import json  # НОВЕ: для передачі даних у JavaScript
from typing import Optional
from dotenv import load_dotenv
from fastapi import *
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from supabase import Client, create_client

# Завантажуємо змінні оточення
load_dotenv()

SUPABASE_URL = os.getenv("DB_LINK")
SUPABASE_KEY = os.getenv("DB_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ ПОМИЛКА: Перевірте файл .env! Змінні DB_LINK або DB_KEY відсутні.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(redirect_slashes=False)

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def main_page():
    return RedirectResponse(url="/show-tracker", status_code=303)


@app.get("/show-tracker")
def show_tracker(request: Request):
    # Отримуємо всі транзакції
    response = (
        supabase.table("transactions")
        .select("*")
        .order("id", desc=True)
        .execute()
    )
    all_transactions = response.data if response.data else []

    # Рахуємо баланс
    total_income = sum(
        float(item["amount"]) for item in all_transactions if item["type"] == "income"
    )
    total_expense = sum(
        float(item["amount"]) for item in all_transactions if item["type"] == "expense"
    )
    balance = total_income - total_expense

    # --- Збираємо статистику для графіка (групуємо витрати) ---
    expense_categories = {}
    for item in all_transactions:
        if item["type"] == "expense":
            cat = item["category"]
            # Додаємо суму до існуючої категорії
            expense_categories[cat] = expense_categories.get(cat, 0) + float(item["amount"])

    cat_labels = list(expense_categories.keys())
    cat_values = list(expense_categories.values())
    # ----------------------------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "transactions": all_transactions,
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "balance": round(balance, 2),
            # Передаємо дані у форматі JSON
            "cat_labels": json.dumps(cat_labels),
            "cat_values": json.dumps(cat_values),
        },
    )


@app.post("/add")
@app.post("/new")
def add_transaction(
    title: str = Form(...),
    amount: float = Form(...),
    type: str = Form(...),
    category: Optional[str] = Form("Загальне"),
):
    supabase.table("transactions").insert(
        {
            "title": title,
            "amount": abs(amount),
            "type": type,
            "category": category if category else "Загальне",
        }
    ).execute()

    return RedirectResponse(status_code=303, url="/show-tracker")


@app.get("/delete/{item_id}")
@app.get("/item-delete/{item_id}")
def delete_transaction(item_id: int):
    supabase.table("transactions").delete().eq("id", item_id).execute()
    return RedirectResponse(status_code=303, url="/show-tracker")


@app.get("/check")
def check_data():
    transactions = supabase.table("transactions").select("*").execute()
    return transactions