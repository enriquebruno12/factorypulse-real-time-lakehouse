create table if not exists machine_events (
	event_id integer generated always as identity,
	machine_id integer not null,
	order_id integer,
	event_type varchar(20) not null,
	event_at timestamptz not null,
	units_produced integer not null default 0,
	created_at timestamptz not null default current_timestamp,
	
	constraint pk_events primary key (event_id),
	constraint fk_machine foreign key (machine_id)
		references machines(machine_id),
	constraint fk_machine_order foreign key (machine_id,order_id)
		references production_orders (machine_id,order_id),
	constraint ck_event check (event_type in ('MACHINE_STARTED','MACHINE_STOPPED','PRODUCTION_REPORTED','FAULT_DETECTED')),
	constraint ck_units check (
		(event_type = 'PRODUCTION_REPORTED' and units_produced >= 0) 
		or
		(event_type <> 'PRODUCTION_REPORTED' and units_produced = 0)
	)
);

select * from machine_events;