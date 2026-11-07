"""Subprocess fixture: exit the supervisor parent; numeric mock worker only."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def main():
    from stream_prada_order.traffic_runtime.supervisor import Supervisor
    from stream_prada_order.traffic_runtime.policy import profile
    supervisor=Supervisor({'mode':'mock','mock_marker':'numeric-tests-only',
                            'template_sha256':profile()['chat_template_sha256']},timeout=10)
    supervisor.start()
    with Path(sys.argv[1]).open('x',encoding='utf-8') as f:
        json.dump({'pid':supervisor.proc.pid},f);f.flush();os.fsync(f.fileno())
    os._exit(73)


if __name__=='__main__':main()
