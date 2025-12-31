import streamlit as st
import config
from datetime import datetime, timedelta
import time
from utils import format_date
from database import TransactionModel


# ======================================
# Render single transaction
# ======================================
def _render_transaction_card(model: TransactionModel, item: dict):
    transaction_type = item.get("type", "Unknown")
    amount = item.get("amount", 0)
    tx_date = item.get("date", datetime.now())
    category = item.get("category", "Others")

    type_icon = "🔴" if transaction_type == "Expense" else "🟢"
    header = f"{type_icon} {format_date(tx_date)} | {category} | ${amount:,.2f}"

    with st.expander(header):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Type:**", transaction_type)
            st.write("**Category:**", category)
            st.write("**Amount:**", f"${amount:,.2f}")

        with col2:
            st.write("**Date:**", format_date(tx_date))
            if item.get("note"):
                st.write("**Description:**", item["note"])
            if item.get("updated_at"):
                st.write("**Last Modified:**", format_date(item["updated_at"]))

        st.divider()
        col_edit, col_delete, _ = st.columns([1, 1, 3])

        with col_delete:
            if st.button("🗑️ Delete", key=f"delete_{item['_id']}", type="primary"):
                if model.delete_transaction(str(item["_id"])):
                    st.success("Transaction deleted")
                    time.sleep(0.5)
                    st.rerun()


# ======================================
# Filters
# ======================================
def _render_filters():
    st.subheader("🔍 Filters")

    col1, col2 = st.columns(2)

    with col1:
        tx_type = st.selectbox(
            "Transaction Type",
            options=[None] + config.TRANSACTION_TYPES,
            format_func=lambda x: x or "All",
        )

        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
        )

    with col2:
        category = st.text_input("Category")
        end_date = st.date_input("End Date", value=datetime.now())

    if st.button("Apply Filters", type="primary"):
        st.session_state.active_filters = {
            "tx_type": tx_type,
            "category": category,
            "start_date": start_date,
            "end_date": end_date,
        }
        st.rerun()

    if st.button("Clear Filters"):
        st.session_state.active_filters = {}
        st.rerun()


# ======================================
# Create transaction
# ======================================
def _render_create_transaction_form(transaction_model, category_model):
    st.subheader("➕ Create Transaction")

    category = None  # ✅ FIX: tránh UnboundLocalError

    col1, col2 = st.columns(2)

    with col1:
        tx_type = st.selectbox("Type *", config.TRANSACTION_TYPES)
        amount = st.number_input("Amount *", min_value=0.01, step=1.0)
        tx_date = st.date_input("Date *", value=datetime.now())

    with col2:
        categories = category_model.get_categories_by_type(tx_type)
        category_names = [c["name"] for c in categories]

        category = st.selectbox("Category *", category_names)
        note = st.text_area("Description")

    if st.button("Save", type="primary"):
        try:
            transaction_model.create_transaction(
                tx_type=tx_type,
                category=category,
                amount=amount,
                date_value=datetime.combine(tx_date, datetime.now().time()),
                note=note,
            )
            st.success("Transaction created")
            st.session_state.show_create_form = False
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    if st.button("Cancel"):
        st.session_state.show_create_form = False
        st.rerun()


# ======================================
# List transactions
# ======================================
def _render_list_transaction(transaction_model: TransactionModel):
    filters = st.session_state.get("active_filters", {})

    transactions = transaction_model.get_transactions(
        tx_type=filters.get("tx_type"),
        category=filters.get("category"),
        start_date=filters.get("start_date"),
        end_date=filters.get("end_date"),
        limit=500,
    )

    if not transactions:
        st.info("No transactions found.")
        return

    for tx in transactions:
        _render_transaction_card(transaction_model, tx)


# ======================================
# Main view
# ======================================
def render_transactions(transaction_model, category_model):
    if not getattr(transaction_model, "user_id", None):
        st.warning("Please log in to view transactions.")
        return

    st.title("📊 Transactions")

    if "show_create_form" not in st.session_state:
        st.session_state.show_create_form = False
    if "active_filters" not in st.session_state:
        st.session_state.active_filters = {}

    col1, col2, col3 = st.columns([3, 1, 1])

    with col2:
        if st.button("➕ CREATE", type="primary"):
            st.session_state.show_create_form = not st.session_state.show_create_form
            st.rerun()

    with col3:
        if st.button("🔍 Filters"):
            st.session_state.show_filters = not st.session_state.get("show_filters", False)
            st.rerun()

    if st.session_state.show_create_form:
        _render_create_transaction_form(transaction_model, category_model)
        st.divider()

    if st.session_state.get("show_filters"):
        _render_filters()
        st.divider()

    _render_list_transaction(transaction_model)
