var input_daterange;

function statusLabel(status) {
    if (status === 'abierta') {
        return '<span class="badge badge-success">Abierta</span>';
    }
    return '<span class="badge badge-secondary">Cerrada</span>';
}

function getData(all) {
    var parameters = {
        'action': 'search',
        'start_date': input_daterange.data('daterangepicker').startDate.format('YYYY-MM-DD'),
        'end_date': input_daterange.data('daterangepicker').endDate.format('YYYY-MM-DD'),
    };

    if (all) {
        parameters['start_date'] = '';
        parameters['end_date'] = '';
    }

    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: parameters,
            dataSrc: ""
        },
        columns: [
            {data: "id"},
            {data: "status"},
            {data: "opened_at"},
            {data: "opening_amount"},
            {data: "close_at"},
            {data: "closing_amount_counted"},
            {data: "id"},
        ],
        columnDefs: [
            {
                targets: [1],
                class: 'text-center',
                orderable: false,
                render: function (data) {
                    return statusLabel(data);
                }
            },
            {
                targets: [3, 5],
                class: 'text-center',
                render: function (data) {
                    if (data === null || data === undefined || data === '') {
                        return '—';
                    }
                    return parseFloat(data).toFixed(2);
                }
            },
            {
                targets: [4],
                class: 'text-center',
                render: function (data) {
                    return data || '—';
                }
            },
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var btns = '';
                    var currentUserId = window.cashCurrentUserId || null;
                    if (row.status === 'abierta' && currentUserId && row.user_opened === currentUserId) {
                        btns += '<a href="/pos/frm/cash/close/' + row.id + '/" class="btn btn-primary btn-xs btn-flat" title="Cierre"><i class="fas fa-cash-register"></i></a> ';
                    }
                    btns += '<a href="/pos/frm/cash/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat" title="Eliminar"><i class="fas fa-trash"></i></a>';
                    return btns;
                }
            },
        ],
        initComplete: function () {
        }
    });
}

function setCashResume(data) {
    var report = data.report_date || '';
    $('#cashReportDate').text(report ? '— Fecha de consulta: ' + report : '');

    if (data.scope_message) {
        $('#cashScopeMessage').text(data.scope_message);
    }

    var sessionText = 'Sin caja abierta en el sistema — totales en cero';
    if (data.session) {
        var nm = data.session.user_opened_name || '';
        sessionText = 'Sesión de caja n.º ' + data.session.id;
        if (nm) {
            sessionText += ' — Cajero: ' + nm;
        }
        sessionText += ' — ' + data.session.status + ' — Apertura: ' + data.session.opened_at;
    }
    $('#cashSessionStatus').text(sessionText);

    $('#salesCount').text(data.sales.count || 0);
    $('#salesTotal').text('S/ ' + (data.sales.total || '0.00'));
    $('#salesCash').text('S/ ' + (data.sales.cash || '0.00'));
    $('#salesYape').text('S/ ' + (data.sales.yape || '0.00'));
    $('#salesPlin').text('S/ ' + (data.sales.plin || '0.00'));
    $('#salesTarjeta').text('S/ ' + (data.sales.tarjeta || data.sales.card || '0.00'));
    $('#salesMixtoYape').text('S/ ' + (data.sales.mixto_yape || '0.00'));

    var expenses = data.expenses || {};
    $('#expensesCount').text(expenses.count || 0);
    $('#expensesTotal').text('S/ ' + (expenses.total || '0.00'));
    $('#cashDrawerExpected').text('S/ ' + ((data.cash_drawer && data.cash_drawer.expected) || '0.00'));

    if (typeof renderCashSessionExpenses === 'function') {
        renderCashSessionExpenses({
            session: data.session,
            rows: expenses.rows || [],
            count: expenses.count || 0,
            total: expenses.total || '0.00',
            expenses_url: window.cashExpensesUrl,
            cash_drawer: data.cash_drawer
        });
    }
}

function getCashResume() {
    $.ajax({
        url: pathname,
        type: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        dataType: 'json',
        data: {
            action: 'cash_resume'
        },
        success: function (data) {
            setCashResume(data);
        },
        error: function () {
            setCashResume({
                report_date: '',
                session: null,
                scope_message: 'No se pudo cargar el resumen.',
                sales: {
                    count: 0,
                    total: '0.00',
                    cash: '0.00',
                    yape: '0.00',
                    plin: '0.00',
                    tarjeta: '0.00',
                    mixto_yape: '0.00',
                    mixto_tarjeta: '0.00',
                    card: '0.00'
                },
                expenses: {count: 0, total: '0.00', rows: []},
                cash_drawer: {expected: '0.00'}
            });
        }
    });
}

$(function () {

    input_daterange = $('input[name="date_range"]');

    input_daterange
        .daterangepicker({
            language: 'auto',
            startDate: new Date(),
            locale: {
                format: 'YYYY-MM-DD',
            }
        })
        .on('apply.daterangepicker', function () {
            getData(false);
        });

    $('.drp-buttons').hide();

    getData(false);
    getCashResume();

    $('.btnSearch').on('click', function () {
        getData(false);
        getCashResume();
    });

    $('.btnSearchAll').on('click', function () {
        getData(true);
        getCashResume();
    });

    $('#cashResumeTab a[data-toggle="pill"]').on('shown.bs.tab', function (e) {
        if ($(e.target).attr('href') === '#tab-expenses' && typeof loadCashSessionExpenses === 'function') {
            loadCashSessionExpenses();
        }
    });
});
