from datetime import datetime
from typing import Optional, List, Dict, Any

from bson.objectid import ObjectId

from .database_manager import DatabaseManager
import config


class TransactionModel:
    """
    Transaction model (per-user)
    Exam requirement (3 points):
    - Validate category exists before create/update
    Also must ensure user data isolation.
    """

    def __init__(self, user_id: Optional[str] = None):
        self.db_manager = DatabaseManager()

        self.collection = self.db_manager.get_collection(config.COLLECTIONS["transaction"])
        self.category_collection = self.db_manager.get_collection(config.COLLECTIONS["category"])

        self.user_id: Optional[ObjectId] = None
        if user_id:
            self.set_user_id(user_id)

        try:
            self.collection.create_index([("user_id", 1), ("date", -1)])
        except Exception:
            pass

    # -----------------------------
    # Helpers
    # -----------------------------
    def set_user_id(self, user_id: Optional[str]):
        # IMPORTANT: store as ObjectId once
        self.user_id = ObjectId(user_id) if user_id else None

    def _require_user(self):
        if not self.user_id:
            raise ValueError("user_id is required. Call set_user_id() first.")

    def _validate_type(self, tx_type: str):
        if tx_type not in ("Income", "Expense"):
            raise ValueError("type must be 'Income' or 'Expense'")

    def _validate_category(self, category: str, tx_type: Optional[str] = None):
        """
        Exam: category must exist in category collection.
        If your categories are separated by type, validate with both name and type.
        """
        self._require_user()
        q: Dict[str, Any] = {"user_id": self.user_id, "name": category}
        if tx_type:
            q["type"] = tx_type

        found = self.category_collection.find_one(q)
        if not found:
            raise ValueError(f"Category '{category}' does not exist")

    # -----------------------------
    # CRUD
    # -----------------------------
    def create_transaction(
        self,
        tx_type: str,
        category: str,
        amount: float,
        date_value: Optional[datetime] = None,
        note: str = "",
    ) -> str:
        self._require_user()
        self._validate_type(tx_type)

        category = (category or "").strip()
        if not category:
            raise ValueError("category is required")

        # ✅ Exam requirement: validate category exists
        self._validate_category(category, tx_type)

        if amount is None:
            raise ValueError("amount is required")

        try:
            amount = float(amount)
        except Exception:
            raise ValueError("amount must be a number")

        if amount < 0:
            raise ValueError("amount must be >= 0")

        now = datetime.utcnow()
        tx_date = date_value if isinstance(date_value, datetime) else now

        doc = {
            "user_id": self.user_id,
            "type": tx_type,
            "category": category,
            "amount": amount,
            "date": tx_date,
            "note": note or "",
            "created_at": now,
            "updated_at": now,
        }

        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get_transactions(
        self,
        tx_type: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        self._require_user()

        q: Dict[str, Any] = {"user_id": self.user_id}

        if tx_type:
            self._validate_type(tx_type)
            q["type"] = tx_type

        if category:
            q["category"] = category

        if start_date or end_date:
            q["date"] = {}

            if start_date:
                if not isinstance(start_date, datetime):
                    start_date = datetime.combine(start_date, datetime.min.time())
                q["date"]["$gte"] = start_date
        
            if end_date:
                if not isinstance(end_date, datetime):
                    end_date = datetime.combine(end_date, datetime.min.time())
                q["date"]["$lt"] = end_date


        cursor = self.collection.find(q).sort([("date", -1)]).limit(int(limit))
        return list(cursor)

    def update_transaction(self, tx_id: str, update_data: Dict[str, Any]) -> bool:
        """
        update_data can include: type, category, amount, date, note
        Must validate category if category/type changed.
        """
        self._require_user()
        if not update_data:
            return False

        update_data = dict(update_data)  # copy
        now = datetime.utcnow()

        # Normalize / validate
        if "type" in update_data and update_data["type"]:
            self._validate_type(update_data["type"])

        if "amount" in update_data and update_data["amount"] is not None:
            try:
                update_data["amount"] = float(update_data["amount"])
            except Exception:
                raise ValueError("amount must be a number")
            if update_data["amount"] < 0:
                raise ValueError("amount must be >= 0")

        # Get existing doc to validate cross-field
        existing = self.collection.find_one({"_id": ObjectId(tx_id), "user_id": self.user_id})
        if not existing:
            raise ValueError("Transaction not found")

        new_type = update_data.get("type", existing.get("type"))
        new_category = update_data.get("category", existing.get("category"))

        if "category" in update_data or "type" in update_data:
            if new_category:
                # ✅ Exam requirement: validate category exists
                self._validate_category(str(new_category).strip(), new_type)

        update_data["updated_at"] = now

        result = self.collection.update_one(
            {"_id": ObjectId(tx_id), "user_id": self.user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    def delete_transaction(self, tx_id: str) -> bool:
        self._require_user()
        result = self.collection.delete_one({"_id": ObjectId(tx_id), "user_id": self.user_id})
        return result.deleted_count > 0

    # -----------------------------
    # Aggregation helpers (optional)
    # -----------------------------
    def sum_by_type(self, tx_type: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> float:
        self._require_user()
        self._validate_type(tx_type)

        match: Dict[str, Any] = {"user_id": self.user_id, "type": tx_type}
        if start_date or end_date:
            q["date"] = {}

            if start_date:
                if not isinstance(start_date, datetime):
                    start_date = datetime.combine(start_date, datetime.min.time())
                q["date"]["$gte"] = start_date
        
            if end_date:
                if not isinstance(end_date, datetime):
                    end_date = datetime.combine(end_date, datetime.min.time())
                q["date"]["$lt"] = end_date

        pipeline = [
            {"$match": match},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        out = list(self.collection.aggregate(pipeline))
        return float(out[0]["total"]) if out else 0.0
    # ==================================================
    # Compatibility helper for Analyzer (DO NOT REMOVE)
    # ==================================================
    def get_transactions_by_date_range(
        self,
        start_date,
        end_date,
        tx_type: str | None = None,
    ):
        """
        Adapter method for Analyzer.
        This keeps old analyzer code working without refactor.
        """

        return self.get_transactions(
            tx_type=tx_type,
            start_date=start_date,
            end_date=end_date,
            limit=10_000
        )

