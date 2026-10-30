# Local setup, SQL checks and Python verification

**Current scope:** 16 Python unit tests, rollback-only SQL constraint checks and a local replay demonstration of idempotent ingestion. Database integration is verified manually; there is no CI workflow yet.

FactoryPulse currently uses numbered SQL files applied manually in order. It does
not yet use a migration framework. Use a fresh, disposable database when
verifying the complete setup. Editing a `CREATE TABLE IF NOT EXISTS` file
changes new databases only; it does not remove columns from an existing one.

| File | Purpose |
| --- | --- |
| `sql/001_create_machines.sql` | Machine master table. |
| `sql/002_create_production_orders.sql` | Orders, quantities, status and schedule. |
| `sql/003_create_machine_events.sql` | Machine event table, required globally unique `source_event_id` and initial unit constraints. |
| `sql/004_enforce_production_report_payload.sql` | Replace `ck_units`: production reports require an order and positive units. |
| `sql/005_create_order_production_summary_view.sql` | Calculate event-derived units for every order, including orders with zero production. |

The `004` change can fail if an existing database has production reports
without an order or with zero units. Review such rows before applying it to a
populated database.

## Verify in a disposable database

With the `factorypulse` user configured in `.env`, start PostgreSQL and
create a fresh test database:

```bash
docker compose up -d
docker compose exec postgres createdb -U factorypulse factorypulse_test
```

If `factorypulse_test` already exists, use another fresh database. Do not
run these checks against a database whose data you need to keep.

In Bash, apply all five files, then run the constraint checks. The manual view check has the fixture gap described below and is excluded from this setup command:

```bash
for file in sql/001_create_machines.sql sql/002_create_production_orders.sql sql/003_create_machine_events.sql sql/004_enforce_production_report_payload.sql sql/005_create_order_production_summary_view.sql; do
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < "$file" || exit 1
done
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < tests/test_constraints.sql || exit 1
```

In PowerShell:

```powershell
@(
    "sql/001_create_machines.sql",
    "sql/002_create_production_orders.sql",
    "sql/003_create_machine_events.sql",
    "sql/004_enforce_production_report_payload.sql",
    "sql/005_create_order_production_summary_view.sql"
) | ForEach-Object {
    Get-Content -Raw $_ | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test
    if ($LASTEXITCODE -ne 0) { throw "Database setup failed: $_" }
}
Get-Content -Raw tests/test_constraints.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test
if ($LASTEXITCODE -ne 0) { throw "Constraint checks failed" }
```

`test_constraints.sql` asserts the expected constraint name for each invalid
insert. A successful run prints 13 `PASS` notices and rolls back its test rows.
**Known fixture gap:** `test_order_production_summary.sql` currently omits
`source_event_id` in its three event inserts. The current schema requires this
column, so the script will fail until those fixtures receive distinct IDs.
This documentation/formatting revision deliberately preserves those inserts.

After that fixture update, `test_order_production_summary.sql` rolls back its test rows,
and its final result is **checked visually**: `V9001` must show **35** units and
`V9002` must show **0**. A wrong result does not yet fail that script.

## Load optional demo data

Apply files 001–005 to a separate, fresh demonstration database, such as the
regular local `factorypulse` database. Then run the seed **once**:

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse < seeds/demo_data.sql
```

In PowerShell:

```powershell
Get-Content -Raw seeds/demo_data.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed" }
```

The seed inserts two machines, two production orders and three events. It is
optional example data, not a migration or a complete machine-state sequence.

## Python unit tests

Use Python 3.12+ and a virtual environment. Install the runtime dependencies as shown in [README.md](README.md); the unit cases themselves use the standard-library `unittest` framework and do not connect to PostgreSQL.

From the repository root:

```bash
python -m unittest discover -s tests -v
```

The current suite has **16 tests**: four simulator tests and twelve reader tests. They cover selected state transitions, event ordering, invalid JSON, object shape, missing fields, integer/string requirements, blank strings, invalid/missing timestamp offsets, allowed event types, unit payload rules and valid timestamp preservation. These unit tests do not prove the database loader's behavior.

## Local ingestion and replay check

1. Apply 001–005 to a fresh demo database, then run `seeds/demo_data.sql` once. Its machine/order records provide `M-001` and `PO-001` for the simulator lookup.
2. Configure `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD` in the ignored `.env` file, consistently with the Docker database settings. Use `127.0.0.1:5433` when running Python on the host.
3. Generate `events.jsonl`, then execute `python src/ingestion/db.py` from the repository root. Direct script execution matches the loader's current `from read_events import read_events` import.
4. Execute the loader again without changing the file.

With none of `EVT-001` through `EVT-007` present initially, the observed local outputs were:

```text
7 lines inserted, 0 lines skipped
0 lines inserted, 7 lines skipped
```

The lookup checks the machine/order pairing before each insert. `ON CONFLICT (source_event_id) DO NOTHING` skips already stored IDs; it does not compare payloads or retrieve the existing `event_id`. All inserts in a run share one transaction. The connection context commits on normal exit or rolls back when an exception escapes; counters are printed after the context exits successfully.

**Next manual verification:** filter stored rows to the seven simulator IDs and confirm a count of 7 and a unit sum of 35 after replay. This database aggregate check is pending; replay counters alone are not a persisted-total assertion. The order summary includes demo events too: the seed contributes 120 units, so `PO-001` should total 155 after the simulator's additional 35 units. Database replay/rollback checks are not yet automated.
