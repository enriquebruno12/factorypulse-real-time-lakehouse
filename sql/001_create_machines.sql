create table if not exists machines (
	machine_id integer generated always as identity,
	machine_code varchar(20) not null ,
	machine_name varchar(100) not null,
	installed_at date,
	is_active boolean not null default true,
	constraint pk_machine primary key (machine_id),
	constraint uq_machine_code unique (machine_code)
);