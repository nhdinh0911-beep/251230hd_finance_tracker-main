import streamlit as st

# =====================================================
# Page config
# =====================================================
st.set_page_config(
    page_title="Finance Tracker",
    page_icon="🤑",
    layout="wide"
)

# =====================================================
# Import models
# =====================================================
from database import (
    UserModel,
    CategoryModel,
    TransactionModel,
    BudgetModel,
)

from analytics.analyzer import FinanceAnalyzer
from analytics.visualizer import FinanceVisualizer

from views import (
    render_categories,
    render_transactions,
    render_user_profile,
    render_dashboard,
    render_budgets,
)

# =====================================================
# Init models (KHÔNG CACHE DB)
# =====================================================
def init_models():
    return {
        "user": UserModel(),
        "category": CategoryModel(),
        "transaction": TransactionModel(),
        "budget": BudgetModel(),
        "visualizer": FinanceVisualizer(),
    }

models = init_models()

# =====================================================
# LOGIN SCREEN (THEO GOOGLE AUTH PLATFORM)
# =====================================================
def login_screen():
    st.title("🔐 Finance Tracker")
    st.subheader("Vui lòng đăng nhập bằng Google")
    st.button("Login with Google", on_click=st.login)

# =====================================================
# AUTH FLOW (CHUẨN STREAMLIT)
# =====================================================
if not st.user.is_logged_in:
    login_screen()
    st.stop()

# =====================================================
# USER LOGIN / CREATE USER IN DB
# =====================================================
user_model: UserModel = models["user"]

try:
    mongo_user_id = user_model.login(st.user.email)
except Exception as e:
    st.error(f"Lỗi xử lý user: {e}")
    st.stop()

# =====================================================
# Set user_id cho các model
# =====================================================
models["category"].set_user_id(mongo_user_id)
models["transaction"].set_user_id(mongo_user_id)
models["budget"].set_user_id(mongo_user_id)

# =====================================================
# Build user info
# =====================================================
user = st.user.to_dict()
user["id"] = mongo_user_id

# =====================================================
# Sidebar
# =====================================================
with st.sidebar:
    st.write(f"👤 {user['email']}")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Home", "Category", "Transaction", "Budget"]
    )

    st.divider()
    if st.button("Logout"):
        st.logout()

# =====================================================
# Main views
# =====================================================
render_user_profile(user_model, user)

analyzer = FinanceAnalyzer(models["transaction"])

if page == "Home":
    render_dashboard(
        analyzer_model=analyzer,
        transaction_model=models["transaction"],
        visualizer_model=models["visualizer"],
    )

elif page == "Category":
    render_categories(models["category"])

elif page == "Transaction":
    render_transactions(
        transaction_model=models["transaction"],
        category_model=models["category"]
    )

elif page == "Budget":
    render_budgets(
        budget_model=models["budget"],
        category_model=models["category"]
    )
