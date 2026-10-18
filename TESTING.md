# Demo data and database integrity tests

The files in `sql/` create the operational schema. The optional
`seeds/demo_data.sql` adds synthetic examples for a disposable demo database.
The tests build their own isolated schemas and do not depend on the seed file.

## Load demo data (optional)

Apply the three schema files in order to a **fresh database**. In Bash:

```bash
for file in sql/001_create_machines.sql sql/002_create_production_orders.sql sql/003_create_machine_events.sql; do
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse < "$file"
done
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse < seeds/demo_data.sql
```

In PowerShell:

```powershell
@(
    "sql/001_create_machines.sql",
    "sql/002_create_production_orders.sql",
    "sql/003_create_machine_events.sql"
) | ForEach-Object {
    Get-Content -Raw $_ | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse
    if ($LASTEXITCODE -ne 0) { throw "Schema setup failed: $_" }
}
Get-Content -Raw seeds/demo_data.sql | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U factorypulse -d factorypulse
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed" }
```

Run the seed only once on a fresh database. It is intentionally not a schema
migration and should not be loaded into a production database.

## Run the integrity tests

1. Start PostgreSQL: `docker compose up -d`.
2. Create a separate test database once:

   ```bash
   docker compose exec postgres createdb -U factorypulse factorypulse_test
   ```

3. Install the Python test dependencies:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

4. Set `TEST_DATABASE_URL` with the password from your local `.env`.
   For example, in PowerShell:

   ```powershell
   $env:TEST_DATABASE_URL = "postgresql://factorypulse:YOUR_LOCAL_PASSWORD@127.0.0.1:5433/factorypulse_test"
   python -m pytest -q
   ```

   In Bash:

   ```bash
   export TEST_DATABASE_URL='postgresql://factorypulse:YOUR_LOCAL_PASSWORD@127.0.0.1:5433/factorypulse_test'
   python -m pytest -q
   ```

   If your password contains URL-reserved characters, URL-encode them in the
   connection string.

The suite refuses to run unless the connected database is named
`factorypulse_test`. Each test creates a uniquely named schema, applies
the three SQL files in order, checks one behavior, and removes that schema.
It does not touch the `factorypulse` database. The test user needs permission
to create schemas in `factorypulse_test`.

A failed run should be investigated before changing the schema or building
the simulator. Tests validate current rules; they do not claim the database
implements every possible manufacturing business rule.
