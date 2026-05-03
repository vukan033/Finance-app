import streamlit as st
from datetime import datetime, date
import uuid
import pandas as pd
import altair as alt
from supabase import create_client

# =========================
# SUPABASE CONFIG
# =========================

SUPABASE_URL = "https://pvteshphuktqtraxvnlz.supabase.co"
SUPABASE_KEY = "sb_publishable_MB3iwNUio21Js_RxB0gqaA_IglNvG6x"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finance App PRO", layout="wide")

# =========================
# INIT STATE
# =========================

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# =========================
# SUPABASE DATA LAYER
# =========================

def load_transactions():
    res = supabase.table("transactions").select("*").execute()
    return res.data if res.data else []

def add_transaction(t):
    supabase.table("transactions").insert(t).execute()

def delete_transaction(tid):
    supabase.table("transactions").delete().eq("id", tid).execute()

def update_transaction(tid, data):
    supabase.table("transactions").update(data).eq("id", tid).execute()

# =========================
# DATE PARSER
# =========================

def parse_date(d):
    try:
        if isinstance(d, str):
            return datetime.fromisoformat(d)
        return d
    except:
        return None

def get_month(dt):
    months = ["Januar","Februar","Mart","April","Maj","Jun",
              "Jul","Avgust","Septembar","Oktobar","Novembar","Decembar"]
    if dt:
        return f"{months[dt.month-1]} {dt.year}"
    return "Nepoznat mesec"

# =========================
# LOAD
# =========================

st.title("💳 BudgetBuddy")

transactions = load_transactions()

# =========================
# MONTH FILTER
# =========================

all_months = [
    "Januar 2026","Februar 2026","Mart 2026","April 2026",
    "Maj 2026","Jun 2026","Jul 2026","Avgust 2026",
    "Septembar 2026","Oktobar 2026","Novembar 2026","Decembar 2026"
]

months_from_data = [get_month(parse_date(t.get("date",""))) for t in transactions]
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
    dt = parse_date(t.get("date",""))
    return dt and get_month(dt) == selected_month

# =========================
# FILTER LOGIC (NEW UX)
# =========================

search = st.text_input("🔍 Pretraga (opis)", "")
filter_type = st.selectbox("🎛 Filter", ["sve", "income", "expense"])

def matches_search(t):
    if search == "":
        return True
    return search.lower() in t.get("description","").lower()

def matches_filter(t):
    if filter_type == "sve":
        return True
    return t["type"] == filter_type

current = [
    t for t in transactions
    if safe_match(t)
    and matches_search(t)
    and matches_filter(t)
]

# =========================
# INSIGHTS ENGINE (NEW)
# =========================

income = sum(t["amount"] for t in current if t["type"] == "income")
expense = sum(t["amount"] for t in current if t["type"] == "expense")
balance = income - expense

def normalize(text):
    return (text or "").lower()

expenses = [t for t in current if t["type"] == "expense"]

keywords = ["kafic", "cigare", "hrana", "voda", "gorivo", "kafa"]

category_totals = {}
keyword_totals = {}

for t in expenses:
    cat = t["category"].lower()
    desc = normalize(t["description"])

    category_totals[cat] = category_totals.get(cat, 0) + t["amount"]

    matched = None
    for k in keywords:
        if k in desc:
            matched = k
            break

    if matched:
        keyword_totals[matched] = keyword_totals.get(matched, 0) + t["amount"]

top_category = max(category_totals, key=category_totals.get) if category_totals else None

top_keyword = None
top_keyword_value = 0

for k, v in keyword_totals.items():
    if v > top_keyword_value:
        top_keyword = k
        top_keyword_value = v

# =========================
# INSIGHTS BAR
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Priliv", f"{income:,.2f}")

with col2:
    st.metric("Odliv", f"{expense:,.2f}")

with col3:
    st.metric("Balance", f"{balance:,.2f}")

st.caption(f"🏷 Najveća kategorija troška: {top_category if top_category else '-'}")

if top_keyword:
    pct = (top_keyword_value / expense * 100) if expense > 0 else 0
    st.caption(
        f"🔥 Najviše trošiš na: {top_keyword} "
        f"({top_keyword_value:,.0f} RSD | {pct:.1f}%)"
    )

# =========================
# METRICS (OLD SECTION KEPT)
# =========================

budget = income * 0.8 - expense
invest = income * 0.2

show_state = st.toggle("📊 Prikaži stanje")

if show_state:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Priliv", f"{income:,.2f}")
    col2.metric("Odliv", f"{expense:,.2f}")
    col3.metric("Budžet", f"{budget:,.2f}")
    col4.metric("Investirano", f"{invest:,.2f}")

# =========================
# CATEGORY BUDGET (UNCHANGED)
# =========================

show_categories = st.toggle("📂 Prikaži budžet po kategorijama")

if show_categories:

    limits = {
        "neophodni": income * 0.5,
        "ekstravagantni": income * 0.1,
        "pokloni": income * 0.1,
        "edukacija": income * 0.1
    }

    spent = {k: 0 for k in limits}

    for t in current:
        if t["type"] == "expense":
            cat = t.get("category","").strip().lower()
            if cat in spent:
                spent[cat] += t["amount"]

    st.subheader("📊 Budžet po kategorijama")

    for k in limits:
        remaining = limits[k] - spent[k]

        st.markdown(
            f"""
            <div style="
                padding:10px;
                border-radius:10px;
                margin-bottom:8px;
                background-color:#111;
                color:#fff;
                font-size:14px;
            ">
                <b>{k.upper()}</b><br>
                💸 Potrošeno: {spent[k]:,.2f}<br>
                🟢 Preostalo: {remaining:,.2f}
            </div>
            """,
            unsafe_allow_html=True
        )

# =========================
# ADD TRANSACTIONS (UNCHANGED)
# =========================

st.markdown("## ➕ Dodaj transakciju")

colA, colB = st.columns(2)

with colA:
    with st.form("income_form"):
        date_val = st.date_input("Datum", value=date.today())
        amount = st.number_input("Iznos", min_value=0.0)
        category = st.selectbox("Kategorija", ["active","passive"])
        desc = st.text_input("Opis")

        if st.form_submit_button("Dodaj priliv"):
            add_transaction({
                "id": str(uuid.uuid4()),
                "date": date_val.isoformat(),
                "amount": amount,
                "type": "income",
                "category": category,
                "description": desc
            })
            st.toast("✅ Priliv uspešno dodat!")
            st.rerun()

with colB:
    with st.form("expense_form"):
        date_val = st.date_input("Datum", value=date.today())
        amount = st.number_input("Iznos", min_value=0.0)
        category = st.selectbox("Kategorija", ["neophodni","ekstravagantni","pokloni","edukacija"])
        desc = st.text_input("Opis")

        if st.form_submit_button("Dodaj odliv"):
            add_transaction({
                "id": str(uuid.uuid4()),
                "date": date_val.isoformat(),
                "amount": amount,
                "type": "expense",
                "category": category,
                "description": desc
            })
            st.toast("❌ Odliv uspešno dodat!")
            st.rerun()

# =========================
# TRANSACTIONS (UNCHANGED)
# =========================

show = st.toggle("Prikaži transakcije")

if show:
    st.markdown("## 📒 Transakcije")

    for t in current:

        col1, col2, col3 = st.columns([0.65, 0.2, 0.15])

        if st.session_state.edit_id == t["id"]:

            with col1:
                new_date = st.date_input("Datum", value=parse_date(t["date"]), key=f"date_{t['id']}")
                new_amount = st.number_input("Iznos", value=float(t["amount"]), key=f"amount_{t['id']}")
                new_category = st.text_input("Kategorija", value=t["category"], key=f"cat_{t['id']}")
                new_desc = st.text_input("Opis", value=t["description"], key=f"desc_{t['id']}")

            with col2:
                if st.button("💾", key=f"save_{t['id']}"):
                    update_transaction(t["id"], {
                        "date": new_date.isoformat(),
                        "amount": new_amount,
                        "category": new_category,
                        "description": new_desc
                    })

                    st.session_state.edit_id = None
                    st.toast("✏️ Transakcija ažurirana!")
                    st.rerun()

            with col3:
                if st.button("❌", key=f"cancel_{t['id']}"):
                    st.session_state.edit_id = None
                    st.rerun()

        else:

            with col1:
                st.markdown(f"""
<div style="
    font-size:12px;
    line-height:1.2;
    padding:4px 0;
">
<b>{'🟢' if t['type']=='income' else '🔴'} {t['amount']} RSD</b>
<br>
<span style="font-size:10px; opacity:0.75;">
📅 {t['date']} • 📂 {t['category']} • 📝 {t['description']}
</span>
</div>
""", unsafe_allow_html=True)

            with col2:
                if st.button("✏️", key=f"edit_{t['id']}"):
                    st.session_state.edit_id = t["id"]
                    st.rerun()

            with col3:
                if st.button("🗑️", key=f"del_{t['id']}"):
                    delete_transaction(t["id"])
                    st.rerun()