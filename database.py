import sqlite3
import threading
from config import DB_PATH, LOCK_TYPES, MAX_WARNS_DEFAULT

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS group_settings (
        chat_id INTEGER PRIMARY KEY,
        welcome_msg TEXT DEFAULT '',
        rules_msg TEXT DEFAULT '',
        auto_delete_bot INTEGER DEFAULT 0,
        welcome_enabled INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS locks (
        chat_id INTEGER NOT NULL,
        lock_type TEXT NOT NULL,
        enabled INTEGER DEFAULT 0,
        warn_count INTEGER DEFAULT 1,
        PRIMARY KEY (chat_id, lock_type)
    );

    CREATE TABLE IF NOT EXISTS warns (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS admin_ranks (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rank TEXT NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS mute_list (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS ban_list (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS whitelist (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS blacklist (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS kill_list (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS bad_words (
        chat_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        PRIMARY KEY (chat_id, word)
    );

    CREATE TABLE IF NOT EXISTS filter_words (
        chat_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        PRIMARY KEY (chat_id, word)
    );
    """)
    conn.commit()


def ensure_group(chat_id: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,)
    )
    for lt in LOCK_TYPES:
        conn.execute(
            "INSERT OR IGNORE INTO locks (chat_id, lock_type, enabled, warn_count) VALUES (?, ?, 0, 1)",
            (chat_id, lt),
        )
    conn.commit()


def get_group_settings(chat_id: int) -> dict:
    ensure_group(chat_id)
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM group_settings WHERE chat_id=?", (chat_id,)
    ).fetchone()
    return dict(row) if row else {}


def set_group_setting(chat_id: int, key: str, value):
    ensure_group(chat_id)
    conn = get_conn()
    conn.execute(f"UPDATE group_settings SET {key}=? WHERE chat_id=?", (value, chat_id))
    conn.commit()


def get_locks(chat_id: int) -> dict:
    ensure_group(chat_id)
    conn = get_conn()
    rows = conn.execute(
        "SELECT lock_type, enabled, warn_count FROM locks WHERE chat_id=?", (chat_id,)
    ).fetchall()
    return {r["lock_type"]: {"enabled": bool(r["enabled"]), "warn_count": r["warn_count"]} for r in rows}


def set_lock(chat_id: int, lock_type: str, enabled: bool):
    ensure_group(chat_id)
    conn = get_conn()
    conn.execute(
        "INSERT INTO locks (chat_id, lock_type, enabled, warn_count) VALUES (?, ?, ?, 1) "
        "ON CONFLICT(chat_id, lock_type) DO UPDATE SET enabled=excluded.enabled",
        (chat_id, lock_type, int(enabled)),
    )
    conn.commit()


def set_lock_warn_count(chat_id: int, lock_type: str, count: int):
    ensure_group(chat_id)
    conn = get_conn()
    conn.execute(
        "INSERT INTO locks (chat_id, lock_type, enabled, warn_count) VALUES (?, ?, 0, ?) "
        "ON CONFLICT(chat_id, lock_type) DO UPDATE SET warn_count=excluded.warn_count",
        (chat_id, lock_type, count),
    )
    conn.commit()


def get_warns(chat_id: int, user_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT count FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id)
    ).fetchone()
    return row["count"] if row else 0


def add_warn(chat_id: int, user_id: int, amount: int = 1) -> int:
    conn = get_conn()
    conn.execute(
        "INSERT INTO warns (chat_id, user_id, count) VALUES (?, ?, ?) "
        "ON CONFLICT(chat_id, user_id) DO UPDATE SET count=count+?",
        (chat_id, user_id, amount, amount),
    )
    conn.commit()
    return get_warns(chat_id, user_id)


def reset_warns(chat_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()


def get_rank(chat_id: int, user_id: int) -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT rank FROM admin_ranks WHERE chat_id=? AND user_id=?", (chat_id, user_id)
    ).fetchone()
    return row["rank"] if row else None


def set_rank(chat_id: int, user_id: int, rank: str | None):
    conn = get_conn()
    if rank is None:
        conn.execute(
            "DELETE FROM admin_ranks WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        )
    else:
        conn.execute(
            "INSERT INTO admin_ranks (chat_id, user_id, rank) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET rank=excluded.rank",
            (chat_id, user_id, rank),
        )
    conn.commit()


def get_all_ranks(chat_id: int) -> list:
    conn = get_conn()
    return [dict(r) for r in conn.execute(
        "SELECT user_id, rank FROM admin_ranks WHERE chat_id=?", (chat_id,)
    ).fetchall()]


def _list_add(table: str, chat_id: int, user_id: int):
    conn = get_conn()
    conn.execute(
        f"INSERT OR IGNORE INTO {table} (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id)
    )
    conn.commit()


def _list_remove(table: str, chat_id: int, user_id: int):
    conn = get_conn()
    conn.execute(
        f"DELETE FROM {table} WHERE chat_id=? AND user_id=?", (chat_id, user_id)
    )
    conn.commit()


def _list_check(table: str, chat_id: int, user_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE chat_id=? AND user_id=?", (chat_id, user_id)
    ).fetchone()
    return row is not None


def _list_all(table: str, chat_id: int) -> list[int]:
    conn = get_conn()
    rows = conn.execute(
        f"SELECT user_id FROM {table} WHERE chat_id=?", (chat_id,)
    ).fetchall()
    return [r["user_id"] for r in rows]


def add_to_mute_list(chat_id, user_id): _list_add("mute_list", chat_id, user_id)
def remove_from_mute_list(chat_id, user_id): _list_remove("mute_list", chat_id, user_id)
def is_in_mute_list(chat_id, user_id): return _list_check("mute_list", chat_id, user_id)
def get_mute_list(chat_id): return _list_all("mute_list", chat_id)

def add_to_ban_list(chat_id, user_id): _list_add("ban_list", chat_id, user_id)
def remove_from_ban_list(chat_id, user_id): _list_remove("ban_list", chat_id, user_id)
def is_in_ban_list(chat_id, user_id): return _list_check("ban_list", chat_id, user_id)
def get_ban_list(chat_id): return _list_all("ban_list", chat_id)

def add_to_whitelist(chat_id, user_id): _list_add("whitelist", chat_id, user_id)
def remove_from_whitelist(chat_id, user_id): _list_remove("whitelist", chat_id, user_id)
def is_in_whitelist(chat_id, user_id): return _list_check("whitelist", chat_id, user_id)
def get_whitelist(chat_id): return _list_all("whitelist", chat_id)

def add_to_blacklist(chat_id, user_id): _list_add("blacklist", chat_id, user_id)
def remove_from_blacklist(chat_id, user_id): _list_remove("blacklist", chat_id, user_id)
def is_in_blacklist(chat_id, user_id): return _list_check("blacklist", chat_id, user_id)
def get_blacklist(chat_id): return _list_all("blacklist", chat_id)

def add_to_kill_list(chat_id, user_id): _list_add("kill_list", chat_id, user_id)
def remove_from_kill_list(chat_id, user_id): _list_remove("kill_list", chat_id, user_id)
def is_in_kill_list(chat_id, user_id): return _list_check("kill_list", chat_id, user_id)
def get_kill_list(chat_id): return _list_all("kill_list", chat_id)


def add_bad_word(chat_id: int, word: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO bad_words (chat_id, word) VALUES (?, ?)", (chat_id, word.lower())
    )
    conn.commit()


def remove_bad_word(chat_id: int, word: str):
    conn = get_conn()
    conn.execute(
        "DELETE FROM bad_words WHERE chat_id=? AND word=?", (chat_id, word.lower())
    )
    conn.commit()


def get_bad_words(chat_id: int) -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT word FROM bad_words WHERE chat_id=?", (chat_id,)
    ).fetchall()
    return [r["word"] for r in rows]


def add_filter_word(chat_id: int, word: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO filter_words (chat_id, word) VALUES (?, ?)", (chat_id, word.lower())
    )
    conn.commit()


def remove_filter_word(chat_id: int, word: str):
    conn = get_conn()
    conn.execute(
        "DELETE FROM filter_words WHERE chat_id=? AND word=?", (chat_id, word.lower())
    )
    conn.commit()


def get_filter_words(chat_id: int) -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT word FROM filter_words WHERE chat_id=?", (chat_id,)
    ).fetchall()
    return [r["word"] for r in rows]
