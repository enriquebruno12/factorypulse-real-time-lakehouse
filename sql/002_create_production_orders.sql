create table if not exists production_orders(
	order_id integer generated always as identity,
	order_code varchar(6) not null unique,
	machine_id integer not null,
	product_code varchar(20) not null,
	planned_quantity integer not null,
	produced_quantity integer not null default 0,
	status varchar(11) not null default 'PLANNED',
	planned_start_at timestamptz not null,
	planned_end_at timestamptz not null,
	created_at timestamptz not null default current_timestamp,
	
	constraint pk_orders primary key (order_id),
	constraint fk_machines foreign key (machine_id) 
		references machines(machine_id),
	constraint ck_planned_quantity check (planned_quantity > 0),
	constraint ck_produced_quantity check (produced_quantity >= 0),
	constraint ck_status check (status in ('PLANNED','IN_PROGRESS','COMPLETED','CANCELLED')),
	constraint ck_planned_end_at check (planned_end_at  > planned_start_at)
	
);
