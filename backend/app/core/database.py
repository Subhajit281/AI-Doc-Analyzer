import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import asyncio
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "document_ai").strip()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
FALLBACK_STORE_PATH = DATA_DIR / "local_store.json"

def ensure_utc(dt: datetime | str | None) -> datetime | None:
    """Safely normalizes any datetime string or naive/aware datetime object to UTC offset-aware."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            if "Z" in dt:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            elif "+" in dt or ("-" in dt[10:] if len(dt) > 10 else False):
                dt = datetime.fromisoformat(dt)
            else:
                dt = datetime.fromisoformat(dt).replace(tzinfo=timezone.utc)
        except Exception:
            return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None

class DatabaseManager:
    """
    Asynchronous database manager supporting MongoDB Atlas / local MongoDB
    with an automatic, resilient persistent local fallback for zero-downtime offline dev.
    """

    def __init__(self):
        self._motor_client = None
        self._db = None
        self._using_mongo = False
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            if MONGODB_URI:
                try:
                    import motor.motor_asyncio
                    client = motor.motor_asyncio.AsyncIOMotorClient(
                        MONGODB_URI,
                        serverSelectionTimeoutMS=3000,
                    )
                    # Test ping
                    await client.admin.command('ping')
                    self._motor_client = client
                    self._db = client[MONGODB_DB_NAME]
                    self._using_mongo = True
                    print(f"[DATABASE] Connected to MongoDB: {MONGODB_DB_NAME}")

                    # Ensure unique index on email
                    await self._db.users.create_index("email", unique=True)
                    await self._db.payments.create_index("order_id", unique=True)
                    # TTL index on otps collection for automatic 10-minute expiry
                    await self._db.otps.create_index("expires_at_dt", expireAfterSeconds=0)
                    # Document collections & 7-day TTL index for automatic expiration
                    await self._db.documents.create_index([("user_id", 1), ("document_id", 1)], unique=True)
                    await self._db.documents.create_index("user_id")
                    await self._db.documents.create_index("document_id")
                    await self._db.documents.create_index("expires_at_dt", expireAfterSeconds=0)
                except Exception as exc:
                    print(f"[DATABASE] MongoDB connection failed ({exc}). Using resilient local store.")
                    self._using_mongo = False
            else:
                self._using_mongo = False

            if not self._using_mongo:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                if not FALLBACK_STORE_PATH.exists():
                    initial_data = {"users": {}, "payments": {}, "queries": [], "otps": {}, "documents": {}}
                    FALLBACK_STORE_PATH.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")

            self._initialized = True

    # --------------------------------------------------------
    # Local fallback helpers
    # --------------------------------------------------------
    def _read_local_store(self) -> dict:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not FALLBACK_STORE_PATH.exists():
            return {"users": {}, "payments": {}, "queries": [], "otps": {}, "documents": {}}
        try:
            store = json.loads(FALLBACK_STORE_PATH.read_text(encoding="utf-8"))
            store.setdefault("users", {})
            store.setdefault("payments", {})
            store.setdefault("queries", [])
            store.setdefault("otps", {})
            store.setdefault("documents", {})
            return store
        except Exception:
            return {"users": {}, "payments": {}, "queries": [], "otps": {}, "documents": {}}

    def _write_local_store(self, data: dict):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        FALLBACK_STORE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # --------------------------------------------------------
    # User Operations
    # --------------------------------------------------------
    async def get_user_by_email(self, email: str) -> dict | None:
        await self.initialize()
        normalized_email = email.strip().lower()

        if self._using_mongo:
            user = await self._db.users.find_one({"email": normalized_email})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        else:
            store = self._read_local_store()
            for uid, user in store.get("users", {}).items():
                if user.get("email", "").lower() == normalized_email:
                    u = dict(user)
                    u["id"] = uid
                    return u
            return None

    async def get_user_by_id(self, user_id: str) -> dict | None:
        await self.initialize()
        if not user_id:
            return None

        if self._using_mongo:
            from bson import ObjectId
            try:
                user = await self._db.users.find_one({"_id": ObjectId(user_id)})
            except Exception:
                user = await self._db.users.find_one({"id": user_id})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        else:
            store = self._read_local_store()
            user = store.get("users", {}).get(user_id)
            if user:
                u = dict(user)
                u["id"] = user_id
                return u
            return None

    async def create_user(self, email: str, password_hash: str, full_name: str = "") -> dict:
        await self.initialize()
        normalized_email = email.strip().lower()

        existing = await self.get_user_by_email(normalized_email)
        if existing:
            raise ValueError("An account with this email already exists.")

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        reset_iso = (now_dt + timedelta(hours=24)).isoformat()
        user_doc = {
            "email": normalized_email,
            "password_hash": password_hash,
            "full_name": full_name.strip(),
            "query_count": 0,
            "query_count_today": 0,
            "query_reset_at": reset_iso,
            "plan": "free",
            "plan_expires_at": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        if self._using_mongo:
            result = await self._db.users.insert_one(user_doc)
            user_doc["id"] = str(result.inserted_id)
            user_doc.pop("_id", None)
            return user_doc
        else:
            user_id = str(uuid.uuid4())
            store = self._read_local_store()
            store.setdefault("users", {})[user_id] = user_doc
            self._write_local_store(store)
            user_doc["id"] = user_id
            return user_doc

    async def update_user(self, user_id: str, updates: dict) -> dict | None:
        await self.initialize()
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self._using_mongo:
            from bson import ObjectId
            try:
                oid = ObjectId(user_id)
                await self._db.users.update_one({"_id": oid}, {"$set": updates})
            except Exception:
                await self._db.users.update_one({"id": user_id}, {"$set": updates})
            return await self.get_user_by_id(user_id)
        else:
            store = self._read_local_store()
            if user_id in store.get("users", {}):
                store["users"][user_id].update(updates)
                self._write_local_store(store)
                u = dict(store["users"][user_id])
                u["id"] = user_id
                return u
            return None

    async def check_and_refresh_quota(self, user_id: str) -> dict | None:
        """
        Checks 24-hour daily quota and paid subscription validity.
        Automatically renews daily quota if 24 hours have elapsed.
        """
        await self.initialize()
        if not user_id:
            return None

        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        now = datetime.now(timezone.utc)
        updates = {}

        # 1. 24-hour daily quota rollover
        reset_at = ensure_utc(user.get("query_reset_at"))
        if not reset_at:
            # Initial setup of 24h cycle: keep any queries used so far today
            today_count = user.get("query_count_today")
            if today_count is None:
                today_count = user.get("query_count", 0)
            updates["query_count_today"] = today_count
            updates["query_reset_at"] = (now + timedelta(hours=24)).isoformat()
        elif now >= reset_at:
            # 24-hour cycle has elapsed: renew daily quota to 0
            updates["query_count_today"] = 0
            updates["query_reset_at"] = (now + timedelta(hours=24)).isoformat()
        elif "query_count_today" not in user or user.get("query_count_today") is None:
            updates["query_count_today"] = user.get("query_count", 0)

        # 2. Plan expiration check
        plan = user.get("plan", "free")
        expires_at = user.get("plan_expires_at")
        if plan in ("day", "month", "year") and expires_at:
            exp_dt = ensure_utc(expires_at)
            if exp_dt and exp_dt <= now:
                updates["plan"] = "free"
                updates["plan_expires_at"] = None

        if updates:
            return await self.update_user(user_id, updates)
        return user

    async def increment_user_query_count(self, user_id: str) -> dict | None:
        """
        Increments lifetime query_count and daily query_count_today.
        Guarantees quota rollover has been performed first.
        """
        await self.initialize()
        if not user_id:
            return None

        refreshed = await self.check_and_refresh_quota(user_id)
        if not refreshed:
            return None

        if self._using_mongo:
            from bson import ObjectId
            try:
                oid = ObjectId(user_id)
                res = await self._db.users.find_one_and_update(
                    {"_id": oid},
                    {"$inc": {"query_count": 1, "query_count_today": 1}},
                    return_document=True,
                )
            except Exception:
                res = await self._db.users.find_one_and_update(
                    {"id": user_id},
                    {"$inc": {"query_count": 1, "query_count_today": 1}},
                    return_document=True,
                )
            if res:
                res["id"] = str(res.pop("_id", res.get("id")))
            return res
        else:
            store = self._read_local_store()
            if user_id in store.get("users", {}):
                u = store["users"][user_id]
                u["query_count"] = u.get("query_count", 0) + 1
                u["query_count_today"] = u.get("query_count_today", 0) + 1
                self._write_local_store(store)
                res = dict(u)
                res["id"] = user_id
                return res
            return None

    # --------------------------------------------------------
    # Payment & Subscription Operations
    # --------------------------------------------------------
    async def create_payment_order(self, payment_data: dict) -> dict:
        await self.initialize()
        now_iso = datetime.now(timezone.utc).isoformat()
        payment_data["created_at"] = now_iso
        payment_data["status"] = payment_data.get("status", "created")

        if self._using_mongo:
            res = await self._db.payments.insert_one(payment_data)
            payment_data["id"] = str(res.inserted_id)
            payment_data.pop("_id", None)
            return payment_data
        else:
            pid = str(uuid.uuid4())
            store = self._read_local_store()
            store.setdefault("payments", {})[payment_data["order_id"]] = payment_data
            self._write_local_store(store)
            payment_data["id"] = pid
            return payment_data

    async def get_payment_by_order_id(self, order_id: str) -> dict | None:
        await self.initialize()
        if self._using_mongo:
            payment = await self._db.payments.find_one({"order_id": order_id})
            if payment:
                payment["id"] = str(payment.pop("_id"))
            return payment
        else:
            store = self._read_local_store()
            return store.get("payments", {}).get(order_id)

    async def mark_payment_paid(self, order_id: str, payment_id: str, signature: str) -> dict | None:
        await self.initialize()
        now_iso = datetime.now(timezone.utc).isoformat()
        updates = {
            "status": "paid",
            "payment_id": payment_id,
            "signature": signature,
            "paid_at": now_iso,
        }

        if self._using_mongo:
            await self._db.payments.update_one({"order_id": order_id}, {"$set": updates})
            return await self.get_payment_by_order_id(order_id)
        else:
            store = self._read_local_store()
            if order_id in store.get("payments", {}):
                store["payments"][order_id].update(updates)
                self._write_local_store(store)
                return store["payments"][order_id]
            return None

    async def get_user_payments(self, user_id: str) -> list:
        await self.initialize()
        if not user_id:
            return []

        if self._using_mongo:
            cursor = self._db.payments.find({"user_id": user_id}).sort("created_at", -1)
            results = []
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                results.append(doc)
            return results
        else:
            store = self._read_local_store()
            results = []
            for p in store.get("payments", {}).values():
                if p.get("user_id") == user_id:
                    results.append(p)
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results

    # --------------------------------------------------------
    # Query Logging
    # --------------------------------------------------------
    async def log_user_query(self, user_id: str, document_id: str, query: str):
        await self.initialize()
        record = {
            "user_id": user_id,
            "document_id": document_id,
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._using_mongo:
            await self._db.queries.insert_one(record)
        else:
            store = self._read_local_store()
            store.setdefault("queries", []).append(record)
            self._write_local_store(store)

    # --------------------------------------------------------
    # OTP Operations (Encrypted, 10-Min Expiry & Rate-Limited)
    # --------------------------------------------------------
    def _cleanup_local_otps(self, store: dict | None = None) -> dict:
        if store is None:
            store = self._read_local_store()
        otps = store.get("otps", {})
        if not otps:
            return store
        now = datetime.now(timezone.utc)
        expired_keys = []
        for k, v in otps.items():
            exp_dt = ensure_utc(v.get("expires_at") or v.get("expires_at_dt"))
            if exp_dt and exp_dt < now:
                expired_keys.append(k)
        if expired_keys:
            for k in expired_keys:
                otps.pop(k, None)
            self._write_local_store(store)
        return store

    async def save_otp(
        self,
        email: str,
        hashed_otp: str,
        salt: str,
        expires_at_iso: str,
        purpose: str = "login",
        expires_at_dt: datetime | None = None,
    ):
        await self.initialize()
        normalized_email = email.lower().strip()
        key = f"{normalized_email}_{purpose}"

        if expires_at_dt is None:
            expires_at_dt = ensure_utc(expires_at_iso) or datetime.now(timezone.utc)

        record = {
            "key": key,
            "email": normalized_email,
            "hashed_otp": hashed_otp,
            "salt": salt,
            "expires_at": expires_at_iso,
            "expires_at_dt": expires_at_dt,
            "purpose": purpose,
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._using_mongo:
            await self._db.otps.update_one({"key": key}, {"$set": record}, upsert=True)
        else:
            store = self._cleanup_local_otps()
            # In local JSON file store, keep expires_at_dt as ISO string for JSON serialization
            local_record = dict(record)
            local_record["expires_at_dt"] = expires_at_iso
            store.setdefault("otps", {})[key] = local_record
            self._write_local_store(store)

    async def get_otp(self, email: str, purpose: str = "login", prune_if_expired: bool = True) -> dict | None:
        await self.initialize()
        key = f"{email.lower().strip()}_{purpose}"
        now = datetime.now(timezone.utc)

        if self._using_mongo:
            doc = await self._db.otps.find_one({"key": key})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                if prune_if_expired:
                    exp_dt = ensure_utc(doc.get("expires_at_dt") or doc.get("expires_at"))
                    if exp_dt and exp_dt < now:
                        await self._db.otps.delete_one({"key": key})
                        return None
            return doc
        else:
            if prune_if_expired:
                self._cleanup_local_otps()
            store = self._read_local_store()
            doc = store.get("otps", {}).get(key)
            if doc and prune_if_expired:
                exp_dt = ensure_utc(doc.get("expires_at") or doc.get("expires_at_dt"))
                if exp_dt and exp_dt < now:
                    del store["otps"][key]
                    self._write_local_store(store)
                    return None
            return doc

    async def increment_otp_attempts(self, email: str, purpose: str = "login") -> int:
        await self.initialize()
        key = f"{email.lower().strip()}_{purpose}"
        if self._using_mongo:
            res = await self._db.otps.find_one_and_update(
                {"key": key},
                {"$inc": {"attempts": 1}},
                return_document=True,
            )
            return res.get("attempts", 0) if res else 0
        else:
            store = self._read_local_store()
            if key in store.get("otps", {}):
                current = store["otps"][key].get("attempts", 0) + 1
                store["otps"][key]["attempts"] = current
                self._write_local_store(store)
                return current
            return 0

    async def delete_otp(self, email: str, purpose: str = "login"):
        await self.initialize()
        key = f"{email.lower().strip()}_{purpose}"
        if self._using_mongo:
            await self._db.otps.delete_one({"key": key})
        else:
            store = self._read_local_store()
            if key in store.get("otps", {}):
                del store["otps"][key]
                self._write_local_store(store)

    # --------------------------------------------------------
    # Document Operations (User-Account Storage with 7-Day TTL)
    # --------------------------------------------------------
    async def save_document(self, doc_data: dict) -> dict:
        await self.initialize()
        now = datetime.now(timezone.utc)
        doc = dict(doc_data)

        # Ensure UTC datetime for MongoDB TTL index
        created_dt = ensure_utc(doc.get("created_at")) or now
        expires_dt = ensure_utc(doc.get("expires_at")) or (created_dt + timedelta(days=7))

        doc["created_at"] = created_dt.isoformat()
        doc["expires_at"] = expires_dt.isoformat()
        doc["expires_at_dt"] = expires_dt
        doc["created_at_dt"] = created_dt

        document_id = doc["document_id"]

        if self._using_mongo:
            # Upsert into MongoDB
            await self._db.documents.update_one(
                {"document_id": document_id},
                {"$set": doc},
                upsert=True,
            )
            doc.pop("_id", None)
            return doc
        else:
            store = self._read_local_store()
            serializable_doc = dict(doc)
            serializable_doc.pop("expires_at_dt", None)
            serializable_doc.pop("created_at_dt", None)
            if "file_bytes" in serializable_doc and isinstance(serializable_doc["file_bytes"], (bytes, bytearray)):
                import base64
                serializable_doc["file_bytes_b64"] = base64.b64encode(serializable_doc["file_bytes"]).decode("utf-8")
                serializable_doc.pop("file_bytes", None)
            store.setdefault("documents", {})[document_id] = serializable_doc
            self._write_local_store(store)
            return doc

    async def get_document(self, document_id: str, user_id: str | None = None) -> dict | None:
        await self.initialize()
        now = datetime.now(timezone.utc)
        if not document_id:
            return None

        if self._using_mongo:
            query = {"document_id": document_id}
            if user_id:
                query["user_id"] = user_id
            doc = await self._db.documents.find_one(query)
            if not doc:
                return None
            doc["id"] = str(doc.pop("_id", ""))

            # Verify 7-day TTL expiration
            exp_dt = ensure_utc(doc.get("expires_at_dt") or doc.get("expires_at"))
            if exp_dt and exp_dt < now:
                await self._db.documents.delete_one({"document_id": document_id})
                return None
            return doc
        else:
            store = self._read_local_store()
            doc = store.get("documents", {}).get(document_id)
            if not doc:
                return None
            if user_id and doc.get("user_id") != user_id:
                return None

            exp_dt = ensure_utc(doc.get("expires_at"))
            if exp_dt and exp_dt < now:
                del store["documents"][document_id]
                self._write_local_store(store)
                return None
            return dict(doc)

    async def get_user_documents(self, user_id: str) -> list[dict]:
        await self.initialize()
        now = datetime.now(timezone.utc)
        if not user_id:
            return []

        if self._using_mongo:
            cursor = self._db.documents.find(
                {"user_id": user_id},
                {"file_bytes": 0}
            ).sort("created_at", -1)

            docs = []
            async for item in cursor:
                item["id"] = str(item.pop("_id", ""))
                exp_dt = ensure_utc(item.get("expires_at_dt") or item.get("expires_at"))
                if exp_dt and exp_dt < now:
                    continue  # Filter out expired docs

                if exp_dt:
                    seconds_left = max(0, (exp_dt - now).total_seconds())
                    days_left = int(seconds_left // 86400)
                    hours_left = int((seconds_left % 86400) // 3600)
                    item["days_remaining"] = days_left
                    item["hours_remaining"] = hours_left
                    item["expiry_label"] = (
                        f"Expires in {days_left}d {hours_left}h"
                        if days_left > 0
                        else f"Expires in {hours_left}h"
                    )
                docs.append(item)
            return docs
        else:
            store = self._read_local_store()
            docs = []
            for doc_id, item in store.get("documents", {}).items():
                if item.get("user_id") == user_id:
                    exp_dt = ensure_utc(item.get("expires_at"))
                    if exp_dt and exp_dt < now:
                        continue
                    clean_item = dict(item)
                    clean_item.pop("file_bytes_b64", None)
                    if exp_dt:
                        seconds_left = max(0, (exp_dt - now).total_seconds())
                        days_left = int(seconds_left // 86400)
                        hours_left = int((seconds_left % 86400) // 3600)
                        clean_item["days_remaining"] = days_left
                        clean_item["hours_remaining"] = hours_left
                        clean_item["expiry_label"] = (
                            f"Expires in {days_left}d {hours_left}h"
                            if days_left > 0
                            else f"Expires in {hours_left}h"
                        )
                    docs.append(clean_item)
            docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
            return docs

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        await self.initialize()
        if not document_id or not user_id:
            return False

        if self._using_mongo:
            res = await self._db.documents.delete_one({
                "document_id": document_id,
                "user_id": user_id,
            })
            return res.deleted_count > 0
        else:
            store = self._read_local_store()
            doc = store.get("documents", {}).get(document_id)
            if doc and doc.get("user_id") == user_id:
                del store["documents"][document_id]
                self._write_local_store(store)
                return True
            return False

    async def cleanup_expired_documents(self) -> list[str]:
        await self.initialize()
        now = datetime.now(timezone.utc)
        expired_ids = []

        if self._using_mongo:
            cursor = self._db.documents.find({
                "$or": [
                    {"expires_at_dt": {"$lt": now}},
                ]
            }, {"document_id": 1})
            async for doc in cursor:
                expired_ids.append(doc["document_id"])
            if expired_ids:
                await self._db.documents.delete_many({"document_id": {"$in": expired_ids}})
        else:
            store = self._read_local_store()
            to_delete = []
            for doc_id, doc in store.get("documents", {}).items():
                exp_dt = ensure_utc(doc.get("expires_at"))
                if exp_dt and exp_dt < now:
                    to_delete.append(doc_id)
            for doc_id in to_delete:
                expired_ids.append(doc_id)
                del store["documents"][doc_id]
            if to_delete:
                self._write_local_store(store)
        return expired_ids

# Singleton
db_manager = DatabaseManager()

