import copy,unittest
from batch_result import file_layout_failures
from device_report_identity import ReportIdentity

class FocusedAuditTests(unittest.TestCase):
 def test_layout_report_requires_each_changed_window_control(self):
  state={'batchIdentifier':'current','expectedVersion':'39'}
  report={'batchIdentifier':'current','buildVersion':'39','completed':True,'phase':'passed','errors':[],
   'checks':[{'name':w+' file buttons '+c,'passed':True} for w in ('load','save') for c in ('use original style','clear original controls')]}
  self.assertEqual(file_layout_failures(state,report),[])
  for kind in ('stale','missing','failed','duplicate'):
   bad=copy.deepcopy(report)
   if kind=='stale':bad['batchIdentifier']='previous'
   if kind=='missing':bad['checks'].pop()
   if kind=='failed':bad['checks'][0]['passed']=False
   if kind=='duplicate':bad['checks'][0]=bad['checks'][1]
   self.assertTrue(file_layout_failures(state,bad),kind)
 def test_focused_phase_requires_world_ticks(self):
  for phase in ('file_layout_audit','scene_performance_audit'):
   self.assertTrue(ReportIdentity.entered_world({'phase':phase,'tick':150}))
   self.assertFalse(ReportIdentity.entered_world({'phase':phase,'tick':0}))
 def test_flight_phase_starts_in_menu_not_world(self):
  self.assertFalse(ReportIdentity.entered_world({'phase':'flight_display_audit','tick':500000}))

if __name__=='__main__':unittest.main()
