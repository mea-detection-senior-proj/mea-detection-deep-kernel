"""Numeric HTTP fixtures only: never downloads weights or uses real HTTP."""
import hashlib
import importlib.util
import io
import json
from email.message import Message
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'phase_j_acquire.py'
spec=importlib.util.spec_from_file_location('phase_j_acquirer',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Response:
    def __init__(self,body=b'123',status=200,**headers):
        self.body=io.BytesIO(body);self.status=status;self.headers=Message();self.read_calls=0;self.closed=False
        for key,value in headers.items():self.headers[key]=str(value)
    def read(self,n):self.read_calls+=1;return self.body.read(n)
    def close(self):self.closed=True


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.plan={'numeric_fixture':True,'allowed_https_hosts':['huggingface.co','us.aws.cdn.hf.co'],
          'files':[{'name':'1','source_url':'https://huggingface.co/numeric/1','bytes':3,
                    'content_sha256':hashlib.sha256(b'123').hexdigest(),'git_blob_sha1':None}],
          'limits':{'wall_seconds':1200,'http_accounted_bytes':8*1024**2,'http_transactions':32,
             'logical_gets':8,'redirects_per_file':3,'storage_bytes':8*1024**2,
             'running_disk_reserve_bytes':0,'initial_disk_free_bytes':0}}
        self.opened=[];self.responses=[Response(**{'Content-Length':3})]
    def tearDown(self):self.temp.cleanup()
    def opener(self,url,timeout):self.opened.append(url);return self.responses.pop(0)
    def transfer(self,**kwargs):return m.Transfer(self.plan,self.base/'run',self.base/'final',open_request=self.opener,**kwargs)

    def test_no_authorization_means_no_request_or_storage(self):
        with self.assertRaisesRegex(m.Stop,'operator_authorization'):self.transfer().acquire()
        self.assertEqual(self.opened,[]);self.assertFalse((self.base/'run').exists())

    def test_numeric_transfer_hashes_and_publishes_without_model_import(self):
        result=self.transfer().acquire(operator_authorized=True)
        self.assertEqual((self.base/'final/1').read_bytes(),b'123')
        self.assertEqual(result['response_body_bytes'],3);self.assertEqual(result['http_transactions'],1)
        self.assertTrue(result['files'][0]['verified']);self.assertFalse(result['model_or_tokenizer_imports'])
        self.assertFalse((self.base/'run/1.partial').exists())

    def test_git_blob_hash_is_not_plain_file_sha1(self):
        spec=self.plan['files'][0];spec['content_sha256']=None
        spec['git_blob_sha1']=hashlib.sha1(b'blob 3\0'+b'123').hexdigest()
        result=self.transfer().acquire(operator_authorized=True)
        self.assertEqual(result['files'][0]['verified_digest'],spec['git_blob_sha1'])

    def test_hash_mismatch_preserves_partial_and_never_publishes(self):
        self.responses=[Response(b'456',**{'Content-Length':3})]
        with self.assertRaisesRegex(m.Stop,'hash_mismatch'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual((self.base/'run/1.partial').read_bytes(),b'456')
        self.assertFalse((self.base/'final').exists());self.assertEqual(len(self.opened),1)

    def test_truncated_body_is_not_retried(self):
        self.responses=[Response(b'12')]
        with self.assertRaisesRegex(m.Stop,'truncated'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual(len(self.opened),1);self.assertFalse((self.base/'final').exists())

    def test_oversized_body_stops_at_first_extra_byte(self):
        self.responses=[Response(b'123456')]
        with self.assertRaisesRegex(m.Stop,'oversized'):self.transfer().acquire(operator_authorized=True)
        stopped=json.loads((self.base/'run/stopped.json').read_bytes());self.assertEqual(stopped['body_bytes'],4)

    def test_wrong_content_length_stops_before_body_read(self):
        response=Response(**{'Content-Length':4});self.responses=[response]
        with self.assertRaisesRegex(m.Stop,'length_mismatch'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual(response.read_calls,0);self.assertTrue(response.closed)

    def test_encoding_and_partial_responses_are_refused(self):
        for headers in [{'Content-Encoding':'gzip'},{'Content-Range':'bytes 0-2/3'}]:
            response=Response(**headers);self.responses=[response]
            transfer=m.Transfer(self.plan,self.base/('run'+str(len(self.opened))),self.base/'final',open_request=self.opener)
            with self.assertRaises(m.Stop):transfer.acquire(operator_authorized=True)
            self.assertEqual(response.read_calls,0)

    def test_unapproved_redirect_is_never_followed(self):
        self.responses=[Response(status=302,Location='https://unapproved.invalid/1')]
        with self.assertRaisesRegex(m.Stop,'unapproved_url'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual(len(self.opened),1)

    def test_redirect_credentials_are_rejected(self):
        for url in ['http://huggingface.co/1','https://user:pass@huggingface.co/1','https://huggingface.co:444/1']:
            with self.assertRaises(m.Stop):m.check_url(url,{'huggingface.co'})

    def test_allowed_redirect_is_logged_without_signature(self):
        self.responses=[Response(status=302,Location='https://us.aws.cdn.hf.co/1?Signature=11223344'),Response()]
        result=self.transfer().acquire(operator_authorized=True)
        self.assertEqual(result['http_transactions'],2)
        self.assertNotIn('11223344',(self.base/'run/events.jsonl').read_text())

    def test_redirect_limit_stops_without_retry(self):
        self.responses=[Response(status=302,Location='https://huggingface.co/1') for _ in range(4)]
        with self.assertRaisesRegex(m.Stop,'redirect_cap'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual(len(self.opened),4)

    def test_request_and_http_byte_caps_stop_before_body(self):
        self.plan['limits']['http_accounted_bytes']=1
        with self.assertRaisesRegex(m.Stop,'http_byte_gate'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual(self.responses[0].read_calls,0) if self.responses else None

    def test_disk_gate_stops_without_body_or_retry(self):
        self.plan['limits']['running_disk_reserve_bytes']=1
        with self.assertRaisesRegex(m.Stop,'disk_free_gate'):self.transfer(disk_free=lambda:0).acquire(operator_authorized=True)
        self.assertEqual(self.opened,[])

    def test_wall_gate_is_checked_before_open(self):
        ticks=iter([0,0,1201,1201,1201])
        with self.assertRaisesRegex(m.Stop,'wall_gate'):self.transfer(clock=lambda:next(ticks)).acquire(operator_authorized=True)
        self.assertEqual(self.opened,[])

    def test_existing_destination_is_never_overwritten(self):
        (self.base/'final').mkdir();(self.base/'final/1').write_bytes(b'456')
        with self.assertRaisesRegex(m.Stop,'new_storage_paths'):self.transfer().acquire(operator_authorized=True)
        self.assertEqual((self.base/'final/1').read_bytes(),b'456');self.assertEqual(self.opened,[])

    def test_approval_is_required_before_file_access(self):
        with self.assertRaisesRegex(m.Stop,'operator_authorization'):m.validate_approval({},None,None)


if __name__=='__main__':
    unittest.main(verbosity=2)
