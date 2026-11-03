import asyncio
from copy import deepcopy

import pytest

from app.services import emag_clearance_review as service


def offer(pid=1, stock=3, invalid=True):
    return {'id':pid,'part_number':f'sku-{pid}','part_number_key':f'PNK{pid}',
            'general_stock':stock,'currency':'RON','sale_price':10,
            'offer_validation_status':{'value':2 if invalid else 1},'validation_status':[{'value':9}]}


def snap(rows, old=False):
    return {'store_id':'demo-ro','platform':'emag','marketplace':'RO','source':'synthetic',
            'coverage':['offers'],'limitations':['Synthetic'],'snapshot_id':'old' if old else 'now',
            'captured_at':'2026-11-01T00:00:00Z' if old else '2026-11-03T00:00:00Z','data':{'offers':rows}}


def test_queue_has_exact_references_and_no_implicit_approval():
    result=service.build(snap([offer(1,2),offer(2,8),offer(3,0)]))
    assert [r['sku'] for r in result['price_validation_queue']]==['sku-2','sku-1']
    row=result['price_validation_queue'][0]
    assert row['snapshot_id']=='now' and row['field_path']=='/data/offers/1'
    assert row['approval_required'] is True and row['approved'] is False
    assert result['marketplace_writes'] is False
    assert result['comparison']['status']=='unavailable'


def test_comparison_is_not_sales_cash_or_saleability():
    result=service.build(snap([offer(1,2,False),offer(3,4)]),snap([offer(1,5),offer(2,3)],True))['comparison']
    assert result['price_rejection_no_longer_observed']==['1']
    assert result['not_observed_now']==['2'] and result['newly_observed']==['3']
    assert result['net_stock_decrease']==3
    assert result['products'][0]['baseline_field_path']=='/data/offers/0'
    assert result['verified_sales_units'] is None and result['settled_cash'] is None
    assert result['saleability_verified'] is False


@pytest.mark.parametrize('change',[{'source':'other'},{'store_id':'other'},{'coverage':['offers','orders']},
                                  {'captured_at':'2026-11-04T00:00:00Z'}, {'captured_at':'2026-11-03T00:00:00Z'}])
def test_incompatible_or_nonprior_baseline_fails(change):
    baseline=snap([offer()],True);baseline.update(change)
    with pytest.raises(ValueError):service.build(snap([offer()]),baseline)


def test_identity_drift_and_unknown_stock_excluded():
    current=[offer(1,0,False),offer(2,None,False)];current[0]['part_number_key']='OTHER'
    result=service.build(snap(current),snap([offer(1,5),offer(2,7)],True))['comparison']
    assert result['identity_mismatches']==['1'] and result['net_stock_decrease'] is None
    assert result['price_rejection_no_longer_observed']==['2']
    assert result['unknown_stock_comparisons']==1


def test_missing_identity_not_a_match_and_new_blocker_not_saleability():
    row=offer();row.pop('part_number_key')
    result=service.build(snap([row]),snap([deepcopy(row)],True))
    assert result['comparison']['identity_mismatches']==['1']
    assert not result['price_validation_queue'][0]['identity_complete']
    row=offer(invalid=False);row['validation_status']=[{'value':10}]
    comparison=service.build(snap([row]),snap([offer()],True))['comparison']
    assert comparison['products'][0]['current_blockers']==['blocked']
    assert comparison['saleability_verified'] is False


def test_mcp_read_scope_and_optional_argument_validation(monkeypatch):
    from app.routers import mcp_server as mcp
    assert mcp.TOOLS['ivyea_emag_clearance_review']['scope']=='read'
    monkeypatch.setattr(service,'read',lambda store,baseline=None:{'store_id':store,'baseline':baseline})
    result=asyncio.run(mcp._call_tool('ivyea_emag_clearance_review',{'store_id':'demo','baseline_snapshot_id':'old'}))
    assert 'old' in result['content'][0]['text']
    for args in ({'store_id':'demo','baseline_snapshot_id':2},{'store_id':'demo','execute':True}):
        assert asyncio.run(mcp._call_tool('ivyea_emag_clearance_review',args))['isError']


def test_http_admin_boundary(monkeypatch):
    import importlib
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.security import require_admin
    from app.routers import emag_operations as module
    app=FastAPI();app.include_router(importlib.reload(module).router,prefix='/api/emag')
    client=TestClient(app);url='/api/emag/stores/demo/clearance-review'
    assert client.get(url).status_code==401
    app.dependency_overrides[require_admin]=lambda:'admin'
    monkeypatch.setattr(service,'read',lambda store,baseline=None:{'marketplace_writes':False})
    assert client.get(url).json()['marketplace_writes'] is False
