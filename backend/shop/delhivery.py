"""Delhivery courier (B2C Express API).

Keys come from settings (backend/.env). Sandbox uses staging-express.delhivery.com,
production uses track.delhivery.com.

Used for: PIN code serviceability, creating a shipment (AWB), tracking,
packing slips (shipping labels), pickup requests and cancelling a shipment.
"""
import json
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

TRACK_PAGE = 'https://www.delhivery.com/track/package/{}'


class DelhiveryError(Exception):
    pass


def configured():
    return bool(settings.DELHIVERY_API_TOKEN)


def _call(method, url, *, params=None, data=None, json_body=None, timeout=20):
    if not configured():
        raise DelhiveryError('Delhivery is not set up. Add DELHIVERY_API_TOKEN to backend/.env.')
    if not url.startswith('http'):
        url = settings.DELHIVERY_BASE_URL + url
    headers = {'Authorization': 'Token ' + settings.DELHIVERY_API_TOKEN, 'Accept': 'application/json'}
    try:
        r = requests.request(method, url, params=params, data=data, json=json_body, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise DelhiveryError(f'Could not reach Delhivery ({e.__class__.__name__}).')
    if r.status_code in (401, 403):
        raise DelhiveryError('Delhivery rejected the API token. Check DELHIVERY_API_TOKEN and DELHIVERY_MODE.')
    try:
        body = r.json()
    except ValueError:
        raise DelhiveryError(f'Unexpected reply from Delhivery (HTTP {r.status_code}).')
    if r.status_code >= 400:
        raise DelhiveryError(_message(body) or f'Delhivery error (HTTP {r.status_code}).')
    return body


def _message(body):
    if isinstance(body, dict):
        for k in ('rmk', 'error', 'message', 'detail', 'remarks'):
            v = body.get(k)
            if v:
                return ' '.join(map(str, v)) if isinstance(v, list) else str(v)
    return ''


# ---------- PIN code serviceability ----------
def pincode(pin):
    """{'serviceable', 'cod', 'prepaid', 'city', 'state'} for a 6-digit PIN code (cached for 12 hours)."""
    key = f'delhivery:pin:{settings.DELHIVERY_MODE}:{pin}'
    hit = cache.get(key)
    if hit is not None:
        return hit
    body = _call('GET', '/c/api/pin-codes/json/', params={'filter_codes': pin})
    codes = body.get('delivery_codes') or []
    info = {'serviceable': False, 'cod': False, 'prepaid': False, 'city': '', 'state': ''}
    if codes:
        pc = codes[0].get('postal_code') or {}
        embargo = str(pc.get('remarks') or '').lower() == 'embargo'
        info.update(prepaid=pc.get('pre_paid') == 'Y' and not embargo, cod=pc.get('cod') == 'Y' and not embargo,
                    city=pc.get('city') or pc.get('district') or '', state=pc.get('state_code') or '')
        info['serviceable'] = info['prepaid'] or info['cod']
    cache.set(key, info, 12 * 3600)
    return info


# ---------- Create shipment ----------
def shipment_payload(order, reverse=False):
    a = order.address or {}
    items = list(order.items.all())
    qty = sum(i.quantity for i in items) or 1
    cod = order.payment_method == 'cod'
    return {
        'shipments': [{
            'name': a.get('name', ''), 'add': ', '.join(x for x in [a.get('line1', ''), a.get('line2', '')] if x),
            'pin': a.get('pincode', ''), 'city': a.get('city', ''), 'state': a.get('state', ''), 'country': 'India',
            'phone': ''.join(ch for ch in a.get('phone', '') if ch.isdigit())[-10:],
            'order': str(order.id).split('-')[0].upper() + ('-R' if reverse else ''), 'order_date': order.created_at.isoformat(),
            'payment_mode': 'Pickup' if reverse else ('COD' if cod else 'Prepaid'), 'cod_amount': str(order.total) if cod and not reverse else '0',
            'total_amount': str(order.total), 'products_desc': ', '.join(i.name for i in items)[:200] or 'Apparel',
            'quantity': str(qty), 'weight': str(settings.DELHIVERY_WEIGHT_GRAMS * qty),
            'shipping_mode': settings.DELHIVERY_SHIPPING_MODE, 'seller_name': 'Aiman Royale',
        }],
        'pickup_location': {'name': settings.DELHIVERY_PICKUP_LOCATION},
    }


def create_shipment(order):
    """Book the order with Delhivery and save its AWB. Returns the AWB."""
    if order.awb:
        return order.awb
    if not settings.DELHIVERY_PICKUP_LOCATION:
        raise DelhiveryError('Add DELHIVERY_PICKUP_LOCATION (your registered warehouse name) to backend/.env.')
    if order.status not in ('paid', 'cod', 'processing'):
        raise DelhiveryError(f'Only paid, COD or processing orders can be shipped (this one is {order.status}).')
    data = 'format=json&data=' + json.dumps(shipment_payload(order))
    body = _call('POST', '/api/cmu/create.json', data=data.encode(), timeout=30)
    packages = body.get('packages') or []
    pkg = packages[0] if packages else {}
    awb = str(pkg.get('waybill') or '')
    if not awb or str(pkg.get('status', '')).lower() == 'fail':
        raise DelhiveryError(_message(pkg) or _message(body) or 'Delhivery did not return a waybill.')
    order.awb = awb
    order.courier_status = 'Manifested'
    order.tracking_url = TRACK_PAGE.format(awb)
    if order.status in ('paid', 'cod'):
        order.status = 'processing'
    order.save(update_fields=['awb', 'courier_status', 'tracking_url', 'status'])
    return awb


# ---------- Tracking ----------
DELIVERED = {'delivered'}
MOVING = {'in transit', 'dispatched', 'pending', 'picked up', 'out for delivery', 'reached destination hub'}


def track(order):
    """Refresh the order's courier status and scan history from Delhivery."""
    if not order.awb:
        raise DelhiveryError('This order has no AWB yet.')
    body = _call('GET', '/api/v1/packages/json/', params={'waybill': order.awb})
    data = body.get('ShipmentData') or []
    if not data:
        raise DelhiveryError(_message(body) or 'No tracking data yet.')
    ship = data[0].get('Shipment') or {}
    status = ship.get('Status') or {}
    events = []
    for s in ship.get('Scans') or []:
        d = s.get('ScanDetail') or {}
        events.append({'time': d.get('ScanDateTime', ''), 'status': d.get('Scan', ''), 'detail': d.get('Instructions', ''), 'location': d.get('ScannedLocation', '')})
    order.courier_status = status.get('Status', '') or order.courier_status
    order.tracking_events = events[::-1][:40]  # newest first
    order.tracking_synced_at = timezone.now()
    s = order.courier_status.lower()
    if s in DELIVERED and order.status in ('processing', 'shipped'):
        order.status = 'delivered'
        order.delivered_at = order.delivered_at or timezone.now()
    elif (s in MOVING or 'transit' in s) and order.status == 'processing' and s != 'manifested':
        order.status = 'shipped'
    order.save(update_fields=['courier_status', 'tracking_events', 'tracking_synced_at', 'status', 'delivered_at'])
    return order.courier_status


# ---------- Packing slip / pickup / cancel ----------
def packing_slip(awbs):
    """Packing slip details for one or more AWBs. Returns the PDF link when Delhivery provides one."""
    body = _call('GET', settings.DELHIVERY_PACKING_SLIP_API_URL, params={'wbns': ','.join(awbs), 'pdf': 'true'})
    pkgs = body.get('packages') or []
    links = [p.get('pdf_download_link') for p in pkgs if p.get('pdf_download_link')]
    return {'links': links, 'packages': pkgs}


def request_pickup(count, when=None):
    """Ask Delhivery to collect parcels from the pickup location (default: tomorrow 11:00)."""
    if not settings.DELHIVERY_PICKUP_LOCATION:
        raise DelhiveryError('Add DELHIVERY_PICKUP_LOCATION to backend/.env.')
    when = when or (timezone.localtime() + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    body = _call('POST', '/fm/request/new/', json_body={'pickup_location': settings.DELHIVERY_PICKUP_LOCATION,
                 'pickup_date': when.strftime('%Y-%m-%d'), 'pickup_time': when.strftime('%H:%M:%S'), 'expected_package_count': int(count)})
    return body


def cancel(order):
    if not order.awb:
        raise DelhiveryError('This order has no AWB.')
    body = _call('POST', '/api/p/edit', json_body={'waybill': order.awb, 'cancellation': 'true'})
    if isinstance(body, dict) and body.get('status') is False:
        raise DelhiveryError(_message(body) or 'Delhivery could not cancel this shipment.')
    order.courier_status = 'Cancelled'
    order.save(update_fields=['courier_status'])
    return body


# ---------- Returns: reverse pickup from the customer back to our warehouse ----------
def create_return(order):
    """Book a Delhivery reverse pickup (payment mode 'Pickup') for a delivered order. Returns the return AWB."""
    if order.return_awb:
        return order.return_awb
    if order.status != 'delivered':
        raise DelhiveryError('Only delivered orders can be picked up for return.')
    if not settings.DELHIVERY_PICKUP_LOCATION:
        raise DelhiveryError('Add DELHIVERY_PICKUP_LOCATION to backend/.env.')
    data = 'format=json&data=' + json.dumps(shipment_payload(order, reverse=True))
    body = _call('POST', '/api/cmu/create.json', data=data.encode(), timeout=30)
    pkg = (body.get('packages') or [{}])[0]
    awb = str(pkg.get('waybill') or '')
    if not awb or str(pkg.get('status', '')).lower() == 'fail':
        raise DelhiveryError(_message(pkg) or _message(body) or 'Delhivery did not return a waybill for the return.')
    order.return_awb = awb
    order.return_status = 'pickup_booked'
    order.return_courier_status = 'Pickup scheduled'
    order.save(update_fields=['return_awb', 'return_status', 'return_courier_status'])
    return awb


def track_return(order):
    body = _call('GET', '/api/v1/packages/json/', params={'waybill': order.return_awb})
    ship = ((body.get('ShipmentData') or [{}])[0]).get('Shipment') or {}
    st = (ship.get('Status') or {}).get('Status', '') or order.return_courier_status
    order.return_courier_status = st
    low = st.lower()
    if order.return_status == 'pickup_booked' and ('transit' in low or 'picked' in low or 'dispatched' in low):
        order.return_status = 'in_transit'
    order.save(update_fields=['return_courier_status', 'return_status'])
    return st


def label_data(awbs):
    """Packing slip data for printing labels: PDF links when Delhivery provides them, else the package details."""
    return packing_slip(awbs)
