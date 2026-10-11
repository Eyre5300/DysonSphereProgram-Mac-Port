import importlib.util, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('monitor',Path(__file__).resolve().parents[1]/'tools/memory_monitor.py')
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)

class MemoryMonitorTests(unittest.TestCase):
 def test_region_columns_and_guard_are_not_physical_total(self):
  text='REGION TYPE SIZE SIZE SIZE SIZE SIZE SIZE SIZE COUNT\nIOAccelerator (graphics) 4.6G 4.1G 1.5G 2.6G 0K 4.1G 380.9M 8189\nGuard 385.0G 0K 0K 0K 0K 0K 0K 1\nTOTAL 400.5G 8.0G 4.7G 5.2G 0K 4.2G 380.9M 22627\nMALLOC ZONE SIZE\nDefaultMallocZone 235.7M 105.8M 105.8M 71.2M 396118 136.3M 40.7M 24% 161\n'
  rows=monitor.parse_vmmap(text);self.assertEqual(len(rows),2);self.assertEqual(rows[0]['regionCount'],8189);self.assertEqual(rows[0]['dirtyBytes'],int(1.5*2**30));self.assertEqual(rows[1]['residentBytes'],0);self.assertGreater(rows[1]['virtualBytes'],300*2**30)
 def test_sizes_are_binary_and_reject_unknown_format(self):
  self.assertEqual(monitor.size_bytes('16'),16);self.assertEqual(monitor.size_bytes('128K'),131072);self.assertEqual(monitor.size_bytes('1.5G'),1610612736)
  with self.assertRaises(ValueError):monitor.size_bytes('unknown')
 def test_unknown_vmmap_is_not_a_fake_success(self):
  self.assertEqual(monitor.parse_vmmap('cannot examine process'),[])
 def test_html_escapes_os_labels_and_explains_metrics(self):
  with tempfile.TemporaryDirectory()as folder:
   p=Path(folder);monitor.render_report(p,'monitor <state>',[],{'time':'now','regions':[{'type':'<script>bad</script>','residentBytes':1,'dirtyBytes':2,'swappedBytes':0,'virtualBytes':1024}]});s=(p/'index.html').read_text();self.assertNotIn('<script>bad</script>',s);self.assertIn('&lt;script&gt;',s);self.assertIn('虚拟地址空间不等于实际占用',s)
if __name__=='__main__':unittest.main()
