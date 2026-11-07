import pytest
from app.services import emag_playbook_rules as r

OFFERS = [{'id': 1, 'general_stock': 2}, {'id': 2, 'general_stock': 0}]


def test_unknown_zero_and_metrics():
    checks = {c['key']: c['status'] for c in r.assess('ads', {'budget_ron': '0'}, OFFERS)['checks']}
    assert checks['budget'] == 'failed'
    assert checks['balance'] == 'unknown'
    p = {'spend_ron': '12', 'clicks': '3', 'revenue_ron': '24'}
    assert r.assess('ads', p, OFFERS)['metrics'] == {}
    p.update(period_start='2026-01-01T00:00:00Z', period_end='2026-01-02T00:00:00Z')
    assert r.assess('ads', p, OFFERS)['metrics'] == {'cpc_ron': '4', 'roas': '2'}


@pytest.mark.parametrize('kind,payload', [
    ('listing', {'extra': True}), ('listing', {'ean_matches': 'yes'}),
    ('listing', {'evidence_url': 'https://user:pass@example.org'}),
    ('competitor', {'price_gross_ron': 1}), ('ads', {'clicks': '1.5'}),
    ('ads', {'clicks': '2', 'impressions': '1'}), ('ads', {'spend_ron': 'NaN'}),
    ('ads', {'period_start': '2026-01-01'}),
    ('variant', {'members': [{'product_id': '1', 'value': 'a'}, {'product_id': '9', 'value': 'b'}]}),
    ('inbound', {'box_count': '1', 'items': [{'product_id': '1', 'quantity': '1', 'box': '2'}]}),
    ('cost_evidence', {'cost_field': 'invented'}), ('cost_evidence', {'unit': 'USD'}),
])
def test_validation(kind, payload):
    with pytest.raises(ValueError):
        r.validate_payload(kind, payload, OFFERS)


def test_sources_and_repairs():
    assert len(r.sources()) == 7
    snapshot = {'platform': 'emag', 'marketplace': 'RO', 'data': {'offers': [
        {'id': 1, 'general_stock': 2, 'offer_validation_status': [{'value': 2}]}]}}
    assert r.repair_guidance(snapshot)[0]['product_id'] == '1'


def test_variants_and_inbound_identity_boundaries():
    variants = {'members': [{'product_id': '1', 'value': 'red'}, {'product_id': '2', 'value': 'blue'}]}
    checks = {c['key']: c['status'] for c in r.assess('variant', variants, OFFERS)['checks']}
    assert checks == {'family_metadata': 'unknown', 'distinct_members': 'passed'}
    for members in ([{'product_id': '1', 'value': 'red'}] * 2,
                    [{'product_id': '1', 'value': 'red'}, {'product_id': '2', 'value': 'red'}]):
        with pytest.raises(ValueError):
            r.validate_payload('variant', {'members': members}, OFFERS)
    first = {'product_id': '1', 'quantity': '1', 'box': '1', 'ean': 'a', 'expected_ean': 'a'}
    for second in ({**first}, {**first, 'box': '2', 'ean': 'b'}, {**first, 'product_id': '2'}):
        with pytest.raises(ValueError):
            r.validate_payload('inbound', {'items': [first, second]}, OFFERS)


def test_inbound_unknown_and_mismatch():
    item = {'product_id': '1', 'quantity': '1', 'box': '1'}
    def barcode():
        return next(c['status'] for c in r.assess('inbound', {'items': [item]}, OFFERS)['checks'] if c['key'] == 'barcodes')
    assert barcode() == 'unknown'
    item.update(ean='a', expected_ean='b')
    assert barcode() == 'failed'


@pytest.mark.parametrize('kind,payload', [
    ('ads', {'period_start': '2026-01-02T00:00:00Z', 'period_end': '2026-01-01T00:00:00Z'}),
    ('cost_evidence', {'observed_at': '2026-01-02T00:00:00Z', 'valid_until': '2026-01-01T00:00:00Z'}),
    ('ads', {'orders': '-1'}), ('ads', {'orders': 'Infinity'}), ('ads', {'orders': '1000000001'}),
    ('listing', {'description': 'x' * 40001}), ('listing', {'main_image_white': False}),
    ('competitor', {'url': 'javascript:alert(1)'}), ('competitor', {'url': 'https://example.org:bad'}),
])
def test_more_malformed_boundaries(kind, payload):
    with pytest.raises(ValueError):
        r.validate_payload(kind, payload, OFFERS)


def test_no_metric_with_zero_denominator_or_incomplete_period():
    payload = {'clicks': '0', 'spend_ron': '0', 'revenue_ron': '4',
               'period_start': '2026-01-01T00:00:00Z', 'period_end': '2026-01-02T00:00:00Z'}
    assert r.assess('ads', payload, OFFERS)['metrics'] == {}
    payload.pop('period_end')
    payload.update(clicks='1', spend_ron='2')
    assert r.assess('ads', payload, OFFERS)['metrics'] == {}


def test_manual_ads_readiness_requires_active_statuses_and_snapshot_stock():
    payload = {'campaign_status': 'active', 'adset_status': 'paused', 'buy_button': 'confirmed',
               'listing_ready': 'confirmed', 'budget_ron': '1', 'balance_ron': '1'}
    checks = {c['key']: c['status'] for c in r.assess('ads', payload, OFFERS[:1])['checks']}
    assert checks['stock'] == 'passed'
    assert checks['adset_status'] == 'failed'
    assert next(c['status'] for c in r.assess('ads', {}, [{'id': 1}])['checks'] if c['key'] == 'stock') == 'unknown'


def test_whitespace_barcodes_do_not_establish_readiness():
    payload = {'items': [{'product_id': '1', 'quantity': '1', 'box': '1', 'ean': ' ', 'expected_ean': ' '}]}
    checks = r.assess('inbound', payload, OFFERS)['checks']
    assert next(c['status'] for c in checks if c['key'] == 'barcodes') == 'unknown'


def test_archive_locators_and_known_ads_date():
    sources = {s['id']: s for s in r.sources()}
    assert 'S03' in sources['category']['locator']
    assert 'S02' in sources['listing']['locator']
    assert '20–21' in sources['batch_import']['locator']
    assert '2024-07' in sources['ads']['version']
    assert all('/home/' not in s['locator'] and 'http' not in s['locator'] for s in sources.values())


@pytest.mark.parametrize('payload,status', [({}, 'unknown'),
    ({'source_language': 'en', 'content_language': 'ro'}, 'failed'),
    ({'source_language': 'ro', 'content_language': 'ro'}, 'passed')])
def test_listing_language_consistency(payload, status):
    assert next(c['status'] for c in r.assess('listing', payload, OFFERS)['checks'] if c['key'] == 'language_consistency') == status


@pytest.mark.parametrize('field,unit', [('purchase_cny', 'RON'), ('cny_to_ron', 'CNY'),
                                       ('commission_pct', 'RON'), ('other_ron', 'percent')])
def test_cost_units_must_match_field(field, unit):
    with pytest.raises(ValueError):
        r.validate_payload('cost_evidence', {'cost_field': field, 'unit': unit}, OFFERS)


@pytest.mark.parametrize('field,unit', [('purchase_cny', 'CNY'), ('domestic_cny', 'CNY'),
                                       ('cny_to_ron', 'RON_per_CNY'), ('commission_pct', 'percent'),
                                       ('vat_pct', 'percent'), ('other_ron', 'RON')])
def test_matching_cost_units(field, unit):
    payload = {'cost_field': field, 'unit': unit, 'value': '0'}
    assert r.validate_payload('cost_evidence', payload, OFFERS)['value'] == '0'
    assert next(c['status'] for c in r.assess('cost_evidence', payload, OFFERS)['checks'] if c['key'] == 'calculator_comparison') == 'unknown'


def test_rejection_repair_contains_review_steps_not_root_cause_claims():
    snapshot = {'platform': 'emag', 'marketplace': 'RO', 'data': {'offers': [
        {'id': 1, 'general_stock': 2, 'validation_status': [{'value': 8}]}]}}
    repair = next(x for x in r.repair_guidance(snapshot) if x['reason'] == 'documentation_rejected')
    assert {'review_main_image', 'review_mandatory_attributes', 'review_language', 'review_barcode'} <= set(repair['rule_ids'])
    assert 'root_cause' not in repair

@pytest.mark.parametrize('value', ['1e-1000000', '0e999999999999999999', '0.0000000000001'])
def test_extreme_decimal_scale_is_validation_error(value):
    payload = {'spend_ron': value, 'revenue_ron': '1',
               'period_start': '2026-01-01T00:00:00Z', 'period_end': '2026-01-02T00:00:00Z'}
    with pytest.raises(ValueError):
        r.assess('ads', payload, OFFERS)


def test_small_business_decimals_and_zero_remain_valid():
    p = {'spend_ron': '0.000001', 'clicks': '1', 'revenue_ron': '1',
         'period_start': '2026-01-01T00:00:00Z', 'period_end': '2026-01-02T00:00:00Z'}
    assert r.assess('ads', p, OFFERS)['metrics']['roas'] == '1E+6'
    assert r.validate_payload('ads', {'spend_ron': '0'}, OFFERS)['spend_ron'] == '0'
