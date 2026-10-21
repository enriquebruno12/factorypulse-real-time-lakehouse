import json

from datetime import datetime, timezone, timedelta

eventos = [
    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0},
    {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':25},
    {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':10},
    {'machine_code':'M-001','event_type':'MACHINE_STOPPED','units_produced':0},
]

horario = datetime(2026,10,21, 8, 0, tzinfo=timezone.utc)

for n,evento in enumerate(eventos):
    evento['order_code'] = 'PO-001'
    evento['source_event_id'] = f'EVT-{n+1:03d}'
    evento['event_at'] = (horario + timedelta(minutes=n*30)).isoformat()
    print(json.dumps(evento))