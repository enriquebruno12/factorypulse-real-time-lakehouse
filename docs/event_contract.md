# FactoryPulse — Machine Event Contract

**Status:** Current local contract with open decisions · **Version:** 0.2 · **Date:** 30 October 2026  
**Scope:** Synthetic machine events generated, read and loaded locally into PostgreSQL. **SQL sources:** [machine events](../sql/003_create_machine_events.sql), [production-report rule](../sql/004_enforce_production_report_payload.sql), and [order summary view](../sql/005_create_order_production_summary_view.sql). See the [companion data dictionary](data_dictionary.md) for every column.

This contract distinguishes SQL guarantees, simulator validation and JSONL ingestion behavior. The local pipeline is implemented for a fixed synthetic scenario; future operational policies would require agreement with manufacturing and analytics stakeholders.

## Common event fields

| Field | Current SQL behavior | Meaning |
| --- | --- | --- |
| `event_id` | Generated integer primary key. | Database row ID, distinct from the source event ID. |
| `source_event_id` | Required unique `varchar(20)` (`uq_source_event_id`). | Stable producer ID, globally unique across sources and machines; duplicate inserts are skipped by the loader. |
| `machine_id` | Required; existing machine. | Machine that produced the event. |
| `order_id` | Required for production reports after 004; optional otherwise. If supplied, must belong to `machine_id`. | Present when the occurrence relates to an order. |
| `event_type` | One of the four types below. | Action or report type. |
| `event_at` | Required `timestamptz`; no timing validation. | Occurrence instant, generated in UTC. |
| `units_produced` | Required, default `0`; constrained by event type. | Additional units, never a cumulative meter reading. |
| `created_at` | Required; defaults to `current_timestamp`. | Database row time when default is used; may differ from `event_at`. |

There is no fault code, severity or persisted machine-state column in the current table. `source_event_id` is now stored and is the loader's conflict target.

## MACHINE_STARTED

**Meaning:** Machine begins a running interval. **Current SQL:** Known machine, required time, optional order, `units_produced = 0`. **Implemented simulator rule:** Accept only from `STOPPED`; repeated starts and direct starts from `FAULTED` are rejected. SQL permits an absent order during warm-up, but the current JSONL reader/loader requires a nonblank matching order code. **Example:** machine 1 starts for order 1 at `2026-01-15T08:00:00Z`.

## MACHINE_STOPPED

**Meaning:** Machine ends a running interval. **Current SQL:** Optional order, `units_produced = 0`. **Implemented simulator rule:** Accept from `RUNNING` or `FAULTED`, then set `STOPPED`. Repeated stops are rejected. SQL permits an absent order; the current JSONL path requires one. Record a fault separately when one caused the stop. **Example:** machine 1 stops for order 1 at `2026-01-15T10:00:00Z`.

## PRODUCTION_REPORTED

**Meaning:** Additional good units produced for one order since the previous report; 30 and 45 represent 75 units total. **Current SQL after 004:** `units_produced > 0` and `order_id IS NOT NULL`; the order must match the machine. **Implemented simulator rule:** Accept production only while the scenario is `RUNNING`. **Still planned:** check order status `IN_PROGRESS` at report time; neither the current reader nor loader enforces historical machine state. **Example:** machine 1 reports 30 additional units for order 1 at `2026-01-15T08:30:00Z`.

## FAULT_DETECTED

**Meaning:** A fault signal was observed; code, severity and cause are not recorded. **Current SQL:** Optional order, `units_produced = 0`. **Implemented simulator rule:** Accept only from `RUNNING`, then set `FAULTED`. A stop must precede a restart; production cannot resume before that restart. SQL does not enforce this sequence. The current JSONL path requires an order code even though SQL allows NULL for this event type. **Example:** machine 1 reports a fault for order 1 at `2026-01-15T09:00:00Z`.

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

The [summary view](../sql/005_create_order_production_summary_view.sql) would show 75 units for this order. The total is calculated from events rather than stored in `production_orders`.

## Validation and quality boundaries

| Rule | Enforced by current SQL? | Current application / remaining owner |
| --- | --- | --- |
| Known event type and machine; matching machine/order when order supplied | Yes | Database constraints; producer can validate early. |
| Zero units for nonproduction; positive units and an order for production | Yes | Database constraints. |
| Order status `IN_PROGRESS` at report time | No | Planned; administrative order status is not automatically updated. |
| Valid start/stop/fault sequence; no output while stopped | No | Implemented in the fixed simulator; historical ingestion-state checks remain planned. |
| Stable source event identity and deduplication | Yes: required unique source ID | The loader skips duplicates with `ON CONFLICT`; payload differences are not checked. |
| Late or invalid input classification | No dedicated classification | The reader fails fast; the loader rolls back on unhandled errors. Quarantine/raw retention and late-event policy remain planned. |
| Event-derived order total | Yes, in the summary view | Use this view for reporting; no duplicate total is stored in `production_orders`. |

## Implemented decisions and remaining work

1. Implemented: every production report has an order and at least one unit (004).
2. Implemented for reporting: accepted event increments define the total in the summary view (005); `production_orders` has no duplicate total field.
3. Implemented in the simulator: a fault changes the scenario state to `FAULTED`; a stop is required before restart and further production. SQL and the ingestion loader do not validate historical sequences.
4. Implemented: `source_event_id` is globally unique and stable across retries. Replays are ignored; changed-payload reuse remains an open policy.
5. Still to decide: late-arrival windows, quarantine rules, multi-source ID generation and historical state validation.


## Incoming JSONL envelope

The current reader requires the following six keys on every input record. Extra keys are not currently rejected.

| JSONL field | Reader check | Loader mapping |
| --- | --- | --- |
| `source_event_id` | Nonblank string | Stored as required unique `source_event_id`; database limit is 20 characters. |
| `machine_code` | Nonblank string | Looked up in `machines` and matched to the order. |
| `order_code` | Nonblank string for every event | Looked up in `production_orders` with the machine; no match raises an error. |
| `event_type` | Nonblank string; one of the four contract values | Stored as event type. |
| `event_at` | Nonblank string; parsed with `datetime.fromisoformat`; explicit offset required | Original string is passed to PostgreSQL `timestamptz`. |
| `units_produced` | Python `int`, excluding booleans; positive for production reports, zero otherwise | Stored as incremental units. |

The reader validates each line independently. It does not track machine state, reorder events or normalize whitespace in codes. The simulator's `offset_minutes` is internal configuration and is removed from emitted payloads. The reader does not require a specific prefix for source IDs; the database's length limit is enforced on insertion.

## Current simulator state model

The single-machine scenario starts at `STOPPED`. Offsets must be nonnegative and strictly increasing; the first may be zero.

| Event | Allowed state before event | State after event |
| --- | --- | --- |
| `MACHINE_STARTED` | `STOPPED` | `RUNNING` |
| `PRODUCTION_REPORTED` | `RUNNING` | `RUNNING` |
| `FAULT_DETECTED` | `RUNNING` | `FAULTED` |
| `MACHINE_STOPPED` | `RUNNING`, `FAULTED` | `STOPPED` |

The committed [sample](../events.jsonl) contains seven events on 21 October 2026 for `M-001` / `PO-001`, from 08:00 to 10:30 UTC. Two reports contribute 25 and 10 units, for 35 total. Its source IDs `EVT-001` through `EVT-007` intentionally remain stable across reruns. Multi-machine state tracking and run/source-aware ID generation are future work.

## Ingestion transaction and duplicate policy

The [loader](../src/ingestion/db.py) reads the fixed local file, resolves IDs and inserts all accepted records through one PostgreSQL connection. A normal context exit commits the transaction; an exception escaping that context rolls back the run. The final inserted/skipped counters are printed after successful exit.

A new source ID produces a new row and returns `event_id`. An existing ID produces no returned row and is counted as skipped. The existing payload is retained without comparison, so this is replay protection rather than detection of conflicting content. Other constraint violations still fail the run. The local demonstration produced 7 inserted / 0 skipped and then 0 inserted / 7 skipped. An independent persisted count/total check and automated database integration tests remain pending. See [TESTING.md](../TESTING.md).
