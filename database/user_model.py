from database.database_manager import DatabaseManager
import config
from datetime import datetime
from bson.objectid import ObjectId

collection_name = config.COLLECTIONS["user"]

class UserModel:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.collection = self.db_manager.get_collection(collection_name)

        self.transaction_collection = self.db_manager.get_collection(
            config.COLLECTIONS["transaction"]
        )
        self.category_collection = self.db_manager.get_collection(
            config.COLLECTIONS["category"]
        )
        self.budget_collection = self.db_manager.get_collection(
            config.COLLECTIONS["budget"]
        )

        # 👉 đảm bảo email unique (chạy 1 lần là đủ)
        self.collection.create_index("email", unique=True)

    # ==================================================
    # CREATE USER
    # ==================================================
    def create_user(self, email: str) -> str:
        now = datetime.utcnow()

        user = {
            "email": email,
            "role": "user",
            "is_active": True,
            "created_at": now,
            "last_login": now,
        }

        result = self.collection.insert_one(user)
        return str(result.inserted_id)

    # ==================================================
    # LOGIN (AUTO CREATE USER)
    # ==================================================
    def login(self, email: str) -> str:
        user = self.collection.find_one({"email": email})

        # 👉 USER CHƯA TỒN TẠI → TẠO MỚI
        if not user:
            return self.create_user(email)

        # 👉 USER BỊ DEACTIVATE
        if not user.get("is_active", False):
            raise ValueError("This account is deactivated. Please contact support.")

        # 👉 UPDATE LAST LOGIN
        self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        return str(user["_id"])

    # ==================================================
    # DEACTIVATE USER
    # ==================================================
    def deactivate_user(self, user_id: str) -> bool:
        oid = ObjectId(user_id)

        user = self.collection.find_one({
            "_id": oid,
            "is_active": True
        })

        if not user:
            raise ValueError("User not found or already deactivated")

        result = self.collection.update_one(
            {"_id": oid},
            {"$set": {"is_active": False}}
        )

        return result.modified_count > 0

    # ==================================================
    # DELETE USER + ALL DATA
    # ==================================================
    def delete_user_with_data(self, user_id: str) -> dict:
        oid = ObjectId(user_id)

        # 1. Delete transactions
        tx_filter = {"user_id": oid}
        transactions_deleted = self.transaction_collection.count_documents(tx_filter)
        self.transaction_collection.delete_many(tx_filter)

        # 2. Delete budgets
        budget_filter = {"user_id": oid}
        budgets_deleted = self.budget_collection.count_documents(budget_filter)
        self.budget_collection.delete_many(budget_filter)

        # 3. Delete custom categories
        default_names = set(
            config.DEFAULT_CATEGORIES_EXPENSE + config.DEFAULT_CATEGORIES_INCOME
        )

        category_filter = {
            "user_id": oid,
            "name": {"$nin": list(default_names)}
        }
        categories_deleted = self.category_collection.count_documents(category_filter)
        self.category_collection.delete_many(category_filter)

        # 4. Delete user
        user_deleted = self.collection.delete_one({"_id": oid}).deleted_count

        return {
            "user_deleted": user_deleted,
            "transactions_deleted": transactions_deleted,
            "budgets_deleted": budgets_deleted,
            "categories_deleted": categories_deleted,
            "message": (
                f"Deleted {user_deleted} user, "
                f"{transactions_deleted} transactions, "
                f"{budgets_deleted} budgets, "
                f"{categories_deleted} categories"
            )
        }
