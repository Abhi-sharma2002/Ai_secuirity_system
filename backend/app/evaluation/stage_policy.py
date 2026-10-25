"""Future selection policy only. This module grants no execution capacity."""
FINAL_POLICY_VERSION = 'final-eligible27-v2'
WITHHELD_FINAL_CASE_IDS = ('final-16', 'final-22', 'final-28')
FINAL_CASE_IDS = tuple(f'final-{n:02d}' for n in range(1, 31)
                       if f'final-{n:02d}' not in WITHHELD_FINAL_CASE_IDS)


def final_workload():
    return {'policy_version': FINAL_POLICY_VERSION, 'case_ids': list(FINAL_CASE_IDS),
            'withheld_case_ids': list(WITHHELD_FINAL_CASE_IDS),
            'cases': 27, 'records': 81, 'max_calls': 108,
            'max_new_units': 3456000, 'proposed_window_hours': 2,
            'active': False, 'screening_settings_status': 'pending separate adoption; runtime unchanged'}
