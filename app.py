import streamlit as st
from pymongo import MongoClient

# =====================================================
# Page config (PHẢI đặt đầu file)
# =====================================================
st.set_page_config(
    page_title="Finance Tracker",
    page_icon="🤑",
    layout="wide"
)

# =====================================================
# Load secrets
# =====================================================
MONGO_URI = st.secrets["MONGO_URI"]
DATABASE_NAME = st.secrets["DATABASE_NAME"]

AUTH = st.secrets["auth"]
CLIENT_ID = AUTH["client_id"]
CLIENT_SECRET = AUTH["client_secret"]
COOKIE_SECRET = AUTH["cookie_secret"]
REDIRECT_URI = AUTH["redirect_uri"]
SERVER_METADATA_URL = AUTH["server_metadata_url"]

# =====================================================
# Init MongoDB
# =====================================================
@st.cache_resource
def init_mongo():
    client = MongoClient(MONGO_URI)
    return client[DATABASE_NAME]

db = init_mongo()

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
# Init models (cache per session)
# =====================================================
@st.cache_resource
def init_models(db):
    return {
        "user": UserModel(db),
        "category": CategoryModel(db),
        "transaction": TransactionModel(db),
        "budget": BudgetModel(db),
        "visualizer": FinanceVisualizer(),
    }

models = init_models(db)

# =====================================================
# Auth UI
# =====================================================
def login_screen():
    st.title("🔐 Finance Tracker")
    st.subheader("Ứng dụng riêng tư – vui lòng đăng nhập")
    st.button("Đăng nhập bằng Google", on_click=st.login)

# =====================================================
# AUTH FLOW
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
    st.error(f"❌ Lỗi xử lý user: {e}")
    st.stop()

# =====================================================
# Set user_id cho các model phụ thuộc user
# =====================================================
models["category"].set_user_id(mongo_user_id)
models["transaction"].set_user_id(mongo_user_id)
models["budget"].set_user_id(mongo_user_id)

# =====================================================
# Build user object cho UI
# =====================================================
user = st.user.to_dict()
user["id"] = mongo_user_id

# =====================================================
# Sidebar
# =====================================================
with st.sidebar:
    st.write(f"👤 {user.get('email')}")
    st.divider()
    page = st.radio(
        "Điều hướng",
        ["Home", "Category", "Transaction", "Budget"]
    )
    st.divider()
    if st.button("🚪 Đăng xuất"):
        st.logout()

# =====================================================
# Main views
# =====================================================
render_user_profile(user_model, user)

analyzer = FinanceAnalyzer(models["transaction"])

if page == "Home":
    st.title("🏠 Tổng quan")
    render_dashboard(
        analyzer_model=analyzer,
        transaction_model=models["transaction"],
        visualizer_model=models["visualizer"],
    )

elif page == "Category":
    st.title("📂 Danh mục")
    render_categories(category_model=models["category"])

elif page == "Transaction":
    st.title("💸 Giao dịch")
    render_transactions(
        transaction_model=models["transaction"],
        category_model=models["category"],
    )

elif page == "Budget":
    st.title("📊 Ngân sách")
    render_budgets(
        budget_model=models["budget"],
        category_model=models["category"],
    )
