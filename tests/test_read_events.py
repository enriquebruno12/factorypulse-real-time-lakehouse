import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.ingestion.read_events import read_events

# Exercise malformed input without keeping fixture files in the repository.
class TestReadEvents(unittest.TestCase):

    # Syntax errors report the line containing malformed JSON.
    def test_invalid_json_line(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                '"event_at":"2026-10-21T08:00:00+00:00",'
                '"units_produced":0}\n'
                '{invalid}',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'line 2'):
                read_events(path)

    # JSON scalars are valid JSON but are not event objects.
    def test_invalid_json_event(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                '"event_at":"2026-10-21T08:00:00+00:00",'
                '"units_produced":0}\n'
                '45\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'line 2 must be a Dict type'):
                read_events(path)

    # Event objects must include every required payload field.
    def test_invalid_fields(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                '"event_at":"2026-10-21T08:00:00+00:00",'
                '"units_produced":0}\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'JSON file is missing field'):
                read_events(path)
        