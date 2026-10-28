import json
from pathlib import Path

def read_events(file_path):
    path = Path(file_path)
    events = []
    required_fields = [
                    'source_event_id',
                    'machine_code',
                    'order_code',
                    'event_type',
                    'event_at',
                    'units_produced'
                ]

    with path.open('r',encoding='utf-8-sig') as file:
        for line_number, line in enumerate(file,start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f'Invalid JSON within file {path}, line {line_number}'
                ) from error
            if not isinstance(event,dict):
                raise ValueError(f'JSON event in file {path}, line {line_number} must be a Dict type')

            for field in required_fields:
                if field not in event:
                    raise ValueError(f'JSON file is missing field {field}, line {line_number}.')
            
            events.append(event)

    return events

def main():
    events = read_events('./events.jsonl')
    print(len(events))
    print(events[1]['units_produced'])


if __name__ == '__main__':
    main()
