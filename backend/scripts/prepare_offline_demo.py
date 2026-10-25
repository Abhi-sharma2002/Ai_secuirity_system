"""Export EXISTING synthetic test fixtures outside genuine experiment storage."""
import argparse
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from app.storage import registry as reg
from app.evaluation import experiment as exp
from backend.tests.evaluation.test_phase9_evaluation import row


def prepare(output):
    output=Path(output)
    if output.resolve().is_relative_to(reg.ROOT.resolve()):
        raise ValueError('Synthetic demo must be outside application runtime storage')
    output.mkdir(parents=True,exist_ok=False)
    for name,rows in [('empty',[]),('partial-unreviewed',[row('A')]),
                      ('arithmetic-fixture',[row(m,False,True) for m in 'ABC'])]:
        source=output/name/'source';source.mkdir(parents=True)
        spec={'experiment_id':'SYNTHETIC-PRESENTATION-FIXTURE','protocol':'paired',
              'output_origin':'synthetic_fixture','workload':{'case_attempts':3}}
        (source/'experiment.json').write_text(json.dumps({'specification':spec},indent=2))
        for i,r in enumerate(rows):
            r=deepcopy(r);r['experiment_id']=spec['experiment_id']
            if name=='arithmetic-fixture':
                r['judgment'].update(reviewer='SYNTHETIC TEST LABEL; NOT HUMAN REVIEW',quality=4)
                r['response']['latency_ms']=10+i
            (source/f'case-fixture-{i}.json').write_text(json.dumps(r,indent=2))
        with redirect_stdout(io.StringIO()):exp.report(source,output/name/'exports')
    (output/'README.md').write_text('# SYNTHETIC VERIFICATION ONLY\n\n'
        'Existing test_phase9_evaluation.row fixtures; no model calls or actual human grades. '
        'These files verify empty, partial/unreviewed and arithmetic presentation. '
        'They are outside genuine experiments and must never be imported as security results.\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    prepare(p.parse_args().output)
