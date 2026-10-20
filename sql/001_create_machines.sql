-- 001: Register machines before creating orders or events.
-- machine_id is an internal key; machine_code is the unique business-facing code.
create table if not exists machines (
	machine_id integer generated always as identity,
	machine_code varchar(20) not null ,
	machine_name varchar(100) not null,
	installed_at date,
	is_active boolean not null default true,
	-- Each machine has one stable internal identifier.
	constraint pk_machine primary key (machine_id),
	-- Prevent two machines from sharing the same readable code.
	constraint uq_machine_code unique (machine_code)
);