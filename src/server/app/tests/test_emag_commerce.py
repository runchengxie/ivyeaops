from datetime import datetime, timezone
import pytest
from app.services import store_artifacts as artifacts
from app.services import emag_commerce as commerce

@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    def create():
        return artifacts.import_snapshot({'store_id':'demo-ro','platform':'emag','marketplace':'RO',
            'captured_at':datetime.now(timezone.utc).isoformat(),'source':'synthetic','coverage':['offers'],
            'limitations':['test only'],'data':{'offers':[{'id':1,'part_number':'sku-1','sale_price':'119','general_stock':10}]}})
    return create

def costs():
    return {'purchase_cny': '20','cny_to_ron': '0.65','domestic_cny': '2','international_ron': '5',
        'duties_ron': '1','fulfilment_ron': '4','other_ron': '2','commission_pct': '10','vat_pct': '19',
        'return_allowance_ron': '3','cost_basis': 'reference','quote_at': '2026-10-30T00:00:00Z'}

def test_complete_economics_and_missing_inputs():
    result=commerce.calculate(costs(),{'sale_price':'119','general_stock':10})
    assert result['economics']['contribution_ron']=='75.54'  # 119 - (22*0.65 + 5+1+4+2+3) - (119*1.19)*0.10
    assert result['economics']['status']=='reference_estimate'
    result=commerce.calculate({}, {'sale_price':'119'})
    assert result['economics']['contribution_ron'] is None
    assert 'purchase_cny' in result['economics']['missing']

@pytest.mark.parametrize('value',['NaN','Infinity','-1',True,'oops'])
def test_invalid_numbers(value):
    with pytest.raises(ValueError): commerce.calculate({**costs(),'purchase_cny':value},{'sale_price':'119'})

def test_replenishment_is_explicit_scenario():
    result=commerce.calculate({'daily_units': '2','lead_days': '10','safety_days': '3','inbound_units': '4','reserved_units': '2'},{'general_stock':10})
    assert result['replenishment']['suggested_units']==14
    assert result['replenishment']['status']=='manual_scenario'
    assert commerce.calculate({}, {})['replenishment']['suggested_units'] is None

def test_ledger_revision_source_confirmation_and_stale(snapshot):
    snap=snapshot()
    inputs={'supplier_url':'https://detail.1688.com/offer/123456.html','supplier_sku':'black XL','supplier_confirmed':True}
    result=commerce.save('demo-ro',snap['snapshot_id'],'1',0,inputs,'operator')
    assert result['revision']==1
    assert commerce.view('demo-ro')['products'][0]['record']['actor']=='operator'
    with pytest.raises(ValueError): commerce.save('demo-ro',snap['snapshot_id'],'1',0,inputs,'operator')
    newer=snapshot()
    assert commerce.view('demo-ro')['products'][0]['record']['stale'] is True
    with pytest.raises(ValueError): commerce.save('demo-ro',snap['snapshot_id'],'1',1,inputs,'operator')
    assert commerce.save('demo-ro',newer['snapshot_id'],'1',1,inputs,'operator')['revision']==2

@pytest.mark.parametrize('url',['https://evil.test/offer/1.html','http://detail.1688.com/offer/1.html','https://detail.1688.com@evil.test/offer/1.html'])
def test_invalid_supplier_links(snapshot,url):
    snap=snapshot()
    with pytest.raises(ValueError): commerce.save('demo-ro',snap['snapshot_id'],'1',0,{'supplier_url':url},'a')

def test_change_preview_never_executes_and_rejects_unsafe_values():
    result=commerce.preview({'snapshot_id':'snap'}, {'id':1,'sale_price':'10','general_stock':3}, {'sale_price':'12','general_stock':4})
    assert result['executable'] is False
    assert result['changes'][0]['before']=='10'
    with pytest.raises(ValueError): commerce.preview({'snapshot_id':'snap'},{'id':1},{'general_stock':-1})
    with pytest.raises(ValueError): commerce.preview({'snapshot_id':'snap'},{'id':1},{'title':'x'})


def test_commerce_api_auth_actor_and_stale_preview(snapshot):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.security import require_admin
    import importlib
    from app.routers import emag_operations as module
    router=importlib.reload(module).router
    snap=snapshot()
    app=FastAPI();app.include_router(router,prefix='/api/emag')
    with TestClient(app) as client:
        base='/api/emag/stores/demo-ro'
        assert client.get(base+'/commerce').status_code==401
        assert client.post(base+'/commerce/1',json={}).status_code==401
        app.dependency_overrides[require_admin]=lambda:'operator'
        result=client.post(base+'/commerce/1',json={'snapshot_id':snap['snapshot_id'],'revision':0,'inputs':costs()})
        assert result.status_code==200
        assert result.json()['actor']=='operator'
        assert client.post(base+'/commerce/99',json={'snapshot_id':snap['snapshot_id'],'revision':0,'inputs':{}}).status_code==409
        assert client.post(base+'/preview/1',json={'snapshot_id':snap['snapshot_id'],'changes':{'sale_price':'120'}}).json()['executable'] is False
        snapshot()
        assert client.post(base+'/preview/1',json={'snapshot_id':snap['snapshot_id'],'changes':{'sale_price':'120'}}).status_code==409

def test_supplier_confirmation_requires_exact_specification(snapshot):
    snap=snapshot()
    with pytest.raises(ValueError): commerce.save('demo-ro',snap['snapshot_id'],'1',0,{'supplier_confirmed':True},'a')

@pytest.mark.parametrize('field,value',[('cny_to_ron','0'),('commission_pct','101'),('vat_pct','101'),('unknown','1')])
def test_invalid_commercial_fields(field,value):
    with pytest.raises(ValueError): commerce.calculate({**costs(),field:value},{'sale_price':'119'})

def test_reserved_backlog_adds_to_replenishment_need():
    result=commerce.calculate({'daily_units':'2','lead_days':'10','safety_days':'3','inbound_units':'0','reserved_units':'20'},{'general_stock':10})
    assert result['replenishment']['suggested_units']==36

@pytest.mark.parametrize('stock',[-1,True,'10','oops'])
def test_invalid_snapshot_stock_is_unknown_not_a_calculation(stock):
    result=commerce.calculate({'daily_units':'2','lead_days':'10','safety_days':'3','inbound_units':'0','reserved_units':'0'},{'general_stock':stock})
    assert result['replenishment']['suggested_units'] is None
    assert 'general_stock' in result['replenishment']['missing']

@pytest.mark.parametrize('price',[True,'NaN','oops',-1])
def test_invalid_price_evidence_keeps_cost_record_readable(price):
    result=commerce.calculate(costs(),{'sale_price':price})
    assert result['economics']['contribution_ron'] is None
    assert 'sale_price' in result['economics']['missing']


def test_more_than_100_updates_keep_paginated_immutable_history(snapshot):
    snap=snapshot()
    for revision in range(105):
        commerce.save('demo-ro',snap['snapshot_id'],'1',revision,{'purchase_cny':str(revision)},'operator')
    record=commerce.view('demo-ro')['products'][0]['record']
    assert record['revision']==105 and len(record['history'])==100
    first=commerce.history('demo-ro','1')
    assert first['entries'][0]['revision']==105
    assert first['next_before']==6
    second=commerce.history('demo-ro','1',before_revision=6)
    assert [e['revision'] for e in second['entries']]==[5,4,3,2,1]
    assert second['entries'][-1]['inputs']['purchase_cny']=='0'
    assert commerce.history('other-ro','1')['entries']==[]


def test_legacy_inline_history_survives_first_archive_save(snapshot):
    import json
    snap=snapshot()
    old={'snapshot_id':snap['snapshot_id'],'revision':100,'inputs':{},'actor':'legacy',
         'history':[{'revision':i,'actor':'legacy','at':'2026-10-30T00:00:00Z','inputs':{'note':str(i)}} for i in range(1,101)]}
    with commerce.database() as conn:
        conn.execute('INSERT INTO products VALUES (?,?,?)',('demo-ro','1',json.dumps(old)))
    assert commerce.history('demo-ro','1')['entries'][0]['revision']==100
    commerce.save('demo-ro',snap['snapshot_id'],'1',100,{},'operator')
    assert commerce.history('demo-ro','1',before_revision=2)['entries'][0]['inputs']['note']=='1'


def test_archive_conflict_rolls_back_latest_record(snapshot):
    import json
    snap=snapshot()
    commerce.save('demo-ro',snap['snapshot_id'],'1',0,{'note':'original'},'operator')
    with commerce.database() as conn:
        conn.execute('UPDATE revisions SET payload=? WHERE store=? AND product=? AND revision=1',
                     (json.dumps({'revision':1,'inputs':{'note':'conflict'}}),'demo-ro','1'))
    with pytest.raises(ValueError,match='Archived history conflict'):
        commerce.save('demo-ro',snap['snapshot_id'],'1',1,{'note':'next'},'operator')
    assert commerce.view('demo-ro')['products'][0]['record']['revision']==1
    assert len(commerce.history('demo-ro','1')['entries'])==1


def test_emag_raw_price_is_net_and_vat_is_not_deducted_twice():
    result=commerce.calculate(costs(),{'sale_price':'119'})['economics']
    assert result['sale_price_basis']=='exclusive_vat'
    assert result['revenue_ex_vat_ron']=='119.00'
    assert result['gross_sale_price_ron']=='141.61'
    assert result['commission_ron']=='14.16'
    assert result['contribution_ron']=='75.54'


def test_net_revenue_does_not_change_with_vat_when_commission_is_zero():
    for vat in ('0','19','21'):
        result=commerce.calculate({**costs(),'vat_pct':vat,'commission_pct':'0'},{'sale_price':'119'})['economics']
        assert result['revenue_ex_vat_ron']=='119.00'
        assert result['contribution_ron']=='89.70'


def profit_inputs(**overrides):
    return {**dict.fromkeys(commerce.COSTS, '0'), 'purchase_cny': '50', 'cny_to_ron': '1',
            'commission_pct': '10', 'vat_pct': '20', 'target_margin_pct': '20', **overrides}


def test_margin_and_reverse_price_scenarios():
    result = commerce.calculate(profit_inputs(), {'sale_price': '100'})['economics']
    assert result['contribution_ron'] == '38.00'
    assert result['contribution_margin_pct'] == '38.00'
    assert result['break_even_ex_vat_ron'] == '56.82'
    assert result['target_sale_ex_vat_ron'] == '73.53'


def test_zero_revenue_and_unachievable_target_are_explicit():
    result = commerce.calculate(profit_inputs(), {'sale_price': '0'})['economics']
    assert result['contribution_margin_pct'] is None
    result = commerce.calculate(profit_inputs(target_margin_pct='90'), {'sale_price': '100'})['economics']
    assert result['target_sale_ex_vat_ron'] is None
    assert result['target_status'] == 'infeasible'
    assert commerce.calculate({}, {})['economics']['break_even_ex_vat_ron'] is None


@pytest.mark.parametrize('value', ['1e-999999', '1e999999', '0.' + '1' * 100])
def test_decimal_precision_is_bounded(value):
    with pytest.raises(ValueError):
        commerce.number(value)


def test_reverse_price_rounds_up_to_meet_target():
    result=commerce.calculate(profit_inputs(purchase_cny='1',commission_pct='0',vat_pct='0',target_margin_pct='30'),{'sale_price':'2'})['economics']
    assert result['target_sale_ex_vat_ron']=='1.43'


def test_profit_scenario_api_is_snapshot_bound_and_read_only(snapshot):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.security import require_admin
    from app.routers.emag_operations import router
    snap=snapshot();app=FastAPI();app.include_router(router,prefix='/api/emag')
    with TestClient(app) as client:
        path='/api/emag/stores/demo-ro/commerce/1/scenario'
        body={'snapshot_id':snap['snapshot_id'],'sale_price':'100','inputs':profit_inputs()}
        assert client.post(path,json=body).status_code==401
        app.dependency_overrides[require_admin]=lambda:'operator'
        result=client.post(path,json=body)
        assert result.status_code==200
        assert result.json()['economics']['contribution_margin_pct']=='38.00'
        assert result.json()['marketplace_writes'] is False
        assert commerce.view('demo-ro')['products'][0]['record'] is None
        snapshot()
        assert client.post(path,json=body).status_code==409


def test_break_even_price_never_rounds_below_costs():
    result=commerce.calculate(profit_inputs(purchase_cny='1',commission_pct='10',vat_pct='0',target_margin_pct='0'),{'sale_price':'2'})['economics']
    assert result['break_even_ex_vat_ron']=='1.12'
    assert result['target_sale_ex_vat_ron']=='1.12'


def test_extreme_allowed_costs_do_not_break_reverse_price():
    result=commerce.calculate(profit_inputs(purchase_cny='1000000000',cny_to_ron='1000000000',commission_pct='99.999999999999',vat_pct='0',target_margin_pct='0'),{'sale_price':'100'})['economics']
    assert result['break_even_ex_vat_ron']=='100000000000000000000000000000000.00'


def test_zero_cost_target_requires_positive_revenue():
    result=commerce.calculate(profit_inputs(purchase_cny='0'),{'sale_price':'100'})['economics']
    assert result['target_sale_ex_vat_ron']=='0.01'


def test_legacy_unsupported_numeric_inputs_remain_readable(snapshot):
    import json
    snap=snapshot()
    commerce.save('demo-ro',snap['snapshot_id'],'1',0,profit_inputs(),'operator')
    with commerce.database() as conn:
        row=json.loads(conn.execute('SELECT payload FROM products').fetchone()[0])
        row['inputs']['purchase_cny']='1e-999'
        conn.execute('UPDATE products SET payload=?',(json.dumps(row),))
    product=commerce.view('demo-ro')['products'][0]
    assert product['record']['inputs']['purchase_cny']=='1e-999'
    assert product['economics']['contribution_ron'] is None
    assert product['input_error']
