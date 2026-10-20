BEGIN;

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
    machine_id, order_id, event_type, event_at, units_produced
)
SELECT machine_id, order_id, 'MACHINE_STARTED',
       TIMESTAMPTZ '2026-10-19 08:00:00+00', 0
FROM production_orders
WHERE order_code = 'V9001';

INSERT INTO machine_events (
    machine_id, order_id, event_type, event_at, units_produced
)
SELECT machine_id, order_id, 'PRODUCTION_REPORTED',
       TIMESTAMPTZ '2026-10-19 09:00:00+00', 25
FROM production_orders
WHERE order_code = 'V9001';

INSERT INTO machine_events (
    machine_id, order_id, event_type, event_at, units_produced
)
SELECT machine_id, order_id, 'PRODUCTION_REPORTED',
       TIMESTAMPTZ '2026-10-19 10:00:00+00', 10
FROM production_orders
WHERE order_code = 'V9001';

SELECT order_code, total_units_produced
FROM vw_order_production_summary
WHERE order_code IN ('V9001', 'V9002')
ORDER BY order_code;

ROLLBACK;