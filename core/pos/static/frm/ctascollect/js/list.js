var tblPaymentsCtasCollect, tblCtasCollect, ctascollect;
var QUOTA_PAY_METHOD_LABELS = {
    efectivo: 'Efectivo',
    yape: 'Yape',
    plin: 'Plin'
};
var date_current;
var input_daterange;
var lastQuotaPaymentId = null;

function computeQuotaProgress(row) {
    var paymentConditionId = row && row.sale && row.sale.payment_condition
        ? row.sale.payment_condition.id
        : null;
    if (paymentConditionId !== 'credito') {
        return null;
    }
    var totalRef = parseInt(row.credit_quota_count, 10) || 1;
    var deuda = parseFloat(String(row.debt || '0').replace(',', '.'));
    var saldo = parseFloat(String(row.saldo || '0').replace(',', '.'));
    var inicial = parseFloat(String(row.credit_down_payment || '0').replace(',', '.'));
    if (isNaN(deuda)) deuda = 0;
    if (isNaN(saldo)) saldo = 0;
    if (isNaN(inicial)) inicial = 0;

    var paidTowardQuotas = Math.max(0, (deuda - saldo) - inicial);
    var quotaAmounts = (row.quota_plan || [])
        .filter(function (q) { return q.num > 0; })
        .map(function (q) {
            var amt = parseFloat(String(q.amount || '0').replace(',', '.'));
            return isNaN(amt) ? 0 : amt;
        });

    var paidCount = 0;
    var acc = 0;
    for (var i = 0; i < quotaAmounts.length; i++) {
        acc += quotaAmounts[i];
        if (paidTowardQuotas + 0.0001 >= acc) {
            paidCount += 1;
        }
    }

    var currentQuota = Math.min(totalRef, paidCount + 1);
    if (saldo <= 0) {
        currentQuota = totalRef;
    }
    return {
        current: currentQuota,
        total: totalRef,
        paidCount: paidCount,
        paidTowardQuotas: paidTowardQuotas
    };
}

function ordinalCuotaLabel(n) {
    var suffix = 'ta';
    if (n === 1 || n === 3) {
        suffix = 'ra';
    } else if (n === 2) {
        suffix = 'da';
    }
    return String(n) + suffix + ' cuota';
}

function getPayQuotaPaymentMethod() {
    var method = ($('#payQuotaPaymentMethod').val() || '').trim();
    return QUOTA_PAY_METHOD_LABELS[method] ? method : '';
}

function clearPayQuotaPaymentMethod() {
    $('#payQuotaPaymentMethod').val('');
    $('.pay-quota-method').removeClass('active').attr('aria-pressed', 'false');
    $('#payQuotaPaymentMethodGrid').removeClass('border border-danger rounded p-1');
    $('#payQuotaPaymentMethodError').hide();
}

function setPayQuotaPaymentMethod(val) {
    if (!QUOTA_PAY_METHOD_LABELS[val]) {
        return;
    }
    $('#payQuotaPaymentMethod').val(val);
    $('.pay-quota-method').removeClass('active').attr('aria-pressed', 'false');
    $('.pay-quota-method[data-value="' + val + '"]').addClass('active').attr('aria-pressed', 'true');
    $('#payQuotaPaymentMethodGrid').removeClass('border border-danger rounded p-1');
    $('#payQuotaPaymentMethodError').hide();
    refreshPayQuotaDesc();
}

function refreshPayQuotaDesc() {
    var labelRaw = $('#payQuotaLabel').val() || '';
    var quotaLabel = labelRaw.split(' / ')[0].trim();
    if (!quotaLabel) {
        return;
    }
    var method = getPayQuotaPaymentMethod();
    if (!method) {
        $('#payQuotaDesc').val('Pago de ' + quotaLabel);
        return;
    }
    $('#payQuotaDesc').val('Pago de ' + quotaLabel + ' (' + QUOTA_PAY_METHOD_LABELS[method] + ')');
}

function extractQuotaLabelFromDesc(desc) {
    var s = String(desc || '');
    var m = s.match(/(\d+\s*(?:ra|da|ta)\s+cuota)/i);
    if (m && m[1]) {
        return m[1].replace(/\s+/g, ' ').trim().toLowerCase();
    }
    return '—';
}

function getCurrentQuotaAmount(row, qp) {
    var amt = null;
    (row.quota_plan || []).forEach(function (q) {
        if (q.num === qp.current) {
            amt = q.amount;
        }
    });
    return amt;
}

function getTodayYmd() {
    var dt = new Date();
    var m = String(dt.getMonth() + 1).padStart(2, '0');
    var d = String(dt.getDate()).padStart(2, '0');
    return dt.getFullYear() + '-' + m + '-' + d;
}

function openPayQuotaModal(row) {
    var qp = computeQuotaProgress(row);
    if (!qp) {
        if (typeof message_error === 'function') {
            message_error('Solo puede pagar cuotas en ventas al crédito.');
        } else {
            alert('Solo puede pagar cuotas en ventas al crédito.');
        }
        return;
    }
    var amount = getCurrentQuotaAmount(row, qp);
    var quotaLabel = ordinalCuotaLabel(qp.current);
    var saldo = parseFloat(String(row.saldo || '0').replace(',', '.'));
    if (isNaN(saldo) || saldo <= 0) {
        if (typeof message_error === 'function') {
            message_error('La cuenta ya no tiene saldo pendiente.');
        } else {
            alert('La cuenta ya no tiene saldo pendiente.');
        }
        return;
    }
    $('#payQuotaCtasCollectId').val(row.id);
    $('#payQuotaLabel').val(quotaLabel + ' / ' + qp.total);
    $('#payQuotaDate').val(getTodayYmd());
    var amountVal = amount !== null ? parseFloat(String(amount).replace(',', '.')) : saldo;
    if (isNaN(amountVal) || amountVal <= 0) {
        amountVal = saldo;
    }
    amountVal = Math.min(amountVal, saldo);
    $('#payQuotaAmount').val(amountVal.toFixed(2));
    $('#payQuotaAmount').attr('max', saldo.toFixed(2));
    $('#payQuotaRemainingLabel').text('Saldo pendiente: S/ ' + saldo.toFixed(2));
    clearPayQuotaPaymentMethod();
    $('#payQuotaDesc').val('Pago de ' + quotaLabel);
    $('#myModalPayQuota').modal('show');
}

function submitPayQuota() {
    var id = $('#payQuotaCtasCollectId').val();
    var dateJoined = $('#payQuotaDate').val();
    var amount = $('#payQuotaAmount').val();
    var desc = $('#payQuotaDesc').val();
    if (!id) {
        return;
    }
    if (!dateJoined) {
        alert('Ingrese la fecha de pago.');
        return;
    }
    var payMethod = getPayQuotaPaymentMethod();
    if (!payMethod) {
        $('#payQuotaPaymentMethodGrid').addClass('border border-danger rounded p-1');
        $('#payQuotaPaymentMethodError').show();
        if (typeof message_error === 'function') {
            message_error('Seleccione la forma de pago: Efectivo, Yape o Plin.');
        } else {
            alert('Seleccione la forma de pago: Efectivo, Yape o Plin.');
        }
        return;
    }
    var n = parseFloat(String(amount || '0').replace(',', '.'));
    if (isNaN(n) || n <= 0) {
        alert('Ingrese un monto válido mayor a 0.');
        return;
    }
    var maxAmount = parseFloat(String($('#payQuotaAmount').attr('max') || '0').replace(',', '.'));
    if (!isNaN(maxAmount) && maxAmount > 0 && n > maxAmount) {
        alert('El pago no puede superar el saldo pendiente (S/ ' + maxAmount.toFixed(2) + ').');
        return;
    }
    $.ajax({
        url: window.ctasCollectPayUrl || '/pos/frm/ctas/collect/add/',
        type: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        dataType: 'json',
        data: {
            action: 'add',
            ctascollect: id,
            date_joined: dateJoined,
            valor: n.toFixed(2),
            desc: desc || '',
            payment_method: payMethod
        },
        success: function (resp) {
            if (resp && resp.error) {
                if (typeof message_error === 'function') {
                    message_error(String(resp.error));
                } else {
                    alert(String(resp.error));
                }
                return;
            }
            $('#myModalPayQuota').modal('hide');
            lastQuotaPaymentId = resp && resp.id ? resp.id : null;
            if (tblCtasCollect) {
                tblCtasCollect.ajax.reload(null, false);
            }
            if (tblPaymentsCtasCollect) {
                tblPaymentsCtasCollect.ajax.reload(null, false);
            }
            if (lastQuotaPaymentId) {
                $('#myModalPrintQuota').modal('show');
            }
        },
        error: function () {
            if (typeof message_error === 'function') {
                message_error('No se pudo registrar el pago de cuota.');
            } else {
                alert('No se pudo registrar el pago de cuota.');
            }
        }
    });
}

function openQuotaPaymentPrint(voucher) {
    if (!lastQuotaPaymentId) {
        return;
    }
    openQuotaPaymentPrintForPayment(lastQuotaPaymentId, voucher);
}

function openQuotaPaymentPrintForPayment(paymentId, voucher) {
    if (!paymentId) {
        return;
    }
    var base = window.ctasCollectPrintBaseUrl || '/pos/frm/ctas/collect/print/voucher/';
    var url = base + String(paymentId) + '/' + String(voucher) + '/';
    window.open(url, '_blank');
}

function escapeHtmlText(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function predioReferenceLine(row) {
    var ref = row && row.predio_reference ? String(row.predio_reference).trim() : '';
    if (!ref) {
        return '';
    }
    return '<br><small class="text-primary"><i class="fas fa-map-marker-alt"></i> ' +
        escapeHtmlText(ref) + '</small>';
}

function fillQuotaPlanPanel(row) {
    var $panel = $('#quotaPlanPanel');
    var paymentConditionId = row && row.sale && row.sale.payment_condition
        ? row.sale.payment_condition.id
        : null;
    if (paymentConditionId !== 'credito') {
        $panel.hide();
        return;
    }
    $panel.show();
    var u = row.sale.client && row.sale.client.user;
    $('#qpClientLine').html(
        u
            ? '<strong>' + escapeHtmlText(u.full_name || '') + '</strong> · DNI ' + escapeHtmlText(u.dni || '—') +
                predioReferenceLine(row)
            : '<span class="text-muted">Sin cliente</span>'
    );
    $('#qpSaleLine').text(
        'Venta N° ' + (row.sale.nro || '—') +
            (row.sale.contract_code ? ' · Contrato ' + row.sale.contract_code : '') +
            ' · Plazo hasta: ' + (row.end_date || '—')
    );
    var ini = row.credit_down_payment || '0.00';
    var fin = row.financed_balance || '0.00';
    var n = parseInt(row.credit_quota_count, 10) || 1;
    $('#qpSummaryLine').html(
        'Total factura: <strong>S/ ' + (row.sale.total || '0.00') + '</strong> · ' +
            'Inicial: <strong>S/ ' + ini + '</strong> · ' +
            'Saldo a cuotizar: <strong>S/ ' + fin + '</strong> · ' +
            '<strong>' + n + '</strong> cuota(s) sobre ese saldo'
    );
    var $tb = $('#tblQuotaPlanBody').empty();
    (row.quota_plan || []).forEach(function (q) {
        var dueDate = q.due_date || '—';
        $tb.append(
            '<tr><td class="text-center">' + q.label + '</td>' +
                '<td class="text-center">' + dueDate + '</td>' +
                '<td class="text-center">S/ ' + q.amount + '</td></tr>'
        );
    });
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

    tblCtasCollect = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
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
            {data: "sale.nro"},
            {data: "sale.client"},
            {data: "quota_plan"},
            {data: "date_joined"},
            {data: "end_date"},
            {data: "debt"},
            {data: "saldo"},
            {data: "state"},
            {data: "state"},
        ],
        columnDefs: [
            {
                targets: [-1],
                orderable: false,
                class: 'text-center',
                render: function (data, type, row) {
                    var buttons = '<a rel="payments" class="btn bg-blue btn-xs btn-flat"><i class="fas fa-dollar-sign"></i></a> ';
                    var qp = computeQuotaProgress(row);
                    if (qp && row.sale && row.sale.id) {
                        buttons += '<a rel="payment_schedule" class="btn btn-info btn-xs btn-flat" title="Descargar cronograma de pagos"><i class="fas fa-calendar-alt"></i></a> ';
                    }
                    if (qp && row.state) {
                        buttons += '<a rel="pay_quota" class="btn btn-success btn-xs btn-flat" title="Pagar cuota"><i class="fas fa-dollar-sign"></i></a> ';
                    } else if (qp && !row.state) {
                        buttons += '<a class="btn btn-success btn-xs btn-flat disabled" title="Cuotas canceladas"><i class="fas fa-check-circle"></i></a> ';
                    }
                    buttons += '<a href="/pos/frm/ctas/collect/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a>';
                    return buttons;
                }
            },
            {
                targets: [1],
                class: 'text-center',
                render: function (data, type, row) {
                    if (!$.isEmptyObject(row.sale.client) && row.sale.client.user) {
                        var u = row.sale.client.user;
                        var name = escapeHtmlText(u.full_name || '');
                        var dni = u.dni
                            ? '<br><small class="text-muted">DNI ' + escapeHtmlText(u.dni) + '</small>'
                            : '';
                        return name + dni + predioReferenceLine(row);
                    }
                    return 'Consumidor final';
                }
            },
            {
                targets: [2],
                orderable: false,
                class: 'text-center align-middle',
                render: function (data, type, row) {
                    var paymentConditionId = row && row.sale && row.sale.payment_condition
                        ? row.sale.payment_condition.id
                        : null;
                    if (paymentConditionId !== 'credito') {
                        return '<span class="text-muted">—</span>';
                    }
                    var qp = computeQuotaProgress(row);
                    if (!qp) {
                        return '<span class="text-muted">—</span>';
                    }
                    var h = '<strong>' + ordinalCuotaLabel(qp.current) + ' / ' + qp.total + '</strong>';
                    h += '<br><span class="small">cuota / referencia</span>';
                    var currentQuotaAmount = null;
                    var currentDueDate = null;
                    (row.quota_plan || []).forEach(function (q) {
                        if (q.num === qp.current) {
                            currentQuotaAmount = q.amount;
                            currentDueDate = q.due_date;
                        }
                    });
                    if (currentDueDate) {
                        h += '<br><small class="text-info"><i class="fas fa-calendar-alt"></i> ' + currentDueDate + '</small>';
                    }
                    if (currentQuotaAmount !== null) {
                        h += '<br><small class="text-muted">S/ ' + currentQuotaAmount + '</small>';
                    }
                    if (row.state === false || String(row.saldo) === '0.00') {
                        h += '<br><small class="text-success">Pagado</small>';
                    }
                    return h;
                }
            },
            {
                targets: [3, 4],
                class: 'text-center',
                render: function (data, type, row) {
                    return data;
                }
            },
            {
                targets: [5, 6],
                orderable: false,
                class: 'text-center',
                render: function (data, type, row) {
                    return 'S/ ' + data;
                }
            },
            {
                targets: [-2],
                orderable: false,
                class: 'text-center',
                render: function (data, type, row) {
                    if (data) {
                        return '<span class="badge badge-danger">Adeuda</span>';
                    }
                    return '<span class="badge badge-success">Pagado</span>';
                }
            }
        ],
        initComplete: function (settings, json) {

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
        .on('apply.daterangepicker', function (ev, picker) {
            getData(false);
        });

    $('.drp-buttons').hide();

    getData(false);

    $('.btnSearch').on('click', function () {
        getData(false);
    });

    $('.btnSearchAll').on('click', function () {
        getData(true);
    });

    $('#data tbody')
        .off()
        .on('click', 'a[rel="pay_quota"]', function () {
            $('.tooltip').remove();
            var tr = tblCtasCollect.cell($(this).closest('td, li')).index(),
                row = tblCtasCollect.row(tr.row).data();
            openPayQuotaModal(row);
        })
        .on('click', 'a[rel="payment_schedule"]', function () {
            $('.tooltip').remove();
            var tr = tblCtasCollect.cell($(this).closest('td, li')).index(),
                row = tblCtasCollect.row(tr.row).data();
            if (row && row.sale && row.sale.id) {
                window.open('/pos/crm/sale/print/payment-schedule/' + row.sale.id + '/', '_blank');
            }
        })
        .on('click', 'a[rel="payments"]', function () {
            $('.tooltip').remove();
            var tr = tblCtasCollect.cell($(this).closest('td, li')).index(),
                row = tblCtasCollect.row(tr.row).data();
            fillQuotaPlanPanel(row);
            tblPaymentsCtasCollect = $('#tblPayments').DataTable({
                // responsive: true,
                // autoWidth: false,
                destroy: true,
                searching: false,
                scrollX: true,
                scrollCollapse: true,
                ajax: {
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: function (d) {
                        d.action = 'search_pays';
                        d.id = row.id;
                    },
                    dataSrc: function (json) {
                        if (!Array.isArray(json)) {
                            return [];
                        }
                        return json.map(function (it) {
                            it.quota_paid_label = extractQuotaLabelFromDesc(it.desc);
                            return it;
                        });
                    }
                },
                columns: [
                    {data: "pos"},
                    {data: "date_joined"},
                    {data: "valor"},
                    {data: "desc"},
                    {data: "quota_paid_label"},
                    {data: "valor"},
                ],
                columnDefs: [
                    {
                        targets: [2],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return 'S/ ' + data;
                        }
                    },
                    {
                        targets: [4],
                        class: 'text-center',
                        orderable: false,
                        render: function (data, type, row) {
                            var html = '';
                            var isQuotaPayment = data && data !== '—';
                            if (isQuotaPayment) {
                                html += '<span class="badge badge-info">' + escapeHtmlText(data) + '</span>';
                                if (row.id) {
                                    html += ' <a href="#" rel="print_pay_ticket" data-id="' + row.id +
                                        '" class="btn btn-primary btn-xs btn-flat ml-1" title="Imprimir ticket">' +
                                        '<i class="fas fa-receipt"></i></a>';
                                    html += ' <a href="#" rel="print_pay_constancia" data-id="' + row.id +
                                        '" class="btn btn-info btn-xs btn-flat" title="Constancia de pago">' +
                                        '<i class="fas fa-file-signature"></i></a>';
                                }
                            } else {
                                html += '<span class="text-muted">—</span>';
                            }
                            return html;
                        }
                    },
                    {
                        targets: [-1],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '<a rel="delete" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-times"></i></a>';
                        }
                    }
                ],
                rowCallback: function (row, data, index) {

                },
                initComplete: function (settings, json) {

                }
            });
            $('#myModalPayments').modal('show');
        });

    $('#tblPayments tbody')
        .off()
        .on('click', 'a[rel="delete"]', function () {
            $('.tooltip').remove();
            var tr = tblPaymentsCtasCollect.cell($(this).closest('td, li')).index(),
                row = tblPaymentsCtasCollect.row(tr.row).data();
            submit_with_ajax('Notificación',
                '¿Estas seguro de eliminar el registro?',
                pathname,
                {
                    'id': row.id,
                    'action': 'delete_pay'
                },
                function () {
                    tblCtasCollect = tblCtasCollect.ajax.reload();
                    tblPaymentsCtasCollect.ajax.reload();
                }
            );
        })
        .on('click', 'a[rel="print_pay_ticket"]', function (e) {
            e.preventDefault();
            openQuotaPaymentPrintForPayment($(this).data('id'), 'ticket');
        })
        .on('click', 'a[rel="print_pay_constancia"]', function (e) {
            e.preventDefault();
            openQuotaPaymentPrintForPayment($(this).data('id'), 'constancia');
        });

    $('#btnSubmitPayQuota').on('click', function () {
        submitPayQuota();
    });

    $(document).on('click', '.pay-quota-method', function () {
        setPayQuotaPaymentMethod($(this).data('value'));
    });

    $('#btnPrintQuotaTicket').on('click', function () {
        openQuotaPaymentPrint('ticket');
    });
    $('#btnPrintQuotaInvoice').on('click', function () {
        openQuotaPaymentPrint('constancia');
    });
});
