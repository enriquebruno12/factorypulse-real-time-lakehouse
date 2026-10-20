# FactoryPulse — Machine Event Contract

**Status:** Proposed for review · **Version:** 0.1 · **Date:** 20 October 2026  
**Scope:** Synthetic machine events for the next project phase. **SQL sources:** [machine events](../sql/003_create_machine_events.sql), [production-report rule](../sql/004_enforce_production_report_payload.sql), and [order summary view](../sql/005_create_order_production_summary_view.sql). See the [companion data dictionary](data_dictionary.md) for every column.

This contract distinguishes current SQL guarantees from proposed simulator rules. A real manufacturer would approve the proposals with operations and analytics stakeholders.

## Common event fields

| Field | Current SQL behavior | Proposed meaning |
| --- | --- | --- |
| `event_id` | Generated integer primary key. | Database row ID, not the source event ID. |
| `machine_id` | Required; existing machine. | Machine that produced the event. |
| `order_id` | Required for production reports after 004; optional otherwise. If supplied, must belong to `machine_id`. | Present when the occurrence relates to an order. |
| `event_type` | One of the four types below. | Action or report type. |
| `event_at` | Required `timestamptz`; no timing validation. | Occurrence instant, generated in UTC. |
| `units_produced` | Required, default `0`; constrained by event type. | Additional units, never a cumulative meter reading. |
| `created_at` | Required; defaults to `current_timestamp`. | Database row time when default is used; may differ from `event_at`. |

There is no source event ID, fault code, severity or machine-state column in the current table.

## MACHINE_STARTED

**Meaning:** Machine begins a running interval. **Current SQL:** Known machine, required time, optional order, `units_produced = 0`. **Proposed simulator rule:** Emit after initial idle/stopped state or recovery. An order may be absent during warm-up. Avoid repeated starts without an intervening stop or explicit recovery decision. **Example:** machine 1 starts for order 1 at `2026-01-15T08:00:00Z`.

## MACHINE_STOPPED

**Meaning:** Machine ends a running interval. **Current SQL:** Optional order, `units_produced = 0`. **Proposed simulator rule:** Normally follow a start. An order may be absent when stopping outside production. Record a fault separately when one caused the stop. **Example:** machine 1 stops for order 1 at `2026-01-15T10:00:00Z`.

## PRODUCTION_REPORTED

**Meaning:** Additional good units produced for one order since the previous report; 30 and 45 represent 75 units total. **Current SQL after 004:** `units_produced > 0` and `order_id IS NOT NULL`; the order must match the machine. **Planned simulator rule:** Require order status `IN_PROGRESS` and a running machine at `event_at`. These state conditions are not yet enforced. **Example:** machine 1 reports 30 additional units for order 1 at `2026-01-15T08:30:00Z`.

## FAULT_DETECTED

**Meaning:** A fault signal was observed; code, severity and cause are not recorded. **Current SQL:** Optional order, `units_produced = 0`. **Proposed simulator rule:** Allow a fault with or without an order. In the first simulator version, emit `MACHINE_STOPPED` if the fault interrupts production and require a later `MACHINE_STARTED` before more production. SQL does not enforce this sequence. **Example:** machine 1 reports a fault for order 1 at `2026-01-15T09:00:00Z`.

## Illustrative sequence

All times are UTC. These are examples, not rows already inserted into the project.

| `event_at` | `event_type` | Machine | Order | Units | Interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| 08:00 | `MACHINE_STARTED` | 1 | 1 | 0 | Running interval starts. |
| 08:30 | `PRODUCTION_REPORTED` | 1 | 1 | 30 | 30 additional units. |
| 08:45 | `PRODUCTION_REPORTED` | 1 | 1 | 45 | 75 reported units in total. |
| 09:00 | `FAULT_DETECTED` | 1 | 1 | 0 | Fault observed. |
| 09:01 | `MACHINE_STOPPED` | 1 | 1 | 0 | Running interval ends. |
| 09:30 | `MACHINE_STARTED` | 1 | 1 | 0 | Work resumes after recovery. |

The [summary view](../sql/005_create_order_production_summary_view.sql) would show 75 units for this order. The database does **not** automatically set `production_orders.produced_quantity` to 75.

## Validation and quality boundaries

| Rule | Enforced by current SQL? | Next-stage owner |
| --- | --- | --- |
| Known event type and machine; matching machine/order when order supplied | Yes | Database constraints; producer can validate early. |
| Zero units for nonproduction; positive units and an order for production | Yes | Database constraints. |
| Order status `IN_PROGRESS` and running machine for production report | No | Simulator/application validation or future database logic. |
| Valid start/stop/fault sequence; no output while stopped | No | Simulator state machine and downstream checks. |
| Stable source event identity and deduplication | No | Future raw event envelope and pipeline. |
| Late, duplicate or invalid input classification | No | Preserve in raw stream or staging and quarantine before curated data; current SQL rejects many invalid rows. |
| Event-derived order total | Yes, in the summary view | Decide how to retire or reconcile the separate stored `produced_quantity` field. |

## Decisions to review before simulation

1. Implemented: every production report has an order and at least one unit (004).
2. Implemented for reporting: accepted event increments define the total in the summary view (005); the stored `produced_quantity` field remains unresolved.
3. Planned simulator behavior: a production-interrupting fault is followed by a stop; production resumes only after a later start. SQL does not yet enforce this sequence.
4. Decide what stable source event ID identifies duplicates.
5. Decide how late an event may arrive and which records should be quarantined.

