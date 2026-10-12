import unittest
from device_report_identity import ReportIdentity
class ReportIdentityTest(unittest.TestCase):
 def test_stale_world_requires_fresh_boot(self):
  old={'autoTestRequested':True,'phase':'batch_finished_normal_exit','tick':999}
  g=ReportIdentity('new','25',old)
  self.assertFalse(g.accept(old));self.assertFalse(g.accept(dict(old,tick=1000)))
  self.assertFalse(g.accept({'autoTestRequested':True,'phase':'main_menu','tick':999}))
  self.assertTrue(g.accept({'autoTestRequested':True,'phase':'boot','tick':0}))
  self.assertTrue(g.accept(dict(old,phase='render_regression')))
 def test_exact_identity_overrides_legacy_boot(self):
  g=ReportIdentity('new','25',None)
  self.assertTrue(g.accept({'autoTestRequested':True,'phase':'boot'}))
  for batch,version in [('old','25'),('new','24'),('', '25')]:
   self.assertFalse(g.accept({'autoTestRequested':True,'batchIdentifier':batch,'buildVersion':version}))
  self.assertTrue(g.accept({'autoTestRequested':True,'batchIdentifier':'new','buildVersion':'25'}))
 def test_no_baseline_is_not_world_evidence(self):
  self.assertFalse(ReportIdentity('new','25',None).accept({'autoTestRequested':True,'phase':'render_regression','tick':999}))
 def test_explicit_world_phases_only(self):
  for phase in ['boot','main_menu','bc_probe_waiting','new_game_loading','preload_timeout','unexpected']:
   self.assertFalse(ReportIdentity.entered_world({'phase':phase,'tick':999}))
  self.assertFalse(ReportIdentity.entered_world({'phase':'render_regression','tick':0}))
  self.assertTrue(ReportIdentity.entered_world({'phase':'touch_combined_regression','tick':999}))
  self.assertFalse(ReportIdentity.entered_world({'phase':'touch_combined_regression','tick':0}))
  self.assertTrue(ReportIdentity.entered_world({'phase':'render_regression','tick':999}))
  self.assertTrue(ReportIdentity.entered_world({'phase':'functional_batch_25','tick':999}))
if __name__=='__main__':unittest.main()
