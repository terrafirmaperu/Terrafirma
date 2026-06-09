function escapeHtmlCash(text) {
    if (text === null || text === undefined) {
        return '';
    }
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function renderCashSessionExpenses(data) {
    var rows = (data && data.rows) ? data.rows : [];
    var total = (data && data.total) ? data.total : '0.00';
    var count = (data && data.count !== undefined) ? data.count : rows.length;
    var expensesUrl = (data && data.expenses_url) ? data.expenses_url : (window.cashExpensesUrl || '/pos/frm/expenses/');
    var $body = $('#cashSessionExpensesBody');
    var $badge = $('#cashSessionExpensesBadge');
    var $total = $('#cashSessionExpensesTotal');
    var $hint = $('#cashSessionExpensesHint');
    var $drawer = $('#cashDrawerExpected');

    $badge.text(count);
    $total.text('S/ ' + total);

    if ($drawer.length && data && data.cash_drawer) {
        $drawer.text('S/ ' + (data.cash_drawer.expected || '0.00'));
    }

    if (data && data.session) {
        $hint.text(
            'Gastos de la sesión n.º ' + data.session.id +
            ' (apertura: ' + (data.session.opened_at || '—') + '). Se descuentan del efectivo en caja.'
        );
    } else {
        $hint.text('Gastos registrados en esta sesión de caja. Se descuentan del efectivo en caja.');
    }

    if (!rows.length) {
        $body.html(
            '<tr class="cash-session-expenses-empty">' +
            '<td colspan="5" class="text-center text-muted">Sin gastos en esta sesión</td>' +
            '</tr>'
        );
        return;
    }

    var html = '';
    rows.forEach(function (row) {
        html += '<tr>' +
            '<td>' + escapeHtmlCash(row.date) + '</td>' +
            '<td>' + escapeHtmlCash(row.type) + '</td>' +
            '<td>' + escapeHtmlCash(row.concept) + '</td>' +
            '<td class="text-right text-danger">S/ ' + escapeHtmlCash(row.amount) + '</td>' +
            '<td class="text-center">' +
            '<a href="' + escapeHtmlCash(expensesUrl) + '" class="btn btn-xs btn-danger btn-flat" ' +
            'title="Ver en módulo de gastos (gasto n.º ' + escapeHtmlCash(row.id) + ')">' +
            '<i class="fas fa-external-link-alt"></i> #' + escapeHtmlCash(row.id) +
            '</a>' +
            '</td>' +
            '</tr>';
    });
    $body.html(html);
}

function loadCashSessionExpenses(options) {
    options = options || {};
    var url = options.url || window.cashSessionExpensesUrl || pathname;
    var payload = {
        action: 'cash_session_expenses'
    };
    if (options.sessionId) {
        payload.session_id = options.sessionId;
    }
    $.ajax({
        url: url,
        type: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        dataType: 'json',
        data: payload,
        success: function (data) {
            if (data.error) {
                renderCashSessionExpenses({rows: [], total: '0.00', count: 0});
                return;
            }
            renderCashSessionExpenses(data);
        },
        error: function () {
            renderCashSessionExpenses({rows: [], total: '0.00', count: 0});
        }
    });
}

$(function () {
    var $collapse = $('#cashSessionExpensesCollapse');
    var $toggle = $('#cashSessionExpensesToggle');
    if (!$collapse.length) {
        return;
    }

    $collapse.on('show.bs.collapse', function () {
        $toggle.find('.cash-session-expenses-chevron')
            .removeClass('fa-chevron-right')
            .addClass('fa-chevron-down');
        $toggle.removeClass('collapsed');
    }).on('hide.bs.collapse', function () {
        $toggle.find('.cash-session-expenses-chevron')
            .removeClass('fa-chevron-down')
            .addClass('fa-chevron-right');
        $toggle.addClass('collapsed');
    });

    if (window.cashSessionExpensesAutoLoad) {
        loadCashSessionExpenses({
            url: window.cashSessionExpensesUrl,
            sessionId: window.cashSessionId || null
        });
    }
});
