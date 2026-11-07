"""OS-process timeouts/crashes exercised with numeric mock worker only."""
from pathlib import Path
import os
import sys
import time
import unittest
import subprocess
import tempfile
import json
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stream_prada_order.traffic_runtime.supervisor import Supervisor,RuntimeFailure
from stream_prada_order.traffic_runtime.policy import profile
from stream_prada_order.traffic_collection.schema import IntegrityError,ExecutionDisabled


def options(**extra):return {'mode':'mock','mock_marker':'numeric-tests-only',
                            'template_sha256':profile()['chat_template_sha256'],**extra}


class SupervisorTests(unittest.TestCase):
    def test_real_default_stops_before_spawning(self):
        s=Supervisor({'mode':'real'})
        with self.assertRaises(ExecutionDisabled):s.start()
        self.assertIsNone(s.proc)

    @unittest.skipUnless(os.name=='nt','Windows job admission failure')
    def test_job_assignment_failure_kills_unattached_worker_without_cooperation(self):
        s=Supervisor(options(),timeout=10)
        with patch('stream_prada_order.traffic_runtime.supervisor.WindowsJob.assign',side_effect=IntegrityError('job_assignment_failed')), \
             patch('stream_prada_order.traffic_runtime.supervisor.send',return_value=None):
            with self.assertRaises(IntegrityError):s.start()
        self.assertFalse(s.proc.is_alive())

    def test_mock_prepare_is_delivered_before_generate(self):
        seen=[]
        with Supervisor(options(),timeout=10) as s:
            result=s.infer('1',lambda p:seen.append(p))
            self.assertEqual(len(seen),1);self.assertEqual(seen[0]['input_tokens'],3)
            self.assertEqual(result['output_tokens'],2);self.assertEqual(s.requests,1)
        self.assertFalse(s.proc.is_alive())

    def test_timeout_during_generate_kills_worker_and_is_unknown(self):
        s=Supervisor(options(generate_hang=True),timeout=1.5);start=time.monotonic()
        try:
            s.start()
            with self.assertRaises(RuntimeFailure) as found:s.infer('1',lambda p:None)
            self.assertEqual(found.exception.delivery,'unknown')
            self.assertEqual(found.exception.runtime_code,'wall_timeout')
        finally:s.close()
        self.assertFalse(s.proc.is_alive());self.assertLess(time.monotonic()-start,5)

    def test_boot_timeout_has_no_victim_delivery(self):
        s=Supervisor(options(boot_hang=True),timeout=0.7)
        with self.assertRaises(RuntimeFailure) as found:s.start()
        self.assertEqual(found.exception.delivery,'not_sent');self.assertFalse(s.proc.is_alive())

    def test_boot_memory_failure_is_classified_without_private_exception_text(self):
        s=Supervisor(options(boot_failure=True),timeout=10)
        with self.assertRaises(RuntimeFailure) as found:s.start()
        self.assertEqual(found.exception.runtime_code,'out_of_memory')
        self.assertEqual(found.exception.delivery,'not_sent')
        self.assertNotIn('numeric-fixture-only',str(found.exception))

    def test_crash_before_and_after_generate_have_distinct_delivery(self):
        for flag,delivery in [('prepare_crash','not_sent'),('generate_crash','unknown')]:
            with Supervisor(options(**{flag:True}),timeout=10) as s:
                with self.assertRaises(RuntimeFailure) as found:s.infer('1',lambda p:None)
                self.assertEqual(found.exception.delivery,delivery)

    def test_known_generation_failure_is_accepted_and_not_retryable(self):
        with Supervisor(options(generate_failure=True),timeout=10) as s:
            with self.assertRaises(RuntimeFailure) as found:s.infer('1',lambda p:None)
            self.assertEqual(found.exception.delivery,'accepted');self.assertFalse(found.exception.retryable)
            with self.assertRaises(IntegrityError):s.infer('2',lambda p:None)

    def test_prepared_logging_failure_prevents_generation(self):
        with Supervisor(options(),timeout=10) as s:
            def fail(_):raise OSError('1')
            with self.assertRaises(RuntimeFailure) as found:s.infer('1',fail)
            self.assertEqual(found.exception.delivery,'not_sent')

    def test_resource_monitor_abort_is_external_to_inference(self):
        enabled=[]
        s=Supervisor(options(generate_hang=True),timeout=10,resource_check=lambda:['cap'] if enabled else [])
        try:
            s.start()
            with self.assertRaises(RuntimeFailure) as found:s.infer('1',lambda p:enabled.append(1))
            self.assertEqual(found.exception.runtime_code,'resource_guard_failed')
            self.assertEqual(found.exception.delivery,'unknown')
        finally:s.close()
        self.assertFalse(s.proc.is_alive())

    @unittest.skipUnless(os.name=='nt','Windows kill-on-close containment')
    def test_parent_process_crash_kills_mock_worker_via_job_object(self):
        import psutil
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'pid.json'
            result=subprocess.run([sys.executable,str(Path(__file__).parent/'phase_h_crash_probe.py'),str(path)],
                                  capture_output=True,timeout=10)
            self.assertEqual(result.returncode,73)
            pid=json.loads(path.read_bytes())['pid'];deadline=time.monotonic()+3
            while psutil.pid_exists(pid) and time.monotonic()<deadline:time.sleep(.02)
            self.assertFalse(psutil.pid_exists(pid))


if __name__=='__main__':unittest.main()
