import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.ingestion.read_events import read_events

class TestReadEvents(unittest.TestCase):

    def test_invalid_json_line(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.jsonl'

            path.write_text(
                '{"machine_code":"M-001"}\n'
                '{invalid}\n',
                encoding= 'utf-8'
            )

            with self.assertRaisesRegex(ValueError,'line 2'):
                read_events(path)

    def test_invalid_json_event(self):
        with TemporaryDirectory() as directory:
                    path = Path(directory) / 'invalid.jsonl'
        
                    path.write_text(
                        '{"machine_code":"M-001"}\n'
                        '45\n',
                        encoding= 'utf-8'
                    )
        
                    with self.assertRaisesRegex(ValueError,'line 2 must be a Dict type'):
                        read_events(path)
        