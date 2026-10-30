-- 004: Replace the initial ck_units from 003 with the approved event payload rule.
-- Production reports need an order and a positive increment; all other events
-- must carry zero units. Existing rows must satisfy this rule before it is added.
-- This migration keeps the constraint name so existing tests still identify ck_units.
alter table machine_events
    drop constraint ck_units,
    add constraint ck_units check (
        (event_type = 'PRODUCTION_REPORTED' and order_id is not null and units_produced > 0)
        or
        (event_type <> 'PRODUCTION_REPORTED' and units_produced = 0)
        );
