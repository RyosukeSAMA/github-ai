import pytest

from pantheon.desktop.plans import suggest_plans, validate_ratings


def providers():
    return [{'id': 'fixture', 'enabled': True, 'connection_saved': True, 'key_configured': True,
             'test_model': 'small', 'api_health': {'state': 'verified'},
             'models': [{'id': 'small', 'available': True}, {'id': 'large', 'available': True}, {'id': 'retired', 'available': False}]}]


def test_plans_do_not_infer_prices_quality_or_other_models_access():
    result = suggest_plans(providers(), {}, {})
    assert [item['model'] for item in result['candidates']] == ['small']
    assert all(item['choice'] is None for item in result['plans'])
    assert result['candidates'][0]['quality'] is None


def test_cost_quality_and_balanced_use_explicit_user_data():
    rates = {'fixture/small': {'input': 1, 'output': 1}, 'fixture/large': {'input': 8, 'output': 10}}
    ratings = {'fixture/small': {'quality': 2, 'capabilities': ['text']}, 'fixture/large': {'quality': 5, 'capabilities': ['text', 'tools']}}
    result = suggest_plans(providers(), rates, ratings, verified_only=False)
    assert result['plans'][0]['choice']['model'] == 'small'
    assert result['plans'][2]['choice']['model'] == 'large'
    assert result['plans'][2]['choice']['verified'] is False
    assert suggest_plans(providers(), rates, ratings, required=['tools'])['candidates'] == []
    assert suggest_plans(providers(), rates, ratings, verified_only=False, required=['tools'])['plans'][2]['choice']['model'] == 'large'


def test_disabled_missing_key_and_unlisted_models_are_excluded():
    for key in ['enabled', 'key_configured', 'connection_saved']:
        value = providers()
        value[0][key] = False
        assert not suggest_plans(value, {}, {}, verified_only=False)['candidates']


@pytest.mark.parametrize('value', [True, float('nan'), 0, 6, '5'])
def test_quality_rating_requires_an_explicit_finite_score(value):
    with pytest.raises(ValueError):
        validate_ratings({'fixture/small': {'quality': value, 'capabilities': ['text']}})


def test_successful_model_specific_probe_can_verify_a_catalog_omitted_alias():
    value = providers()
    value[0]['models'][0]['available'] = False
    result = suggest_plans(value, {'fixture/small': {'input': 1, 'output': 1}}, {})
    assert result['plans'][0]['choice']['model'] == 'small'
    assert result['plans'][0]['choice']['verified'] is True
    value[0]['api_health']['state'] = 'expired'
    assert suggest_plans(value, {}, {}, verified_only=False)['candidates'] == [
        item for item in suggest_plans(providers(), {}, {}, verified_only=False)['candidates'] if item['model'] == 'large']
