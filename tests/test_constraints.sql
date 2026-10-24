-- Run only against a disposable database after sql/001, 002, 003 and 004.
-- psql -v ON_ERROR_STOP=1 -f tests/test_constraints.sql
-- Each negative case expects a specific constraint, not just any error.
-- The inner BEGIN/EXCEPTION blocks isolate expected failures so later cases run.
-- The transaction is rolled back, so this file leaves no test rows behind.

BEGIN;

-- Dollar quoting delimits this PL/pgSQL test block; it is not a transaction.
DO $test$
DECLARE
    machine_a integer;
    machine_b integer;
    order_a integer;
    actual_constraint text;
BEGIN
    -- Arrange two machines and one order for the positive and negative cases.
    INSERT INTO machines (machine_code, machine_name)
    VALUES ('TEST-M-1', 'Test machine one')
    RETURNING machine_id INTO machine_a;

    INSERT INTO machines (machine_code, machine_name)
    VALUES ('TEST-M-2', 'Test machine two')
    RETURNING machine_id INTO machine_b;

    INSERT INTO production_orders (
        order_code, machine_id, product_code, planned_quantity,
        planned_start_at, planned_end_at
    )
    VALUES (
        'T-001', machine_a, 'TEST-P', 100,
        TIMESTAMPTZ '2026-10-19 08:00:00+00',
        TIMESTAMPTZ '2026-10-19 16:00:00+00'
    )
    RETURNING order_id INTO order_a;

    -- Positive control: valid machine/order pair and positive production increment.
    INSERT INTO machine_events (
        machine_id, order_id, event_type, event_at, units_produced
    )
    VALUES (
        machine_a, order_a, 'PRODUCTION_REPORTED',
        TIMESTAMPTZ '2026-10-19 09:00:00+00', 25
    );
    RAISE NOTICE 'PASS: valid machine, order and event';

    -- Test 01 / uq_machine_code: a machine code cannot be inserted twice.
    BEGIN
        INSERT INTO machines (machine_code, machine_name)
        VALUES ('TEST-M-1', 'Duplicate code');
        RAISE EXCEPTION 'FAIL: duplicate machine code was accepted';
    EXCEPTION WHEN unique_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'uq_machine_code' THEN
            RAISE EXCEPTION 'FAIL: expected uq_machine_code, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: duplicate machine code rejected';
    END;

    -- Test 02 / ck_planned_quantity: an order cannot target zero units.
    BEGIN
        INSERT INTO production_orders (
            order_code, machine_id, product_code, planned_quantity,
            planned_start_at, planned_end_at
        )
        VALUES (
            'T-002', machine_a, 'TEST-P', 0,
            TIMESTAMPTZ '2026-10-19 08:00:00+00',
            TIMESTAMPTZ '2026-10-19 16:00:00+00'
        );
        RAISE EXCEPTION 'FAIL: zero planned quantity was accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_planned_quantity' THEN
            RAISE EXCEPTION 'FAIL: expected ck_planned_quantity, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: zero planned quantity rejected';
    END;

    -- Test 03 / ck_planned_end_at: planned end must be after planned start.
    BEGIN
        INSERT INTO production_orders (
            order_code, machine_id, product_code, planned_quantity,
            planned_start_at, planned_end_at
        )
        VALUES (
            'T-003', machine_a, 'TEST-P', 100,
            TIMESTAMPTZ '2026-10-19 16:00:00+00',
            TIMESTAMPTZ '2026-10-19 08:00:00+00'
        );
        RAISE EXCEPTION 'FAIL: invalid order schedule was accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_planned_end_at' THEN
            RAISE EXCEPTION 'FAIL: expected ck_planned_end_at, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: invalid order schedule rejected';
    END;

    -- Test 04 / ck_status: an unknown order status is not allowed.
    BEGIN
        INSERT INTO production_orders (
            order_code, machine_id, product_code, planned_quantity,
            status, planned_start_at, planned_end_at
        )
        VALUES (
            'T-004', machine_a, 'TEST-P', 100, 'UNKNOWN',
            TIMESTAMPTZ '2026-10-19 08:00:00+00',
            TIMESTAMPTZ '2026-10-19 16:00:00+00'
        );
        RAISE EXCEPTION 'FAIL: invalid order status was accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_status' THEN
            RAISE EXCEPTION 'FAIL: expected ck_status, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: invalid order status rejected';
    END;

    -- Test 05 / fk_machines: an order cannot reference a missing machine.
    BEGIN
        INSERT INTO production_orders (
            order_code, machine_id, product_code, planned_quantity,
            planned_start_at, planned_end_at
        )
        VALUES (
            'T-005', -1, 'TEST-P', 100,
            TIMESTAMPTZ '2026-10-19 08:00:00+00',
            TIMESTAMPTZ '2026-10-19 16:00:00+00'
        );
        RAISE EXCEPTION 'FAIL: missing machine was accepted';
    EXCEPTION WHEN foreign_key_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'fk_machines' THEN
            RAISE EXCEPTION 'FAIL: expected fk_machines, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: missing machine rejected';
    END;

    -- Test 06 / fk_machine_order: an event cannot link an order to the wrong machine.
    BEGIN
        INSERT INTO machine_events (
            machine_id, order_id, event_type, event_at, units_produced
        )
        VALUES (
            machine_b, order_a, 'MACHINE_STARTED',
            TIMESTAMPTZ '2026-10-19 09:00:00+00', 0
        );
        RAISE EXCEPTION 'FAIL: event with another machine''s order was accepted';
    EXCEPTION WHEN foreign_key_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'fk_machine_order' THEN
            RAISE EXCEPTION 'FAIL: expected fk_machine_order, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: machine/order mismatch rejected';
    END;

    -- Test 07 / ck_event: an unknown event type is not allowed.
    BEGIN
        INSERT INTO machine_events (
            machine_id, event_type, event_at, units_produced
        )
        VALUES (
            machine_a, 'UNKNOWN',
            TIMESTAMPTZ '2026-10-19 09:00:00+00', 0
        );
        RAISE EXCEPTION 'FAIL: unknown event type was accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_event' THEN
            RAISE EXCEPTION 'FAIL: expected ck_event, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: unknown event type rejected';
    END;

    -- Test 08 / ck_units: a stop event cannot report produced units.
    BEGIN
        INSERT INTO machine_events (
            machine_id, event_type, event_at, units_produced
        )
        VALUES (
            machine_a, 'MACHINE_STOPPED',
            TIMESTAMPTZ '2026-10-19 09:00:00+00', 10
        );
        RAISE EXCEPTION 'FAIL: stop event with units was accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_units' THEN
            RAISE EXCEPTION 'FAIL: expected ck_units, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: stop event with units rejected';
    END;

    -- Test 09 / ck_units: a production increment cannot be negative.
    BEGIN
        INSERT INTO machine_events (
            machine_id, order_id, event_type, event_at, units_produced
        )
        VALUES (
            machine_a, order_a, 'PRODUCTION_REPORTED',
            TIMESTAMPTZ '2026-10-19 09:00:00+00', -1
        );
        RAISE EXCEPTION 'FAIL: negative production increment was accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_units' THEN
            RAISE EXCEPTION 'FAIL: expected ck_units, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: negative production increment rejected';
    END;
    
    -- Test 10 / ck_units: a production report must identify its order (004).
    BEGIN
        INSERT INTO machine_events (
            machine_id, order_id, event_type, event_at, units_produced
        )
        VALUES (
            machine_a, null, 'PRODUCTION_REPORTED',
            TIMESTAMPTZ '2026-10-19 09:00:00+00', 100
        );
        RAISE EXCEPTION 'FAIL: event with no order accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_units' THEN
            RAISE EXCEPTION 'FAIL: expected ck_units, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: event with no order rejected';
    END;
    
    -- Test 11 / ck_units: a production report must contain at least one unit (004).
    BEGIN
        INSERT INTO machine_events (
            machine_id, order_id, event_type, event_at, units_produced
        )
        VALUES (
            machine_a, order_a, 'PRODUCTION_REPORTED',
            TIMESTAMPTZ '2026-10-19 09:00:00+00', 0
        );
        RAISE EXCEPTION 'FAIL: production reported with no units produced accepted';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint = CONSTRAINT_NAME;
        IF actual_constraint IS DISTINCT FROM 'ck_units' THEN
            RAISE EXCEPTION 'FAIL: expected ck_units, got %', actual_constraint;
        END IF;
        RAISE NOTICE 'PASS: production reported with no units produced rejected';
    END;
END;
$test$;

-- Remove all setup rows, including the successful inserts.
ROLLBACK;

