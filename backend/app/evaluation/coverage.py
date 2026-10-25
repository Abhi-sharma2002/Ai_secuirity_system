"""Read-only coverage-v2 projection; no semantic grading or historical rewrites."""
COMPLETED = {'answered', 'insufficient_evidence', 'conflict', 'policy_blocked'}


def describe(spec, rows):
    workload = spec.get('workload', {})
    scheduled = workload.get('case_attempts', 0)
    selected = workload.get('selected_case_ids')
    withheld = workload.get('withheld_case_ids')
    repetitions = spec.get('repetitions', workload.get('repetitions', 1))
    modes = ['A'] if spec.get('protocol') == 'baseline' else list('ABC')
    keys = [(r['case_id'], r['mode'], r['repetition']) for r in rows]
    if len(keys) != len(set(keys)) or len(rows) > scheduled:
        raise ValueError('Duplicate or excess coverage records')
    if selected is not None and any(r['case_id'] not in selected for r in rows):
        raise ValueError('Record outside selected schedule')
    if withheld is not None and (len(withheld) != len(set(withheld)) or
            set(withheld) & set(selected or [r['case_id'] for r in rows])):
        raise ValueError('Withheld cases must be outside executable schedule')
    if any(r['mode'] not in modes or not 0 <= r['repetition'] < repetitions for r in rows):
        raise ValueError('Record outside mode/repetition schedule')
    def counts(group, expected):
        complete = sum(r['response']['status'] in COMPLETED for r in group)
        interrupted = sum(r['response']['status']=='interrupted_or_in_progress' for r in group)
        calls = [c for r in group for c in r['response'].get('calls', [])]
        attempts = [c.get('attempts') for c in calls]
        return {'scheduled_records': expected, 'recorded_records': len(group),
                'completed_records': complete, 'failed_records': len(group)-complete-interrupted,
                'interrupted_records': interrupted, 'unexecuted_records': expected-len(group),
                'actual_provider_attempts_known': sum(a for a in attempts if type(a) is int and a >= 0),
                'provider_attempts_unknown_traces': sum(type(a) is not int or a < 0 for a in attempts),
                'reserved_call_slots_known': sum(len(r['response'].get('reservation_ids', [])) for r in group),
                'reserved_call_slots_unknown_records': sum('reservation_ids' not in r['response'] for r in group),
                'local_reservation_units_known': sum(r['response'].get('reservation_units') or 0 for r in group),
                'local_reservation_units_unknown_records': sum(r['response'].get('reservation_units') is None for r in group)}
    complete_cases = {r['case_id'] for r in rows if all(
        any(x['case_id']==r['case_id'] and x['mode']==m and x['repetition']==rep and
            x['response']['status'] in COMPLETED for x in rows)
        for m in modes for rep in range(repetitions))}
    return {'version':'coverage-v2', **counts(rows, scheduled),
            'scheduled_cases': len(selected) if selected is not None else workload.get('cases'),
            'recorded_cases': len({r['case_id'] for r in rows}), 'completed_cases_all_modes':len(complete_cases),
            'withheld_case_ids':withheld, 'withheld_cases':len(withheld) if withheld is not None else None,
            'withheld_records':len(withheld)*len(modes)*repetitions if withheld is not None else None,
            'withheld_outside_executable_schedule':True,
            'maximum_provider_attempts':workload.get('maximum_api_calls_without_retries'),
            'maximum_local_reservation_units':workload.get('conservative_reserved_tokens'),
            'by_mode':{m:counts([r for r in rows if r['mode']==m], scheduled//len(modes)) for m in modes},
            'definitions': 'Scheduled = executable configuration/repetition slots; withheld excluded. '
                'Recorded = completed + failed + interrupted; scheduled = recorded + unexecuted. '
                'Completed is operational, not semantic success. Unknown historical withholding stays null. '
                'Provider attempts, reserved call slots and local units are separate; no refunds inferred.'}
