import json
from pathlib import Path

def read_events(file_path):
    path = Path(file_path)
    events = []

    with path.open('r',encoding='utf-8-sig') as file:
        for line in file:
            events.append(json.loads(line))
    return events

events = read_events('./events.jsonl')

print(len(events))
print(events[1]['units_produced'])