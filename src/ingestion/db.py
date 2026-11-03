import os
import psycopg
import argparse
import logging
import time
from dotenv import load_dotenv
from src.ingestion.read_events import read_events

# Name the logger after this module; configuration belongs to the CLI entry point.
logger = logging.getLogger(__name__)


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
            (machine_code, order_code)
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
            (machine_id, order_id, event['source_event_id'], event['event_type'], event['event_at'], event['units_produced'])
        )

        # RETURNING yields a row only when PostgreSQL actually inserted an event.
        event_id = cursor.fetchone()

        if event_id is None:
            result = event_id
        else:
            result = event_id[0]

    return result


# Process an already validated batch using the caller's connection.
# This function does not commit: main owns the transaction boundary.
def ingest_events(connection, events):
    skipped = 0
    inserted = 0

    for event in events:
        result = get_machine_order_ids(connection, event['machine_code'], event['order_code'])
        if result is None:
            raise ValueError(f"Combination of machine_code {event['machine_code']} and order_code {event['order_code']} was not found, event {event['source_event_id']}")

        machine_id = result[0]
        order_id = result[1]

        # Distinguish inserted rows from source IDs already present in the table.
        inserted_event_id = insert_event(connection, event, machine_id, order_id)

        if inserted_event_id is None:
            skipped += 1
        else:
            inserted += 1
    # Positional return order matches the unpacking performed by main.
    return inserted, skipped


# Orchestrate CLI arguments, configuration, file reading and the transaction.
def main():

    # Console logs include local timestamp, severity, module name and message.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

    parser = argparse.ArgumentParser(
        description='Load machine events from JSON file into PostgreSQL'
    )

    parser.add_argument(
        '--input',
        default='events.jsonl',
        help='Path to the JSONL file to load'
    )

    # --input selects a JSONL path; relative paths use the working directory.
    args = parser.parse_args()

    # A monotonic counter measures duration, not a wall-clock timestamp.
    start_time = time.perf_counter()

    logger.info('Loading events from %s', args.input)

    # Load local connection settings without storing credentials in source code.
    load_dotenv()

    # Only PG* settings are required by this loader; POSTGRES_* configures Docker.
    envs = [
        'PGHOST',
        'PGPORT',
        'PGDATABASE',
        'PGUSER',
        'PGPASSWORD'
    ]

    # Reject missing or empty values without logging their contents.
    for env in envs:
        if not os.getenv(env):
            raise ValueError(f'{env} value is missing')

    # All lookups and inserts share one transaction. Normal exit commits;
    # an exception leaving this block rolls back and closes the connection.
    with psycopg.connect(
        host=os.environ['PGHOST'],
        port=os.environ['PGPORT'],
        dbname=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD'],
        # Bound connection establishment; this is not a query execution timeout.
        connect_timeout=10
    ) as connection:

        # Read and validate the complete file before the first database lookup.
        events = read_events(args.input)

        # Pass the same connection so every lookup/insert shares this transaction.
        inserted, skipped = ingest_events(connection, events)

    # Include connection setup, validation, ingestion, commit and connection close.
    elapsed_time = time.perf_counter() - start_time


    # Report success only after the connection context has committed.
    logger.info(f'{inserted} lines inserted, {skipped} lines skipped, completed in {elapsed_time:.2f}s')

# Run with python -m src.ingestion.db; importing this module does not run main.
if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Log the active traceback, then preserve a failing process exit status.
        logger.exception('Event ingestion failed')
        raise
