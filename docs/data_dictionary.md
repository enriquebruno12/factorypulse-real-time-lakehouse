# FactoryPulse — Operational Data Dictionary

**Status:** Proposed for review · **Version:** 0.1 · **Date:** 20 October 2026  
**Scope:** Current PostgreSQL operational schema for a synthetic manufacturing scenario.  
**SQL sources:** [machines](../sql/001_create_machines.sql), [production orders](../sql/002_create_production_orders.sql), [machine events](../sql/003_create_machine_events.sql), [production-report rule](../sql/004_enforce_production_report_payload.sql), and [order summary view](../sql/005_create_order_production_summary_view.sql).

This dictionary separates rules already enforced by the SQL from business decisions proposed for the future simulator. It does not describe an actual factory.

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
| `event_id` | `integer` | Generated identity; primary key (`pk_events`). | Database row identifier, not a source event ID or deduplication key. |
| `machine_id` | `integer` | Required; foreign key (`fk_machine`) to `machines.machine_id`. | Machine associated with the event. |
| `order_id` | `integer` | Nullable for nonproduction events; required for production reports after 004. With `machine_id`, foreign key (`fk_machine_order`) to `production_orders(machine_id, order_id)` when supplied. | Related order if known; SQL permits NULL for starts, stops and faults; 004 requires an order for production reports. |
| `event_type` | `varchar(20)` | Required; one of `MACHINE_STARTED`, `MACHINE_STOPPED`, `PRODUCTION_REPORTED`, `FAULT_DETECTED` (`ck_event`). | Kind of occurrence. |
| `event_at` | `timestamptz` | Required. | Occurrence time; no ordering or future-time check. |
| `units_produced` | `integer` | Required; default `0`; greater than zero for production reports after 004, exactly zero otherwise (`ck_units`). | Incremental unit count; zero-unit production reports are rejected after 004. |
| `created_at` | `timestamptz` | Required; defaults to `current_timestamp`. | Row creation time when default is used, potentially later than `event_at`. |

## Relationships and time semantics

- One machine can have many orders and events. Each order has exactly one machine.
- An event has exactly one existing machine and may have one order. When `order_id` is supplied, the composite foreign key requires that order to belong to the event's machine. With `order_id = NULL`, only the machine relationship applies.
- `timestamptz` represents an instant; PostgreSQL displays it in the session time zone. The original source offset is not retained in this schema. UTC is the proposed simulator convention.

## Implemented derived total and remaining decisions

- File 004 requires an order and a positive increment for `PRODUCTION_REPORTED`.
- The [order summary view](../sql/005_create_order_production_summary_view.sql) is the source for produced totals: it sums accepted production increments and returns zero for orders without reports. The `production_orders` table has no separate produced-total column.
- Still to implement: order status validation at report time; machine-state sequences; stable source event IDs, duplicate and late-event handling; and a policy for inactive machines.

See the companion [event contract](event_contract.md) for detailed behavior and the distinction between implemented and planned rules.

