-- Optional demo data. Run once against a fresh, disposable FactoryPulse database.
-- Never run this file as part of schema setup or against a production database.
BEGIN;

-- Two registered machines for the example factory.
INSERT INTO machines (machine_code, machine_name, installed_at)
VALUES
    ('M-001', 'Assembly Line A', DATE '2024-03-15'),
    ('M-002', 'Packaging Line B', DATE '2024-06-10');

-- Each order uses a machine code lookup rather than assuming identity values.
INSERT INTO production_orders (
    order_code, machine_id, product_code, planned_quantity,
    planned_start_at, planned_end_at
)
VALUES
    (
        'PO-001',
        (SELECT machine_id FROM machines WHERE machine_code = 'M-001'),
        'P-100', 500,
        TIMESTAMPTZ '2026-10-19 08:00:00+00',
        TIMESTAMPTZ '2026-10-19 16:00:00+00'
    ),
    (
        'PO-002',
        (SELECT machine_id FROM machines WHERE machine_code = 'M-002'),
        'P-200', 300,
        TIMESTAMPTZ '2026-10-19 09:00:00+00',
        TIMESTAMPTZ '2026-10-19 17:00:00+00'
    );

INSERT INTO machine_events (
    machine_id, order_id, event_type, event_at, units_produced
)
-- Start assembly before its production increment.
SELECT m.machine_id, o.order_id, 'MACHINE_STARTED',
       TIMESTAMPTZ '2026-10-19 08:00:00+00', 0
FROM machines AS m
JOIN production_orders AS o ON o.machine_id = m.machine_id
WHERE m.machine_code = 'M-001' AND o.order_code = 'PO-001';

INSERT INTO machine_events (
    machine_id, order_id, event_type, event_at, units_produced
)
-- Report 120 additional units for the assembly order.
SELECT m.machine_id, o.order_id, 'PRODUCTION_REPORTED',
       TIMESTAMPTZ '2026-10-19 09:00:00+00', 120
FROM machines AS m
JOIN production_orders AS o ON o.machine_id = m.machine_id
WHERE m.machine_code = 'M-001' AND o.order_code = 'PO-001';

INSERT INTO machine_events (
    machine_id, order_id, event_type, event_at, units_produced
)
-- Record a packaging fault; the schema does not yet enforce event sequence.
SELECT m.machine_id, o.order_id, 'FAULT_DETECTED',
       TIMESTAMPTZ '2026-10-19 10:00:00+00', 0
FROM machines AS m
JOIN production_orders AS o ON o.machine_id = m.machine_id
WHERE m.machine_code = 'M-002' AND o.order_code = 'PO-002';

COMMIT;
