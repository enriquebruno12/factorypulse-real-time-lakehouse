import json
from pathlib import Path

# Read newline-delimited JSON and report input errors with their source line.
def read_events(file_path):
    path = Path(file_path)
    events = []
    # These keys form the minimum event payload expected by ingestion.
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
            # Parse one JSON document per line while preserving its line number.
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f'Invalid JSON within file {path}, line {line_number}'
                ) from error
            # A valid JSON scalar or array is not an event record.
            if not isinstance(event,dict):
                raise ValueError(f'JSON event in file {path}, line {line_number} must be a Dict type')

            # Reject incomplete records before handing them to later stages.
            for field in required_fields:
                if field not in event:
                    raise ValueError(f'JSON file is missing field {field}, line {line_number}.')
            
            events.append(event)

    return events

# Direct execution shows a quick read check; imports expose read_events only.
def main():
    events = read_events('./events.jsonl')
    print(len(events))
    print(events[1]['units_produced'])


if __name__ == '__main__':
    main()
