import copy
import unittest
from batch_result import FLIGHT_KEY_CHECKS, flight_audit_failures


class FlightAuditGateTests(unittest.TestCase):
    def fixture(self):
        identity = {'batchIdentifier': 'synthetic-current', 'buildVersion': '44'}
        state = {'batchIdentifier': identity['batchIdentifier'], 'expectedVersion': '44',
                 'flagsVerified': True, 'enteredWorld': True, 'consoleExitCode': 0,
                 'finalGameReport': dict(identity, phase='batch_finished_normal_exit', autoTestCompleted=True, errors=[])}
        checks = []
        for width in (1600, 1376):
            checks += ['PASS original options list contains '+str(width)+'x'+str(width*3//4),
                       'PASS original preview applies '+str(width)+'x'+str(width*3//4),
                       'PASS original resolution confirmation stores '+str(width)]
        checks += ['PASS save path isolation available', 'PASS isolated world entered',
                   'PASS native move/scroll/button callbacks installed and zero-delta callback delivery works: 31',
                   'PASS flight transport assertions complete']
        report = dict(identity, completed=True, phase='passed', savePathRestored=True, errors=[], checks=checks)
        keyboard = dict(identity, completed=True, checks=['PASS '+key+': synthetic evidence' for key in FLIGHT_KEY_CHECKS])
        return state, report, keyboard

    def test_accepts_complete_current_evidence(self):
        self.assertEqual(flight_audit_failures(*self.fixture()), [])

    def test_no_check_can_be_silently_omitted(self):
        for index in (1, 2):
            original = self.fixture()
            for i in range(len(original[index]['checks'])):
                altered = copy.deepcopy(original)
                altered[index]['checks'].pop(i)
                self.assertTrue(flight_audit_failures(*altered), (index, i))

    def test_failures_and_old_or_unrestored_runs_are_rejected(self):
        for kind in ('stale', 'incomplete', 'error', 'restore', 'duplicate', 'keyboard-fail', 'no-world'):
            state, report, keyboard = self.fixture()
            if kind == 'stale': report['batchIdentifier'] = 'previous'
            if kind == 'incomplete': keyboard['completed'] = False
            if kind == 'error': report['errors'] = ['synthetic failure']
            if kind == 'restore': report['savePathRestored'] = False
            if kind == 'duplicate': keyboard['checks'].append(keyboard['checks'][0])
            if kind == 'keyboard-fail': keyboard['checks'].append('FAIL unexpected input: synthetic')
            if kind == 'no-world': state['enteredWorld'] = False
            self.assertTrue(flight_audit_failures(state, report, keyboard), kind)


if __name__ == '__main__':
    unittest.main()
