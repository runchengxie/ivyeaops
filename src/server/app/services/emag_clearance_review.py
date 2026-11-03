"""Read-only clearance handoff and explicit-baseline observations."""
from datetime import datetime

from app.services import emag_audit, emag_clearance, emag_operations, store_artifacts
from app.services.emag_readonly import _values


def _identity(offer):
    values = tuple(offer.get(key) for key in ('part_number', 'part_number_key'))
    return values if all(isinstance(v, str) and v.strip() for v in values) else None


def build(current, baseline=None):
    issues = emag_operations._issues(current)
    clearance = emag_clearance.build(current)
    offers = current['data']['offers']
    indexed = {str(o['id']): (i, o) for i, o in enumerate(offers)}
    queue = []
    for row in clearance['rows']:
        if row['stock'] is None or row['stock'] <= 0:
            continue
        index, offer = indexed[row['offer_id']]
        if 2 not in _values(offer, 'offer_validation_status'):
            continue
        queue.append({**row, 'snapshot_id': current['snapshot_id'],
                      'part_number_key': offer.get('part_number_key'), 'currency': offer.get('currency'),
                      'field_path': f'/data/offers/{index}', 'identity_complete': _identity(offer) is not None,
                      'approval_required': True, 'approved': False,
                      'next_step': 'Confirm intended current price, then inspect the browser validation confirmation.'})
    comparison = {'status': 'unavailable', 'verified_sales_units': None,
                  'settled_cash': None, 'saleability_verified': False}
    if baseline is not None:
        baseline_issues = emag_operations._issues(baseline)
        if (not emag_audit._compatible(current, baseline)
                or datetime.fromisoformat(baseline['captured_at'].replace('Z', '+00:00'))
                >= datetime.fromisoformat(current['captured_at'].replace('Z', '+00:00'))):
            raise ValueError('Baseline must be an earlier compatible store/source/coverage snapshot')
        before = {str(o['id']): (i, o) for i, o in enumerate(baseline['data']['offers'])}
        products, mismatches, disappeared, deltas, newly_blocked = [], [], [], [], []
        blockers = {}
        for issue in issues:
            blockers.setdefault(str(issue['id']), []).append(issue['reason'])
        baseline_blockers = {}
        for issue in baseline_issues:
            baseline_blockers.setdefault(str(issue['id']), []).append(issue['reason'])
        unknown = 0
        for key in sorted(before.keys() & indexed.keys()):
            bi, old = before[key]
            ci, new = indexed[key]
            if _identity(old) is None or _identity(old) != _identity(new):
                mismatches.append(key)
                continue
            old_stock, new_stock = old.get('general_stock'), new.get('general_stock')
            known = all(emag_clearance.known_stock(v) for v in (old_stock, new_stock))
            delta = old_stock - new_stock if known else None
            if known:
                deltas.append(delta)
            else:
                unknown += 1
            old_price = _values(old, 'offer_validation_status')
            new_price = _values(new, 'offer_validation_status')
            # Explicit valid price evidence is required; absent/error status is unknown.
            cleared = 2 in old_price and new_price and all(type(v) is int and v == 1 for v in new_price)
            if cleared:
                disappeared.append(key)
            prior = sorted(baseline_blockers.get(key, []))
            current_blockers = sorted(blockers.get(key, []))
            added = sorted(set(current_blockers) - set(prior))
            if 'blocked' in added:
                newly_blocked.append(key)
            products.append({'offer_id': key, 'sku': new.get('part_number'),
                             'stock_before': old_stock if emag_clearance.known_stock(old_stock) else None,
                             'stock_after': new_stock if emag_clearance.known_stock(new_stock) else None,
                             'stock_decrease': delta, 'current_blockers': current_blockers,
                             'baseline_blockers': prior, 'new_blockers': added,
                             'baseline_field_path': f'/data/offers/{bi}', 'field_path': f'/data/offers/{ci}'})
        comparison.update(status='available', baseline_snapshot_id=baseline['snapshot_id'],
                          baseline_captured_at=baseline['captured_at'], products=products,
                          identity_mismatches=mismatches, unknown_stock_comparisons=unknown,
                          net_stock_decrease=sum(deltas) if deltas else None,
                          price_rejection_no_longer_observed=disappeared,
                          newly_blocked_products=newly_blocked,
                          not_observed_now=sorted(before.keys() - indexed.keys()),
                          newly_observed=sorted(indexed.keys() - before.keys()))
    return {'store_id': current['store_id'], 'snapshot_id': current['snapshot_id'],
            'captured_at': current['captured_at'], 'source': current['source'],
            'coverage': current['coverage'], 'summary': clearance['summary'],
            'price_validation_queue': queue, 'comparison': comparison,
            'order_observations': clearance['order_observations'], 'marketplace_writes': False,
            'limitations': [*current['limitations'],
                           'Imported evidence only; no live browser or API request is made.',
                           'Disappeared price rejection is not storefront saleability or proof of an intervention effect.',
                           'Stock movement, order status, returns and settlement are separate observations.',
                           'A queue entry is not approval. Recheck live identity, current price and exact user approval before submission.']}


def read(store_id, baseline_snapshot_id=None):
    current = store_artifacts.read_snapshot(store_id)
    baseline = store_artifacts.read_snapshot(store_id, baseline_snapshot_id) if baseline_snapshot_id is not None else None
    return build(current, baseline)
