"""Prepare local, inactive evaluation/review artifacts. Never activates or calls providers."""
import csv
import hashlib
import json
import os
from pathlib import Path
import random
from unittest.mock import patch

from app.core.config import LiveSettings
from app.evaluation import experiment as exp, semantics
from app.defenses import screening
from app.defenses.contracts import Answer
from app.llm.experiment_settings import identity_settings

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'docs/evaluation/trial-execution-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    path = OUTPUT/name
    if path.exists():
        raise ValueError('Preparation output exists; preserve it and create a new version')
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True)+'\n')


def main():
    # No prepare(), run(), report(), registry mutation, retrieval or model loading.
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((exp.DATASET/'manifest.json').read_text())
    annotations = json.loads((exp.DATASET/'annotations.json').read_text())
    old = json.loads((ROOT/'docs/evidence/consolidated-remaining-execution-proposal-v1.json').read_text())
    approved = json.loads((ROOT/'docs/evidence/development-approval-preparation-v1/binding.json').read_text())
    assert sha(exp.DATASET/'annotations.json') == approved['annotation_hash']
    assert sha(exp.DATASET/'manifest.json') == (exp.DATASET/'manifest.sha256').read_text().strip()
    rules = semantics.snapshot()
    config = LiveSettings.from_env()
    with patch('socket.socket.connect', side_effect=AssertionError('Preparation has no network')):
        implementation = exp.execution_identity()
    proposed_settings = identity_settings() | {
        'screening_prompt_version': screening.PROMPT_VERSION,
        'screening_reasoning_effort': 'minimal', 'answering_reasoning_effort': 'not sent',
        'request_timeout_seconds': 30, 'stream': False, 'protocol': 'paired',
        'repetitions': 1, 'local_schedule_seed': 5,
        'pacing': 'Existing evaluator/gate pacing; serial, zero extra generic-evaluator delay; no retries'}
    plans = {
        'verification': {'candidate_label': 'azure-d08-contract-v2-verification-stage-v2',
            'case_ids': ['development-08'], 'scope': 'screening_only; also tests authentication; no separate authentication request',
            'records': 0, 'max_calls': 1, 'max_new_units': 32000, 'window_hours': 1},
        'development': {'candidate_label': 'azure-development-eligible5-contract-v2-stage-v2',
            'case_ids': [f'development-{i:02}' for i in range(8,13)], 'records': 15,
            'max_calls': 20, 'max_new_units': 640000, 'window_hours': 2},
        'final': {'candidate_label': 'azure-final-eligible27-contract-v2-stage-v2',
            'case_ids': [f'final-{i:02}' for i in range(1,31) if i not in (16,22,28)], 'records': 81,
            'max_calls': 108, 'max_new_units': 3456000, 'window_hours': 2,
            'conditional': 'Successful correction verification, completed reviewed development, explicit readiness/configuration acceptance'},
        'interactive': {'candidate_label': 'azure-interactive-benign-contract-v2-stage-v2',
            'case_ids': [], 'records': None, 'max_calls': 5, 'max_new_units': 160000, 'window_hours': 1,
            'scope': 'Benign local-source Ask/demo only, user-triggered; no benchmark or prohibited payloads'}}
    shared = {'status': 'DRAFT; PROPOSAL ONLY; NOT AUTHORIZED OR ACTIVATED',
        'implementation_identity': implementation, 'implementation_identity_sha256': exp.digest(implementation),
        'dataset_manifest_sha256': sha(exp.DATASET/'manifest.json'),
        'annotations_sha256': sha(exp.DATASET/'annotations.json'),
        'snapshot_sha256': sha(exp.DATASET/'snapshot.json'),
        'scoring_sha256': sha(exp.SCORING_SPEC), 'approved_semantics': rules,
        'legacy_e037_rubric_sha256': sha(exp.DATASET/'revisions/legacy-e037-task-v2/rubric.json'),
        'prompt_hash': exp.PROMPT_HASH,
        'screening_schema_sha256': exp.digest(screening.Screening.model_json_schema()),
        'answer_schema_sha256': exp.digest(Answer.model_json_schema()),
        'azure_deployment': config.model, 'model': 'gpt-5-mini', 'model_version': '2025-08-07',
        'endpoint_sha256': hashlib.sha256(config.base_url.encode()).hexdigest(),
        'proposed_settings': proposed_settings, 'final_dataset_role': 'exposed; never untouched holdout',
        'execution_identity_frozen': False, 'generation_authorized': False,
        'activation_times': None, 'receipt_created': False,
        'required_adoption': 'Minimal reasoning for C screening across proposed new stages requires explicit approval and stage-profile wiring before activation; current default unchanged.'}
    write('identity-inputs.json', shared)
    for name, split in [('development','development'),('final','final')]:
        plan = plans[name];rng = random.Random(5);order={}
        for c in [c for c in manifest['cases'] if c['split']==split]:
            modes=list('ABC');rng.shuffle(modes)
            if c['case_id'] in plan['case_ids']:order[c['case_id']]=modes
        assert order == {k:v for k,v in old['plans'][name]['mode_orders'].items() if k in plan['case_ids']}
        plan['mode_orders']=order
        planned=[];reviews=[]
        for cid in plan['case_ids']:
            c=next(c for c in manifest['cases'] if c['case_id']==cid)
            ann=next(a for a in annotations['cases'] if a['case_id']==cid)
            policy=next(p for p in annotations['policies'] if p['policy_id']==ann['policy_id'])
            for mode in order[cid]:
                planned.append({'case_id':cid,'mode':mode,'repetition':0,'maximum_calls':2 if mode=='C' else 1,
                    'reservation_units':64000 if mode=='C' else 32000,'status':'not_executed'})
            reviews.append({'case_id':cid,'query':c['query'],'expected_task':c['expected_task'],
                'expected_legitimate_policy_facts':policy['facts'], 'expected_behavior':policy['behavior'],
                'attack_objective':c['attack_objective'],'category':{k:c[k] for k in ['adversarial','channel','subtype']},
                'expected_source_support':ann['support'],'approved_scoring':semantics.criteria(rules,cid),
                'rubric_version':c['rubric_version'],'mode_order':order[cid],
                'actual_initial_evidence':None,'source_exposure':None,'A_response':None,'B_response':None,'C_response':None,
                'C_screening_and_retained_evidence':None,'reviewer':None,'human_approved':False,
                'review_status':'pending_execution; not an importable response-bound judgment',
                'required_review_fields':['attack_success','task_success','benign_false_positive_if_applicable',
                    'quality_0_to_4','citation_support','retrieval_and_answering_exposure','uncertainty_notes']})
        assert len(planned)==plan['records']
        assert sum(p['maximum_calls'] for p in planned)==plan['max_calls']
        assert sum(p['reservation_units'] for p in planned)==plan['max_new_units']
        write(name+'-review-preparation.json',reviews)
        with (OUTPUT/(name+'-schedule.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(planned[0]));writer.writeheader();writer.writerows(planned)
        write(name+'-conditional-identity.json',{'stage':name,'identity_inputs_sha256':exp.digest(shared),
            'plan':plan,'actual_execution_identity':None,'actual_case_evidence_bindings':None,
            'status':'conditional candidate; not frozen or authorized'})
    total_calls=sum(p['max_calls'] for p in plans.values());total_units=sum(p['max_new_units'] for p in plans.values())
    assert (total_calls,total_units)==(134,4288000)
    write('proposal.json',{'status':'DRAFT; NO ALLOCATION OR EXECUTION', 'plans':plans,
        'total_max_calls':total_calls,'total_max_new_units':total_units,
        'withheld_development':['development-07-A','development-07-B','development-07-C'],
        'withheld_final':['final-16','final-22','final-28'],'reviewed_development_not_rerun':[f'development-{i:02}' for i in range(1,7)],
        'new_development_population':'08 C is a new-prompt treatment after old failure; 14 other eligible records unexecuted',
        'existing_allocations_reused':False,'new_capacity_granted':0})
    write('preparation-checks.json',{'provider_calls':0,'allowances_created':0,'model_downloads':0,
        'schedule_parity_with_prior_preparation':True,'development_records':15,'final_records':81,
        'budget_arithmetic_passed':True,'approved_semantics_bound':True,
        'historical_benign_reviews_reused':18,'legacy_e037_version_preserved':True})
    print(json.dumps({'prepared':True,'provider_calls':0,'new_capacity':0,'development_records':15,'final_records':81,'max_calls_proposed':total_calls,'units_proposed':total_units}))


if __name__=='__main__':
    main()
