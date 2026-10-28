import json
from datetime import datetime, timezone, timedelta

# Enforce the fictional machine state and payload rules before emitting events.
def validate_sequence(events):
    # The example machine starts stopped; offsets must increase within this run.
    current_state = 'STOPPED'
    last_offset = None

    for n,event in enumerate(events):

        event_number = f'EVT-{n+1:03d}'

        # Reject event types outside the contract before checking transitions.
        if event['event_type'] not in ('MACHINE_STARTED','PRODUCTION_REPORTED','MACHINE_STOPPED','FAULT_DETECTED'):
            raise ValueError(f"{event['event_type']} invalid, expected MACHINE_STARTED, PRODUCTION_REPORTED, MACHINE_STOPPED OR FAULT_DETECTED . Event number {event_number}")
        
        # Production reports are valid only while the machine is running.
        if current_state != 'RUNNING' and event['event_type'] == 'PRODUCTION_REPORTED':
            raise ValueError(f'machine is not running. Event number {event_number}')

        # A restart requires a prior stop, including after a fault.
        if current_state != 'STOPPED' and event['event_type'] == 'MACHINE_STARTED':
            raise ValueError(f'cannot start machine from {current_state}. Event number {event_number}')

        # Faults can only be detected during a running interval.
        if current_state != 'RUNNING' and event['event_type'] == 'FAULT_DETECTED':
            raise ValueError(f'fault is not possible from {current_state}. Event number {event_number}')

        # Stops are allowed after normal operation or a detected fault.
        if current_state not in ('FAULTED', 'RUNNING') and event['event_type'] == 'MACHINE_STOPPED':
            raise ValueError(f'stopping is not possible from {current_state}. Event number {event_number}')

        # Preserve strict event order; the first event may use offset zero.
        if last_offset is not None:
            if event['offset_minutes'] <= last_offset:
                raise ValueError(f'offset must be greater than the previous event’s offset. Event number {event_number}')

        if event['offset_minutes'] < 0:
            raise ValueError(f'offset must be 0 or greater. Event number {event_number}')

        # Only production reports carry a positive unit increment.
        if event['event_type'] in ('MACHINE_STARTED', 'MACHINE_STOPPED', 'FAULT_DETECTED') and event['units_produced']!= 0:
            raise ValueError(f'units produced different from 0 only possible when event type is PRODUCTION_REPORTED. Event number {event_number}')

        if event['event_type'] == 'PRODUCTION_REPORTED' and event['units_produced'] <=0:
            raise ValueError(f'units produced must be greater than 0 when event type is PRODUCTION_REPORTED. Event number {event_number}')


        # Apply the event's state transition after all validations pass.
        if event['event_type'] == 'MACHINE_STARTED':
            current_state = 'RUNNING'
        elif event['event_type'] == 'FAULT_DETECTED':
            current_state = 'FAULTED'
        elif event['event_type'] == 'MACHINE_STOPPED':
            current_state = 'STOPPED'

        last_offset = event['offset_minutes']

# Generate a deterministic example and emit one JSON object per output line.
def main():

    events = [
        {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
        {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':25, 'offset_minutes':30},
        {'machine_code':'M-001','event_type':'FAULT_DETECTED','units_produced':0, 'offset_minutes':60},
        {'machine_code':'M-001','event_type':'MACHINE_STOPPED','units_produced':0, 'offset_minutes':61},
        {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':90},
        {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':10, 'offset_minutes':120},
        {'machine_code':'M-001','event_type':'MACHINE_STOPPED','units_produced':0, 'offset_minutes':150},
    ]

    horario = datetime(2026,10,21, 8, 0, tzinfo=timezone.utc)

    # Validate before printing so an invalid scenario emits no partial output.
    validate_sequence(events)

    for n,event in enumerate(events):

        # Keep offset_minutes internal to the simulator's scenario definition.
        event_result = event.copy()

        event_result['order_code'] = 'PO-001'
        event_result['source_event_id'] = f'EVT-{n+1:03d}'
        event_result['event_at'] = (horario + timedelta(minutes=event_result.pop('offset_minutes'))).isoformat()
        print(json.dumps(event_result))
    

if __name__ == '__main__':
    main()