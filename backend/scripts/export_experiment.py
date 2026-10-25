"""Read saved artifacts and export to a NEW directory; no registry/provider use."""
import argparse
from pathlib import Path
from app.evaluation.experiment import report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--legacy-single-run', action='store_true')
    args=p.parse_args()
    report(args.source,args.output,legacy=args.legacy_single_run)


if __name__=='__main__':main()
