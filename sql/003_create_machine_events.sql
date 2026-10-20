-- 003: Record machine occurrences. Apply 004 afterward for the final
-- production-report rule; the initial ck_units below permits zero-unit reports.
create table if not exists machine_events (
	event_id integer generated always as identity,
	machine_id integer not null,
	-- Optional for start, stop and fault events; 004 requires it for production reports.
	order_id integer,
	event_type varchar(20) not null,
	event_at timestamptz not null,
	units_produced integer not null default 0,
	created_at timestamptz not null default current_timestamp,
	
	constraint pk_events primary key (event_id),
	-- Every event must reference a registered machine.
	constraint fk_machine foreign key (machine_id)
		references machines(machine_id),
	-- If an order is supplied, it must belong to this same machine.
	constraint fk_machine_order foreign key (machine_id,order_id)
		references production_orders (machine_id,order_id),
	-- Reject event types outside the supported four.
	constraint ck_event check (event_type in ('MACHINE_STARTED','MACHINE_STOPPED','PRODUCTION_REPORTED','FAULT_DETECTED')),
	-- Starts, stops and faults carry zero units; 004 tightens production reports.
	constraint ck_units check (
		(event_type = 'PRODUCTION_REPORTED' and units_produced >= 0) 
		or
		(event_type <> 'PRODUCTION_REPORTED' and units_produced = 0)
	)
);