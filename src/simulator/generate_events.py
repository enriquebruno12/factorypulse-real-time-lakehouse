import json

from datetime import datetime, timezone, timedelta

eventos = [
    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
    {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':25, 'offset_minutes':30},
    {'machine_code':'M-001','event_type':'FAULT_DETECTED','units_produced':0, 'offset_minutes':60},
    {'machine_code':'M-001','event_type':'MACHINE_STOPPED','units_produced':0, 'offset_minutes':61},
    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':90},
    {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':10, 'offset_minutes':120},
    {'machine_code':'M-001','event_type':'MACHINE_STOPPED','units_produced':0, 'offset_minutes':150},
]

horario = datetime(2026,10,21, 8, 0, tzinfo=timezone.utc)

for n,event in enumerate(eventos):

    event_result = event.copy()

    event_result['order_code'] = 'PO-001'
    event_result['source_event_id'] = f'EVT-{n+1:03d}'
    event_result['event_at'] = (horario + timedelta(minutes=event_result.pop('offset_minutes'))).isoformat()
    print(json.dumps(event_result))