DEFAULTS = {
    'booking_days': 7,
    'booking_cutoff_minutes': 30,
    'checkin_early_minutes': 15,
    'checkin_late_minutes': 15,
    'face_threshold': 0.45,
    'active_min_reservations': 8,
    'active_min_rate': 0.8,
    'inactive_min_reservations': 3,
    'inactive_max_rate': 0.4,
}

INT_KEYS = {
    'booking_days',
    'booking_cutoff_minutes',
    'checkin_early_minutes',
    'checkin_late_minutes',
    'active_min_reservations',
    'inactive_min_reservations',
}
FLOAT_KEYS = {'face_threshold', 'active_min_rate', 'inactive_max_rate'}


def _cast(key, value):
    if key in INT_KEYS:
        return int(value)
    if key in FLOAT_KEYS:
        return float(value)
    return value


def _read(key, raw):
    try:
        return _cast(key, raw)
    except (TypeError, ValueError):
        return DEFAULTS[key]


def get_config(key):
    from apps.common.models import SystemConfig

    raw = SystemConfig.objects.filter(key=key).values_list('value', flat=True).first()
    if raw is None:
        raw = DEFAULTS[key]
    return _read(key, raw)


def get_configs(keys):
    from apps.common.models import SystemConfig

    rows = dict(SystemConfig.objects.filter(key__in=keys).values_list('key', 'value'))
    return {key: _read(key, rows.get(key, DEFAULTS[key])) for key in keys}
