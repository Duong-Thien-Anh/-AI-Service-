from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from config import settings

_pool: ThreadedConnectionPool | None = None

def _now() -> datetime:
    return datetime.now(timezone.utc)

def create_db_if_not_exists():
    """Kết nối vào postgres mặc định để tạo database nếu chưa tồn tại"""
    try:
        result = urlparse(settings.database_url)
        username = result.username
        password = result.password
        host = result.hostname
        port = result.port or 5432
        target_db = result.path.lstrip('/')

        temp_conn = psycopg2.connect(
            dbname='postgres',
            user=username,
            password=password,
            host=host,
            port=port,
            connect_timeout=5
        )
        temp_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with temp_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (target_db,))
            exists = cur.fetchone()
            if not exists:
                print(f"--- [Hệ thống] Database '{target_db}' không tồn tại. Đang khởi tạo... ---")
                cur.execute(f'CREATE DATABASE "{target_db}"')
            else:
                print(f"--- [Hệ thống] Kết nối Database '{target_db}' sẵn sàng ---")
        temp_conn.close()
    except Exception as e:
        print(f"--- [Lưu ý] Kiểm tra Database: {e} ---")

def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        create_db_if_not_exists()
        _pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.database_url,
        )
    return _pool

def _with_conn(fn):
    """Decorator để quản lý connection từ pool tự động"""
    def _wrapped(*args, **kwargs):
        pool = _get_pool()
        conn = pool.getconn()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                result = fn(cur, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            print(f"Database Error: {e}")
            raise
        finally:
            pool.putconn(conn)
    return _wrapped

# ==========================================================
# CÁC HÀM KHỞI TẠO (INITIALIZATION)
# ==========================================================

def init_db(cur) -> None:
    """Hàm này chỉ thực thi SQL, yêu cầu phải có cur truyền vào"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
          id BIGSERIAL PRIMARY KEY,
          user_id TEXT NOT NULL,
          user_name TEXT,
          ticket_id TEXT NOT NULL UNIQUE,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL,
          closed_at TIMESTAMPTZ
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_closed ON conversations(user_id, closed_at);")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
          id BIGSERIAL PRIMARY KEY,
          conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
          role TEXT NOT NULL,
          text TEXT NOT NULL,
          timestamp TIMESTAMPTZ NOT NULL
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conversation_id, id);")

@_with_conn
def startup_db(cur) -> None:
    """Hàm này có Decorator để dùng riêng cho main.py lúc khởi động"""
    init_db(cur)

# ==========================================================
# CÁC HÀM NGHIỆP VỤ (BUSINESS LOGIC)
# ==========================================================

def _create_conversation(cur, user_id: str, user_name: str | None) -> dict:
    now = _now()
    cur.execute("""
        INSERT INTO conversations (user_id, user_name, ticket_id, created_at, updated_at, closed_at)
        VALUES (%s, %s, %s, %s, %s, NULL)
        RETURNING id
    """, (user_id, user_name, "TKT-PENDING", now, now))
    
    result = cur.fetchone()
    conversation_id = int(result["id"])
    ticket_id = f"TKT-{conversation_id + 1000}"
    
    cur.execute("UPDATE conversations SET ticket_id = %s WHERE id = %s", (ticket_id, conversation_id))
    return {"conversation_id": conversation_id, "ticket_id": ticket_id}

@_with_conn
def get_or_create_open_conversation_with_context(
    cur, user_id: str, user_name: str | None, context_limit: int
) -> dict:
    # Gọi trực tiếp init_db vì đã có cur từ Decorator của hàm này
    init_db(cur)
    
    cur.execute("""
        SELECT id, ticket_id FROM conversations
        WHERE user_id = %s AND closed_at IS NULL
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    
    row = cur.fetchone()
    if row is None:
        convo = _create_conversation(cur, user_id, user_name)
        conversation_id, ticket_id = convo["conversation_id"], convo["ticket_id"]
    else:
        conversation_id, ticket_id = int(row["id"]), str(row["ticket_id"])
        cur.execute("""
            UPDATE conversations 
            SET updated_at = %s, user_name = COALESCE(%s, user_name) 
            WHERE id = %s
        """, (_now(), user_name, conversation_id))

    cur.execute("SELECT COUNT(*)::int AS c FROM messages WHERE conversation_id = %s", (conversation_id,))
    message_count = int(cur.fetchone()["c"])

    if context_limit <= 0:
        return {
            "conversation_id": conversation_id, 
            "ticket_id": ticket_id, 
            "context_messages": [], 
            "message_count": message_count
        }

    cur.execute("""
        SELECT role, text, timestamp FROM messages 
        WHERE conversation_id = %s 
        ORDER BY id DESC LIMIT %s
    """, (conversation_id, context_limit))
    
    rows = cur.fetchall()
    rows.reverse()
    
    context_messages = [
        {
            "role": r["role"], 
            "text": r["text"], 
            "timestamp": r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else str(r["timestamp"])
        } for r in rows
    ]

    return {
        "conversation_id": conversation_id,
        "ticket_id": ticket_id,
        "context_messages": context_messages,
        "message_count": message_count,
    }

@_with_conn
def add_message(cur, conversation_id: int, role: str, text: str, timestamp: str | None = None) -> None:
    ts = datetime.fromisoformat(timestamp) if timestamp else _now()
    cur.execute("""
        INSERT INTO messages (conversation_id, role, text, timestamp) 
        VALUES (%s, %s, %s, %s)
    """, (conversation_id, role, text, ts))
    
    cur.execute("UPDATE conversations SET updated_at = %s WHERE id = %s", (_now(), conversation_id))

@_with_conn
def get_latest_conversation_history(cur, user_id: str) -> dict | None:
    cur.execute("""
        SELECT id, ticket_id FROM conversations 
        WHERE user_id = %s 
        ORDER BY (closed_at IS NULL) DESC, id DESC LIMIT 1
    """, (user_id,))
    
    row = cur.fetchone()
    if row is None: return None
    
    conversation_id, ticket_id = int(row["id"]), str(row["ticket_id"])
    
    cur.execute("""
        SELECT role, text, timestamp FROM messages 
        WHERE conversation_id = %s ORDER BY id ASC
    """, (conversation_id,))
    
    messages = [
        {
            "role": r["role"], 
            "text": r["text"], 
            "timestamp": r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else str(r["timestamp"])
        } for r in cur.fetchall()
    ]
    return {"conversation_id": conversation_id, "ticket_id": ticket_id, "messages": messages}

@_with_conn
def close_open_conversation(cur, user_id: str) -> None:
    cur.execute("""
        SELECT id FROM conversations 
        WHERE user_id = %s AND closed_at IS NULL 
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    
    row = cur.fetchone()
    if row:
        now = _now()
        cur.execute("""
            UPDATE conversations 
            SET closed_at = %s, updated_at = %s 
            WHERE id = %s
        """, (now, now, int(row["id"])))