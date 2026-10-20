alter table machine_events
	drop constraint ck_units,
	add constraint ck_units check (
		(event_type = 'PRODUCTION_REPORTED' and order_id is not null and units_produced > 0) 
		or
		(event_type <> 'PRODUCTION_REPORTED' and units_produced = 0)
		);

