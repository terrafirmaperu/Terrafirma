"""Layout del timeline (lienzo 1120×720 px)."""

from core.pos.models import (
    ADVISORY_STAGE_MAX,
    ADVISORY_STAGE_MIN,
    portal_visible_stages,
    sync_advisory_progress_stages,
)

TIMELINE_CANVAS_W = 1120
TIMELINE_CANVAS_H = 720

PATH_D = (
    'M 70 360 C 200 285, 320 435, 450 360 '
    'S 720 298, 900 342 S 1020 378, 1050 322'
)

CONN_SIDE_OFFSET = 62
CARD_APPROX_HEIGHT = 118

_STAGE_ICONS = (
    'bi-geo-alt-fill',
    'bi-stopwatch-fill',
    'bi-arrow-down-up',
    'bi-send-fill',
    'bi-files',
    'bi-clipboard-check-fill',
    'bi-building-fill',
    'bi-file-earmark-check-fill',
    'bi-flag-fill',
)

_REFERENCE_LAYOUT = (
    {'item_top': 56, 'item_left': 118, 'dot_left': 172, 'dot_top': 358},
    {'item_top': 488, 'item_left': 232, 'dot_left': 332, 'dot_top': 362},
    {'item_top': 48, 'item_left': 378, 'dot_left': 508, 'dot_top': 388},
    {'item_top': 492, 'item_left': 498, 'dot_left': 678, 'dot_top': 372},
    {'item_top': 52, 'item_left': 668, 'dot_left': 848, 'dot_top': 366},
    {'item_top': 486, 'item_left': 812, 'dot_left': 848, 'dot_top': 366},
)


def ensure_case_stages(case):
    expected = max(
        ADVISORY_STAGE_MIN,
        min(ADVISORY_STAGE_MAX, int(case.total_stages or ADVISORY_STAGE_MIN)),
    )
    if case.stages.count() != expected:
        sync_advisory_progress_stages(case)
    return list(case.stages.order_by('order'))


def _stage_status(order, current_stage):
    if order < current_stage:
        return 'is-done'
    if order == current_stage:
        return 'is-current'
    return 'is-pending'


def _layout_px(n):
    ref = _REFERENCE_LAYOUT
    if n <= 0:
        return []
    if n <= len(ref):
        return ref[:n]
    out = []
    a0, a1 = ref[0], ref[-1]
    for i in range(n):
        t = i / float(n - 1)
        out.append({key: int(a0[key] + t * (a1[key] - a0[key])) for key in a0})
    return out


def _side_conn(pos, placement):
    """L en el costado: vertical fuera de la franja + horizontal hasta el punto."""
    dot_left = pos['dot_left']
    dot_top = pos['dot_top']
    item_top = pos['item_top']
    side = -CONN_SIDE_OFFSET if dot_left > 620 else CONN_SIDE_OFFSET
    conn_left = dot_left + side

    if placement == 'item--above':
        conn_top = item_top + CARD_APPROX_HEIGHT
        conn_height = max(24, dot_top - conn_top)
    else:
        conn_top = dot_top
        conn_height = max(24, item_top - 10 - conn_top)

    h_left = min(conn_left, dot_left)
    conn_h_width = abs(dot_left - conn_left)

    return conn_left, conn_top, conn_height, h_left, dot_top, conn_h_width


def _path_fill_to_stage(current, n, anchors):
    """Avance del trazo SVG hasta el punto de la etapa en curso."""
    if current >= n:
        return 100
    if not anchors:
        return max(2, min(100, int(current / float(max(n, 1)) * 100)))
    idx = min(current, len(anchors)) - 1
    dot_left = anchors[idx]['dot_left']
    # Misma escala horizontal que el path (aprox. x 70 → 1050)
    return max(3, min(100, int((dot_left - 70) / 980.0 * 100) + 4))


def _accent_for_index(i, n):
    if n <= 1:
        return 'accent-0'
    t = i / float(n - 1)
    if t < 0.25:
        return 'accent-0'
    if t < 0.5:
        return 'accent-1'
    if t < 0.75:
        return 'accent-2'
    return 'accent-3'


def build_timeline_layout(case):
    stages = [s for s in ensure_case_stages(case) if s.is_visible_portal]
    n = len(stages)
    if not n:
        return []

    current = max(1, min(int(case.current_stage or 1), int(case.total_stages or 1)))
    anchors = _layout_px(n)
    result = []

    for i, stage in enumerate(stages):
        pos = anchors[i]
        order = stage.order
        placement = 'item--above' if i % 2 == 0 else 'item--below'
        conn_left, conn_top, conn_height, conn_h_left, conn_h_top, conn_h_width = _side_conn(
            pos, placement,
        )

        result.append({
            'order': order,
            'title': (stage.title or '').strip() or 'Etapa {}'.format(order),
            'description': (stage.description or '').strip(),
            'status_class': _stage_status(order, current),
            'icon': _STAGE_ICONS[i % len(_STAGE_ICONS)],
            'item_class': 'item{}'.format(min(i + 1, 9)),
            'placement': placement,
            'accent_class': _accent_for_index(i, n),
            'use_inline_position': i >= len(_REFERENCE_LAYOUT),
            'item_top': pos['item_top'],
            'item_left': pos['item_left'],
            'dot_left': pos['dot_left'],
            'dot_top': pos['dot_top'],
            'conn_left': conn_left,
            'conn_top': conn_top,
            'conn_height': conn_height,
            'conn_h_left': conn_h_left,
            'conn_h_top': conn_h_top,
            'conn_h_width': conn_h_width,
        })

    return result


def _portal_progress_meta(case, visible_stages):
    """Progreso y etapa actual según etapas visibles en portal."""
    n_all = max(1, int(case.total_stages or 1))
    current = max(1, min(int(case.current_stage or 1), n_all))
    if not visible_stages:
        return 0, current, n_all, False

    n_vis = len(visible_stages)
    done = sum(1 for s in visible_stages if s.order < current)
    has_current = any(s.order == current for s in visible_stages)
    if has_current:
        done += 1
    pct = int(round(100.0 * done / n_vis)) if n_vis else 0
    is_complete = all(s.order < current for s in visible_stages) and not has_current
    if has_current:
        is_complete = False
    if current >= n_all and visible_stages and visible_stages[-1].order <= current:
        is_complete = True
        pct = 100
    return pct, current, n_vis, is_complete


def build_timeline_context(case):
    visible = portal_visible_stages(case)
    n = max(1, len(visible) or int(case.total_stages or 1))
    current = max(1, min(int(case.current_stage or 1), int(case.total_stages or 1)))
    pct, current, n_vis, is_complete = _portal_progress_meta(case, visible)
    anchors = _layout_px(n)
    path_fill = _path_fill_to_stage(current, max(n, n_vis), anchors)

    return {
        'path_d': PATH_D,
        'progress_percent': pct,
        'path_fill': path_fill,
        'is_complete': is_complete,
        'current_stage': current,
        'total_stages': n_vis or int(case.total_stages or 1),
    }
