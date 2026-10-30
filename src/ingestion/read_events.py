import json
from pathlib import Path
from datetime import datetime

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

    event_types_allowed = ['MACHINE_STARTED', 'PRODUCTION_REPORTED', 'FAULT_DETECTED', 'MACHINE_STOPPED']

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

                value = event[field]

                # Booleans are rejected as well as strings and other numeric types.
                if field == 'units_produced':
                    if type(value) is not int:
                        raise ValueError(f'{field} has to have a int value, line {line_number}')
                else:
                    if not isinstance(value, str):
                        raise ValueError(f'{field} must be str type, line {line_number}.')
                    if not value.strip():
                        raise ValueError(f'{field} cannot be empty, line {line_number}')

                # Parse for validation while preserving the original timestamp string.
                if field == 'event_at':
                    try:
                        parsed_date = datetime.fromisoformat(value)
                    except ValueError as error:
                        raise ValueError (f'Invalid {field}, line {line_number}: {value}') from error

                    # Explicit offsets disambiguate the occurrence instant.
                    if parsed_date.tzinfo is None:
                        raise ValueError(f'{field} must include timezone, line {line_number}')

                # Limit accepted strings to the four event types in the contract.
                if field == 'event_type':
                    if value not in event_types_allowed:
                        raise ValueError(f'{field} received {value}, expected one of the following:'
                                         f'[MACHINE_STARTED, PRODUCTION_REPORTED, FAULT_DETECTED, MACHINE_STOPPED], line {line_number}')

            # Check relationships between fields after every type has been validated.
            if event['event_type'] == 'PRODUCTION_REPORTED' and event['units_produced'] <=0:
                raise ValueError(f'{field} must have units produced greater than 0, line number {line_number}')
            elif event['event_type'] in ['MACHINE_STARTED', 'FAULT_DETECTED','MACHINE_STOPPED'] and event['units_produced'] != 0:
                raise ValueError(f'{event['event_type']} has to have 0 as units produced , line number {line_number}')

            events.append(event)

    return events

# Direct execution shows a quick read check; imports expose read_events only.
def main():
    events = read_events('./events.jsonl')
    print(len(events))
    print(events[1]['units_produced'])


if __name__ == '__main__':
    main()
