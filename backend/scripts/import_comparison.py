"""Offline bridge from authoritative saved requests; never activates/calls a model."""
import argparse
import contextlib
import io
from pathlib import Path
from app.evaluation.dataset import read_json
from app.evaluation.comparison_review import import_saved
from app.storage import registry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-id',required=True)
    parser.add_argument('--criteria',type=Path,required=True)
    parser.add_argument('--database',type=Path,default=registry.ROOT/'registry.sqlite3')
    parser.add_argument('--output-root',type=Path,default=registry.ROOT/'experiments')
    parser.add_argument('--exported-comparison',type=Path,help='Optional downloaded JSON; must exactly match the authoritative saved request')
    args=parser.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        folder=import_saved(args.database,args.request_id,read_json(args.criteria),args.output_root,
            exported=read_json(args.exported_comparison) if args.exported_comparison else None)
    print('Unreviewed interactive comparison imported:',folder)
    print('Inspect review-packets.json; fill review-template.json explicitly before importing judgments.')


if __name__=='__main__':main()
