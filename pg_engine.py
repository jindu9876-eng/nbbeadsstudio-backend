import os
import sys
import json
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from pydantic._internal._model_construction import ModelMetaclass

import asyncpg

logger = logging.getLogger("backend.pg_engine")

# Global asyncpg connection pool
_pg_pool: Optional[asyncpg.Pool] = None
_use_fallback_mock: bool = False
_mock_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

FALLBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "fallback_db.json")

def _save_fallback_db():
    if not _use_fallback_mock and _pg_pool is not None:
        return
    try:
        os.makedirs(os.path.dirname(FALLBACK_DB_PATH), exist_ok=True)
        def serialize_item(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        with open(FALLBACK_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(_mock_store, f, default=serialize_item, indent=2)
    except Exception as e:
        logger.warning(f"Could not persist fallback database to file: {e}")

def _load_fallback_db():
    global _mock_store
    if os.path.exists(FALLBACK_DB_PATH):
        try:
            with open(FALLBACK_DB_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and loaded:
                    _mock_store = loaded
                    logger.info(f"Loaded {sum(len(v) for v in _mock_store.values())} records from fallback DB file.")
                    return True
        except Exception as e:
            logger.warning(f"Could not load fallback database from file: {e}")
    return False

# -------------------------------------------------------------
# Binary Expressions & Field Proxy for `Model.field == val`
# -------------------------------------------------------------

class BinaryExpr:
    def __init__(self, field: str, op: str, value: Any):
        self.field = field
        self.op = op
        self.value = value

    def __repr__(self):
        return f"BinaryExpr({self.field} {self.op} {self.value})"

class FieldProxy:
    def __init__(self, field_name: str):
        self.field_name = field_name

    def __eq__(self, other):
        return BinaryExpr(self.field_name, "=", other)

    def __ne__(self, other):
        return BinaryExpr(self.field_name, "!=", other)

    def __gt__(self, other):
        return BinaryExpr(self.field_name, ">", other)

    def __ge__(self, other):
        return BinaryExpr(self.field_name, ">=", other)

    def __lt__(self, other):
        return BinaryExpr(self.field_name, "<", other)

    def __le__(self, other):
        return BinaryExpr(self.field_name, "<=", other)

    def __repr__(self):
        return f"FieldProxy({self.field_name})"

class DocumentMeta(ModelMetaclass):
    def __getattr__(cls, name: str):
        if not name.startswith("_") and name in cls.model_fields:
            return FieldProxy(name)
        return super().__getattr__(name)

# -------------------------------------------------------------
# Query Cursor
# -------------------------------------------------------------

class PgQuery:
    def __init__(self, model_cls, filters: list):
        self.model_cls = model_cls
        self.filters = filters
        self._sort: Optional[List[tuple]] = None
        self._skip: int = 0
        self._limit: Optional[int] = None

    def sort(self, *fields):
        # Supports: .sort("name"), .sort("-created_at"), .sort([("created_at", -1)])
        sort_list = []
        for f in fields:
            if isinstance(f, str):
                if f.startswith("-"):
                    sort_list.append((f[1:], "DESC"))
                else:
                    sort_list.append((f, "ASC"))
            elif isinstance(f, list):
                for item in f:
                    if isinstance(item, tuple):
                        direction = "DESC" if item[1] in (-1, "desc", "DESC") else "ASC"
                        sort_list.append((item[0], direction))
            elif isinstance(f, tuple):
                direction = "DESC" if f[1] in (-1, "desc", "DESC") else "ASC"
                sort_list.append((f[0], direction))
        self._sort = sort_list
        return self

    def skip(self, n: int):
        self._skip = max(0, n)
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    async def to_list(self) -> List[Any]:
        return await execute_find(self.model_cls, self.filters, sort=self._sort, skip=self._skip, limit=self._limit)

    async def count(self) -> int:
        return await execute_count(self.model_cls, self.filters)

    def __await__(self):
        return self.to_list().__await__()

# -------------------------------------------------------------
# Document Base Class
# -------------------------------------------------------------

class Document(BaseModel, metaclass=DocumentMeta):
    id: Optional[str] = Field(default=None)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.id = None

    @classmethod
    def get_table_name(cls) -> str:
        settings = getattr(cls, "Settings", None)
        if settings and hasattr(settings, "name"):
            return settings.name
        return cls.__name__.lower() + "s"

    @classmethod
    def get_json_fields(cls) -> set:
        json_fields = set()
        for name, field in cls.model_fields.items():
            origin = getattr(field.annotation, "__origin__", None)
            if origin in (list, dict) or field.annotation in (list, dict, Any):
                json_fields.add(name)
        return json_fields

    @classmethod
    async def get(cls, id: str):
        if not id:
            return None
        return await execute_get(cls, str(id))

    @classmethod
    async def find_one(cls, *args, **kwargs):
        filters = list(args)
        if kwargs:
            filters.append(kwargs)
        results = await execute_find(cls, filters, limit=1)
        return results[0] if results else None

    @classmethod
    def find(cls, *args, **kwargs):
        filters = list(args)
        if kwargs:
            filters.append(kwargs)
        return PgQuery(cls, filters)

    @classmethod
    def find_all(cls, *args, **kwargs):
        return cls.find(*args, **kwargs)

    @classmethod
    async def count(cls, *args, **kwargs) -> int:
        filters = list(args)
        if kwargs:
            filters.append(kwargs)
        return await execute_count(cls, filters)

    async def insert(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:24]
        now = datetime.utcnow()
        if hasattr(self, "created_at") and not getattr(self, "created_at", None):
            setattr(self, "created_at", now)
        if hasattr(self, "updated_at") and not getattr(self, "updated_at", None):
            setattr(self, "updated_at", now)
        await execute_insert(self)
        return self

    async def save(self):
        if not self.id:
            return await self.insert()
        if hasattr(self, "updated_at"):
            setattr(self, "updated_at", datetime.utcnow())
        await execute_update(self)
        return self

    async def delete(self):
        if self.id:
            await execute_delete(self.__class__, self.id)

    async def set(self, updates: Dict[str, Any]):
        for k, v in updates.items():
            if hasattr(self, k):
                setattr(self, k, v)
        if hasattr(self, "updated_at"):
            setattr(self, "updated_at", datetime.utcnow())
        await execute_update(self)
        return self

# -------------------------------------------------------------
# SQL Building Helpers
# -------------------------------------------------------------

def build_where_clause(criteria, param_offset=1):
    clauses = []
    params = []

    def process_item(item):
        nonlocal param_offset
        if isinstance(item, BinaryExpr):
            clauses.append(f"{item.field} {item.op} ${param_offset}")
            params.append(item.value)
            param_offset += 1
        elif isinstance(item, dict):
            for k, v in item.items():
                if k == "_id" or k == "id":
                    k = "id"
                if k == "$or" and isinstance(v, list):
                    or_clauses = []
                    for sub in v:
                        for sub_k, sub_v in sub.items():
                            if sub_k in ("_id", "id"):
                                sub_k = "id"
                            if isinstance(sub_v, dict) and "$regex" in sub_v:
                                or_clauses.append(f"{sub_k} ILIKE ${param_offset}")
                                params.append(f"%{sub_v['$regex']}%")
                                param_offset += 1
                            else:
                                or_clauses.append(f"{sub_k} = ${param_offset}")
                                params.append(sub_v)
                                param_offset += 1
                    if or_clauses:
                        clauses.append(f"({' OR '.join(or_clauses)})")
                elif isinstance(v, dict):
                    for op, val in v.items():
                        sql_op = {"$gte": ">=", "$lte": "<=", "$gt": ">", "$lt": "<", "$ne": "!="}.get(op, "=")
                        if op == "$regex":
                            clauses.append(f"{k} ILIKE ${param_offset}")
                            params.append(f"%{val}%")
                            param_offset += 1
                        elif op == "$in" and isinstance(val, (list, tuple)):
                            if not val:
                                clauses.append("1=0")
                            else:
                                placeholders = [f"${param_offset + i}" for i in range(len(val))]
                                clauses.append(f"{k} IN ({', '.join(placeholders)})")
                                params.extend(val)
                                param_offset += len(val)
                        else:
                            clauses.append(f"{k} {sql_op} ${param_offset}")
                            params.append(val)
                            param_offset += 1
                else:
                    clauses.append(f"{k} = ${param_offset}")
                    params.append(v)
                    param_offset += 1

    for c in criteria:
        process_item(c)

    where_sql = " AND ".join(clauses) if clauses else "1=1"
    return where_sql, params, param_offset

# -------------------------------------------------------------
# Database Execution
# -------------------------------------------------------------

async def execute_get(model_cls, record_id: str):
    global _pg_pool, _use_fallback_mock
    table = model_cls.get_table_name()
    if _use_fallback_mock or _pg_pool is None:
        data = _mock_store.get(table, {}).get(record_id)
        return model_cls(**data) if data else None

    async with _pg_pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {table} WHERE id = $1", record_id)
        if not row:
            return None
        return _row_to_model(model_cls, dict(row))

async def execute_find(model_cls, criteria: list, sort=None, skip: int = 0, limit: Optional[int] = None):
    global _pg_pool, _use_fallback_mock
    table = model_cls.get_table_name()

    if _use_fallback_mock or _pg_pool is None:
        all_records = list(_mock_store.get(table, {}).values())
        filtered = [r for r in all_records if _mock_matches(r, criteria)]
        if sort:
            for field_name, direction in reversed(sort):
                reverse = (direction == "DESC")
                def _get_sort_val(record):
                    val = record.get(field_name)
                    if val is None:
                        return (1, 0, "")
                    if isinstance(val, datetime):
                        return (0, 1, val.isoformat())
                    if isinstance(val, (int, float)):
                        return (0, 0, float(val))
                    return (0, 1, str(val))
                filtered.sort(key=_get_sort_val, reverse=reverse)
        if skip:
            filtered = filtered[skip:]
        if limit is not None:
            filtered = filtered[:limit]
        return [model_cls(**r) for r in filtered]

    where_sql, params, next_idx = build_where_clause(criteria, param_offset=1)
    sql = f"SELECT * FROM {table} WHERE {where_sql}"

    if sort:
        sort_clauses = [f"{field} {direction}" for field, direction in sort]
        sql += f" ORDER BY {', '.join(sort_clauses)}"

    if limit is not None:
        sql += f" LIMIT ${next_idx}"
        params.append(limit)
        next_idx += 1

    if skip > 0:
        sql += f" OFFSET ${next_idx}"
        params.append(skip)
        next_idx += 1

    async with _pg_pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        return [_row_to_model(model_cls, dict(r)) for r in rows]

async def execute_count(model_cls, criteria: list) -> int:
    global _pg_pool, _use_fallback_mock
    table = model_cls.get_table_name()

    if _use_fallback_mock or _pg_pool is None:
        all_records = list(_mock_store.get(table, {}).values())
        filtered = [r for r in all_records if _mock_matches(r, criteria)]
        return len(filtered)

    where_sql, params, _ = build_where_clause(criteria, param_offset=1)
    sql = f"SELECT COUNT(*) FROM {table} WHERE {where_sql}"

    async with _pg_pool.acquire() as conn:
        val = await conn.fetchval(sql, *params)
        return val or 0

async def execute_insert(instance):
    global _pg_pool, _use_fallback_mock
    model_cls = instance.__class__
    table = model_cls.get_table_name()
    data = instance.model_dump()
    json_fields = model_cls.get_json_fields()

    if _use_fallback_mock or _pg_pool is None:
        clean_data = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in data.items()}
        _mock_store.setdefault(table, {})[str(instance.id)] = clean_data
        _save_fallback_db()
        return

    columns = []
    placeholders = []
    values = []
    idx = 1
    for k, v in data.items():
        columns.append(k)
        placeholders.append(f"${idx}")
        if k in json_fields:
            values.append(json.dumps(v))
        else:
            values.append(v)
        idx += 1

    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    async with _pg_pool.acquire() as conn:
        await conn.execute(sql, *values)

async def execute_update(instance):
    global _pg_pool, _use_fallback_mock
    model_cls = instance.__class__
    table = model_cls.get_table_name()
    data = instance.model_dump()
    json_fields = model_cls.get_json_fields()

    if _use_fallback_mock or _pg_pool is None:
        clean_data = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in data.items()}
        _mock_store.setdefault(table, {})[str(instance.id)] = clean_data
        _save_fallback_db()
        return

    clauses = []
    values = []
    idx = 1
    for k, v in data.items():
        if k == "id":
            continue
        clauses.append(f"{k} = ${idx}")
        if k in json_fields:
            values.append(json.dumps(v))
        else:
            values.append(v)
        idx += 1

    values.append(str(instance.id))
    sql = f"UPDATE {table} SET {', '.join(clauses)} WHERE id = ${idx}"

    async with _pg_pool.acquire() as conn:
        await conn.execute(sql, *values)

async def execute_delete(model_cls, record_id: str):
    global _pg_pool, _use_fallback_mock
    table = model_cls.get_table_name()

    if _use_fallback_mock or _pg_pool is None:
        _mock_store.get(table, {}).pop(str(record_id), None)
        _save_fallback_db()
        return

    async with _pg_pool.acquire() as conn:
        await conn.execute(f"DELETE FROM {table} WHERE id = $1", str(record_id))

def _row_to_model(model_cls, row_dict: dict):
    json_fields = model_cls.get_json_fields()
    for k in json_fields:
        if k in row_dict and isinstance(row_dict[k], str):
            try:
                row_dict[k] = json.loads(row_dict[k])
            except Exception:
                pass
    return model_cls(**row_dict)

def _mock_matches(record: dict, criteria: list) -> bool:
    def _normalize_cmp(a, b):
        if isinstance(a, datetime) and isinstance(b, str):
            return a.isoformat(), b
        if isinstance(a, str) and isinstance(b, datetime):
            return a, b.isoformat()
        return a, b

    for item in criteria:
        if isinstance(item, BinaryExpr):
            val = record.get(item.field)
            val, cmp_val = _normalize_cmp(val, item.value)
            if item.op == "=" and val != cmp_val: return False
            if item.op == "!=" and val == cmp_val: return False
            if item.op == ">" and (val is None or val <= cmp_val): return False
            if item.op == ">=" and (val is None or val < cmp_val): return False
            if item.op == "<" and (val is None or val >= cmp_val): return False
            if item.op == "<=" and (val is None or val > cmp_val): return False
        elif isinstance(item, dict):
            for k, v in item.items():
                if k in ("_id", "id"):
                    k = "id"
                if k == "$or" and isinstance(v, list):
                    sub_match = False
                    for sub in v:
                        if _mock_matches(record, [sub]):
                            sub_match = True
                            break
                    if not sub_match:
                        return False
                elif isinstance(v, dict):
                    rec_val = record.get(k)
                    for op, op_val in v.items():
                        c_val, c_op_val = _normalize_cmp(rec_val, op_val)
                        if op == "$gte" and (c_val is None or c_val < c_op_val): return False
                        if op == "$lte" and (c_val is None or c_val > c_op_val): return False
                        if op == "$gt" and (c_val is None or c_val <= c_op_val): return False
                        if op == "$lt" and (c_val is None or c_val >= c_op_val): return False
                        if op == "$regex" and (rec_val is None or str(op_val).lower() not in str(rec_val).lower()): return False
                        if op == "$in" and rec_val not in op_val: return False
                else:
                    if record.get(k) != v:
                        return False
    return True

# -------------------------------------------------------------
# Table Schemas
# -------------------------------------------------------------

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS admins (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    parent_id VARCHAR(64),
    description TEXT,
    image TEXT,
    icon VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    short_description TEXT,
    category VARCHAR(255) NOT NULL,
    subcategory VARCHAR(255),
    brand VARCHAR(255),
    mrp DOUBLE PRECISION NOT NULL DEFAULT 0,
    sale_price DOUBLE PRECISION NOT NULL DEFAULT 0,
    discount_percent DOUBLE PRECISION DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    sku VARCHAR(100) UNIQUE NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    color VARCHAR(100),
    size VARCHAR(100),
    weight VARCHAR(100),
    dimensions VARCHAR(100),
    featured BOOLEAN DEFAULT FALSE,
    trending BOOLEAN DEFAULT FALSE,
    best_seller BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'active',
    thumbnail TEXT,
    gallery_images JSONB DEFAULT '[]'::jsonb,
    variants JSONB DEFAULT '[]'::jsonb,
    seo JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    items JSONB DEFAULT '[]'::jsonb,
    subtotal DOUBLE PRECISION NOT NULL DEFAULT 0,
    shipping DOUBLE PRECISION NOT NULL DEFAULT 0,
    gst DOUBLE PRECISION NOT NULL DEFAULT 0,
    discount DOUBLE PRECISION NOT NULL DEFAULT 0,
    total DOUBLE PRECISION NOT NULL DEFAULT 0,
    payment_status VARCHAR(50) DEFAULT 'pending',
    shipping_status VARCHAR(50) DEFAULT 'pending',
    shipping_address JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS carts (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    items JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wishlists (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    product_ids JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS banners (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    subtitle TEXT,
    button_text VARCHAR(100),
    button_link TEXT,
    image TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_settings (
    id VARCHAR(64) PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    hide_price_and_cart BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

# -------------------------------------------------------------
# Database Initialization & Auto-Creation
# -------------------------------------------------------------

async def ensure_pg_database(host, port, user, password, dbname):
    """Checks if dbname exists on postgres, and creates it if missing."""
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres",
            timeout=5
        )
        try:
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
            if not exists:
                logger.info(f"Database '{dbname}' does not exist on PostgreSQL. Creating database...")
                await conn.execute(f'CREATE DATABASE "{dbname}"')
                logger.info(f"Database '{dbname}' created successfully.")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Could not verify/create database '{dbname}' on PostgreSQL: {e}")

async def init_pg(host: str, port: int, user: str, password: str, dbname: str):
    global _pg_pool, _use_fallback_mock
    try:
        # 1. Ensure database exists
        await ensure_pg_database(host, port, user, password, dbname)

        # 2. Setup connection pool with JSON codecs
        async def init_connection(conn):
            await conn.set_type_codec(
                'jsonb',
                encoder=json.dumps,
                decoder=json.loads,
                schema='pg_catalog'
            )

        _pg_pool = await asyncpg.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            init=init_connection,
            min_size=2,
            max_size=10,
            command_timeout=30
        )

        # 3. Create Tables and Indexes
        async with _pg_pool.acquire() as conn:
            await conn.execute(CREATE_TABLES_SQL)

        _use_fallback_mock = False
        logger.info(f"Successfully connected to PostgreSQL database '{dbname}' at {host}:{port} and verified tables.")
        return True

    except Exception as e:
        _use_fallback_mock = True
        _load_fallback_db()
        logger.error(
            f"\n"
            f"************************************************************************\n"
            f"[POSTGRESQL CONNECTION FAILED]\n"
            f"Could not connect to PostgreSQL database '{dbname}' on {host}:{port} with user '{user}'.\n"
            f"Error: {e}\n"
            f"Please update DB_PASSWORD in backend/.env with your valid PostgreSQL password.\n"
            f"Falling back to Local Persistent JSON Store so server remains operational and data is saved.\n"
            f"************************************************************************\n"
        )
        return False
