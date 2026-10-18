import copy,hashlib,io,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import publish_checked as p

class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.report={'status':'validated','sha256':'a'*64,'bytes':4,'counts':{'judges':{'new':1}}}
        self.spec=SimpleNamespace(repo='Nason/fjc-judges-database',file='fjc-judges.duckdb')
    def test_flat_and_nested_validation(self):
        self.assertEqual(p.validation_report(self.report),self.report)
        self.assertEqual(p.validation_report({'validation':self.report}),self.report)
    def test_missing_counts_fails_before_publish(self):
        del self.report['counts']
        with self.assertRaisesRegex(ValueError,'requires'):p.validation_report(self.report)
    def test_invalid_counts_rejected(self):
        self.report['counts']['judges']['new']=-1
        with self.assertRaisesRegex(ValueError,'table count'):p.validation_report(self.report)
    def test_lfs_identity(self):
        api=Mock();api.get_paths_info.return_value=[SimpleNamespace(size=4,lfs=SimpleNamespace(sha256='a'*64))]
        self.assertEqual(p.remote_identity(api,self.spec,'c'*40,4,'a'*64),'lfs-sha256')
    def test_plain_blob_streamed_identity(self):
        api=Mock();api.get_paths_info.return_value=[SimpleNamespace(size=4,lfs=None)]
        with patch.object(p.urllib.request,'urlopen',return_value=io.BytesIO(b'data')):
            self.assertEqual(p.remote_identity(api,self.spec,'c'*40,4,hashlib.sha256(b'data').hexdigest()),'streamed-sha256')
    def test_plain_blob_oversized_or_truncated_rejected(self):
        api=Mock();api.get_paths_info.return_value=[SimpleNamespace(size=4,lfs=None)]
        for content in [b'large',b'sml']:
            with patch.object(p.urllib.request,'urlopen',return_value=io.BytesIO(content)):
                with self.assertRaises(RuntimeError):p.remote_identity(api,self.spec,'c'*40,4,'a'*64)
    def test_remote_hash_mismatch_rejected(self):
        api=Mock();api.get_paths_info.return_value=[SimpleNamespace(size=4,lfs=SimpleNamespace(sha256='b'*64))]
        with self.assertRaisesRegex(RuntimeError,'hash mismatch'):p.remote_identity(api,self.spec,'c'*40,4,'a'*64)

if __name__=='__main__':unittest.main()
