import unittest

from src.simulator.generate_events import validate_sequence

class TestGenerateEvents(unittest.TestCase):

    def test_invalid_production(self):
        events = [
            {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
            {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':0, 'offset_minutes':30}
        ]
        with self.assertRaisesRegex(ValueError, 'units produced must be greater than 0'):
            validate_sequence(events)

    def test_valid_fault_sequence(self):
        events = [
                    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
                    {'machine_code':'M-001','event_type':'FAULT_DETECTED','units_produced':0, 'offset_minutes':30},
                    {'machine_code':'M-001','event_type':'MACHINE_STOPPED','units_produced':0, 'offset_minutes':60}
                ]
        validate_sequence(events)

    def test_invalid_fault_sequence(self):
        events = [
                    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
                    {'machine_code':'M-001','event_type':'FAULT_DETECTED','units_produced':0, 'offset_minutes':30},
                    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':60}
                ]

        with self.assertRaisesRegex(ValueError,'cannot start machine from FAULTED'):
            validate_sequence(events)

    def test_invalid_offset_minutes(self):
        events = [
                    {'machine_code':'M-001','event_type':'MACHINE_STARTED','units_produced':0, 'offset_minutes':0},
                    {'machine_code':'M-001','event_type':'PRODUCTION_REPORTED','units_produced':30, 'offset_minutes':0}
                ]

        with self.assertRaisesRegex(ValueError,'offset must be greater than'):
            validate_sequence(events)