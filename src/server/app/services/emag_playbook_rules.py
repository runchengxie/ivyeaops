"""Pure local evidence checks. Manual confirmations never verify marketplace state."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, DecimalException, InvalidOperation
from urllib.parse import urlsplit

from app.services.emag_commerce import COSTS

TRI = ('unknown', 'confirmed', 'failed')
LISTING_TRI = ('category_access', 'commission_contract', 'mandatory_complete', 'title_matches',
               'images_match', 'main_image_white', 'main_image_no_overlay', 'ean_matches', 'dimensions_confirmed')
TEXT = {
    'listing': 'title description brand model color size package_contents ean source_language content_language evidence_url',
    'variant': 'family_name family_id family_type',
    'competitor': 'url observed_at delivery specification',
    'ads': 'campaign_id adset_id campaign_status adset_status period_start period_end',
    'inbound': 'reception_id tracking_number',
    'cost_evidence': 'cost_field value unit source_url observed_at valid_until scope',
}
NUMBERS = {'competitor': ('price_gross_ron',), 'ads': ('balance_ron', 'budget_ron', 'impressions', 'clicks', 'spend_ron', 'orders', 'revenue_ron'),
           'inbound': ('box_count',), 'cost_evidence': ('value',)}
TRIS = {'listing': LISTING_TRI, 'competitor': ('comparable',), 'ads': ('buy_button', 'listing_ready'), 'inbound': ('address_confirmed',)}
SOURCE_ARCHIVE = {
    'category': ('Category access and commission contracts', 'S03, pages 1–4', None),
    'listing': ('Listing creation and content requirements', 'S02, pages 1–21', None),
    'batch_import': ('Batch product import and variant families', 'S01, pages 1–5; S02, pages 20–21 (families)', None),
    'pricing': ('Pricing and commercial cost inputs', 'S04, pages 1–4', None),
    'fbe': ('FBE reception and inbound preparation', 'S06, pages 1–4', None),
    'ads': ('Advertising setup and campaign reporting', 'S05, pages 1–2; S07, slides 1–35', 'S07: 2024-07; S05: publication date unknown'),
    'selection': ('Product selection worksheets', 'S08, sheets 1–4', None),
}
SOURCE_FOR = {'listing': ['category', 'listing'], 'variant': ['batch_import', 'listing'], 'competitor': ['selection', 'pricing'],
              'ads': ['ads', 'listing'], 'inbound': ['fbe'], 'cost_evidence': ['pricing']}


def sources():
    return [{'id': key, 'title': title, 'url': None, 'locator': locator,
             'version': version or 'Historical archive; publication date unknown',
             'review_status': 'requires_current_review',
             'caveat': 'Historical training reference. Confirm current seller-portal requirements; external videos and inaccessible supplements supply no rules. Fees, bids, tax rates and warehouse addresses are not current defaults; compare monetary evidence manually with saved calculator inputs.'}
            for key, (title, locator, version) in SOURCE_ARCHIVE.items()]


def _number(value, integer=False, positive=False):
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise ValueError('Numeric fields require numeric strings')
    try:
        n = Decimal(value)
    except InvalidOperation:
        raise ValueError('Invalid numeric input') from None
    if not n.is_finite() or n.as_tuple().exponent < -12 or n.as_tuple().exponent > 12 or n < 0 or n > 1000000000 or (integer and n != n.to_integral_value()) or (positive and n == 0):
        raise ValueError('Numeric input is outside its allowed range')
    return n


def _date(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError()
        return stamp
    except ValueError:
        raise ValueError('Dates require ISO timestamps with timezone') from None


def _url(value):
    try:
        p = urlsplit(value)
        if p.scheme != 'https' or not p.hostname or p.username is not None or p.password is not None or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError()
        _ = p.port
    except ValueError:
        raise ValueError('Links require HTTPS without user information') from None


def validate_payload(kind, payload, offers):
    if kind not in TEXT or not isinstance(payload, dict):
        raise ValueError('Unknown playbook kind or invalid payload')
    fields = set(TEXT[kind].split()) | set(NUMBERS.get(kind, ())) | set(TRIS.get(kind, ())) | {'note'}
    fields |= {'members'} if kind == 'variant' else {'items'} if kind == 'inbound' else set()
    if set(payload) - fields:
        raise ValueError('Unknown payload field')
    p = deepcopy(payload)
    for key, value in p.items():
        if key in ('members', 'items'):
            continue
        if not isinstance(value, str) or len(value) > (40000 if key == 'description' else 2000):
            raise ValueError('Text field has invalid type or length')
        if key in NUMBERS.get(kind, ()) and value.strip():
            _number(value, key in ('impressions', 'clicks', 'orders', 'box_count'), key == 'box_count')
        if key in ('url', 'evidence_url', 'source_url') and value:
            _url(value)
        if key in ('observed_at', 'valid_until', 'period_start', 'period_end') and value:
            _date(value)
    for key in TRIS.get(kind, ()):
        p.setdefault(key, 'unknown')
        if p[key] not in TRI:
            raise ValueError('Invalid confirmation state')
    enums = {'family_type': ('color', 'size', 'other'), 'delivery': ('emag_delivery', 'seller', 'unknown'),
             'campaign_status': ('unknown', 'draft', 'active', 'paused'), 'adset_status': ('unknown', 'draft', 'active', 'paused'),
             'unit': ('CNY', 'RON', 'percent', 'RON_per_CNY'), 'cost_field': COSTS}
    for key, values in enums.items():
        if key in p and p[key] not in values:
            raise ValueError(f'Invalid {key}')
    if kind == 'cost_evidence' and p.get('cost_field') and p.get('unit'):
        field = p['cost_field']
        expected_unit = ('RON_per_CNY' if field == 'cny_to_ron' else
                         'CNY' if field in ('purchase_cny', 'domestic_cny') else
                         'percent' if field in ('commission_pct', 'vat_pct') else 'RON')
        if p['unit'] != expected_unit:
            raise ValueError('Cost unit does not match the selected calculator field')
    for start, end in (('period_start', 'period_end'), ('observed_at', 'valid_until')):
        if p.get(start) and p.get(end) and _date(p[end]) <= _date(p[start]):
            raise ValueError('End date must follow start date')
    if kind == 'ads' and p.get('clicks', '').strip() and p.get('impressions', '').strip() and _number(p['clicks']) > _number(p['impressions']):
        raise ValueError('Clicks cannot exceed impressions')
    ids = {str(o['id']) for o in offers}
    if kind in ('variant', 'inbound'):
        key = 'members' if kind == 'variant' else 'items'
        rows = p.setdefault(key, [])
        if not isinstance(rows, list) or len(rows) > 100 or (kind == 'variant' and len(rows) < 2):
            raise ValueError('Invalid member/item count')
        seen, values, barcodes, product_codes = set(), set(), {}, {}
        for row in rows:
            allowed = {'product_id', 'value'} if kind == 'variant' else {'product_id', 'ean', 'expected_ean', 'quantity', 'box'}
            if not isinstance(row, dict) or set(row) - allowed or not isinstance(row.get('product_id'), str) or row['product_id'] not in ids:
                raise ValueError('Select products from this snapshot')
            if any(not isinstance(v, str) or len(v) > 2000 for v in row.values()):
                raise ValueError('Invalid item text')
            if kind == 'variant':
                value = row.get('value', '').strip()
                if not value or row['product_id'] in seen or value in values:
                    raise ValueError('Variant products and values must be distinct')
                seen.add(row['product_id'])
                values.add(value)
            else:
                for barcode_key in ('ean', 'expected_ean'):
                    if barcode_key in row:
                        row[barcode_key] = row[barcode_key].strip()
                box = _number(row.get('box'), True, True)
                _number(row.get('quantity'), True, True)
                identity = (row['product_id'], box)
                if identity in seen or (p.get('box_count', '').strip() and box > _number(p['box_count'])):
                    raise ValueError('Duplicate line or box exceeds box count')
                seen.add(identity)
                codes = (row.get('ean', ''), row.get('expected_ean', ''))
                if row['product_id'] in product_codes and product_codes[row['product_id']] != codes:
                    raise ValueError('Inconsistent product barcodes')
                product_codes[row['product_id']] = codes
                for code in codes:
                    if code and code in barcodes and barcodes[code] != row['product_id']:
                        raise ValueError('Barcode belongs to multiple products')
                    if code:
                        barcodes[code] = row['product_id']
    return p


def assess(kind, payload, offers):
    p = validate_payload(kind, payload, offers)
    refs = SOURCE_FOR[kind]
    checks, metrics = [], {}

    def check(key, status):
        checks.append({'key': key, 'status': status, 'source_ids': refs[:]})

    def known(key):
        return bool(p.get(key, '').strip())

    for key in TRIS.get(kind, ()):
        check(key, {'unknown': 'unknown', 'confirmed': 'passed', 'failed': 'failed'}[p[key]])
    if kind == 'listing':
        for key in ('title', 'description', 'brand', 'model', 'color', 'size', 'package_contents', 'ean', 'source_language', 'content_language', 'evidence_url'):
            check(key, 'passed' if known(key) else 'unknown')
        check('language_consistency', 'unknown' if not known('source_language') or not known('content_language') else
              'passed' if p['source_language'].strip().casefold() == p['content_language'].strip().casefold() else 'failed')
    elif kind == 'variant':
        check('family_metadata', 'passed' if all(known(k) for k in ('family_name', 'family_id', 'family_type')) else 'unknown')
        check('distinct_members', 'passed')
    elif kind == 'competitor':
        check('observation', 'passed' if all(known(k) for k in ('url', 'observed_at', 'price_gross_ron', 'specification')) else 'unknown')
    elif kind == 'ads':
        stocks = [o.get('general_stock') for o in offers]
        check('stock', 'unknown' if not stocks or any(type(s) is not int or s < 0 for s in stocks) else 'passed' if all(s > 0 for s in stocks) else 'failed')
        for key in ('campaign_status', 'adset_status'):
            check(key, 'unknown' if p.get(key, 'unknown') == 'unknown' else 'passed' if p[key] == 'active' else 'failed')
        for key in ('balance', 'budget'):
            field = key + '_ron'
            check(key, 'unknown' if not known(field) else 'passed' if _number(p[field]) > 0 else 'failed')
        period = known('period_start') and known('period_end')
        check('result_period', 'passed' if period else 'unknown')
        if period:
            for output, numerator, denominator in (('cpc_ron', 'spend_ron', 'clicks'), ('roas', 'revenue_ron', 'spend_ron')):
                if known(numerator) and known(denominator) and _number(p[denominator]) > 0:
                    try:
                        metrics[output] = str(_number(p[numerator]) / _number(p[denominator]))
                    except DecimalException:
                        raise ValueError('Result cannot be represented as a business decimal') from None
    elif kind == 'inbound':
        rows = p['items']
        status = 'failed' if any(r.get('ean') and r.get('expected_ean') and r['ean'] != r['expected_ean'] for r in rows) else 'unknown' if not rows or any(not r.get('ean') or not r.get('expected_ean') for r in rows) else 'passed'
        check('barcodes', status)
        check('packing', 'passed' if rows and known('box_count') else 'unknown')
        check('reception', 'passed' if known('reception_id') else 'unknown')
        check('tracking', 'passed' if known('tracking_number') else 'unknown')
    else:
        check('provenance', 'passed' if all(known(k) for k in ('cost_field', 'value', 'unit', 'source_url', 'observed_at', 'scope')) else 'unknown')
        check('calculator_comparison', 'unknown')
    return {'checks': checks, 'source_ids': refs[:], 'metrics': metrics}


def repair_guidance(snapshot):
    from app.services.emag_operations import _issues
    mapping = {'invalid_price': (['review_price_evidence', 'compare_cost_inputs'], ['pricing']),
               'documentation_rejected': (['review_listing_rejection', 'confirm_category_contract', 'review_main_image', 'review_mandatory_attributes', 'review_language', 'review_barcode'], ['listing', 'category']),
               'blocked': (['review_block_reason', 'confirm_category_contract'], ['category', 'listing'])}
    result = []
    for issue in _issues(snapshot):
        rule_ids, refs = mapping.get(issue['reason'], (['review_platform_status'], ['listing']))
        result.append({'product_id': str(issue['id']), 'issue_id': issue['issue_id'], 'reason': issue['reason'],
                       'rule_ids': rule_ids[:], 'source_ids': refs[:]})
    return result
