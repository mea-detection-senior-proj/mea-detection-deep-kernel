"""Exercise generation bridge with fake tokenizer/model/tensors only."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_h_helpers import fake_backend,FakeTensor
from stream_prada_order.traffic_runtime.backend import QwenBackend
from stream_prada_order.traffic_runtime.policy import profile
from stream_prada_order.traffic_collection.schema import IntegrityError,ExecutionDisabled


class BackendTests(unittest.TestCase):
    def test_default_load_is_disabled_before_import_or_cache_access(self):
        with self.assertRaises(ExecutionDisabled):QwenBackend().load('not-a-real-snapshot')

    def test_boolean_flag_without_a_validated_real_grant_is_insufficient(self):
        with self.assertRaises(ExecutionDisabled):QwenBackend().load('not-a-real-snapshot',execution_authorized=True)

    def test_exact_usage_includes_full_prompt_and_generated_eos(self):
        b=fake_backend();prepared=b.prepare('1');result=b.generate()
        self.assertEqual(prepared['input_ids'],[1,2,3])
        self.assertEqual(result['input_tokens'],3)
        self.assertEqual(result['text'],'4')
        self.assertEqual(result['output_tokens'],2)
        self.assertEqual(result['output_ids'],[4,151645])
        self.assertFalse(b.tokenizer.calls[1][2]['add_special_tokens'])
        self.assertFalse(b.tokenizer.calls[1][2]['truncation'])
        self.assertEqual(b.model.kwargs['generation_config'],profile()['generation'])

    def test_single_turn_template_has_no_unrecorded_history(self):
        b=fake_backend();b.prepare('1');b.generate();b.prepare('2')
        render=[x for x in b.tokenizer.calls if x[0]=='render']
        self.assertEqual(render[1][1],[{'role':'system','content':profile()['system_message']},{'role':'user','content':'2'}])
        self.assertEqual(render[0][2]['chat_template'],profile()['chat_template'])

    def test_overlength_input_is_rejected_before_generate(self):
        b=fake_backend();b.tokenizer.__class__=type('LongTokenizer',(type(b.tokenizer),),{
            '__call__':lambda self,*args,**kwargs:{'input_ids':FakeTensor([[1]*2049]),'attention_mask':FakeTensor([[1]*2049])}})
        with self.assertRaisesRegex(IntegrityError,'input_token_cap'):b.prepare('1')
        self.assertIsNone(b.model.kwargs)

    def test_missing_or_wrong_prefix_is_not_fabricated_usage(self):
        b=fake_backend();b.prepare('1')
        b.model.generate=lambda **kwargs:type('Output',(),{'sequences':FakeTensor([[9,4]])})()
        with self.assertRaisesRegex(IntegrityError,'prefix_mismatch'):b.generate()

    def test_non_unit_padding_mask_is_rejected(self):
        b=fake_backend();b.tokenizer.__class__=type('PaddedTokenizer',(type(b.tokenizer),),{
            '__call__':lambda self,*args,**kwargs:{'input_ids':FakeTensor([[1,2,3]]),'attention_mask':FakeTensor([[1,0,1]])}})
        with self.assertRaisesRegex(IntegrityError,'unexpected_padding'):b.prepare('1')


if __name__=='__main__':unittest.main()
