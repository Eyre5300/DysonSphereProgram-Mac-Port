import hashlib,types,unittest
from unittest.mock import patch
import apply_din_cjk_fallback as m
class Font:
 def __init__(self,name,pid,data):self.type=types.SimpleNamespace(name='Font');self.path_id=pid;self.name=name;self.data=data
 def read_typetree(self):return {'m_Name':self.name,'m_FontData':self.data}
class FontIdentity(unittest.TestCase):
 def test_reordered_ids_do_not_change_identity(self):
  pins={name:hashlib.sha256(name.encode()).hexdigest() for name in m.PINNED}
  objects=[Font(name,987-i,name.encode()) for i,name in enumerate(reversed(pins))]
  with patch.object(m,'PINNED',pins):
   resolved=m.resolve_fonts(objects)
   self.assertEqual(set(resolved),set(pins));self.assertEqual(resolved['DIN'].path_id,985)
 def test_changed_bytes_and_duplicate_names_fail_closed(self):
  with patch.object(m,'PINNED',{'DIN':hashlib.sha256(b'original').hexdigest()}):
   for objects in [[],[Font('DIN',9,b'changed')],[Font('DIN',9,b'original'),Font('DIN',33,b'original')]]:
    with self.assertRaises(ValueError):m.resolve_fonts(objects)
if __name__=='__main__':unittest.main()
