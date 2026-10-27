from types import SimpleNamespace
from unittest.mock import patch
from app.evaluation import comparison_provenance
from app.llm.experiment_settings import identity_settings
from app.rag import comparison


def test_real_azure_capture_allows_comparison_preparation_without_transport():
    config = SimpleNamespace(provider='azure_openai', model='gpt-5-mini',
                             base_url='https://synthetic.invalid/openai/v1', request_timeout_seconds=30)
    with patch.object(comparison_provenance.LiveSettings, 'from_env', return_value=config), \
         patch('app.evaluation.experiment.execution_identity', return_value={'synthetic': True}), \
         patch.object(comparison.live, 'approval', return_value=object()), \
         patch.object(comparison.live, 'allowance_capacity', return_value={
             'stopped': False, 'remaining_calls': 4, 'remaining_reserved_tokens': 128000}), \
         patch.object(comparison, 'search', return_value={'hits': [{'id': 'synthetic', 'text': 'Orientation takes 7 days.'}]}), \
         patch.object(comparison.live, 'validate_interactive_input'), \
         patch.object(comparison, 'respond', return_value={'status': 'answered'}) as respond, \
         patch('socket.socket.connect', side_effect=AssertionError('No networking')):
        result = comparison.compare('Synthetic onboarding question', 'synthetic-request')
    assert result['status'] == 'completed'
    assert respond.call_count == 3
    profile = result['review_provenance']
    assert profile['provider'] == 'azure_openai'
    for stage in ('generation', 'screening'):
        assert profile['stage_settings'][stage] == {
            'provider': 'azure_openai', 'api': 'azure_openai_v1_chat_completions', **identity_settings()}
    assert profile['routing'] == {'allow_fallbacks': False}
    assert 'api_key' not in profile
