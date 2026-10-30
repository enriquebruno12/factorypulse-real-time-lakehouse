# FactoryPulse — Operational Data Dictionary

**Status:** Current local implementation · **Version:** 0.2 · **Date:** 30 October 2026  
**Scope:** Current PostgreSQL operational schema for a synthetic manufacturing scenario.  
**SQL sources:** [machines](../sql/001_create_machines.sql), [production orders](../sql/002_create_production_orders.sql), [machine events](../sql/003_create_machine_events.sql), [production-report rule](../sql/004_enforce_production_report_payload.sql), and [order summary view](../sql/005_create_order_production_summary_view.sql).

This dictionary describes the current SQL and distinguishes database guarantees from simulator and ingestion validation. It models a synthetic factory; cloud processing and several business decisions remain planned.

## machines

**Grain:** One registered machine per row. **Primary key:** `machine_id`.

| Column | PostgreSQL type | Current SQL rule | Meaning |
| --- | --- | --- | --- |
| `machine_id` | `integer` | Generated identity; primary key (`pk_machine`). | Internal machine identifier used by orders and events. |
| `machine_code` | `varchar(20)` | Required; unique (`uq_machine_code`). | Human-readable machine code. Format and nonblank value are not validated. |
| `machine_name` | `varchar(100)` | Required. | Descriptive label; SQL accepts an empty string. |
| `installed_at` | `date` | Optional. | Installation date if known. |
| `is_active` | `boolean` | Required; default `true`. | Administrative active flag. SQL still permits orders and events for an inactive machine. |

## production_orders

**Grain:** One production order assigned to one machine per row. **Primary key:** `order_id`.

| Column | PostgreSQL type | Current SQL rule | Meaning |
| --- | --- | --- | --- |
| `order_id` | `integer` | Generated identity; primary key (`pk_orders`). | Internal order identifier. |
| `order_code` | `varchar(6)` | Required; unique. | Human-readable order code; no format or nonblank check. |
| `machine_id` | `integer` | Required; foreign key (`fk_machines`) to `machines.machine_id`. | Assigned machine. |
| `product_code` | `varchar(20)` | Required. | Product identifier as text; no product master table or format check. |
| `planned_quantity` | `integer` | Required; greater than zero (`ck_planned_quantity`). | Target number of units. |
| `status` | `varchar(11)` | Required; default `PLANNED`; one of `PLANNED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` (`ck_status`). | Administrative order status; events do not automatically change it. |
| `planned_start_at` | `timestamptz` | Required. | Planned start instant. |
| `planned_end_at` | `timestamptz` | Required; later than `planned_start_at` (`ck_planned_end_at`). | Planned end instant; actual completion is not represented. |
| `created_at` | `timestamptz` | Required; defaults to `current_timestamp`. | Row creation time when default is used; caller may supply another value. |

The pair (`machine_id`, `order_id`) is also unique (`uq_machine_order`). As `order_id` is already unique, this does not add a business uniqueness rule; it provides a referenced key for the composite foreign key on events.

## machine_events

**Grain:** One recorded machine occurrence per row. **Primary key:** `event_id`.

| Column | PostgreSQL type | Current SQL rule | Meaning |
| --- | --- | --- | --- |
| `event_id` | `integer` | Generated identity; primary key (`pk_events`). | Database row identifier, distinct from the source deduplication key. |
| `source_event_id` | `varchar(20)` | Required; globally unique (`uq_source_event_id`). | Stable producer ID across retries. The loader skips an insert when this ID already exists. |
| `machine_id` | `integer` | Required; foreign key (`fk_machine`) to `machines.machine_id`. | Machine associated with the event. |
| `order_id` | `integer` | Nullable for nonproduction events; required for production reports after 004. With `machine_id`, foreign key (`fk_machine_order`) to `production_orders(machine_id, order_id)` when supplied. | Related order if known; SQL permits NULL for starts, stops and faults; 004 requires an order for production reports. |
| `event_type` | `varchar(20)` | Required; one of `MACHINE_STARTED`, `MACHINE_STOPPED`, `PRODUCTION_REPORTED`, `FAULT_DETECTED` (`ck_event`). | Kind of occurrence. |
| `event_at` | `timestamptz` | Required. | Occurrence time; no ordering or future-time check. |
| `units_produced` | `integer` | Required; default `0`; greater than zero for production reports after 004, exactly zero otherwise (`ck_units`). | Incremental unit count; zero-unit production reports are rejected after 004. |
| `created_at` | `timestamptz` | Required; defaults to `current_timestamp`. | Row creation time when default is used, potentially later than `event_at`. |

## Relationships and time semantics

- One machine can have many orders and events. Each order has exactly one machine.
- An event has exactly one existing machine and may have one order. When `order_id` is supplied, the composite foreign key requires that order to belong to the event's machine. With `order_id = NULL`, only the machine relationship applies.
- `timestamptz` represents an instant; PostgreSQL displays it in the session time zone. The original source offset is not retained in this schema. The simulator emits UTC offsets (`+00:00`). The JSONL reader requires an explicit offset but accepts other offsets and preserves the input string until loading.

## Implemented derived total and remaining decisions

- File 004 requires an order and a positive increment for `PRODUCTION_REPORTED`.
- The [order summary view](../sql/005_create_order_production_summary_view.sql) is the source for produced totals: it sums accepted production increments and returns zero for orders without reports. The `production_orders` table has no separate produced-total column.
- Source IDs and duplicate skipping are implemented: the loader uses `ON CONFLICT (source_event_id) DO NOTHING` without modifying the existing row.
- Machine-state sequences are validated by the single-machine simulator, not against historical database events during ingestion.
- Still to implement: order status validation at report time; historical state validation; changed-payload conflict detection; late-event handling; and a policy for inactive machines.

See the companion [event contract](event_contract.md) for detailed behavior and the distinction between implemented and planned rules.


## JSONL-to-database mapping

The [reader](../src/ingestion/read_events.py) requires all six JSONL keys: `source_event_id`, `machine_code`, `order_code`, `event_type`, `event_at` and `units_produced`. The first five must be nonblank strings; units must have Python type `int` (booleans are rejected). It checks supported event types, parseable timestamps with offsets and positive/zero unit rules.

The [loader](../src/ingestion/db.py) resolves `machine_code` and `order_code` through a join of registered machines and their orders. The resulting `machine_id` and `order_id` are written with source ID, type, occurrence time and units. A missing pair raises an error; the transaction for that run is rolled back. Source ID uniqueness is global, so producers must coordinate IDs across all machines and sources. IDs from the fixed simulator repeat intentionally on replay.

SQL allows an absent order for nonproduction events. The current JSONL application path is stricter: every event must have a nonblank order code and a registered matching pair. Text length and PostgreSQL integer range limits remain enforced by the database rather than fully prevalidated by the reader. SQL `NOT NULL` alone also does not reject blank source IDs; the reader supplies that check.

The schema is applied manually from creation files during this development stage. Recreating only `machine_events` does not recreate dependent views: apply 003, then 004, then 005 after the appropriate disposable-database rebuild. See [TESTING.md](../TESTING.md), including the known view-fixture gap.
