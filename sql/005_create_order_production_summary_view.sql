create view vw_order_production_summary as
select o.order_id, o.order_code, o.machine_id, o.planned_quantity, coalesce(sum(e.units_produced),0) as total_units_produced 
from production_orders o
left join machine_events e
	on o.order_id = e.order_id
	and e.event_type = 'PRODUCTION_REPORTED'
group by o.order_id;