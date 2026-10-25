"""Read the shared evaluation settings without private environment overrides."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / 'eval_config.yaml'
KEYS = {'provider', 'model', 'temperature', 'max_tokens', 'top_k',
        'chunk_size', 'chunk_overlap', 'judge_model'}


class EvaluationError(ValueError):
    """A controlled local explanation, containing no provider payload or credential."""


def load_config():
    try:
        config = yaml.safe_load(CONFIG_PATH.read_text())
    except (OSError, yaml.YAMLError):
        raise EvaluationError('Missing or invalid eval_config.yaml') from None
    if not isinstance(config, dict) or set(config) != KEYS:
        raise EvaluationError('eval_config.yaml must contain exactly the eight required keys')
    if (config['provider'] != 'openrouter'
            or config['model'] != 'nvidia/nemotron-3-ultra-550b-a55b:free'):
        raise EvaluationError('Evaluation configuration must use the fixed OpenRouter free route')
    if type(config['temperature']) not in (int, float) or config['temperature'] != 0:
        raise EvaluationError('Evaluation temperature must be zero')
    if any(type(config[k]) is not int or config[k] <= 0 for k in ('max_tokens', 'top_k', 'chunk_size')):
        raise EvaluationError('Evaluation token, retrieval and chunk limits must be positive integers')
    if config['top_k'] > 20 or type(config['chunk_overlap']) is not int or not 0 <= config['chunk_overlap'] < config['chunk_size']:
        raise EvaluationError('Invalid evaluation retrieval or chunk overlap settings')
    if config['judge_model'] is not None:
        raise EvaluationError('A separate judge route is not authorized')
    return config
