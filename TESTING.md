# SQL demo data and constraint checks

The schema is defined by `sql/001_create_machines.sql`,
`sql/002_create_production_orders.sql`, and
`sql/003_create_machine_events.sql`. Apply them in that order.

- `seeds/demo_data.sql` inserts valid synthetic examples. Run it only when
  you want a populated demonstration database. It is not a migration.
- `tests/test_constraints.sql` creates temporary test rows, deliberately
  attempts invalid inserts, verifies which constraint rejected each insert,
  and ends with `ROLLBACK`. No test rows are kept.

Both files are plain SQL for PostgreSQL 17. No Python packages are needed.

## Run the constraint checks

Use a fresh, disposable database so the test is independent of any data
you have already entered. With the `factorypulse` user configured in
`.env`, start PostgreSQL and create the test database:

```bash
docker compose up -d
docker compose exec postgres createdb -U factorypulse factorypulse_test
```

If `factorypulse_test` already exists, use a fresh database instead of
reusing old tables and data. Do not run the checks against your regular
`factorypulse` database.

In Bash, create the schema and run the checks:

```bash
for file in sql/001_create_machines.sql sql/002_create_production_orders.sql sql/003_create_machine_events.sql; do
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < "$file"
done
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test < tests/test_constraints.sql
```

In PowerShell:

```powershell
@(
    "sql/001_create_machines.sql",
    "sql/002_create_production_orders.sql",
    "sql/003_create_machine_events.sql"
) | ForEach-Object {
    Get-Content -Raw $_ | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test
    if ($LASTEXITCODE -ne 0) { throw "Schema setup failed: $_" }
}
Get-Content -Raw tests/test_constraints.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse_test
if ($LASTEXITCODE -ne 0) { throw "Constraint checks failed" }
```

A successful run prints ten `PASS` notices, then `ROLLBACK`. Any
unexpected acceptance, SQL error, or rejection by the wrong constraint
makes the command fail.

## Load optional demo data

Apply the three schema files to a separate, fresh demonstration database,
such as the regular local `factorypulse` database. Then run the seed
**once**:

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse < seeds/demo_data.sql
```

In PowerShell, use:

```powershell
Get-Content -Raw seeds/demo_data.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed" }
```

The seed inserts two machines, two production orders and three events. It
is intentionally separate from the constraint checks and should never be
applied automatically to a production database.
