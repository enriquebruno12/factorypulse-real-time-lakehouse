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

select * from production_orders;

select * from machines;

insert into production_orders(order_code, machine_id, product_code, planned_quantity, planned_start_at, planned_end_at)
	values
	('PO-001',1,'P-100',5000,'2026-10-16','2026-10-22'),
	('PO-002',1,'P-200',2500,'2026-10-18','2026-10-25'),
	('PO-003',2,'P-300',8000,'2026-10-20','2026-10-27');

select order_code, planned_quantity, produced_quantity, status, created_at
from production_orders;

insert into production_orders(order_code, machine_id, product_code, planned_quantity, produced_quantity, planned_start_at, planned_end_at)
	values
	('PO-004',2,'P-500',5000, 6000,'2026-10-20','2026-10-20');

alter table production_orders
add constraint uq_machine_order
	unique (machine_id,order_id);
