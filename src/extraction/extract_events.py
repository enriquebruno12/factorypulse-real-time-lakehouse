import os
import psycopg
import json
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def main():

    logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )

    parser = argparse.ArgumentParser(
        description='Extract machine events from PostgreSQL'
    )
    parser.add_argument(
        '--output',
        default='extracted_events.jsonl',
        help='Path to the extracted file'
    )
    args = parser.parse_args()
    path = Path(args.output)
    logger.info('Starting events extraction into %s',path)
    path.parent.mkdir(parents=True, exist_ok=True)
    load_dotenv()

    envs = [
            'PGHOST',
            'PGPORT',
            'PGDATABASE',
            'PGUSER',
            'PGPASSWORD'
        ]

    for env in envs:
        if not os.getenv(env):
            raise ValueError(f'{env} value is missing')
    
    with psycopg.connect(
            host=os.environ['PGHOST'],
            port=os.environ['PGPORT'],
            dbname=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            connect_timeout=10
        ) as connection:

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select source_event_id, machine_id, order_id, event_type, event_at, units_produced, created_at
                from machine_events
                order by event_id;
                """
            )

            events = cursor.fetchall()

            with path.open('w',encoding='utf-8') as file:
                for event in events:
                    event_result = {
                        'source_event_id':event[0],
                        'machine_id': event[1],
                        'order_id': event[2],
                        'event_type':event[3],
                        'event_at':event[4].isoformat(),
                        'units_produced':event[5],
                        'created_at': event[6].isoformat()
                    }
                    file.write(json.dumps(event_result) + '\n')
    logger.info('Event extraction finished, %s lines were exported to %s.', len(events), path)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.exception('Event extraction failed')
        raise