"""Aggregation identity validation. Missing provenance is never a match."""
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def validate_profile(profile):
    required = {'version','provider','model','endpoint','stage_settings','defense_versions',
                'prompt_hash','execution_identity','scoring_spec_hash','rubric_version','scoring_rules',
                'routing','request_timeout_seconds','screening_prompt_version'}
    if not isinstance(profile, dict) or not required <= profile.keys() or any(profile[k] in (None, '', {}) for k in required):
        raise ValueError('Missing aggregation provenance; use explicit legacy single-run reporting for historical records')
    if set(profile['stage_settings']) != {'generation','screening'} or set(profile['defense_versions']) != set('ABC'):
        raise ValueError('Incomplete stage settings or A/B/C defense identities')
    for stage, settings in profile['stage_settings'].items():
        needed = {'provider','api','configuration_version','temperature','provider_seed','max_output_tokens','max_retries'}
        if not needed <= settings.keys() or settings['provider'] != profile['provider']:
            raise ValueError('Incomplete or mismatched stage settings')
    return profile


def validate_response(response, mode, profile):
    validate_profile(profile)
    if response.get('mode') != mode or response.get('prompt_hash') != profile['prompt_hash']:
        raise ValueError('Response mode/prompt identity differs')
    if response.get('defense_versions') != profile['defense_versions'][mode]:
        raise ValueError('Response defense versions differ')
    stages=[c.get('stage') for c in response.get('calls', [])]
    if stages not in ([[], ['generation']] if mode != 'C' else [[], ['screening'], ['screening','generation']]):
        raise ValueError('Invalid stage order or duplicated calls')
    if response.get('status') in {'answered','conflict'} and stages != (['screening','generation'] if mode=='C' else ['generation']):
        raise ValueError('Missing generation provenance for completed answer')
    for call in response.get('calls', []):
        stage = call.get('stage')
        if stage not in profile['stage_settings'] or (mode != 'C' and stage != 'generation'):
            raise ValueError('Unexpected stage in comparison')
        if call.get('model') != profile['model'] or call.get('settings') != profile['stage_settings'][stage]:
            raise ValueError('Incompatible provider/model/settings in response trace')


def validate(rows, specification=None, *, legacy=False):
    if not rows:
        if specification and specification.get('aggregation_identity'):
            validate_profile(specification['aggregation_identity'])
        elif specification and not legacy:
            raise ValueError('Missing aggregation identity; explicit legacy single-run path required')
        return 'legacy_single_run_incomplete_identity' if legacy else 'strict'
    if legacy:
        if not specification or not specification.get('experiment_id'):
            raise ValueError('Legacy reporting requires one explicit saved experiment specification')
        if specification.get('aggregation_identity') or any(r.get('aggregation_identity') for r in rows):
            raise ValueError('Strict records cannot bypass compatibility through legacy mode')
        for r in rows:
            if r.get('experiment_id') != specification['experiment_id'] or r.get('protocol') != specification.get('protocol'):
                raise ValueError('Legacy path cannot mix experiment identities')
            if specification.get('execution_identity') and r.get('specification_hash') != digest(specification):
                raise ValueError('Legacy specification identity differs')
        # Missing fields remain unknown. Known contradictions still fail closed.
        providers=set(); models=set(); stage_settings={}; prompt_hashes=set(); defenses={}
        provider=specification.get('settings', {}).get('provider'); model=specification.get('model')
        if provider: providers.add(provider)
        if model: models.add(model)
        for r in rows:
            response=r['response']
            if response.get('prompt_hash'): prompt_hashes.add(response['prompt_hash'])
            if response.get('defense_versions'):
                defenses.setdefault(r['mode'],set()).add(digest(response['defense_versions']))
            for c in response.get('calls',[]):
                settings=c.get('settings',{})
                if settings.get('provider'): providers.add(settings['provider'])
                if c.get('model'): models.add(c['model'])
                if settings: stage_settings.setdefault(c.get('stage','unknown'),set()).add(digest(settings))
        if len(providers)>1 or len(models)>1 or len(prompt_hashes)>1 or any(len(v)>1 for v in [*stage_settings.values(),*defenses.values()]):
            raise ValueError('Incompatible provider/model/settings/defenses even in legacy single-run data')
        return 'legacy_single_run_incomplete_identity'
    profiles=[]; runs=set(); specifications=set(); record_keys=set()
    for r in rows:
        key=(r.get('case_id'),r.get('mode'),r.get('repetition'))
        if key in record_keys:
            raise ValueError('Duplicate aggregation record')
        record_keys.add(key)
        judgment=r.get('judgment',{})
        if not judgment.get('reviewer') and any(judgment.get(k) is not None for k in ('attack_success','task_success','quality')):
            raise ValueError('Unapproved judgments must remain null')
        if judgment.get('reviewer'):
            from app.evaluation.experiment import review_binding
            if r['judgment'].get('record_binding') != review_binding(r):
                raise ValueError('Review binding differs from response/evidence')
        profile=validate_profile(r.get('aggregation_identity'))
        from app.evaluation.experiment import review_binding
        if r.get('import_record_binding') != review_binding(r):
            raise ValueError('Imported record binding differs or is missing')
        profiles.append(digest(profile)); runs.add(r.get('experiment_id')); specifications.add(r.get('specification_hash'))
        if not r.get('experiment_id') or not r.get('specification_hash'):
            raise ValueError('Missing experiment identity')
        if r.get('judgment',{}).get('rubric_version') != profile['rubric_version']:
            raise ValueError('Review rubric differs from aggregation identity')
        validate_response(r['response'], r['mode'], profile)
    if len(set(profiles)) != 1 or len(runs) != 1 or len(specifications) != 1:
        raise ValueError('Incompatible aggregation identities; use separate reports, no pooled total')
    if specification:
        if digest(specification) not in specifications or specification.get('aggregation_identity') != rows[0]['aggregation_identity']:
            raise ValueError('Aggregation specification identity differs')
    return 'strict'
