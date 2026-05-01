import json
import streamlit as st
from datetime import datetime
import uuid

st.set_page_config(page_title="Finance App PRO", layout="wide")

FILE = "transactions.json"

# =========================
# INIT STATE FIX
# =========================

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# =========================
# DATA
# =========================

def load_transactions():
    try:
        with open(FILE, "r") as f:
            data = json.load(f)

        for t in data:
            if "id" not in t:
                t["id"] = str(uuid.uuid4())

        return data

    except:
        return []

def save_transactions(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

# =========================
# DATE PARSER
# =========================

def parse_date(date_str):
    try:
        date_str = date_str.strip()

        formats = [
            "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y",
            "%d.%m.%y", "%d/%m/%y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue

        parts = date_str.replace("/", ".").replace("-", ".").split(".")
        if len(parts) == 3:
            d, m, y = parts
            return datetime(int(y), int(m), int(d))

    except:
        return None

    return None


def get_month(dt):
    months = [
        "Januar","Februar","Mart","April","Maj","Jun",
        "Jul","Avgust","Septembar","Oktobar","Novembar","Decembar"
    ]
    if dt:
        return f"{months[dt.month-1]} {dt.year}"
    return "Nepoznat mesec"


# =========================
# LOAD DATA
# =========================

st.title("💳 Finance Dashboard")

transactions = load_transactions()

# =========================
# MONTH SELECT
# =========================

all_months = [
    "Januar 2026","Februar 2026","Mart 2026","April 2026",
    "Maj 2026","Jun 2026","Jul 2026","Avgust 2026",
    "Septembar 2026","Oktobar 2026","Novembar 2026","Decembar 2026"
]

months_from_data = [
    get_month(parse_date(t.get("date", ""))) for t in transactions
]

months = sorted(set(all_months + months_from_data))

if "selected_month" not in st.session_state:
    st.session_state.selected_month = "Maj 2026"

selected_month = st.selectbox(
    "📅 Izaberi mesec",
    months,
    index=months.index(st.session_state.selected_month)
    if st.session_state.selected_month in months else 0
)

st.session_state.selected_month = selected_month


def safe_match(t):
    dt = parse_date(t.get("date", ""))
    return dt and get_month(dt) == selected_month


current = [t for t in transactions if safe_match(t)]


# =========================
# METRICS
# =========================

income = sum(t["amount"] for t in current if t["type"] == "income")
expense = sum(t["amount"] for t in current if t["type"] == "expense")

budget = income * 0.8 - expense
invest = income * 0.2

show_state = st.toggle("📊 Prikaži stanje")

if show_state:

    st.subheader("📊 Stanje")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Priliv", f"{income:,.2f}")
    col2.metric("Odliv", f"{expense:,.2f}")
    col3.metric("Budžet", f"{budget:,.2f}")
    col4.metric("Investirano", f"{invest:,.2f}")


# =========================
# CATEGORY BUDGET (FIXED MATCH)
# =========================

show_categories = st.toggle("📂 Prikaži preostalo po kategorijama")

if show_categories:

    st.subheader("Preostalo po kategorijama")

    limits = {
        "neophodni": income * 0.5,
        "ekstravagantni": income * 0.1,
        "pokloni": income * 0.1,
        "edukacija": income * 0.1
    }

    spent = {k: 0 for k in limits}

    for t in current:
        if t["type"] == "expense":
            cat = t.get("category", "").strip().lower()
            if cat in spent:
                spent[cat] += t["amount"]

    remaining = {k: limits[k] - spent[k] for k in limits}

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Neophodni", f"{remaining['neophodni']:,.2f}")
    c2.metric("Ekstravagantni", f"{remaining['ekstravagantni']:,.2f}")
    c3.metric("Pokloni", f"{remaining['pokloni']:,.2f}")
    c4.metric("Edukacija", f"{remaining['edukacija']:,.2f}")


# =========================
# ADD TRANSACTIONS
# =========================

st.markdown("## ➕ Dodaj transakciju")

colA, colB = st.columns(2)

with colA:
    st.markdown("### 🟢 Priliv")

    with st.form("income_form"):
        date = st.text_input("Datum (dd.mm.yyyy)", key="income_date")
        amount = st.number_input("Iznos", min_value=0.0, key="income_amount")
        category = st.selectbox("Kategorija", ["active", "passive"], key="income_cat")
        description = st.text_input("Opis", key="income_desc")

        if st.form_submit_button("Dodaj priliv"):
            transactions.append({
                "id": str(uuid.uuid4()),
                "date": date,
                "amount": amount,
                "type": "income",
                "category": category,
                "description": description
            })
            save_transactions(transactions)
            st.rerun()

with colB:
    st.markdown("### 🔴 Odliv")

    with st.form("expense_form"):
        date = st.text_input("Datum (dd.mm.yyyy)", key="expense_date")
        amount = st.number_input("Iznos", min_value=0.0, key="expense_amount")
        category = st.selectbox(
            "Kategorija",
            ["neophodni", "ekstravagantni", "pokloni", "edukacija"],
            key="expense_cat"
        )
        description = st.text_input("Opis", key="expense_desc")

        if st.form_submit_button("Dodaj odliv"):
            transactions.append({
                "id": str(uuid.uuid4()),
                "date": date,
                "amount": amount,
                "type": "expense",
                "category": category,
                "description": description
            })
            save_transactions(transactions)
            st.rerun()


# =========================
# TRANSACTIONS LIST + DELETE
# =========================

show = st.toggle("Prikaži transakcije")

if show:

    st.subheader("Transakcije")

    for t in transactions:

        col1, col2, col3 = st.columns([0.8, 0.1, 0.1])

        with col1:
            st.write(f"{t['date']} | {t['amount']} | {t['type']} | {t['category']} | {t['description']}")

        with col2:
            if st.button("✏️", key=f"edit_{t['id']}"):
                st.session_state.edit_id = t["id"]
                st.session_state.edit_mode = True
                st.rerun()

        with col3:
            if st.button("🗑️", key=f"delete_{t['id']}"):
                transactions = [x for x in transactions if x["id"] != t["id"]]
                save_transactions(transactions)
                st.rerun()


# =========================
# EDIT FORM
# =========================

if st.session_state.edit_mode and st.session_state.edit_id is not None:

    t = next((x for x in transactions if x["id"] == st.session_state.edit_id), None)

    if t:

        st.markdown("## ✏️ Izmena transakcije")

        with st.form(f"edit_{t['id']}"):

            date = st.text_input("Datum", value=t["date"])
            amount = st.number_input("Iznos", value=float(t["amount"]))

            type_ = st.selectbox(
                "Tip",
                ["income", "expense"],
                index=0 if t["type"] == "income" else 1
            )

            category = st.text_input("Kategorija", value=t["category"])
            description = st.text_input("Opis", value=t["description"])

            if st.form_submit_button("Sačuvaj izmene"):

                t["date"] = date
                t["amount"] = amount
                t["type"] = type_
                t["category"] = category
                t["description"] = description

                save_transactions(transactions)

                st.session_state.edit_mode = False
                st.session_state.edit_id = None

                st.rerun()