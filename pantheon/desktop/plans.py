"""Explicit model suggestions using saved access evidence and user-entered ratings/rates."""
from __future__ import annotations

import math
import re

CAPABILITIES = {'text', 'tools', 'vision'}


def validate_ratings(values):
    if not isinstance(values, dict) or len(values) > 200:
        raise ValueError('Use up to 200 model ratings')
    result = {}
    for key, value in values.items():
        if (not isinstance(key, str) or not re.fullmatch(r'[a-z0-9_-]+/[^\s]{1,160}', key)
                or not isinstance(value, dict) or set(value) != {'quality', 'capabilities'}):
            raise ValueError('Each provider/model rating needs quality and capabilities')
        quality = value['quality']
        if type(quality) not in {int, float} or not math.isfinite(quality) or not 1 <= quality <= 5:
            raise ValueError('Your quality rating must be between 1 and 5')
        capabilities = value['capabilities']
        if not isinstance(capabilities, list) or any(not isinstance(item, str) or item not in CAPABILITIES for item in capabilities):
            raise ValueError('Choose text, tools or vision capabilities')
        result[key] = {'quality': quality, 'capabilities': sorted(set(capabilities))}
    return result


def suggest_plans(providers, prices, ratings, *, verified_only=True, required=('text',)):
    if type(verified_only) is not bool or not isinstance(required, (list, tuple)) or any(not isinstance(item, str) or item not in CAPABILITIES for item in required):
        raise ValueError('Choose valid access and capability requirements')
    ratings = validate_ratings(ratings)
    candidates = []
    for provider in providers:
        if not provider.get('connection_saved') or not provider.get('key_configured') or not provider.get('enabled', True):
            continue
        for model in provider.get('models', []):
            if model.get('available') is False:
                continue
            identity = provider['id']+'/'+model['id']
            verified = provider.get('test_model') == model['id'] and provider.get('api_health', {}).get('state') == 'verified'
            if verified_only and not verified:
                continue
            rating = ratings.get(identity, {})
            capabilities = set(rating.get('capabilities', [])) | {'text'}
            if not set(required).issubset(capabilities):
                continue
            rates = prices.get(identity)
            cost = rates['input']+rates['output'] if rates else None
            candidates.append({'provider': provider['id'], 'model': model['id'], 'verified': verified,
                               'quality': rating.get('quality'), 'capabilities': sorted(capabilities),
                               'capability_source': 'Text catalog; extra capabilities are your declarations',
                               'price': rates, 'sample_usd': cost})
    candidates.sort(key=lambda item: (item['provider'], item['model']))
    plans = []
    for kind in ['cost', 'balanced', 'quality']:
        eligible = [item for item in candidates if (kind == 'quality' or item['sample_usd'] is not None)
                    and (kind == 'cost' or item['quality'] is not None)]
        if not eligible:
            plans.append({'kind': kind, 'choice': None, 'reason': 'No eligible model. Review saved API evidence, your prices, ratings and capability requirements.'})
            continue
        if kind == 'cost':
            eligible.sort(key=lambda item: item['sample_usd'])
        elif kind == 'quality':
            eligible.sort(key=lambda item: -item['quality'])
        else:
            costs = [item['sample_usd'] for item in eligible]
            low, spread = min(costs), max(costs)-min(costs)
            eligible.sort(key=lambda item: -(.6*(item['quality']-1)/4 + .4*(1-(item['sample_usd']-low)/spread if spread else 1)))
        plans.append({'kind': kind, 'choice': eligible[0], 'reason': {'cost': 'Lowest entered price for 1M input + 1M output tokens.',
                      'balanced': '60% your quality rating + 40% normalized entered price.',
                      'quality': 'Highest quality rating entered by you; cost can remain unknown.'}[kind]})
    return {'plans': plans, 'candidates': candidates,
            'note': 'These are reviewable suggestions, not automatic routing or quality guarantees. Prices and ratings are user-entered; API evidence is model-specific. No model requests were sent.'}
