import unittest
from apply_verta_binding import adapt

class VertaBindingGuard(unittest.TestCase):
    def test_preserves_storage_upload_and_is_idempotent(self):
        source='upload();\nmat.SetBuffer("_VertaBuffer", cbuffer);\nexport();'
        fixed=adapt(source)
        self.assertEqual(fixed.replace('PortSetBuffer','SetBuffer'),source)
        self.assertEqual(adapt(fixed),fixed)
    def test_unknown_and_duplicate_bindings_fail_closed(self):
        for source in ['', 'mat.SetBuffer("_VertaBuffer", other);', 'mat.SetBuffer("_VertaBuffer", cbuffer);'*2, 'mat.PortSetBuffer("_VertaBuffer", cbuffer);'*2, 'mat.SetBuffer("_VertaBuffer", cbuffer);mat.PortSetBuffer("_VertaBuffer", cbuffer);']:
            with self.subTest(source=source),self.assertRaises(ValueError): adapt(source)

if __name__=='__main__': unittest.main()
