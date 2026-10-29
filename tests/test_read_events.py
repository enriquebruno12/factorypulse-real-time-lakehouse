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

    def test_invalid_units_produced(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                '"event_at":"2026-10-21T08:00:00+00:00",'
                '"units_produced":"asd"}\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'has to have a int value'):
                read_events(path)

    def test_invalid_values(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":123,'
                '"event_at":"2026-10-21T08:00:00+00:00",'
                '"units_produced":0}\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'must be str type'):
                read_events(path)

    def test_blank_values(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":" ",'
                '"event_at":"2026-10-21T08:00:00+00:00",'
                '"units_produced":0}\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'cannot be empty'):
                read_events(path)

    def test_invalid_event_at(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                '"event_at":"banana",'
                '"units_produced":0}\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'Invalid event_at, line 1'):
                read_events(path)

    def test_missing_timezone(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                '"event_at":"2026-10-21T08:00:00",'
                '"units_produced":0}\n',
                encoding='utf-8'
            )

            with self.assertRaisesRegex(ValueError,'must include timezone'):
                read_events(path)

    def test_valid_event_at(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'valid.jsonl'

            timestamp = "2026-10-21T08:00:00+00:00"

            path.write_text(
                '{"order_code":"PO-001",'
                '"source_event_id":"EVT-001",'
                '"machine_code":"M-001",'
                '"event_type":"MACHINE_STARTED",'
                f'"event_at":"{timestamp}",'
                '"units_produced":0}\n',
                encoding='utf-8'
            )
            
            events = read_events(path)

            self.assertEqual (len(events),1)
            self.assertEqual(events[0]['event_at'], timestamp)