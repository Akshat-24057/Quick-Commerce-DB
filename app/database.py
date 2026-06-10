"""
=============================================================================
Quick Commerce Demand & Supply Database System
Embedded SQL Module (Python + MySQL)
=============================================================================

Configuration (recommended):
- Streamlit secrets: .streamlit/secrets.toml
  [mysql]
  host = "localhost"
  port = 3306
  user = "root"
  password = "YOUR_PASSWORD_HERE"
  database = "quick_commerce_new"

Or environment variables:
- MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
=============================================================================
"""

from __future__ import annotations

import os
import hashlib
import threading
import time
from datetime import datetime, date, timedelta

import mysql.connector
from mysql.connector import Error


# ─────────────────────────────────────────────────────────────────────────────
# Connection wrapper to keep sqlite-like calling pattern used in app.py
# ─────────────────────────────────────────────────────────────────────────────
class CursorWrapper:
    """A tiny wrapper so we can do cursor.execute(...).fetchone() like sqlite."""

    def __init__(self, cursor):
        self._c = cursor

    def execute(self, sql: str, params=None):
        self._c.execute(sql, params or ())
        return self

    def executemany(self, sql: str, seq_params):
        self._c.executemany(sql, seq_params)
        return self

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    @property
    def lastrowid(self):
        return self._c.lastrowid

    def close(self):
        try:
            self._c.close()
        except Exception:
            pass


class DB:
    def __init__(self, raw_conn: mysql.connector.MySQLConnection):
        self._conn = raw_conn

    def ping(self):
        # FIX: Use attempts=1, delay=0 — no blocking retries for local dev
        self._conn.ping(reconnect=True, attempts=1, delay=0)

    def cursor(self) -> CursorWrapper:
        self.ping()
        return CursorWrapper(self._conn.cursor(dictionary=True))

    def execute(self, sql: str, params=None) -> CursorWrapper:
        self.ping()
        cur = CursorWrapper(self._conn.cursor(dictionary=True))
        cur.execute(sql, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _get_mysql_config():
    """Read MySQL config from env (and optionally Streamlit secrets)."""

    cfg = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        # FIX: Default MySQL port is 3306, NOT 8501 (8501 is Streamlit's port!)
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "quick_commerce_new"),
        "charset": "utf8mb4",
        "autocommit": False,
        # FIX: Fail fast (10s) instead of hanging indefinitely
        "connect_timeout": 10,
    }

    # If running under Streamlit, allow st.secrets override
    try:
        import streamlit as st  # type: ignore

        if "mysql" in st.secrets:
            s = st.secrets["mysql"]
            cfg.update(
                {
                    "host": s.get("host", cfg["host"]),
                    "port": int(s.get("port", cfg["port"])),
                    "user": s.get("user", cfg["user"]),
                    "password": s.get("password", cfg["password"]),
                    "database": s.get("database", cfg["database"]),
                }
            )
    except Exception:
        pass

    return cfg


def get_connection() -> DB:
    """Return a MySQL connection wrapped as DB (sqlite-like API).

    If the target database does not exist yet, we create it automatically.
    """
    cfg = _get_mysql_config()
    try:
        raw = mysql.connector.connect(**cfg)
        return DB(raw)
    except Error as e:
        # 1049 = ER_BAD_DB_ERROR (Unknown database)
        if getattr(e, "errno", None) == 1049:
            bootstrap_cfg = dict(cfg)
            bootstrap_cfg.pop("database", None)
            raw2 = mysql.connector.connect(**bootstrap_cfg)
            cur = raw2.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` DEFAULT CHARACTER SET utf8mb4"
            )
            raw2.commit()
            cur.close()
            raw2.close()
            raw = mysql.connector.connect(**cfg)
            return DB(raw)
        raise


TRANSACTION_DEMO_SQL = {
    "committed_sale": """-- Demo 1: A committed transaction that deducts inventory and keeps the change.
START TRANSACTION;

SELECT available_qty INTO @before_qty
FROM Transaction_Demo_Inventory
WHERE item_code = 'MILK'
FOR UPDATE;

UPDATE Transaction_Demo_Inventory
SET available_qty = available_qty - 4
WHERE item_code = 'MILK';

INSERT INTO Transaction_Demo_Log(
    scenario_name,
    step_label,
    item_code,
    quantity_before,
    quantity_after,
    status,
    remarks
)
SELECT
    'Committed transaction',
    'Milk sale committed',
    'MILK',
    @before_qty,
    available_qty,
    'COMMITTED',
    '4 milk packets were deducted and the transaction ended with COMMIT.'
FROM Transaction_Demo_Inventory
WHERE item_code = 'MILK';

COMMIT;""",
    "committed_restock": """-- Demo 2: A committed transaction that adds stock and keeps the new value.
START TRANSACTION;

SELECT available_qty INTO @before_qty
FROM Transaction_Demo_Inventory
WHERE item_code = 'JUICE'
FOR UPDATE;

UPDATE Transaction_Demo_Inventory
SET available_qty = available_qty + 6
WHERE item_code = 'JUICE';

INSERT INTO Transaction_Demo_Log(
    scenario_name,
    step_label,
    item_code,
    quantity_before,
    quantity_after,
    status,
    remarks
)
SELECT
    'Committed transaction',
    'Juice restock committed',
    'JUICE',
    @before_qty,
    available_qty,
    'COMMITTED',
    '6 juice bottles were added and the transaction ended with COMMIT.'
FROM Transaction_Demo_Inventory
WHERE item_code = 'JUICE';

COMMIT;""",
    "rollback_sale": """-- Demo 3: A transaction makes a change but rolls it back instead of committing.
START TRANSACTION;

SELECT available_qty INTO @before_qty
FROM Transaction_Demo_Inventory
WHERE item_code = 'MILK'
FOR UPDATE;

UPDATE Transaction_Demo_Inventory
SET available_qty = available_qty - 7
WHERE item_code = 'MILK';

ROLLBACK;

INSERT INTO Transaction_Demo_Log(
    scenario_name,
    step_label,
    item_code,
    quantity_before,
    quantity_after,
    status,
    remarks
)
SELECT
    'Rollback transaction',
    'Milk sale rolled back',
    'MILK',
    @before_qty,
    available_qty,
    'ROLLED BACK',
    'A temporary deduction was attempted, but ROLLBACK restored the original quantity.'
FROM Transaction_Demo_Inventory
WHERE item_code = 'MILK';""",
    "conflict_session_a": """-- Demo 4A: Session A locks the row, updates it, waits, and then commits.
START TRANSACTION;

SELECT available_qty INTO @before_qty
FROM Transaction_Demo_Inventory
WHERE item_code = 'BREAD'
FOR UPDATE;

UPDATE Transaction_Demo_Inventory
SET available_qty = available_qty - 5
WHERE item_code = 'BREAD';

INSERT INTO Transaction_Demo_Log(
    scenario_name,
    step_label,
    item_code,
    quantity_before,
    quantity_after,
    status,
    remarks
)
SELECT
    'Conflict demo',
    'Session A locked row',
    'BREAD',
    @before_qty,
    available_qty,
    'PENDING',
    'Session A updated the row and is holding the lock for 5 seconds.'
FROM Transaction_Demo_Inventory
WHERE item_code = 'BREAD';

DO SLEEP(5);
COMMIT;

INSERT INTO Transaction_Demo_Log(
    scenario_name,
    step_label,
    item_code,
    quantity_before,
    quantity_after,
    status,
    remarks
)
SELECT
    'Conflict demo',
    'Session A committed',
    'BREAD',
    @before_qty,
    available_qty,
    'COMMITTED',
    'Session A finished first, so its deduction stayed in the database.'
FROM Transaction_Demo_Inventory
WHERE item_code = 'BREAD';""",
    "conflict_session_b": """-- Demo 4B: Session B tries to touch the same row while Session A still holds the lock.
SET SESSION innodb_lock_wait_timeout = 2;
START TRANSACTION;

SELECT available_qty INTO @before_qty
FROM Transaction_Demo_Inventory
WHERE item_code = 'BREAD'
FOR UPDATE;

UPDATE Transaction_Demo_Inventory
SET available_qty = available_qty - 3
WHERE item_code = 'BREAD';

INSERT INTO Transaction_Demo_Log(
    scenario_name,
    step_label,
    item_code,
    quantity_before,
    quantity_after,
    status,
    remarks
)
SELECT
    'Conflict demo',
    'Session B committed',
    'BREAD',
    @before_qty,
    available_qty,
    'COMMITTED',
    'This row only appears if Session B obtains the lock before timeout.'
FROM Transaction_Demo_Inventory
WHERE item_code = 'BREAD';

COMMIT;""",
}

TRANSACTION_DEMO_CATALOG = {
    "committed_sale": {
        "title": "Committed transaction — stock deduction",
        "script_label": "Embedded SQL demo",
        "description": "This example starts a transaction, deducts 4 milk packets, writes an audit row, and finishes with COMMIT. Because the transaction commits, the changed quantity remains visible after execution.",
        "impact": "The available quantity for MILK permanently decreases and the audit table keeps a COMMITTED entry.",
    },
    "committed_restock": {
        "title": "Committed transaction — restock update",
        "script_label": "Embedded SQL demo",
        "description": "This example simulates a successful restock. The transaction adds 6 juice bottles and commits the change.",
        "impact": "The quantity for JUICE increases permanently and the audit table shows a COMMITTED restock event.",
    },
    "rollback_sale": {
        "title": "Rollback transaction — change is cancelled",
        "script_label": "Embedded SQL demo",
        "description": "This example deducts stock inside a transaction but then issues ROLLBACK instead of COMMIT. The temporary update is discarded before it can persist.",
        "impact": "The quantity returns to its original value, and the audit table records that the attempted change was rolled back.",
    },
    "conflict_session_a": {
        "title": "Conflict demo — Session A",
        "script_label": "Embedded Session A SQL",
        "description": "Session A locks the BREAD row, updates it, waits for a few seconds, and then commits.",
        "impact": "This session holds the row lock long enough to block a second writer.",
    },
    "conflict_session_b": {
        "title": "Conflict demo — Session B",
        "script_label": "Embedded Session B SQL",
        "description": "Session B tries to update the same row while Session A is still holding the lock.",
        "impact": "This session hits a lock wait timeout and gets rolled back.",
    },
    "conflict_pair": {
        "title": "Conflicting transactions — same row, two sessions",
        "script_labels": ["Embedded Session A SQL", "Embedded Session B SQL"],
        "description": "Two separate database sessions try to update the same BREAD row at nearly the same time. Session A locks and updates the row first. Session B then attempts the same operation and fails because the row is still locked.",
        "impact": "Only Session A's quantity change is committed. Session B is rolled back, so the second deduction never reaches the database.",
    },
}


def get_transaction_demo_catalog():
    return TRANSACTION_DEMO_CATALOG


def load_transaction_demo_sql(demo_key: str) -> str:
    if demo_key not in TRANSACTION_DEMO_SQL:
        raise ValueError(f"Demo '{demo_key}' does not have embedded SQL.")
    return TRANSACTION_DEMO_SQL[demo_key]


def create_transaction_demo_objects(conn: DB):
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Transaction_Demo_Inventory (
            item_id        INT PRIMARY KEY AUTO_INCREMENT,
            item_code      VARCHAR(32) NOT NULL UNIQUE,
            item_name      VARCHAR(100) NOT NULL,
            available_qty  INT NOT NULL,
            unit           VARCHAR(32) DEFAULT 'units',
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Transaction_Demo_Log (
            log_id           INT PRIMARY KEY AUTO_INCREMENT,
            scenario_name    VARCHAR(100) NOT NULL,
            step_label       VARCHAR(100) NOT NULL,
            item_code        VARCHAR(32),
            quantity_before  INT NULL,
            quantity_after   INT NULL,
            status           VARCHAR(32) NOT NULL,
            remarks          TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    conn.commit()


def ensure_transaction_demo_seed(conn: DB):
    create_transaction_demo_objects(conn)
    row = conn.execute("SELECT COUNT(*) AS cnt FROM Transaction_Demo_Inventory").fetchone()
    if (row or {}).get("cnt", 0) == 0:
        reset_transaction_demo(conn)


def reset_transaction_demo(conn: DB | None = None):
    owns_conn = conn is None
    demo_conn = conn or get_connection()
    try:
        create_transaction_demo_objects(demo_conn)
        c = demo_conn.cursor()
        c.execute("DELETE FROM Transaction_Demo_Log")
        c.execute("DELETE FROM Transaction_Demo_Inventory")
        c.executemany(
            """
            INSERT INTO Transaction_Demo_Inventory(item_code, item_name, available_qty, unit)
            VALUES (%s, %s, %s, %s)
            """,
            [
                ("MILK", "Milk Packets", 40, "packets"),
                ("BREAD", "Bread Loaves", 25, "loaves"),
                ("JUICE", "Juice Bottles", 18, "bottles"),
            ],
        )
        demo_conn.commit()
    finally:
        if owns_conn:
            demo_conn.close()


def _rows_to_dicts(rows):
    return [dict(r) for r in (rows or [])]


def get_transaction_demo_snapshot(conn: DB | None = None):
    owns_conn = conn is None
    demo_conn = conn or get_connection()
    try:
        ensure_transaction_demo_seed(demo_conn)
        inventory = _rows_to_dicts(
            demo_conn.execute(
                """
                SELECT item_code, item_name, available_qty, unit, updated_at
                FROM Transaction_Demo_Inventory
                ORDER BY item_id
                """
            ).fetchall()
        )
        logs = _rows_to_dicts(
            demo_conn.execute(
                """
                SELECT log_id, scenario_name, step_label, item_code, quantity_before,
                       quantity_after, status, remarks, created_at
                FROM Transaction_Demo_Log
                ORDER BY log_id DESC
                LIMIT 12
                """
            ).fetchall()
        )
        return {"inventory": inventory, "logs": logs}
    finally:
        if owns_conn:
            demo_conn.close()


def _split_sql_script(sql_text: str):
    statements = []
    current = []
    in_single = False
    in_double = False

    for raw_line in sql_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        line = raw_line
        idx = 0
        while idx < len(line):
            ch = line[idx]
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            if ch == ";" and not in_single and not in_double:
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(ch)
            idx += 1
        current.append("\n")

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _execute_sql_script(conn: DB, sql_text: str):
    executed = []
    for statement in _split_sql_script(sql_text):
        cur = conn.execute(statement)
        cur.close()
        executed.append(statement)
    return executed


def _write_demo_log(scenario_name: str, step_label: str, item_code: str, quantity_before, quantity_after, status: str, remarks: str):
    conn = get_connection()
    try:
        create_transaction_demo_objects(conn)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO Transaction_Demo_Log(
                scenario_name, step_label, item_code, quantity_before, quantity_after, status, remarks
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (scenario_name, step_label, item_code, quantity_before, quantity_after, status, remarks),
        )
        conn.commit()
    finally:
        conn.close()


def run_transaction_demo(demo_key: str):
    if demo_key not in {"committed_sale", "committed_restock", "rollback_sale"}:
        raise ValueError(f"Unsupported demo key: {demo_key}")

    demo_conn = get_connection()
    try:
        reset_transaction_demo(demo_conn)
        before = get_transaction_demo_snapshot(demo_conn)
        sql_text = load_transaction_demo_sql(demo_key)
        _execute_sql_script(demo_conn, sql_text)
        demo_conn.commit()
        after = get_transaction_demo_snapshot(demo_conn)
        return {
            "ok": True,
            "message": f"{TRANSACTION_DEMO_CATALOG[demo_key]['title']} finished successfully.",
            "before": before,
            "after": after,
            "sql": sql_text,
        }
    except Exception as exc:
        demo_conn.rollback()
        after = get_transaction_demo_snapshot(demo_conn)
        return {
            "ok": False,
            "message": f"Execution failed: {exc}",
            "before": before if 'before' in locals() else {"inventory": [], "logs": []},
            "after": after,
            "sql": sql_text if 'sql_text' in locals() else "",
        }
    finally:
        demo_conn.close()


def run_conflicting_transaction_demo():
    controller_conn = get_connection()
    try:
        reset_transaction_demo(controller_conn)
        before = get_transaction_demo_snapshot(controller_conn)
    finally:
        controller_conn.close()

    sql_a = load_transaction_demo_sql("conflict_session_a")
    sql_b = load_transaction_demo_sql("conflict_session_b")
    timeline = []
    timeline_lock = threading.Lock()
    outcome = {"session_a": None, "session_b": None}

    def add_timeline(session_name: str, message: str):
        with timeline_lock:
            timeline.append({"session": session_name, "message": message})

    def run_session_a():
        conn_a = get_connection()
        try:
            add_timeline("Session A", "Started and attempting to lock the BREAD row.")
            _execute_sql_script(conn_a, sql_a)
            conn_a.commit()
            outcome["session_a"] = "committed"
            add_timeline("Session A", "Committed its stock update after holding the lock.")
        except Exception as exc:
            conn_a.rollback()
            outcome["session_a"] = f"failed: {exc}"
            add_timeline("Session A", f"Failed with error: {exc}")
        finally:
            conn_a.close()

    def run_session_b():
        time.sleep(0.4)
        conn_b = get_connection()
        try:
            add_timeline("Session B", "Started shortly after Session A and tried to update the same row.")
            _execute_sql_script(conn_b, sql_b)
            conn_b.commit()
            outcome["session_b"] = "committed"
            add_timeline("Session B", "Unexpectedly committed. The row lock may not have blocked the second session.")
        except Exception as exc:
            conn_b.rollback()
            outcome["session_b"] = f"rolled back: {exc}"
            observer = get_connection()
            try:
                qty_row = observer.execute(
                    "SELECT available_qty FROM Transaction_Demo_Inventory WHERE item_code='BREAD'"
                ).fetchone()
                visible_qty = (qty_row or {}).get("available_qty")
            finally:
                observer.close()
            _write_demo_log(
                "Conflict demo",
                "Session B rollback",
                "BREAD",
                visible_qty,
                visible_qty,
                "ROLLED BACK",
                f"Session B could not acquire the row lock, so its transaction was rolled back: {exc}",
            )
            add_timeline("Session B", f"Rolled back because the row was locked: {exc}")
        finally:
            conn_b.close()

    thread_a = threading.Thread(target=run_session_a)
    thread_b = threading.Thread(target=run_session_b)
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    final_conn = get_connection()
    try:
        after = get_transaction_demo_snapshot(final_conn)
    finally:
        final_conn.close()

    session_b_expected = str(outcome.get("session_b", "")).startswith("rolled back")
    session_a_expected = outcome.get("session_a") == "committed"
    ok = session_a_expected and session_b_expected
    message = (
        "Conflict demo completed: Session A committed, while Session B was rolled back after hitting the row lock."
        if ok else
        f"Conflict demo completed with unexpected outcome. Session A: {outcome.get('session_a')}, Session B: {outcome.get('session_b')}"
    )

    return {
        "ok": ok,
        "message": message,
        "before": before,
        "after": after,
        "timeline": timeline,
        "sql": {"session_a": sql_a, "session_b": sql_b},
    }


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA CREATION  (Embedded DDL SQL)
# ─────────────────────────────────────────────────────────────────────────────

def create_schema(conn: DB):
    c = conn.cursor()

    # 1) Category
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Category (
            category_id   INT PRIMARY KEY AUTO_INCREMENT,
            name          VARCHAR(255) NOT NULL,
            parent_id     INT NULL,
            description   TEXT,
            is_active     TINYINT DEFAULT 1,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_category_parent
                FOREIGN KEY (parent_id) REFERENCES Category(category_id)
                ON DELETE SET NULL
                ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 2) Supplier
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Supplier (
            supplier_id    INT PRIMARY KEY AUTO_INCREMENT,
            name           VARCHAR(255) NOT NULL,
            phone          VARCHAR(32) NOT NULL UNIQUE,
            email          VARCHAR(255) NOT NULL UNIQUE,
            address        TEXT NOT NULL,
            contact_person VARCHAR(255),
            gstin          VARCHAR(64) UNIQUE,
            rating         DECIMAL(3,2) DEFAULT 0.00,
            is_active      TINYINT DEFAULT 1,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 3) Product
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Product (
            product_id         INT PRIMARY KEY AUTO_INCREMENT,
            name               VARCHAR(255) NOT NULL,
            description        TEXT,
            brand              VARCHAR(255),
            price              DECIMAL(10,2) NOT NULL,
            weight             DECIMAL(10,2) NOT NULL,
            category_id        INT NOT NULL,
            is_active          TINYINT DEFAULT 1,
            sku                VARCHAR(128) UNIQUE,
            barcode            VARCHAR(128) UNIQUE,
            min_order_quantity INT DEFAULT 1,
            max_order_quantity INT DEFAULT 100,
            tax_rate           DECIMAL(5,2) DEFAULT 0.00,
            image_url          TEXT,
            shelf_life_days    INT,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_product_category
                FOREIGN KEY (category_id) REFERENCES Category(category_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 4) Warehouse
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Warehouse (
            warehouse_id          INT PRIMARY KEY AUTO_INCREMENT,
            name                  VARCHAR(255) NOT NULL,
            location              VARCHAR(255) NOT NULL,
            address               TEXT NOT NULL,
            capacity              INT NOT NULL,
            latitude              DECIMAL(10,6),
            longitude             DECIMAL(10,6),
            serviceable_radius_km DECIMAL(6,2) DEFAULT 5.00,
            is_operational        TINYINT DEFAULT 1,
            operating_hours_start TIME DEFAULT '06:00:00',
            operating_hours_end   TIME DEFAULT '23:59:00',
            contact_phone         VARCHAR(32),
            manager_name          VARCHAR(255),
            created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 5) Batch_Inventory
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Batch_Inventory (
            batch_id          INT PRIMARY KEY AUTO_INCREMENT,
            product_id        INT NOT NULL,
            warehouse_id      INT NOT NULL,
            supplier_id       INT NOT NULL,
            batch_number      VARCHAR(128) UNIQUE,
            manufacture_date  DATE NOT NULL,
            expiry_date       DATE NOT NULL,
            initial_quantity  INT NOT NULL,
            current_quantity  INT NOT NULL,
            reserved_quantity INT DEFAULT 0,
            reorder_level     INT DEFAULT 10,
            shelf_location    VARCHAR(128),
            cost_price        DECIMAL(10,2),
            is_damaged        TINYINT DEFAULT 0,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_batch_product
                FOREIGN KEY (product_id) REFERENCES Product(product_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_batch_warehouse
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_batch_supplier
                FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            INDEX idx_batch_wh_prod (warehouse_id, product_id),
            INDEX idx_batch_expiry (expiry_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 6) Inventory (aggregated)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Inventory (
            inventory_id      INT PRIMARY KEY AUTO_INCREMENT,
            warehouse_id      INT NOT NULL,
            product_id        INT NOT NULL,
            total_quantity    INT NOT NULL DEFAULT 0,
            reserved_quantity INT NOT NULL DEFAULT 0,
            last_restocked_at DATETIME NULL,
            reorder_threshold INT DEFAULT 20,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_inventory (warehouse_id, product_id),
            CONSTRAINT fk_inventory_wh
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_inventory_product
                FOREIGN KEY (product_id) REFERENCES Product(product_id)
                ON DELETE RESTRICT ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 7) Customer
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Customer (
            customer_id            INT PRIMARY KEY AUTO_INCREMENT,
            name                   VARCHAR(255) NOT NULL,
            phone                  VARCHAR(32) NOT NULL UNIQUE,
            email                  VARCHAR(255) NOT NULL UNIQUE,
            address                TEXT NOT NULL,
            latitude               DECIMAL(10,6),
            longitude              DECIMAL(10,6),
            pincode                VARCHAR(16),
            is_active              TINYINT DEFAULT 1,
            preferred_warehouse_id INT NULL,
            total_orders           INT DEFAULT 0,
            total_spent            DECIMAL(12,2) DEFAULT 0.00,
            created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_customer_pref_wh
                FOREIGN KEY (preferred_warehouse_id) REFERENCES Warehouse(warehouse_id)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 8) Customer_Address
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Customer_Address (
            address_id    INT PRIMARY KEY AUTO_INCREMENT,
            customer_id   INT NOT NULL,
            address_type  VARCHAR(32) DEFAULT 'Home',
            address_line1 TEXT NOT NULL,
            address_line2 TEXT,
            landmark      VARCHAR(255),
            city          VARCHAR(128) NOT NULL,
            state         VARCHAR(128) NOT NULL,
            pincode       VARCHAR(16) NOT NULL,
            latitude      DECIMAL(10,6),
            longitude     DECIMAL(10,6),
            is_default    TINYINT DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_cust_addr_customer
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 9) Delivery_Partner
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Delivery_Partner (
            partner_id            INT PRIMARY KEY AUTO_INCREMENT,
            name                  VARCHAR(255) NOT NULL,
            phone                 VARCHAR(32) NOT NULL UNIQUE,
            email                 VARCHAR(255) UNIQUE,
            vehicle_type          VARCHAR(32) NOT NULL,
            vehicle_number        VARCHAR(64),
            license_number        VARCHAR(64),
            address               TEXT NOT NULL,
            assigned_warehouse_id INT NULL,
            availability_status   VARCHAR(32) DEFAULT 'Available',
            rating                DECIMAL(3,2) DEFAULT 0.00,
            total_deliveries      INT DEFAULT 0,
            successful_deliveries INT DEFAULT 0,
            is_active             TINYINT DEFAULT 1,
            created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_dp_wh
                FOREIGN KEY (assigned_warehouse_id) REFERENCES Warehouse(warehouse_id)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 10) Orders
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Orders (
            order_id             INT PRIMARY KEY AUTO_INCREMENT,
            order_number         VARCHAR(64) UNIQUE,
            customer_id          INT NOT NULL,
            warehouse_id         INT NOT NULL,
            delivery_partner_id  INT NULL,
            order_status         VARCHAR(32) NOT NULL DEFAULT 'Placed',
            payment_status       VARCHAR(32) DEFAULT 'Pending',
            placed_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            confirmed_at         DATETIME NULL,
            packed_at            DATETIME NULL,
            dispatched_at        DATETIME NULL,
            delivered_at         DATETIME NULL,
            cancelled_at         DATETIME NULL,
            expected_delivery_time DATETIME NULL,
            actual_delivery_time_minutes INT NULL,
            subtotal             DECIMAL(12,2) NOT NULL DEFAULT 0.00,
            tax_amount           DECIMAL(12,2) DEFAULT 0.00,
            delivery_fee         DECIMAL(12,2) DEFAULT 0.00,
            discount_amount      DECIMAL(12,2) DEFAULT 0.00,
            total_amount         DECIMAL(12,2) NOT NULL,
            cancellation_reason  TEXT,
            delivery_instructions TEXT,
            distance_km          DECIMAL(8,2),
            created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_orders_customer
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_orders_wh
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_orders_dp
                FOREIGN KEY (delivery_partner_id) REFERENCES Delivery_Partner(partner_id)
                ON DELETE SET NULL ON UPDATE CASCADE,
            INDEX idx_orders_customer (customer_id),
            INDEX idx_orders_status (order_status),
            INDEX idx_orders_placed_at (placed_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 11) Order_Item
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Order_Item (
            order_item_id    INT PRIMARY KEY AUTO_INCREMENT,
            order_id         INT NOT NULL,
            product_id       INT NOT NULL,
            batch_id         INT NOT NULL,
            quantity         INT NOT NULL,
            price_at_time    DECIMAL(12,2) NOT NULL,
            tax_at_time      DECIMAL(6,2) DEFAULT 0.00,
            discount_at_time DECIMAL(12,2) DEFAULT 0.00,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_oi_order
                FOREIGN KEY (order_id) REFERENCES Orders(order_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_oi_product
                FOREIGN KEY (product_id) REFERENCES Product(product_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_oi_batch
                FOREIGN KEY (batch_id) REFERENCES Batch_Inventory(batch_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            INDEX idx_oi_order (order_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 12) Payment
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Payment (
            payment_id      INT PRIMARY KEY AUTO_INCREMENT,
            order_id        INT NOT NULL UNIQUE,
            transaction_id  VARCHAR(128) UNIQUE,
            amount          DECIMAL(12,2) NOT NULL,
            payment_method  VARCHAR(64) NOT NULL,
            payment_status  VARCHAR(32) NOT NULL DEFAULT 'Pending',
            payment_gateway VARCHAR(128),
            paid_at         DATETIME NULL,
            refund_amount   DECIMAL(12,2) DEFAULT 0.00,
            refund_date     DATETIME NULL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_payment_order
                FOREIGN KEY (order_id) REFERENCES Orders(order_id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 13) Stock_Ledger
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Stock_Ledger (
            ledger_id         INT PRIMARY KEY AUTO_INCREMENT,
            batch_id          INT NOT NULL,
            transaction_type  VARCHAR(32) NOT NULL,
            quantity_change   INT NOT NULL,
            transaction_date  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reference_type    VARCHAR(32) NOT NULL,
            reference_id      INT NULL,
            performed_by      VARCHAR(255),
            notes             TEXT,
            previous_quantity INT,
            new_quantity      INT,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_ledger_batch
                FOREIGN KEY (batch_id) REFERENCES Batch_Inventory(batch_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            INDEX idx_ledger_date (transaction_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 14) Warehouse_Inventory_Alert
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Warehouse_Inventory_Alert (
            alert_id      INT PRIMARY KEY AUTO_INCREMENT,
            warehouse_id  INT NOT NULL,
            product_id    INT NULL,
            batch_id      INT NULL,
            alert_type    VARCHAR(32) NOT NULL,
            alert_message TEXT NOT NULL,
            severity      VARCHAR(16) DEFAULT 'Medium',
            is_resolved   TINYINT DEFAULT 0,
            resolved_at   DATETIME NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_alert_wh
                FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_alert_product
                FOREIGN KEY (product_id) REFERENCES Product(product_id)
                ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_alert_batch
                FOREIGN KEY (batch_id) REFERENCES Batch_Inventory(batch_id)
                ON DELETE SET NULL ON UPDATE CASCADE,
            INDEX idx_alert_resolved (is_resolved),
            INDEX idx_alert_severity (severity)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 15) Coupon
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Coupon (
            coupon_id            INT PRIMARY KEY AUTO_INCREMENT,
            coupon_code          VARCHAR(64) UNIQUE NOT NULL,
            description          TEXT,
            discount_type        VARCHAR(32) NOT NULL,
            discount_value       DECIMAL(10,2) NOT NULL,
            min_order_value      DECIMAL(12,2) DEFAULT 0.00,
            max_discount_amount  DECIMAL(12,2) NULL,
            valid_from           DATE NOT NULL,
            valid_until          DATE NOT NULL,
            usage_limit          INT NULL,
            usage_count          INT DEFAULT 0,
            per_user_limit       INT DEFAULT 1,
            is_active            TINYINT DEFAULT 1,
            created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 16) Product_Review
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Product_Review (
            review_id     INT PRIMARY KEY AUTO_INCREMENT,
            product_id    INT NOT NULL,
            customer_id   INT NOT NULL,
            order_id      INT NOT NULL,
            rating        INT NOT NULL,
            review_title  VARCHAR(255),
            review_text   TEXT,
            is_verified_purchase TINYINT DEFAULT 1,
            is_approved   TINYINT DEFAULT 0,
            helpful_count INT DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_review_product
                FOREIGN KEY (product_id) REFERENCES Product(product_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_review_customer
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            CONSTRAINT fk_review_order
                FOREIGN KEY (order_id) REFERENCES Orders(order_id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # 17) Delivery_Rating
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Delivery_Rating (
            rating_id           INT PRIMARY KEY AUTO_INCREMENT,
            order_id            INT NOT NULL UNIQUE,
            delivery_partner_id INT NOT NULL,
            rating              INT NOT NULL,
            feedback            TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_dr_order
                FOREIGN KEY (order_id) REFERENCES Orders(order_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_dr_partner
                FOREIGN KEY (delivery_partner_id) REFERENCES Delivery_Partner(partner_id)
                ON DELETE RESTRICT ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# TRIGGER CREATION
# ─────────────────────────────────────────────────────────────────────────────

def create_triggers(conn: DB):
    c = conn.cursor()

    # Trigger 1: deduct stock + insert ledger on Order_Item insert
    c.execute("DROP TRIGGER IF EXISTS trg_after_order_item_insert")
    c.execute(
        """
        CREATE TRIGGER trg_after_order_item_insert
        AFTER INSERT ON Order_Item
        FOR EACH ROW
        BEGIN
            DECLARE prev_qty INT;
            DECLARE wh_id INT;

            SELECT current_quantity, warehouse_id
            INTO prev_qty, wh_id
            FROM Batch_Inventory
            WHERE batch_id = NEW.batch_id
            LIMIT 1;

            UPDATE Batch_Inventory
            SET current_quantity = current_quantity - NEW.quantity
            WHERE batch_id = NEW.batch_id;

            UPDATE Inventory
            SET total_quantity = total_quantity - NEW.quantity
            WHERE product_id = NEW.product_id
              AND warehouse_id = wh_id;

            INSERT INTO Stock_Ledger (
                batch_id, transaction_type, quantity_change,
                transaction_date, reference_type, reference_id,
                performed_by, notes, previous_quantity, new_quantity
            ) VALUES (
                NEW.batch_id, 'Sale', -NEW.quantity,
                NOW(), 'Order', NEW.order_id,
                'TRIGGER:trg_after_order_item_insert',
                'Auto-deducted on order item insert',
                prev_qty, (prev_qty - NEW.quantity)
            );
        END
        """
    )

    # Trigger 2: low stock / out of stock alerts
    c.execute("DROP TRIGGER IF EXISTS trg_low_stock_alert")
    c.execute(
        """
        CREATE TRIGGER trg_low_stock_alert
        AFTER UPDATE ON Batch_Inventory
        FOR EACH ROW
        BEGIN
            IF NEW.current_quantity <> OLD.current_quantity THEN

                /* Case A: hits zero -> Critical */
                IF NEW.current_quantity = 0 AND OLD.current_quantity > 0 THEN
                    INSERT INTO Warehouse_Inventory_Alert (
                        warehouse_id, product_id, batch_id,
                        alert_type, alert_message, severity, is_resolved
                    )
                    SELECT
                        NEW.warehouse_id,
                        NEW.product_id,
                        NEW.batch_id,
                        'Out of Stock',
                        CONCAT('CRITICAL: Batch ', NEW.batch_id, ' is completely out of stock.'),
                        'Critical',
                        0
                    WHERE NOT EXISTS (
                        SELECT 1 FROM Warehouse_Inventory_Alert
                        WHERE batch_id = NEW.batch_id
                          AND alert_type = 'Out of Stock'
                          AND is_resolved = 0
                    );

                /* Case B: drops <= reorder_level (but > 0) -> High */
                ELSEIF NEW.current_quantity > 0
                    AND NEW.current_quantity <= NEW.reorder_level
                    AND OLD.current_quantity > OLD.reorder_level THEN

                    INSERT INTO Warehouse_Inventory_Alert (
                        warehouse_id, product_id, batch_id,
                        alert_type, alert_message, severity, is_resolved
                    )
                    SELECT
                        NEW.warehouse_id,
                        NEW.product_id,
                        NEW.batch_id,
                        'Low Stock',
                        CONCAT('LOW STOCK: Batch ', NEW.batch_id,
                               ' — Current: ', NEW.current_quantity,
                               ', Reorder Level: ', NEW.reorder_level),
                        'High',
                        0
                    WHERE NOT EXISTS (
                        SELECT 1 FROM Warehouse_Inventory_Alert
                        WHERE batch_id = NEW.batch_id
                          AND alert_type = 'Low Stock'
                          AND is_resolved = 0
                    );

                END IF;
            END IF;
        END
        """
    )

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────────────────────────────────

def seed_data(conn: DB):
    c = conn.cursor()

    c.execute("SELECT COUNT(*) AS cnt FROM Category")
    if (c.fetchone() or {}).get("cnt", 0) > 0:
        return

    # Categories
    c.executemany(
        "INSERT INTO Category(name, parent_id, description) VALUES (%s,%s,%s)",
        [
            ("Groceries", None, "Essential grocery items"),
            ("Electronics", None, "Electronic devices and accessories"),
            ("Personal Care", None, "Health and hygiene products"),
            ("Beverages", None, "Drinks and refreshments"),
            ("Snacks", None, "Quick bites and munchies"),
            ("Fruits & Vegetables", 1, "Fresh produce"),
            ("Dairy Products", 1, "Milk, cheese, yogurt and more"),
            ("Cooking Essentials", 1, "Spices, oils, and staples"),
            ("Mobile Accessories", 2, "Chargers, cases, and more"),
            ("Health & Hygiene", 3, "Sanitizers, soaps, and wellness"),
        ],
    )

    # Suppliers
    c.executemany(
        """INSERT INTO Supplier(name,phone,email,address,contact_person,gstin,rating)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        [
            (
                "Fresh Farms Pvt Ltd",
                "9876543210",
                "contact@freshfarms.com",
                "12, Agriculture Market, Delhi",
                "Ramesh Kumar",
                "07AABCU9603R1ZX",
                4.5,
            ),
            (
                "Dairy Best Co.",
                "9876543211",
                "sales@dairybest.com",
                "45, Milk Colony, Gurgaon",
                "Suresh Sharma",
                "06AABCU9603R1ZY",
                4.7,
            ),
            (
                "Tech Suppliers Inc.",
                "9876543212",
                "info@techsuppliers.com",
                "78, Electronics Hub, Noida",
                "Amit Verma",
                "09AABCU9603R1ZZ",
                4.3,
            ),
            (
                "Snack Masters",
                "9876543213",
                "orders@snackmasters.com",
                "23, Food Street, Delhi",
                "Priya Singh",
                "07AABCU9603R1ZA",
                4.6,
            ),
            (
                "Beverage Distributors",
                "9876543214",
                "contact@bevdist.com",
                "56, Drink Avenue, Faridabad",
                "Vikram Malhotra",
                "06AABCU9603R1ZB",
                4.4,
            ),
        ],
    )

    # Products
    c.executemany(
        """INSERT INTO Product(name,description,brand,price,weight,category_id,
                               sku,barcode,tax_rate,shelf_life_days)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            (
                "Organic Bananas",
                "Fresh organic bananas - 6 pieces",
                "FreshFarms",
                60.00,
                600,
                6,
                "FF-BAN-001",
                "8901234567890",
                0.00,
                7,
            ),
            (
                "Full Cream Milk 1L",
                "Fresh full cream milk",
                "Amul",
                65.00,
                1000,
                7,
                "AML-MLK-001",
                "8901234567891",
                0.00,
                5,
            ),
            (
                "Whole Wheat Bread",
                "Freshly baked whole wheat bread",
                "Britannia",
                45.00,
                400,
                1,
                "BRT-BRD-001",
                "8901234567892",
                5.00,
                4,
            ),
            (
                "Potato Chips - Classic",
                "Crispy salted potato chips",
                "Lays",
                20.00,
                50,
                5,
                "LAY-CHP-001",
                "8901234567893",
                12.00,
                180,
            ),
            (
                "Coca Cola 600ml",
                "Chilled soft drink",
                "Coca-Cola",
                40.00,
                600,
                4,
                "COC-COL-001",
                "8901234567894",
                12.00,
                365,
            ),
            (
                "Tomatoes 500g",
                "Fresh red tomatoes",
                "FreshFarms",
                30.00,
                500,
                6,
                "FF-TOM-001",
                "8901234567895",
                0.00,
                5,
            ),
            (
                "Basmati Rice 5kg",
                "Premium aged basmati rice",
                "India Gate",
                450.00,
                5000,
                8,
                "IND-RIC-001",
                "8901234567896",
                5.00,
                730,
            ),
            (
                "Mobile Phone Charger",
                "Fast charging USB-C cable",
                "Mi",
                299.00,
                50,
                9,
                "MI-CHR-001",
                "8901234567897",
                18.00,
                1825,
            ),
            (
                "Hand Sanitizer 250ml",
                "Antibacterial hand sanitizer",
                "Dettol",
                80.00,
                250,
                10,
                "DET-SAN-001",
                "8901234567898",
                18.00,
                730,
            ),
            (
                "Greek Yogurt 200g",
                "High protein Greek yogurt",
                "Epigamia",
                75.00,
                200,
                7,
                "EPI-YOG-001",
                "8901234567899",
                5.00,
                15,
            ),
        ],
    )

    # Warehouses
    c.executemany(
        """INSERT INTO Warehouse(name,location,address,capacity,latitude,longitude,
                                  serviceable_radius_km,contact_phone,manager_name)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            (
                "DarkStore Dwarka",
                "Dwarka Sector 10",
                "Plot 45, Dwarka Sector 10, Delhi - 110075",
                5000,
                28.5921,
                77.0460,
                5.00,
                "9811111111",
                "Rajesh Kumar",
            ),
            (
                "DarkStore Rohini",
                "Rohini Sector 15",
                "Shop 12, Rohini Sector 15, Delhi - 110085",
                4500,
                28.7485,
                77.1072,
                4.50,
                "9822222222",
                "Priya Sharma",
            ),
            (
                "DarkStore Noida",
                "Sector 62 Noida",
                "Building A, Sector 62, Noida - 201301",
                6000,
                28.6273,
                77.3714,
                6.00,
                "9833333333",
                "Amit Verma",
            ),
            (
                "DarkStore Gurgaon",
                "DLF Phase 3",
                "Tower B, DLF Phase 3, Gurgaon - 122002",
                5500,
                28.4931,
                77.0935,
                5.50,
                "9844444444",
                "Sneha Gupta",
            ),
        ],
    )

    # Batch Inventory
    today = date.today()
    batches = [
        (1, 1, 1, "FF-BAN-2026-001", today - timedelta(5), today + timedelta(10), 100, 85, 20, "A-01-15", 50.0),
        (2, 1, 2, "AML-MLK-2026-001", today - timedelta(3), today + timedelta(4), 80, 60, 15, "B-02-08", 55.0),
        (3, 1, 1, "BRT-BRD-2026-001", today - timedelta(2), today + timedelta(8), 50, 40, 10, "C-01-22", 38.0),
        (4, 1, 4, "LAY-CHP-2026-001", today - timedelta(15), today + timedelta(90), 200, 180, 30, "D-05-11", 15.0),
        (5, 1, 5, "COC-COL-2026-001", today - timedelta(10), today + timedelta(120), 150, 120, 25, "E-03-06", 32.0),
        (1, 2, 1, "FF-BAN-2026-002", today - timedelta(4), today + timedelta(11), 90, 75, 20, "A-02-10", 50.0),
        (2, 2, 2, "AML-MLK-2026-002", today - timedelta(2), today + timedelta(5), 70, 55, 15, "B-01-12", 55.0),
        (6, 2, 1, "FF-TOM-2026-001", today - timedelta(1), today + timedelta(3), 60, 12, 15, "A-03-05", 24.0),
        (7, 2, 1, "IND-RIC-2026-001", today - timedelta(60), today + timedelta(600), 30, 25, 5, "F-01-20", 380.0),
        (10, 2, 2, "EPI-YOG-2026-001", today - timedelta(3), today + timedelta(12), 100, 90, 20, "B-05-08", 65.0),
        (3, 3, 1, "BRT-BRD-2026-002", today - timedelta(3), today + timedelta(7), 60, 50, 10, "C-02-18", 38.0),
        (4, 3, 4, "LAY-CHP-2026-002", today - timedelta(12), today + timedelta(95), 250, 230, 40, "D-03-15", 15.0),
        (5, 3, 5, "COC-COL-2026-002", today - timedelta(8), today + timedelta(115), 180, 160, 30, "E-02-09", 32.0),
        (8, 3, 3, "MI-CHR-2026-001", today - timedelta(30), today + timedelta(700), 50, 45, 10, "G-01-12", 250.0),
        (9, 3, 3, "DET-SAN-2026-001", today - timedelta(20), today + timedelta(680), 120, 110, 20, "H-02-06", 65.0),
        (1, 4, 1, "FF-BAN-2026-003", today - timedelta(3), today + timedelta(12), 110, 95, 20, "A-04-08", 50.0),
        (6, 4, 1, "FF-TOM-2026-002", today - timedelta(1), today + timedelta(2), 70, 8, 15, "A-05-12", 24.0),
        (7, 4, 1, "IND-RIC-2026-002", today - timedelta(50), today + timedelta(580), 40, 35, 8, "F-02-15", 380.0),
        (9, 4, 3, "DET-SAN-2026-002", today - timedelta(15), today + timedelta(360), 100, 85, 20, "H-01-10", 65.0),
        (10, 4, 2, "EPI-YOG-2026-002", today - timedelta(2), today + timedelta(13), 80, 70, 15, "B-03-20", 65.0),
    ]

    c.executemany(
        """INSERT INTO Batch_Inventory(product_id,warehouse_id,supplier_id,batch_number,
                                       manufacture_date,expiry_date,initial_quantity,
                                       current_quantity,reorder_level,shelf_location,cost_price)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        batches,
    )

    # Aggregated Inventory
    inv_rows = [
        (1, 1, 85, 0, today - timedelta(5), 20),
        (1, 2, 60, 0, today - timedelta(3), 15),
        (1, 3, 40, 0, today - timedelta(2), 10),
        (1, 4, 180, 0, today - timedelta(15), 30),
        (1, 5, 120, 0, today - timedelta(10), 25),
        (2, 1, 75, 0, today - timedelta(4), 20),
        (2, 2, 55, 0, today - timedelta(2), 15),
        (2, 6, 12, 0, today - timedelta(1), 15),
        (2, 7, 25, 0, today - timedelta(60), 5),
        (2, 10, 90, 0, today - timedelta(3), 20),
        (3, 3, 50, 0, today - timedelta(3), 10),
        (3, 4, 230, 0, today - timedelta(12), 40),
        (3, 5, 160, 0, today - timedelta(8), 30),
        (3, 8, 45, 0, today - timedelta(30), 10),
        (3, 9, 110, 0, today - timedelta(20), 20),
        (4, 1, 95, 0, today - timedelta(3), 20),
        (4, 6, 8, 0, today - timedelta(1), 15),
        (4, 7, 35, 0, today - timedelta(50), 8),
        (4, 9, 85, 0, today - timedelta(15), 20),
        (4, 10, 70, 0, today - timedelta(2), 15),
    ]

    c.executemany(
        """INSERT INTO Inventory(warehouse_id,product_id,total_quantity,reserved_quantity,
                                  last_restocked_at,reorder_threshold)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        inv_rows,
    )

    # Customers
    c.executemany(
        """INSERT INTO Customer(name,phone,email,address,latitude,longitude,
                                 pincode,preferred_warehouse_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            (
                "Rahul Sharma",
                "9811111111",
                "rahul.sharma@email.com",
                "A-101, Dwarka Sector 12, Delhi",
                28.5882,
                77.0460,
                "110075",
                1,
            ),
            (
                "Priya Verma",
                "9822222222",
                "priya.verma@email.com",
                "B-205, Rohini Sector 18, Delhi",
                28.7520,
                77.1072,
                "110085",
                2,
            ),
            (
                "Amit Kumar",
                "9833333333",
                "amit.kumar@email.com",
                "C-302, Sector 63, Noida",
                28.6289,
                77.3728,
                "201301",
                3,
            ),
            (
                "Sneha Gupta",
                "9844444444",
                "sneha.gupta@email.com",
                "D-401, DLF Phase 2, Gurgaon",
                28.4942,
                77.0948,
                "122002",
                4,
            ),
            (
                "Vikram Singh",
                "9855555555",
                "vikram.singh@email.com",
                "E-501, Dwarka Sector 8, Delhi",
                28.5891,
                77.0520,
                "110075",
                1,
            ),
            (
                "Anjali Mehta",
                "9866666666",
                "anjali.mehta@email.com",
                "F-102, Sector 62, Noida",
                28.6260,
                77.3700,
                "201301",
                3,
            ),
            (
                "Rohan Joshi",
                "9877777777",
                "rohan.joshi@email.com",
                "G-203, Rohini Sector 20, Delhi",
                28.7530,
                77.1100,
                "110085",
                2,
            ),
            (
                "Pooja Nair",
                "9888888888",
                "pooja.nair@email.com",
                "H-304, DLF Phase 4, Gurgaon",
                28.4920,
                77.0920,
                "122002",
                4,
            ),
        ],
    )

    # Delivery Partners
    c.executemany(
        """INSERT INTO Delivery_Partner(name,phone,email,vehicle_type,vehicle_number,
                                         license_number,address,assigned_warehouse_id,rating)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            (
                "Rajesh Kumar",
                "9711111111",
                "rajesh.del@email.com",
                "Bike",
                "DL-01-AB-1234",
                "DL-1234567890",
                "Dwarka, Delhi",
                1,
                4.8,
            ),
            (
                "Suresh Yadav",
                "9722222222",
                "suresh.del@email.com",
                "Scooter",
                "DL-02-CD-5678",
                "DL-9876543210",
                "Rohini, Delhi",
                2,
                4.6,
            ),
            (
                "Manoj Tiwari",
                "9733333333",
                "manoj.del@email.com",
                "Bike",
                "UP-16-EF-9012",
                "UP-1122334455",
                "Noida",
                3,
                4.7,
            ),
            (
                "Deepak Verma",
                "9744444444",
                "deepak.del@email.com",
                "Bicycle",
                "HR-26-GH-3456",
                "HR-5566778899",
                "Gurgaon",
                4,
                4.5,
            ),
            (
                "Sanjay Rawat",
                "9755555555",
                "sanjay.del@email.com",
                "Bike",
                "DL-03-IJ-7890",
                "DL-6677889900",
                "Dwarka, Delhi",
                1,
                4.9,
            ),
            (
                "Anil Sharma",
                "9766666666",
                "anil.del@email.com",
                "Scooter",
                "UP-17-KL-2345",
                "UP-7788990011",
                "Noida",
                3,
                4.4,
            ),
        ],
    )

    # Coupons
    c.executemany(
        """INSERT INTO Coupon(coupon_code,description,discount_type,discount_value,
                               min_order_value,max_discount_amount,valid_from,valid_until,
                               usage_limit,per_user_limit)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            (
                "FIRST50",
                "First order 50% off",
                "Percentage",
                50.00,
                100.00,
                100.00,
                today,
                date(2026, 12, 31),
                1000,
                1,
            ),
            (
                "SAVE100",
                "Rs.100 off on orders above Rs.500",
                "Fixed Amount",
                100.00,
                500.00,
                None,
                today,
                today + timedelta(30),
                None,
                3,
            ),
            (
                "FREEDEL",
                "Free delivery on all orders",
                "Free Delivery",
                0.00,
                200.00,
                None,
                today,
                today + timedelta(15),
                5000,
                5,
            ),
        ],
    )

    # Stock Ledger initial Stock In entries (first 5 batches)
    for i in range(1, 6):
        c.execute(
            """
            INSERT INTO Stock_Ledger(batch_id,transaction_type,quantity_change,
                                     transaction_date,reference_type,performed_by,
                                     notes,previous_quantity,new_quantity)
            SELECT batch_id,'Stock In',initial_quantity,NOW(),
                   'Supplier','System','Initial stock loaded',0,initial_quantity
            FROM Batch_Inventory WHERE batch_id=%s
            """,
            (i,),
        )

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# INITIALISE DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> DB:
    conn = get_connection()
    create_schema(conn)
    create_triggers(conn)
    seed_data(conn)
    create_transaction_demo_objects(conn)
    ensure_transaction_demo_seed(conn)
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# USE CASE 1: ORDER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_all_customers(conn: DB):
    return conn.execute(
        """
        SELECT customer_id, name, phone, email, address,
               preferred_warehouse_id, total_orders, total_spent
        FROM Customer
        WHERE is_active = 1
        ORDER BY name
        """
    ).fetchall()


def get_warehouses(conn: DB):
    return conn.execute(
        """
        SELECT warehouse_id, name, location, address,
               serviceable_radius_km, is_operational
        FROM Warehouse
        WHERE is_operational = 1
        ORDER BY name
        """
    ).fetchall()


def get_available_products(conn: DB, warehouse_id: int):
    """List products with available stock at a given warehouse (FEFO nearest expiry batch)."""
    return conn.execute(
        """
        SELECT
            p.product_id,
            p.name AS product_name,
            p.brand,
            p.price,
            p.tax_rate,
            c.name AS category,
            (i.total_quantity - i.reserved_quantity) AS available_qty,
            b.expiry_date AS nearest_expiry,
            b.batch_id
        FROM Product p
        JOIN Category c ON p.category_id = c.category_id
        JOIN Inventory i
            ON p.product_id = i.product_id
           AND i.warehouse_id = %s
        JOIN Batch_Inventory b
            ON b.product_id = p.product_id
           AND b.warehouse_id = %s
        WHERE p.is_active = 1
          AND (i.total_quantity - i.reserved_quantity) > 0
          AND b.current_quantity > 0
          AND b.expiry_date > CURDATE()
          AND b.expiry_date = (
              SELECT MIN(b2.expiry_date)
              FROM Batch_Inventory b2
              WHERE b2.product_id = p.product_id
                AND b2.warehouse_id = %s
                AND b2.current_quantity > 0
                AND b2.expiry_date > CURDATE()
          )
        ORDER BY c.name, p.name
        """,
        (warehouse_id, warehouse_id, warehouse_id),
    ).fetchall()


def place_order(conn: DB, customer_id: int, warehouse_id: int, cart, payment_method: str):
    c = conn.cursor()
    try:
        # 1. Verify stock not expired and quantity is available
        for item in cart:
            row = c.execute(
                """
                SELECT current_quantity, expiry_date
                FROM Batch_Inventory
                WHERE batch_id = %s AND product_id = %s AND warehouse_id = %s
                """,
                (item["batch_id"], item["product_id"], warehouse_id),
            ).fetchone()
            if not row:
                raise ValueError(f"Batch {item['batch_id']} not found in this warehouse.")

            exp = row["expiry_date"]
            if isinstance(exp, str):
                exp = date.fromisoformat(exp)
            if exp <= date.today():
                raise ValueError(f"Batch {item['batch_id']} has expired — cannot sell.")
            if row["current_quantity"] < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for batch {item['batch_id']}. "
                    f"Available: {row['current_quantity']}, Requested: {item['quantity']}"
                )

        # 2. Compute totals
        subtotal = sum(i["quantity"] * float(i["price"]) for i in cart)
        tax_amt = sum(i["quantity"] * float(i["price"]) * (float(i["tax_rate"]) / 100) for i in cart)
        total = round(subtotal + tax_amt, 2)

        # 3. Generate order number
        cnt_row = c.execute("SELECT COUNT(*) AS cnt FROM Orders").fetchone() or {"cnt": 0}
        count = cnt_row["cnt"]
        order_num = f"ORD-{datetime.now().strftime('%Y')}-{count+1:05d}"

        # 4. Insert Orders row
        c.execute(
            """
            INSERT INTO Orders(
                order_number, customer_id, warehouse_id,
                order_status, payment_status, placed_at,
                expected_delivery_time,
                subtotal, tax_amount, total_amount
            )
            VALUES (%s,%s,%s,'Placed','Pending',NOW(),
                    DATE_ADD(NOW(), INTERVAL 20 MINUTE),
                    %s,%s,%s)
            """,
            (order_num, customer_id, warehouse_id, subtotal, tax_amt, total),
        )
        order_id = c.lastrowid

        # 5. Insert Order_Item rows (Trigger 1 fires for each row)
        for item in cart:
            c.execute(
                """
                INSERT INTO Order_Item(order_id, product_id, batch_id,
                                       quantity, price_at_time, tax_at_time)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["batch_id"],
                    item["quantity"],
                    float(item["price"]),
                    float(item["tax_rate"]),
                ),
            )

        # 6. Insert Payment row
        c.execute(
            """
            INSERT INTO Payment(order_id, amount, payment_method, payment_status)
            VALUES (%s,%s,%s,'Completed')
            """,
            (order_id, total, payment_method),
        )

        # 7. Mark payment as paid + generate transaction id
        txn_id = f"TXN-{payment_method[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        c.execute(
            """
            UPDATE Payment
            SET transaction_id = %s, paid_at = NOW()
            WHERE order_id = %s
            """,
            (txn_id, order_id),
        )

        # 8. Assign best available partner (optional)
        partner = c.execute(
            """
            SELECT partner_id FROM Delivery_Partner
            WHERE assigned_warehouse_id = %s
              AND availability_status = 'Available'
              AND is_active = 1
            ORDER BY rating DESC
            LIMIT 1
            """,
            (warehouse_id,),
        ).fetchone()

        partner_id = partner["partner_id"] if partner else None
        c.execute(
            """
            UPDATE Orders
            SET order_status = 'Confirmed',
                confirmed_at = NOW(),
                delivery_partner_id = %s,
                payment_status = 'Paid'
            WHERE order_id = %s
            """,
            (partner_id, order_id),
        )

        if partner_id:
            c.execute(
                """
                UPDATE Delivery_Partner
                SET availability_status = 'Busy'
                WHERE partner_id = %s
                """,
                (partner_id,),
            )

        conn.commit()
        return order_id

    except Exception as e:
        conn.rollback()
        raise e


def get_order_history(conn: DB, customer_id=None):
    sql = """
        SELECT o.order_id, o.order_number, o.order_status, o.payment_status,
               o.total_amount, o.placed_at, o.delivered_at,
               o.expected_delivery_time,
               c.name AS customer_name,
               w.name AS warehouse_name,
               dp.name AS partner_name,
               p.payment_method
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        JOIN Warehouse w ON o.warehouse_id = w.warehouse_id
        LEFT JOIN Delivery_Partner dp ON o.delivery_partner_id = dp.partner_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
    """
    if customer_id:
        sql += " WHERE o.customer_id = %s ORDER BY o.placed_at DESC"
        return conn.execute(sql, (customer_id,)).fetchall()
    sql += " ORDER BY o.placed_at DESC"
    return conn.execute(sql).fetchall()


def get_order_items(conn: DB, order_id: int):
    return conn.execute(
        """
        SELECT oi.order_item_id, pr.name AS product_name, pr.brand,
               oi.quantity, oi.price_at_time, oi.tax_at_time,
               oi.quantity * oi.price_at_time AS subtotal,
               bi.expiry_date, bi.batch_number
        FROM Order_Item oi
        JOIN Product pr ON oi.product_id = pr.product_id
        JOIN Batch_Inventory bi ON oi.batch_id = bi.batch_id
        WHERE oi.order_id = %s
        """,
        (order_id,),
    ).fetchall()


def update_order_status(conn: DB, order_id: int, new_status: str):
    ts_col = {
        "Packed": "packed_at",
        "Out for Delivery": "dispatched_at",
        "Delivered": "delivered_at",
        "Cancelled": "cancelled_at",
    }
    col = ts_col.get(new_status)
    if col:
        conn.execute(
            f"""
            UPDATE Orders
            SET order_status = %s, {col} = NOW()
            WHERE order_id = %s
            """,
            (new_status, order_id),
        )
    else:
        conn.execute(
            "UPDATE Orders SET order_status = %s WHERE order_id = %s",
            (new_status, order_id),
        )

    # Free up delivery partner if delivered/cancelled
    if new_status in ("Delivered", "Cancelled"):
        conn.execute(
            """
            UPDATE Delivery_Partner
            SET availability_status = 'Available'
            WHERE partner_id = (
                SELECT delivery_partner_id FROM Orders WHERE order_id = %s
            )
            """,
            (order_id,),
        )

        if new_status == "Delivered":
            conn.execute(
                """
                UPDATE Customer
                SET total_orders = total_orders + 1,
                    total_spent  = total_spent  + (
                        SELECT total_amount FROM Orders WHERE order_id = %s
                    )
                WHERE customer_id = (
                    SELECT customer_id FROM Orders WHERE order_id = %s
                )
                """,
                (order_id, order_id),
            )
            conn.execute(
                """
                UPDATE Delivery_Partner
                SET total_deliveries = total_deliveries + 1,
                    successful_deliveries = successful_deliveries + 1,
                    availability_status = 'Available'
                WHERE partner_id = (
                    SELECT delivery_partner_id FROM Orders WHERE order_id = %s
                )
                """,
                (order_id,),
            )

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# USE CASE 2: INVENTORY & ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

def get_inventory_summary(conn: DB, warehouse_id=None):
    sql = """
        SELECT i.inventory_id,
               w.name AS warehouse_name,
               p.name AS product_name,
               p.brand,
               c.name AS category,
               i.total_quantity,
               i.reserved_quantity,
               (i.total_quantity - i.reserved_quantity) AS available_qty,
               i.reorder_threshold,
               CASE
                   WHEN (i.total_quantity - i.reserved_quantity) = 0 THEN 'Out of Stock'
                   WHEN (i.total_quantity - i.reserved_quantity) <= i.reorder_threshold THEN 'Low Stock'
                   ELSE 'In Stock'
               END AS stock_status
        FROM Inventory i
        JOIN Warehouse w ON i.warehouse_id = w.warehouse_id
        JOIN Product p ON i.product_id = p.product_id
        JOIN Category c ON p.category_id = c.category_id
    """
    if warehouse_id:
        sql += " WHERE i.warehouse_id = %s ORDER BY stock_status, p.name"
        return conn.execute(sql, (warehouse_id,)).fetchall()
    sql += " ORDER BY stock_status, w.name, p.name"
    return conn.execute(sql).fetchall()


def get_batch_details(conn: DB, warehouse_id=None):
    sql = """
        SELECT b.batch_id, b.batch_number,
               w.name AS warehouse,
               p.name AS product,
               s.name AS supplier,
               b.manufacture_date, b.expiry_date,
               b.initial_quantity, b.current_quantity,
               b.reorder_level, b.shelf_location, b.cost_price,
               CASE
                   WHEN b.expiry_date < CURDATE() THEN 'Expired'
                   WHEN b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 3 DAY) THEN 'Expiring Soon'
                   WHEN b.current_quantity = 0 THEN 'Out of Stock'
                   WHEN b.current_quantity <= b.reorder_level THEN 'Low Stock'
                   ELSE 'OK'
               END AS batch_status
        FROM Batch_Inventory b
        JOIN Warehouse w ON b.warehouse_id = w.warehouse_id
        JOIN Product p ON b.product_id = p.product_id
        JOIN Supplier s ON b.supplier_id = s.supplier_id
    """
    if warehouse_id:
        sql += " WHERE b.warehouse_id = %s ORDER BY b.expiry_date"
        return conn.execute(sql, (warehouse_id,)).fetchall()
    sql += " ORDER BY b.expiry_date"
    return conn.execute(sql).fetchall()


def get_stock_alerts(conn: DB):
    return conn.execute(
        """
        SELECT a.alert_id, w.name AS warehouse, p.name AS product,
               a.alert_type, a.alert_message, a.severity,
               a.is_resolved, a.created_at
        FROM Warehouse_Inventory_Alert a
        JOIN Warehouse w ON a.warehouse_id = w.warehouse_id
        LEFT JOIN Product p ON a.product_id = p.product_id
        ORDER BY
            CASE a.severity
                WHEN 'Critical' THEN 1
                WHEN 'High'     THEN 2
                WHEN 'Medium'   THEN 3
                ELSE 4
            END,
            a.created_at DESC
        """
    ).fetchall()


def resolve_alert(conn: DB, alert_id: int):
    conn.execute(
        """
        UPDATE Warehouse_Inventory_Alert
        SET is_resolved = 1, resolved_at = NOW()
        WHERE alert_id = %s
        """,
        (alert_id,),
    )
    conn.commit()


def replenish_stock(conn: DB, batch_id: int, quantity: int, performed_by: str = "Staff"):
    c = conn.cursor()
    row = c.execute(
        """
        SELECT current_quantity, product_id, warehouse_id
        FROM Batch_Inventory WHERE batch_id = %s
        """,
        (batch_id,),
    ).fetchone()
    if not row:
        raise ValueError("Batch not found")

    prev_qty = row["current_quantity"]
    new_qty = prev_qty + quantity

    c.execute(
        """
        UPDATE Batch_Inventory
        SET current_quantity = current_quantity + %s
        WHERE batch_id = %s
        """,
        (quantity, batch_id),
    )

    c.execute(
        """
        UPDATE Inventory
        SET total_quantity = total_quantity + %s,
            last_restocked_at = NOW()
        WHERE product_id = %s AND warehouse_id = %s
        """,
        (quantity, row["product_id"], row["warehouse_id"]),
    )

    c.execute(
        """
        INSERT INTO Stock_Ledger(batch_id, transaction_type, quantity_change,
                                 reference_type, performed_by, notes,
                                 previous_quantity, new_quantity)
        VALUES (%s, 'Stock In', %s, 'Supplier', %s, 'Manual replenishment', %s, %s)
        """,
        (batch_id, quantity, performed_by, prev_qty, new_qty),
    )

    conn.commit()


def get_stock_ledger(conn: DB, batch_id=None, limit: int = 100):
    limit = int(limit)
    sql = """
        SELECT sl.ledger_id, sl.transaction_type, sl.quantity_change,
               sl.transaction_date, sl.reference_type, sl.reference_id,
               sl.performed_by, sl.notes,
               sl.previous_quantity, sl.new_quantity,
               p.name AS product_name,
               w.name AS warehouse_name
        FROM Stock_Ledger sl
        JOIN Batch_Inventory bi ON sl.batch_id = bi.batch_id
        JOIN Product p ON bi.product_id = p.product_id
        JOIN Warehouse w ON bi.warehouse_id = w.warehouse_id
    """
    if batch_id:
        sql += " WHERE sl.batch_id = %s ORDER BY sl.transaction_date DESC LIMIT %s"
        return conn.execute(sql, (batch_id, limit)).fetchall()
    sql += " ORDER BY sl.transaction_date DESC LIMIT %s"
    return conn.execute(sql, (limit,)).fetchall()


# ─── Analytics ───────────────────────────────────────────────────────────────

def get_sales_summary(conn: DB):
    return conn.execute(
        """
        SELECT DATE(placed_at) AS sale_date,
               COUNT(*) AS num_orders,
               SUM(total_amount) AS revenue
        FROM Orders
        WHERE order_status NOT IN ('Cancelled','Returned')
          AND DATE(placed_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DATE(placed_at)
        ORDER BY sale_date
        """
    ).fetchall()


def get_top_products(conn: DB, limit: int = 10):
    return conn.execute(
        """
        SELECT p.name AS product_name,
               p.brand,
               SUM(oi.quantity) AS total_qty,
               SUM(oi.quantity * oi.price_at_time) AS total_revenue,
               COUNT(DISTINCT oi.order_id) AS order_count
        FROM Order_Item oi
        JOIN Product p ON oi.product_id = p.product_id
        GROUP BY p.product_id, p.name, p.brand
        ORDER BY total_revenue DESC
        LIMIT %s
        """,
        (int(limit),),
    ).fetchall()


def get_customer_analysis(conn: DB):
    return conn.execute(
        """
        SELECT c.customer_id, c.name, c.phone, c.email,
               c.total_orders, c.total_spent,
               CASE
                    WHEN c.total_orders = 0 THEN 'New'
                    WHEN c.total_spent  > 1000 THEN 'Premium'
                    WHEN c.total_orders > 3 THEN 'Regular'
                    ELSE 'Occasional'
               END AS customer_segment,
               w.name AS preferred_warehouse
        FROM Customer c
        LEFT JOIN Warehouse w ON c.preferred_warehouse_id = w.warehouse_id
        WHERE c.is_active = 1
        ORDER BY c.total_spent DESC
        """
    ).fetchall()


def get_warehouse_performance(conn: DB):
    return conn.execute(
        """
        SELECT w.name AS warehouse,
               COUNT(o.order_id) AS total_orders,
               SUM(CASE WHEN o.order_status='Delivered' THEN 1 ELSE 0 END) AS delivered,
               SUM(CASE WHEN o.order_status='Cancelled' THEN 1 ELSE 0 END) AS cancelled,
               ROUND(AVG(o.actual_delivery_time_minutes),1) AS avg_delivery_mins,
               ROUND(SUM(o.total_amount),2) AS total_revenue
        FROM Warehouse w
        LEFT JOIN Orders o ON w.warehouse_id = o.warehouse_id
        GROUP BY w.warehouse_id, w.name
        ORDER BY total_revenue DESC
        """
    ).fetchall()


def get_delivery_partner_performance(conn: DB):
    return conn.execute(
        """
        SELECT dp.name, dp.vehicle_type, dp.rating,
               dp.total_deliveries, dp.successful_deliveries,
               dp.availability_status,
               w.name AS warehouse
        FROM Delivery_Partner dp
        LEFT JOIN Warehouse w ON dp.assigned_warehouse_id = w.warehouse_id
        WHERE dp.is_active = 1
        ORDER BY dp.rating DESC
        """
    ).fetchall()


def get_expiring_soon(conn: DB, days: int = 7):
    return conn.execute(
        """
        SELECT b.batch_id, p.name AS product, w.name AS warehouse,
               b.expiry_date, b.current_quantity,
               DATEDIFF(b.expiry_date, CURDATE()) AS days_left
        FROM Batch_Inventory b
        JOIN Product p ON b.product_id = p.product_id
        JOIN Warehouse w ON b.warehouse_id = w.warehouse_id
        WHERE b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
          AND b.expiry_date  > CURDATE()
          AND b.current_quantity > 0
        ORDER BY b.expiry_date
        """,
        (int(days),),
    ).fetchall()


# ─── Customer & Delivery Partner CRUD ─────────────────────────────────────────

def add_customer(conn: DB, name, phone, email, address, pincode, warehouse_id):
    conn.execute(
        """
        INSERT INTO Customer(name, phone, email, address, pincode,
                             preferred_warehouse_id)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (name, phone, email, address, pincode, warehouse_id),
    )
    conn.commit()


def add_delivery_partner(conn: DB, name, phone, email, vehicle_type, vehicle_number, address, warehouse_id):
    conn.execute(
        """
        INSERT INTO Delivery_Partner(name, phone, email, vehicle_type,
                                     vehicle_number, address,
                                     assigned_warehouse_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (name, phone, email, vehicle_type, vehicle_number, address, warehouse_id),
    )
    conn.commit()


def get_kpis(conn: DB):
    row = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM Orders WHERE DATE(placed_at)=CURDATE()) AS orders_today,
            (SELECT COALESCE(SUM(total_amount),0) FROM Orders
             WHERE DATE(placed_at)=CURDATE() AND order_status!='Cancelled') AS revenue_today,
            (SELECT COUNT(*) FROM Orders
             WHERE order_status IN ('Placed','Confirmed','Processing','Packed')) AS active_orders,
            (SELECT COUNT(*) FROM Warehouse_Inventory_Alert
             WHERE is_resolved=0) AS open_alerts,
            (SELECT COUNT(*) FROM Customer WHERE is_active=1) AS total_customers,
            (SELECT COUNT(*) FROM Delivery_Partner
             WHERE availability_status='Available' AND is_active=1) AS available_partners
        """
    ).fetchone()
    return dict(row) if row else {
        "orders_today": 0,
        "revenue_today": 0,
        "active_orders": 0,
        "open_alerts": 0,
        "total_customers": 0,
        "available_partners": 0,
    }
