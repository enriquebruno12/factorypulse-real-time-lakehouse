-- 005: One row per production order, including orders without events.
-- The event-derived total sums production increments instead of storing a
-- duplicate counter in production_orders.
create view vw_order_production_summary as
-- Group by the order key so each order appears once.
select o.order_id, o.order_code, o.machine_id, o.planned_quantity, coalesce(sum(e.units_produced),0) as total_units_produced
from production_orders o
-- Keep orders with no matching production report.
left join machine_events e
    on o.order_id = e.order_id
    -- Filter in ON so orders with no production remain in the result.
    and e.event_type = 'PRODUCTION_REPORTED'
group by o.order_id;
