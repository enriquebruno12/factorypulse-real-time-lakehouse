import unittest

from src.simulator.generate_events import validate_sequence

class TesteGenerateEvents(unittest.TestCase):

    def test_invalid_production(self):
        events = [
            {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
            {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':0, 'offset_minutes':30}
        ]
        with self.assertRaises(ValueError):
            validate_sequence(events)