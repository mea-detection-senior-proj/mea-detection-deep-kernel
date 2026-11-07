"""Offline preflight accounting on numeric metadata; no model/runtime execution."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from stream_prada_order import phase_i_check as checks
from stream_prada_order.traffic_runtime.policy import snapshot_lock


class PhaseICheckTests(unittest.TestCase):
    def test_hub_precedence_and_explicit_legacy_roots(self):
        with tempfile.TemporaryDirectory() as folder:
            env={'HF_HOME':str(Path(folder)/'home'),'HF_HUB_CACHE':str(Path(folder)/'new'),
                 'HUGGINGFACE_HUB_CACHE':str(Path(folder)/'legacy'),'TRANSFORMERS_CACHE':str(Path(folder)/'old')}
            roots=checks.cache_roots(env,Path(folder))
            self.assertEqual(roots[0]['path'],os.path.normcase(os.path.abspath(env['HF_HUB_CACHE'])))
            self.assertIn('TRANSFORMERS_CACHE',[r['origin'] for r in roots])
            self.assertEqual(len({r['path'] for r in roots}),len(roots))

    def test_xdg_is_supported_and_h_default_difference_is_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            roots=checks.cache_roots({'XDG_CACHE_HOME':str(Path(folder)/'xdg')},Path(folder))
            self.assertEqual(roots[0]['path'],os.path.normcase(str(Path(folder)/'xdg/huggingface/hub')))
            self.assertEqual(roots[1]['origin'],'frozen_h_default')

    def test_default_does_not_search_unconfigured_drives(self):
        with tempfile.TemporaryDirectory() as folder:
            roots=checks.cache_roots({},Path(folder))
            self.assertEqual(len(roots),1)
            self.assertEqual(roots[0]['path'],os.path.normcase(str(Path(folder)/'.cache/huggingface/hub')))

    def test_network_cache_is_refused(self):
        with self.assertRaisesRegex(ValueError,'network_cache'):checks.cache_roots({'HF_HUB_CACHE':'//unapproved/cache'},Path.cwd())

    def test_same_snapshot_from_cache_and_explicit_location_is_not_rehashed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);snapshot=root/'models--Qwen--Qwen2.5-1.5B-Instruct'/'snapshots'/checks.MODEL_REVISION
            result={'status':'blocked','codes':['snapshot_missing'],'bytes_read':0,'verified_files':[]}
            with patch('stream_prada_order.traffic_runtime.readiness.inspect_snapshot',return_value=result) as inspect:
                inventory=checks.inventory([{'origin':'test','path':str(root)}],[snapshot])
            self.assertEqual(inspect.call_count,1)
            self.assertEqual(inventory['bytes_read'],0)
            self.assertFalse(inventory['all_required_hashes_verified'])

    def test_hash_read_budget_is_shared_across_explicit_candidates(self):
        with tempfile.TemporaryDirectory() as folder:
            results=[{'status':'passed','bytes_read':3*1024**3},{'status':'blocked','bytes_read':0}]
            with patch('stream_prada_order.traffic_runtime.readiness.inspect_snapshot',side_effect=results) as inspect:
                checks.inventory([], [Path(folder)/'1',Path(folder)/'2'])
            self.assertEqual(inspect.call_args_list[1].kwargs['read_cap'],5*1024**3)

    def test_root_budget_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'root_budget'):checks.inventory([], [Path(folder)/str(i) for i in range(17)])

    def test_exact_download_plan_is_arithmetic_not_execution(self):
        plan=checks.download_plan(snapshot_lock())
        self.assertEqual(plan['required_file_count'],8)
        self.assertEqual(plan['final_file_bytes'],3098967011)
        self.assertEqual(plan['automatic_retries'],0)
        self.assertEqual(plan['proposed_max_http_transactions'],32)
        self.assertLess(plan['staging_plus_final_conservative_bytes'],plan['proposed_storage_cap_bytes'])
        for entry in plan['files']:self.assertIn('/resolve/'+checks.MODEL_REVISION+'/',entry['source_url'])
        self.assertTrue(plan['no_download_performed'])

    def test_download_plan_rejects_path_traversal(self):
        lock=snapshot_lock();lock['files']['../1']=lock['files']['LICENSE']
        with self.assertRaisesRegex(ValueError,'filename'):checks.download_plan(lock)

    def test_disk_check_does_not_create_the_proposed_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'1'/'2'
            result=checks.disk_info(target)
            self.assertGreater(result['free_bytes'],0);self.assertFalse(target.exists())

    def test_dirty_checkout_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'out'
            with patch('stream_prada_order.traffic_runtime.policy.checkout_status',return_value={
                'branch':'experiment/stream-prada-order','clean':False,'main_unchanged':True}):
                with self.assertRaisesRegex(ValueError,'clean_isolated'):checks.run(target)
            self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
