from datetime import date, datetime, timedelta

from django.utils import timezone

from apps.common.errors import BusinessError


def aware_on(day, clock_time):
    combined = datetime.combine(day, clock_time)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(combined, tz)


def minutes_between(start_time, end_time):
    start = datetime.combine(date.min, start_time)
    end = datetime.combine(date.min, end_time)
    return int((end - start).total_seconds() // 60)


def parse_date(value, field='日期'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise BusinessError(f'{field}格式应为 YYYY-MM-DD')


def optional_range(request):
    raw_from = request.query_params.get('date_from')
    raw_to = request.query_params.get('date_to')
    start = parse_date(raw_from, '开始日期') if raw_from else None
    end = parse_date(raw_to, '结束日期') if raw_to else None
    if start and end and start > end:
        raise BusinessError('开始日期不能晚于结束日期')
    return start, end


def stat_range(request):
    raw_from = request.query_params.get('date_from')
    raw_to = request.query_params.get('date_to')
    today = timezone.localdate()
    if not raw_from and not raw_to:
        return today - timedelta(days=29), today
    if not raw_from or not raw_to:
        raise BusinessError('请同时提供开始和结束日期')
    start = parse_date(raw_from, '开始日期')
    end = parse_date(raw_to, '结束日期')
    if start > end:
        raise BusinessError('开始日期不能晚于结束日期')
    if (end - start).days + 1 > 180:
        raise BusinessError('统计区间不能超过 180 天')
    return start, end


def page_params(request):
    try:
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
    except (TypeError, ValueError):
        raise BusinessError('分页参数不正确')
    return max(page, 1), min(max(page_size, 1), 100)


def paginate(queryset, request):
    page, page_size = page_params(request)
    total = queryset.count()
    start = (page - 1) * page_size
    return total, queryset[start:start + page_size]


def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def log_action(admin, action, target_type, target_id, detail=''):
    from apps.common.models import OperationLog

    OperationLog.objects.create(
        admin=admin,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        detail=(detail or '')[:255],
    )


def fmt_dt(value):
    if not value:
        return ''
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')
