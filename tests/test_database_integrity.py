"""Integration tests for the operational PostgreSQL schema.

Set TEST_DATABASE_URL to a database named factorypulse_test before running.
Every test creates and removes its own schema; demo data is not required.
"""

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import errors, sql


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = [
    ROOT / "sql" / "001_create_machines.sql",
    ROOT / "sql" / "002_create_production_orders.sql",
    ROOT / "sql" / "003_create_machine_events.sql",
]


@pytest.fixture
def db():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set TEST_DATABASE_URL to a database named factorypulse_test.")

    with psycopg.connect(url, autocommit=True) as conn:
        database_name = conn.execute("SELECT current_database()").fetchone()[0]
        if database_name != "factorypulse_test":
            pytest.fail(
                f"Refusing to run against {database_name!r}; expected 'factorypulse_test'."
            )

        schema_name = f"test_{uuid.uuid4().hex}"
        conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
        )
        try:
            conn.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name))
            )
            for path in SCHEMA_FILES:
                conn.execute(path.read_text(encoding="utf-8"))
            yield conn
        finally:
            conn.execute("SET search_path TO public")
            conn.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name))
            )


def add_machine(conn, code="M-001"):
    return conn.execute(
        "INSERT INTO machines (machine_code, machine_name) "
        "VALUES (%s, %s) RETURNING machine_id",
        (code, f"Machine {code}"),
    ).fetchone()[0]


def add_order(conn, machine_id, code="PO-001", planned_quantity=500):
    return conn.execute(
        "INSERT INTO production_orders "
        "(order_code, machine_id, product_code, planned_quantity, "
        "planned_start_at, planned_end_at) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING order_id",
        (
            code,
            machine_id,
            "P-100",
            planned_quantity,
            "2026-10-19T08:00:00+00:00",
            "2026-10-19T16:00:00+00:00",
        ),
    ).fetchone()[0]


def add_event(conn, machine_id, order_id, event_type, units_produced=0):
    return conn.execute(
        "INSERT INTO machine_events "
        "(machine_id, order_id, event_type, event_at, units_produced) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING event_id",
        (
            machine_id,
            order_id,
            event_type,
            "2026-10-19T09:00:00+00:00",
            units_produced,
        ),
    ).fetchone()[0]


def test_valid_machine_order_and_event(db):
    machine_id = add_machine(db)
    order_id = add_order(db, machine_id)
    event_id = add_event(db, machine_id, order_id, "PRODUCTION_REPORTED", 120)

    row = db.execute(
        "SELECT machine_id, order_id, units_produced "
        "FROM machine_events WHERE event_id = %s",
        (event_id,),
    ).fetchone()
    assert row == (machine_id, order_id, 120)


def test_duplicate_machine_code_is_rejected(db):
    add_machine(db)
    with pytest.raises(errors.UniqueViolation):
        add_machine(db)


def test_nonpositive_planned_quantity_is_rejected(db):
    machine_id = add_machine(db)
    with pytest.raises(errors.CheckViolation):
        add_order(db, machine_id, planned_quantity=0)


def test_order_for_missing_machine_is_rejected(db):
    with pytest.raises(errors.ForeignKeyViolation):
        add_order(db, 999999)


def test_order_end_must_follow_start(db):
    machine_id = add_machine(db)
    with pytest.raises(errors.CheckViolation):
        db.execute(
            "INSERT INTO production_orders "
            "(order_code, machine_id, product_code, planned_quantity, "
            "planned_start_at, planned_end_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                "PO-001",
                machine_id,
                "P-100",
                500,
                "2026-10-19T16:00:00+00:00",
                "2026-10-19T08:00:00+00:00",
            ),
        )


def test_event_cannot_use_order_from_another_machine(db):
    first_machine = add_machine(db, "M-001")
    second_machine = add_machine(db, "M-002")
    order_id = add_order(db, first_machine)
    with pytest.raises(errors.ForeignKeyViolation):
        add_event(db, second_machine, order_id, "MACHINE_STARTED")


def test_unknown_event_type_is_rejected(db):
    machine_id = add_machine(db)
    with pytest.raises(errors.CheckViolation):
        add_event(db, machine_id, None, "UNKNOWN")


def test_nonproduction_event_cannot_report_units(db):
    machine_id = add_machine(db)
    with pytest.raises(errors.CheckViolation):
        add_event(db, machine_id, None, "MACHINE_STOPPED", 10)


def test_negative_production_increment_is_rejected(db):
    machine_id = add_machine(db)
    order_id = add_order(db, machine_id)
    with pytest.raises(errors.CheckViolation):
        add_event(db, machine_id, order_id, "PRODUCTION_REPORTED", -1)
