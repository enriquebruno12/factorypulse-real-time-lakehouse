-- Run after 001-005 in a disposable database. Expected result:
-- V9001 = 35 units (25 + 10); V9002 = 0 units (no production events).
-- This is a visual result check; the query does not raise on wrong totals.
-- Known setup gap: these event inserts still omit the required source_event_id.
-- Update those fixtures before running this check against the current schema.
BEGIN;

-- Arrange one machine and two orders: one producing, one with no events.
INSERT INTO machines (machine_code, machine_name)
VALUES ('VW-TEST-1', 'View test machine');

INSERT INTO production_orders (
    order_code, machine_id, product_code, planned_quantity,
    status, planned_start_at, planned_end_at
)
SELECT
    'V9001', machine_id, 'TEST-P', 100,
    'IN_PROGRESS',
    TIMESTAMPTZ '2026-10-19 08:00:00+00',
    TIMESTAMPTZ '2026-10-19 16:00:00+00'
FROM machines
WHERE machine_code = 'VW-TEST-1';

INSERT INTO production_orders (
    order_code, machine_id, product_code, planned_quantity,
    planned_start_at, planned_end_at
)
SELECT
    'V9002', machine_id, 'TEST-P', 100,
    TIMESTAMPTZ '2026-10-19 08:00:00+00',
    TIMESTAMPTZ '2026-10-19 16:00:00+00'
FROM machines
WHERE machine_code = 'VW-TEST-1';

INSERT INTO machine_events (
    machine_id, order_id, source_event_id, event_type, event_at, units_produced
)
-- A state event contributes no production units.
SELECT machine_id, order_id, 'DEMO-EVT-999', 'MACHINE_STARTED',
       TIMESTAMPTZ '2026-10-19 08:00:00+00', 0
FROM production_orders
WHERE order_code = 'V9001';

INSERT INTO machine_events (
    machine_id, order_id, source_event_id, event_type, event_at, units_produced
)
-- First incremental report: 25 units.
SELECT machine_id, order_id, 'DEMO-EVT-998', 'PRODUCTION_REPORTED',
       TIMESTAMPTZ '2026-10-19 09:00:00+00', 25
FROM production_orders
WHERE order_code = 'V9001';

INSERT INTO machine_events (
    machine_id, order_id, source_event_id, event_type, event_at, units_produced
)
-- Second incremental report: 10 more units, for a total of 35.
SELECT machine_id, order_id, 'DEMO-EVT-997', 'PRODUCTION_REPORTED',
       TIMESTAMPTZ '2026-10-19 10:00:00+00', 10
FROM production_orders
WHERE order_code = 'V9001';

-- Inspect both orders; LEFT JOIN plus COALESCE keeps V9002 at zero.
-- These rows are inspected manually; this script does not assert the totals.
SELECT order_code, total_units_produced
FROM vw_order_production_summary
WHERE order_code IN ('V9001', 'V9002')
ORDER BY order_code;

-- Discard test rows while leaving the previously created view intact.
ROLLBACK;
