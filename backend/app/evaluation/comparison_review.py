"""Import authoritative saved comparisons into separate, unapproved review runs."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import fcntl
from app.evaluation.compatibility import digest, validate_profile, validate_response


def read_saved(database, request_id):
    with sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro', uri=True) as db:
        row=db.execute('SELECT result FROM requests WHERE id=?',(request_id,)).fetchone()
    if row is None:
        raise ValueError('Saved comparison request not found')
    # The DB is authoritative, not a user-edited downloaded JSON file.
    return json.loads(row[0])


def validate_comparison(source, request_id):
    if source.get('scope') != 'benign_interactive_comparison' or source.get('source_request_id') != request_id:
        raise ValueError('Missing saved comparison request provenance; older records cannot be reconstructed from current configuration')
    profile=validate_profile(source.get('review_provenance'))
    if source.get('source_record_binding') != digest({k:v for k,v in source.items() if k!='source_record_binding'}):
        raise ValueError('Saved comparison binding differs; response/evidence was altered or binding is missing')
    if source.get('prompt_hash') != profile['prompt_hash']:
        raise ValueError('Comparison prompt identity differs')
    initial=source.get('initial_evidence')
    if not isinstance(initial,dict) or not all(k in initial for k in ('hits','snapshot','omitted_ids')):
        raise ValueError('Missing saved initial retrieval provenance')
    results=source.get('results')
    if not isinstance(results,dict) or not set(results)<=set('ABC'):
        raise ValueError('Invalid comparison modes')
    modes=list(results)
    if modes not in [[],['A'],['A','B'],['A','B','C']]:
        raise ValueError('Comparison execution is not the saved A/B/C prefix')
    if source.get('not_executed_modes') != [m for m in 'ABC' if m not in results]:
        raise ValueError('Missing/inconsistent unexecuted-mode coverage')
    from app.evaluation.experiment import COMPLETED
    for mode,response in results.items():
        validate_response(response,mode,profile)
        if response.get('candidate_evidence') != initial['hits'] or response.get('snapshot') != initial['snapshot'] or response.get('omitted_ids') != initial['omitted_ids']:
            raise ValueError('Comparison initial evidence differs across modes')
        for key in ('answer','references','supplied_evidence','screening','calls','latency_ms','reservation_units','reservation_ids','status'):
            if key not in response:raise ValueError('Missing response/evidence metadata: '+key)
        if response.get('question') != source.get('question'):
            raise ValueError('Comparison question differs')
        if mode != modes[-1] and response['status'] not in COMPLETED:
            raise ValueError('Comparison continued after operational error')
    if source.get('status')=='completed' and (modes!=list('ABC') or any(r['status'] not in COMPLETED for r in results.values())):
        raise ValueError('Completed comparison has incomplete/failed coverage')
    return profile


def validate_import(folder, spec, rows):
    from app.evaluation.dataset import read_json
    source=read_json(Path(folder)/'source-comparison.json')
    criteria=read_json(Path(folder)/'review-criteria.json')
    profile=validate_comparison(source,spec['source_request_id'])
    if digest(source)!=spec['source_comparison_hash'] or digest(criteria)!=spec['review_criteria_hash'] or profile!=spec['aggregation_identity']:
        raise ValueError('Imported comparison or criteria was altered')
    if set(source['results'])!={r['mode'] for r in rows} or len(rows)!=len(source['results']):
        raise ValueError('Imported comparison rows missing/duplicated')
    expected_case=case_for(source,criteria)
    for row in rows:
        if row['response']!=source['results'][row['mode']] or row['case']!=expected_case or row.get('aggregation_identity')!=profile:
            raise ValueError('Imported response/evidence/case identity was altered')


def case_for(source, criteria):
    if set(criteria)!={'question','expected_answer','review_notes','criteria_author','adversarial'} or any(not isinstance(criteria.get(k),str) or not criteria[k].strip() for k in ('question','expected_answer','review_notes','criteria_author')):
        raise ValueError('Supply question, expected_answer, review_notes, criteria_author and adversarial=false; no inferred task oracle')
    if criteria['adversarial'] is not False:
        raise ValueError('This bridge requires explicit benign classification; attack records need a separately authorized evaluation protocol')
    if criteria['question']!=source['question']:
        raise ValueError('Review criterion question differs from saved question')
    return {'case_id':'interactive-case','query':source['question'],'expected_task':criteria['expected_answer'],
            'review_notes':criteria['review_notes'],'criteria_author':criteria['criteria_author'],
            'criteria_timing':'retrospective','adversarial':False,'channel':'none','subtype':'benign',
            'attack_objective':None,'population':'interactive_not_controlled_benchmark'}


def import_saved(database, request_id, criteria, output_root, *, exported=None):
    from app.evaluation import experiment as exp
    source=read_saved(database,request_id)
    if exported is not None and exported!=source:
        raise ValueError('Downloaded comparison differs from authoritative saved response')
    profile=validate_comparison(source,request_id); case=case_for(source,criteria)
    run_id='interactive-'+digest(request_id)[:24]
    root=Path(output_root);root.mkdir(parents=True,exist_ok=True)
    destination=root/run_id
    with (root/'.comparison-import.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if destination.exists():raise FileExistsError('Comparison already imported; use its existing review run')
        spec={'experiment_id':run_id,'protocol':'interactive_paired','repetitions':1,
              'source_kind':'interactive_comparison','controlled_benchmark':False,
              'source_request_id':request_id,'source_comparison_hash':digest(source),
              'review_criteria_hash':digest(criteria),'aggregation_identity':profile,
              'output_origin':source.get('output_origin','application_execution'),
              'execution_identity':profile['execution_identity'],'scoring_spec_hash':profile['scoring_spec_hash'],
              'settings':{'provider':profile['provider']},'model':profile['model'],
              'workload':{'case_attempts':3,'selected_case_ids':[case['case_id']],'withheld_case_ids':[],
                          'cases':1,'repetitions':1,'maximum_api_calls_without_retries':4,'conservative_reserved_tokens':128000}}
        with tempfile.TemporaryDirectory(prefix='.comparison-import-',dir=root) as tmp:
            stage=Path(tmp)/'run';stage.mkdir()
            (stage/'source-comparison.json').write_text(json.dumps(source,indent=2))
            (stage/'review-criteria.json').write_text(json.dumps(criteria,indent=2))
            (stage/'experiment.json').write_text(json.dumps({'specification':spec},indent=2))
            for mode,response in source['results'].items():
                row={'experiment_id':run_id,'protocol':'interactive_paired','case_id':case['case_id'],'mode':mode,
                     'repetition':0,'specification_hash':digest(spec),'aggregation_identity':deepcopy(profile),
                     'output_origin':spec['output_origin'],'case':deepcopy(case),'response':deepcopy(response),
                     'exposed':None,'answering_exposed':None,
                     'judgment':{'attack_success':None,'task_success':None,'quality':None,'reviewer':None,'rubric_version':exp.RUBRIC}}
                row['import_record_binding']=exp.review_binding(row)
                (stage/f'case-{mode}.json').write_text(json.dumps(row,indent=2))
            exp.report(stage)
            stage.rename(destination)
    return destination
