import os
import psycopg
from dotenv import load_dotenv
from read_events import read_events

# Resolve source business codes to the internal IDs of a matching machine/order pair.
def get_machine_order_ids(connection, machine_code, order_code):

    with connection.cursor() as cursor:
        cursor.execute(
            """
                select m.machine_id, po.order_id
                from machines m
                inner join production_orders po
                    on m.machine_id = po.machine_id
                where m.machine_code = %s
                and po.order_code = %s;
            """,
            (machine_code,order_code)
        )
        result = cursor.fetchone()

    # No matching pair produces None; the caller decides how to report it.
    return result


# Insert one event; an existing source ID is skipped without changing its payload.
def insert_event(connection, event, machine_id, order_id):

    with connection.cursor() as cursor:
        cursor.execute(
            """
                insert into machine_events (machine_id, order_id, source_event_id, event_type, event_at, units_produced)
                values(%s,%s,%s,%s,%s,%s)
                on conflict (source_event_id) do nothing
                returning event_id;
            """,
            (machine_id, order_id,event['source_event_id'], event['event_type'],event['event_at'],event['units_produced'])
        )

        # RETURNING yields a row only when PostgreSQL actually inserted an event.
        event_id = cursor.fetchone()

        if event_id is None:
            result = event_id
        else:
            result = event_id[0]

    return result

def main():
    # Load local connection settings without storing credentials in source code.
    load_dotenv()

    # All lookups and inserts share one transaction. Normal exit commits;
    # an exception leaving this block rolls back and closes the connection.
    with psycopg.connect(
        host =os.environ['PGHOST'],
        port=os.environ['PGPORT'],
        dbname=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD']
    ) as connection:

        # Read and validate the complete file before the first database lookup.
        events = read_events('./events.jsonl')
        skipped = 0
        inserted = 0

        for event in events:
            result = get_machine_order_ids(connection, event['machine_code'], event['order_code'])
            if result is None:
                raise ValueError(f"Combination of machine_code {event['machine_code']} and order_code {event['order_code']} was not found, event {event['source_event_id']}")

            machine_id= result[0]
            order_id = result[1]

            # Distinguish inserted rows from source IDs already present in the table.
            inserted_event_id = insert_event(connection, event, machine_id, order_id)

            if inserted_event_id is None:
                skipped+=1
            else:
                inserted+=1

    # Report success only after the connection context has committed.
    print(f'{inserted} lines inserted, {skipped} lines skipped')

if __name__ == '__main__':
    main()
