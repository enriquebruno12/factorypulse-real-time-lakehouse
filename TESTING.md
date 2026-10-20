# SQL setup, demo data and checks

FactoryPulse currently uses numbered SQL files applied manually in order. It does
not yet use a migration framework. Use a fresh, disposable database when
verifying the complete setup. Editing a `CREATE TABLE IF NOT EXISTS` file
changes new databases only; it does not remove columns from an existing one.

| File | Purpose |
| --- | --- |
| `sql/001_create_machines.sql` | Machine master table. |
| `sql/002_create_production_orders.sql` | Orders, quantities, status and schedule. |
| `sql/003_create_machine_events.sql` | Machine event table and initial constraints. |
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

In Bash, apply all five files, then run both checks:

```bash
for file in sql/001_create_machines.sql sql/002_create_production_orders.sql sql/003_create_machine_events.sql sql/004_enforce_production_report_payload.sql sql/005_create_order_production_summary_view.sql; do
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < "$file" || exit 1
done
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < tests/test_constraints.sql || exit 1
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < tests/test_order_production_summary.sql || exit 1
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
Get-Content -Raw tests/test_order_production_summary.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test
if ($LASTEXITCODE -ne 0) { throw "View result check failed to execute" }
```

`test_constraints.sql` asserts the expected constraint name for each invalid
insert. A successful run prints 12 `PASS` notices and rolls back its test rows.
`test_order_production_summary.sql` also rolls back its test rows, but its
final result is **checked visually**: `V9001` must show **35** units and
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
