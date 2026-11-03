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

In Bash, apply all five files, then run the constraint checks:

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

The view-check fixtures now include distinct source IDs. Run the check against the same disposable database:

```powershell
Get-Content -Raw tests/test_order_production_summary.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test
if ($LASTEXITCODE -ne 0) { throw "View check execution failed" }
```

On Bash:

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < tests/test_order_production_summary.sql
```

Its final result is **checked visually**: `V9001` must show **35** units and `V9002` must show **0**. A wrong total does not yet fail the script. The script rolls back its test rows.

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
3. Generate `events.jsonl`, then execute `python -m src.ingestion.db --input events.jsonl` from the repository root with the virtual environment active. Module execution supports the loader's absolute `src.ingestion.read_events` import.
4. Execute the loader again without changing the file.

With none of `EVT-001` through `EVT-007` present initially, the observed local outputs were:

```text
7 lines inserted, 0 lines skipped
0 lines inserted, 7 lines skipped
```

The lookup checks the machine/order pairing before each insert. `ON CONFLICT (source_event_id) DO NOTHING` skips already stored IDs; it does not compare payloads or retrieve the existing `event_id`. All inserts in a run share one transaction. The connection context commits on normal exit or rolls back when an exception escapes; counters and elapsed seconds are logged after the context exits successfully.

**Manual result observed locally:** filtering stored rows to the seven simulator IDs confirmed 7 rows and 35 units after replay. Replay counters alone are not a persisted-total assertion; use the query below when repeating the check. The order summary includes demo events too: the seed contributes 120 units, so `PO-001` should total 155 after the simulator's additional 35 units. Database replay/rollback checks are not yet automated.


```sql
SELECT COUNT(*) AS event_count, SUM(units_produced) AS total_units
FROM machine_events
WHERE source_event_id IN (
    'EVT-001', 'EVT-002', 'EVT-003', 'EVT-004',
    'EVT-005', 'EVT-006', 'EVT-007'
);
```

## Manual rollback and process exit checks

These procedures were exercised locally during development. They are not automated tests of `db.py`, and they must use a disposable local database. The automated Python suite still tests only the simulator and reader.

### Batch failure and rollback

The committed `events_rollback_test.jsonl` contains `EVT-050` for registered `M-001` / `PO-001`, followed by `EVT-051` for nonexistent `PO-123`. Before running it, confirm that `PO-123` does not exist and that neither test source ID is already stored. Existing IDs would skip inserts and weaken the rollback check. If adapting the fixture, keep source IDs distinct and within the database's 20-character limit.

```powershell
python -m src.ingestion.db --input events_rollback_test.jsonl
$LASTEXITCODE
```

Expected behavior: a start log, an `ERROR` log containing `Event ingestion failed`, the missing machine/order error for `EVT-051`, no success summary, and a nonzero exit code (observed locally: `1`). The logged traceback may be followed by the re-raised traceback. Query the same database afterward:

```sql
SELECT COUNT(*) AS event_count, SUM(units_produced) AS total_units
FROM machine_events
WHERE source_event_id IN ('EVT-050', 'EVT-051');
```

With both IDs absent before the test, expect **0 rows** and a **NULL** sum afterward: the first insert was rolled back when the second lookup failed. Generated identity values may have gaps after rollback; IDs are not a row counter.

### Missing or empty configuration

The loader requires nonempty `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD`. Temporarily leave `PGDATABASE=` in the local `.env` and run the module. Expect `ValueError: PGDATABASE value is missing`, an error log and nonzero exit status. Restore the value after the check. `load_dotenv()` does not normally override an existing process environment variable, so a preexisting `PGDATABASE` in the shell can mask this test. Do not print passwords while diagnosing configuration.

### Database unavailable and recovery

In the disposable local environment:

```powershell
docker compose stop postgres
python -m src.ingestion.db --input events.jsonl
$LASTEXITCODE
docker compose start postgres
docker compose ps
```

Expect a connection failure, an error log and a nonzero exit code. `connect_timeout=10` limits connection establishment; a refusal may fail immediately, so an exact ten-second wait is not the assertion. After PostgreSQL is healthy again, rerun the normal input and immediately check `$LASTEXITCODE`: expect `0` and the successful summary. `stop` / `start` preserve the named volume.

### CLI and successful-run logs

```powershell
python -m src.ingestion.db --help
python -m src.ingestion.db --input events.jsonl
$LASTEXITCODE
```

Help lists `--input` and does not ingest events. A successful load logs the input path and, after commit, inserted/skipped counts plus elapsed seconds. Replaying the sample should log 0 inserted / 7 skipped. Timestamps use the local system time; when run with `-m`, the module's logger name is `__main__`. Duration comes from `time.perf_counter()` and includes successful connection-context exit; no timing threshold is asserted. The completion summary is not emitted on failure.

## Verification boundaries

- **Automated now:** 16 simulator/reader unit tests; SQL constraint assertions when their script is executed.
- **Manual now:** view totals, persisted replay aggregates, transaction rollback, missing configuration, connection failure/recovery, CLI logs and process exit status.
- **Not yet implemented:** automated loader integration tests or a CI workflow. `ingest_events(connection, events)` is now callable without invoking the CLI, providing a seam for those future tests. The caller remains responsible for committing or rolling back its connection.
