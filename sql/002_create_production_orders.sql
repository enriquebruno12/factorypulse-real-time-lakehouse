-- 002: Create production orders after machines.
-- Every order belongs to one machine and has a positive target and valid schedule.
-- Production totals are derived from machine_events by the view in 005.
create table if not exists production_orders(
    order_id integer generated always as identity,
    order_code varchar(6) not null unique,
    machine_id integer not null,
    product_code varchar(20) not null,
    -- Planned quantity is a target; actual production comes from machine events.
    planned_quantity integer not null,
    status varchar(11) not null default 'PLANNED',
    planned_start_at timestamptz not null,
    planned_end_at timestamptz not null,
    created_at timestamptz not null default current_timestamp,

    constraint pk_orders primary key (order_id),
    -- Do not assign an order to a machine that does not exist.
    constraint fk_machines foreign key (machine_id)
        references machines(machine_id),
    -- A production plan must target at least one unit.
    constraint ck_planned_quantity check (planned_quantity > 0),
    -- Restrict the administrative lifecycle to known status values.
    constraint ck_status check (status in ('PLANNED','IN_PROGRESS','COMPLETED','CANCELLED')),
    -- The planned end must occur after the planned start.
    constraint ck_planned_end_at check (planned_end_at  > planned_start_at),
    -- This pair is referenced by the composite foreign key in machine_events.
    -- order_id is already unique; this does not add another business key.
    constraint uq_machine_order unique (machine_id,order_id)

);
