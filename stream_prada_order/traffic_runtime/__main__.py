"""Offline commands only: no start/infer/download/enable or victim endpoint."""
import argparse
import json
from pathlib import Path

from .policy import read_json,profile,bindings
from .readiness import readiness
from .audit import runtime_audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
    commands.add_parser('describe')
    r=commands.add_parser('readiness')
    for name in ['snapshot','approval','evidence-root','manifest','query-plan','storage-root']:r.add_argument('--'+name,type=Path)
    r.add_argument('--approval-sha256')
    a=commands.add_parser('audit');a.add_argument('--root',type=Path,required=True)
    b=commands.add_parser('bindings');b.add_argument('--manifest',type=Path,required=True);b.add_argument('--query-plan',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='describe':result={'profile':profile(),'real_execution_enabled':False,'model_loaded':False}
        elif args.command=='readiness':
            result=readiness(args.snapshot,args.approval,args.approval_sha256,
                    read_json(args.manifest) if args.manifest else None,
                    read_json(args.query_plan) if args.query_plan else None,args.evidence_root,args.storage_root)
        elif args.command=='bindings':result=bindings(read_json(args.manifest),read_json(args.query_plan))
        else:result=runtime_audit(args.root)
        print(json.dumps(result,indent=2,ensure_ascii=True,allow_nan=False))
        return 2 if result.get('status')=='BLOCKED' else 0
    except Exception:
        print(json.dumps({'status':'BLOCKED','codes':['offline_validation_failed'],'real_execution_enabled':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
