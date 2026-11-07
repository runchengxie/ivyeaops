"""Private procurement records and explicit scenarios; no marketplace execution."""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext
from urllib.parse import urlsplit
from app.services import store_artifacts as artifacts, emag_operations

COSTS = ('purchase_cny', 'cny_to_ron', 'domestic_cny', 'international_ron', 'duties_ron',
         'fulfilment_ron', 'other_ron', 'commission_pct', 'vat_pct', 'return_allowance_ron')
DEMAND = ('daily_units', 'lead_days', 'safety_days', 'inbound_units', 'reserved_units')
TEXT = ('supplier_url', 'supplier_sku', 'quote_at', 'cost_basis', 'note')


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a numeric input')
    try:
        text = str(value)
        if len(text) > 64:
            raise ValueError('Numeric input is too long')
        result = Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValueError('Invalid numeric input') from None
    if not result.is_finite() or not -12 <= result.as_tuple().exponent <= 12 or result < 0 or result > Decimal('1000000000'):
        raise ValueError('Numeric inputs must be finite and between 0 and 1000000000')
    return result


def validate(inputs):
    if not isinstance(inputs, dict) or set(inputs) - set(COSTS + DEMAND + TEXT + ('supplier_confirmed', 'target_margin_pct')):
        raise ValueError('Unknown commercial input')
    for key in COSTS + DEMAND + ('target_margin_pct',):
        if inputs.get(key) not in (None, ''):
            value = number(inputs[key])
            if key in ('commission_pct', 'vat_pct', 'target_margin_pct') and value > 100:
                raise ValueError('Percentage must be at most 100')
            if key == 'cny_to_ron' and value == 0:
                raise ValueError('Exchange rate must be positive')
    for key in TEXT:
        if key in inputs and (not isinstance(inputs[key], str) or len(inputs[key]) > 2000):
            raise ValueError('Text input must contain at most 2000 characters')
    url = inputs.get('supplier_url')
    if url:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != 'detail.1688.com'
                or not re.fullmatch(r'/offer/[0-9]+\.html', parsed.path) or parsed.query or parsed.fragment):
            raise ValueError('Use a canonical HTTPS detail.1688.com offer link')
    if 'supplier_confirmed' in inputs and type(inputs['supplier_confirmed']) is not bool:
        raise ValueError('Supplier confirmation must be boolean')
    if inputs.get('supplier_confirmed') and (not url or not inputs.get('supplier_sku', '').strip()):
        raise ValueError('Confirm both the supplier link and exact supplier SKU')
    if inputs.get('cost_basis', 'reference') not in ('reference', 'actual'):
        raise ValueError('Cost basis must be reference or actual')
    if inputs.get('quote_at'):
        try:
            stamp = datetime.fromisoformat(inputs['quote_at'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError('Quote time requires an ISO timestamp with timezone') from None


def calculate(inputs, offer):
    with localcontext() as context:
        context.prec = 80
        return _calculate(inputs, offer)


def _calculate(inputs, offer):
    validate(inputs)
    missing = [key for key in COSTS if inputs.get(key) in (None, '')]
    try:
        number(offer.get('sale_price'))
    except ValueError:
        missing.append('sale_price')
    economics = {'sale_price_basis':'exclusive_vat','status': 'incomplete', 'missing': missing, 'contribution_ron': None, 'contribution_margin_pct': None,
                 'break_even_ex_vat_ron': None, 'target_sale_ex_vat_ron': None, 'target_status': 'missing',
                 'note': 'Per-unit scenario, not accounting profit; raw eMAG price excludes VAT. Commission percentage is a user-entered gross-price scenario assumption, not a verified platform fee rule; confirm fees and procurement.'}
    if not missing:
        v = {key: number(inputs[key]) for key in COSTS}
        sale = number(offer['sale_price'])
        revenue = sale
        gross_sale = sale * (1 + v['vat_pct'] / 100)
        cost = ((v['purchase_cny'] + v['domestic_cny']) * v['cny_to_ron']
                + sum(v[k] for k in ('international_ron', 'duties_ron', 'fulfilment_ron', 'other_ron', 'return_allowance_ron')))
        commission = gross_sale * v['commission_pct'] / 100
        contribution = revenue - cost - commission
        retained = 1 - (1 + v['vat_pct'] / 100) * v['commission_pct'] / 100
        economics['contribution_margin_pct'] = f'{contribution / revenue * 100:.2f}' if revenue else None
        economics['break_even_ex_vat_ron'] = str((cost / retained).quantize(Decimal('0.01'),rounding=ROUND_CEILING)) if retained > 0 else None
        if inputs.get('target_margin_pct') not in (None, ''):
            denominator = retained - number(inputs['target_margin_pct']) / 100
            economics['target_status'] = 'calculated' if denominator > 0 else 'infeasible'
            economics['target_sale_ex_vat_ron'] = str(max(Decimal('0.01'),(cost / denominator).quantize(Decimal('0.01'),rounding=ROUND_CEILING))) if denominator > 0 else None
        economics.update(status='actual_inputs_estimate' if inputs.get('cost_basis') == 'actual' else 'reference_estimate',
                         revenue_ex_vat_ron=f'{revenue:.2f}', gross_sale_price_ron=f'{gross_sale:.2f}', unit_cost_ron=f'{cost:.2f}',
                         commission_ron=f'{commission:.2f}', contribution_ron=f'{revenue-cost-commission:.2f}')
    missing_demand = [key for key in DEMAND if inputs.get(key) in (None, '')]
    if type(offer.get('general_stock')) is not int or offer['general_stock'] < 0:
        missing_demand.append('general_stock')
    replenishment = {'status': 'incomplete', 'missing': missing_demand, 'suggested_units': None,
                     'note': 'Manual demand scenario; validate demand, usable stock, lead time and supplier MOQ before purchasing.'}
    if not missing_demand:
        v = {key: number(inputs[key]) for key in DEMAND}
        stock = number(offer['general_stock'])
        target = v['daily_units'] * (v['lead_days'] + v['safety_days'])
        available = stock + v['inbound_units'] - v['reserved_units']
        replenishment.update(status='manual_scenario', available_units=str(available),
                             target_units=str(target), suggested_units=int(max(Decimal(0), target-available).to_integral_value(rounding=ROUND_CEILING)))
    return {'economics': economics, 'replenishment': replenishment}


@contextmanager
def database():
    from app.core.config import settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.data_dir / 'emag-commerce.sqlite3', timeout=15)
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS products (store TEXT, product TEXT, payload TEXT, PRIMARY KEY(store,product))')
        conn.execute('CREATE TABLE IF NOT EXISTS revisions (store TEXT, product TEXT, revision INTEGER, payload TEXT, PRIMARY KEY(store,product,revision))')
        with conn:
            yield conn
    finally:
        conn.close()


def source(store_id):
    snapshot = artifacts.read_snapshot(store_id)
    emag_operations._issues(snapshot)
    return snapshot


def view(store_id):
    snapshot = source(store_id)
    with database() as conn:
        saved = {row[0]: json.loads(row[1]) for row in conn.execute('SELECT product,payload FROM products WHERE store=?', (store_id,))}
    products = []
    for offer in snapshot['data']['offers']:
        record = saved.get(str(offer['id']))
        if record:
            record['stale'] = record['snapshot_id'] != snapshot['snapshot_id']
        try:
            result = calculate(record['inputs'] if record else {}, offer)
            input_error = None
        except ValueError as exc:
            result = calculate({}, offer)
            input_error = str(exc)
        products.append({'offer': offer, 'record': record, 'input_error': input_error, **result})
    return {'store_id': store_id, 'snapshot_id': snapshot['snapshot_id'], 'captured_at': snapshot['captured_at'], 'products': products}


def save(store_id, snapshot_id, product_id, revision, inputs, actor):
    validate(inputs)
    with artifacts.snapshot_guard(), database() as conn:
        snapshot = source(store_id)
        if snapshot['snapshot_id'] != snapshot_id:
            raise ValueError('Evidence is stale; reload first')
        if not any(str(o['id']) == product_id for o in snapshot['data']['offers']):
            raise ValueError('Product is absent from current snapshot')
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT payload FROM products WHERE store=? AND product=?', (store_id, product_id)).fetchone()
        old = json.loads(row[0]) if row else {'revision': 0, 'history': []}
        if type(revision) is not int or revision != old['revision']:
            raise ValueError('Record changed; reload first')
        history = old['history'] + [{'revision': revision+1, 'snapshot_id': snapshot_id, 'actor': actor, 'at': datetime.now(timezone.utc).isoformat(), 'inputs': inputs}]
        for entry in history:
            existing=conn.execute('SELECT payload FROM revisions WHERE store=? AND product=? AND revision=?',(store_id,product_id,entry['revision'])).fetchone()
            if existing and json.loads(existing[0])!=entry:
                raise ValueError('Archived history conflict; refusing to overwrite evidence')
            if not existing:
                conn.execute('INSERT INTO revisions VALUES (?,?,?,?)',(store_id,product_id,entry['revision'],json.dumps(entry)))
        history=history[-100:]
        record = {'snapshot_id': snapshot_id, 'revision': revision+1, 'inputs': inputs, 'actor': actor, 'history': history}
        conn.execute('INSERT OR REPLACE INTO products VALUES (?,?,?)', (store_id, product_id, json.dumps(record)))
    return record


def preview(snapshot, offer, changes):
    if not changes or set(changes) - {'sale_price', 'general_stock'}:
        raise ValueError('Preview supports sale_price and general_stock only')
    result = []
    for key, value in changes.items():
        parsed = number(value)
        if key == 'general_stock' and parsed != parsed.to_integral_value():
            raise ValueError('Stock must be an integer')
        if key == 'sale_price' and parsed <= 0:
            raise ValueError('Price must be positive')
        if offer.get(key) is None:
            raise ValueError('Current value is unknown; collect evidence first')
        result.append({'field': key, 'before': offer[key], 'after': str(parsed)})
    return {'snapshot_id': snapshot['snapshot_id'], 'product_id': str(offer['id']), 'changes': result,
            'executable': False, 'reason': 'Marketplace writer unavailable; this is a local preview only.'}



def history(store_id, product_id, before_revision=None):
    artifacts.validate_id(store_id)
    if before_revision is not None and (type(before_revision) is not int or not 1<=before_revision<=9223372036854775807):
        raise ValueError('History cursor must be a positive integer')
    with database() as conn:
        rows=conn.execute('SELECT payload FROM revisions WHERE store=? AND product=? AND (? IS NULL OR revision<?) ORDER BY revision DESC LIMIT 101',
                          (store_id,product_id,before_revision,before_revision)).fetchall()
        entries=[json.loads(row[0]) for row in rows]
        if not entries:
            row=conn.execute('SELECT payload FROM products WHERE store=? AND product=?',(store_id,product_id)).fetchone()
            if row:
                entries=sorted((e for e in json.loads(row[0]).get('history',[]) if before_revision is None or e['revision']<before_revision),key=lambda e:e['revision'],reverse=True)[:101]
    return {'entries':entries[:100],'next_before':entries[99]['revision'] if len(entries)>100 else None}
