"""Apply explicit human judgments to an imported comparison; no backend/provider use."""
import argparse
import contextlib
import fcntl
import io
from pathlib import Path
from app.evaluation.dataset import read_json
from app.evaluation.experiment import adjudicate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--judgments',type=Path,required=True)
    args=parser.parse_args()
    spec=read_json(args.source/'experiment.json')['specification']
    if spec.get('source_kind')!='interactive_comparison':
        parser.error('Use the explicit legacy workflow for historical experiments; this command reviews imported comparisons only')
    with (args.source/'.review.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with contextlib.redirect_stdout(io.StringIO()):
            adjudicate(args.source,args.judgments)
    print('Human judgments imported and comparison report regenerated:',args.source)


if __name__=='__main__':main()
