var tblPaymentsCtasCollect, tblCtasCollect, ctascollect;
var QUOTA_PAY_METHOD_LABELS = {
    efectivo: 'Efectivo',
    yape: 'Yape',
    plin: 'Plin'
};
var date_current;
var input_daterange;
var lastQuotaPaymentId = null;
var payQuotaEntregables = [];

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
    var entregableLabel = getPayQuotaEntregableLabel();
    var parts = ['Pago de ' + quotaLabel];
    if (entregableLabel) {
        parts.push(entregableLabel);
    }
    $('#payQuotaDesc').val(parts.join(' — '));
}

function getPayQuotaEntregableLabel() {
    var $sel = $('#payQuotaEntregable');
    if (!$sel.length || !$sel.val()) {
        return '';
    }
    var text = $sel.find('option:selected').text();
    return text && text.indexOf('Sin entregable') === -1 ? text : '';
}

function getPayQuotaEntregableOption(val) {
    if (!val) {
        return null;
    }
    for (var i = 0; i < payQuotaEntregables.length; i++) {
        if (payQuotaEntregables[i].id === val) {
            return payQuotaEntregables[i];
        }
    }
    return null;
}

function initPayQuotaEntregableSelect(row) {
    var $wrap = $('#payQuotaEntregableWrap');
    var $sel = $('#payQuotaEntregable');
    if (!$sel.length) {
        return;
    }
    payQuotaEntregables = (row && row.worker_entregables) ? row.worker_entregables.slice() : [];
    if ($sel.hasClass('select2-hidden-accessible')) {
        $sel.select2('destroy');
    }
    $sel.find('option:not(:first)').remove();
    payQuotaEntregables.forEach(function (opt) {
        $sel.append($('<option>', { value: opt.id, text: opt.label }));
    });
    if (!payQuotaEntregables.length) {
        $wrap.hide();
        $sel.val('').trigger('change');
        return;
    }
    $wrap.show();
    $sel.select2({
        width: '100%',
        dropdownParent: $('#payQuotaEntregableWrap'),
        placeholder: 'Entregable / proceso',
        allowClear: true,
        dropdownAutoWidth: false
    });
    $sel.val(null).trigger('change.select2');
    $('#payQuotaEntregableHint').text(
        payQuotaEntregables.length === 1
            ? '1 opción desde configuración Obrero del producto.'
            : payQuotaEntregables.length + ' opciones desde configuración Obrero del producto.'
    );
}

function onPayQuotaEntregableChange() {
    var opt = getPayQuotaEntregableOption($('#payQuotaEntregable').val());
    if (opt && opt.charge_amount) {
        var charge = parseFloat(String(opt.charge_amount).replace(',', '.'));
        var maxAmount = parseFloat(String($('#payQuotaAmount').attr('max') || '0').replace(',', '.'));
        if (!isNaN(charge) && charge > 0) {
            if (!isNaN(maxAmount) && maxAmount > 0) {
                charge = Math.min(charge, maxAmount);
            }
            $('#payQuotaAmount').val(charge.toFixed(2));
        }
    }
    refreshPayQuotaDesc();
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

function initPayQuotaCollectorSelect() {
    var $sel = $('#payQuotaCollector');
    if (!$sel.length) {
        return;
    }
    if (!$sel.data('options-loaded')) {
        $sel.find('option:not(:first)').remove();
        (window.ctasCollectCollectors || []).forEach(function (c) {
            $sel.append($('<option>', { value: String(c.id), text: c.name }));
        });
        $sel.data('options-loaded', true);
    }
    if ($sel.hasClass('select2-hidden-accessible')) {
        $sel.select2('destroy');
    }
    $sel.select2({
        width: '100%',
        dropdownParent: $('#payQuotaCollectorWrap'),
        placeholder: 'Lugar de cobro',
        allowClear: false,
        dropdownAutoWidth: false
    });
}

function setPayQuotaCollectorDefault(row) {
    var id = String(window.ctasCollectDefaultCollectorId || '');
    if (row && row.sale && row.sale.collector && row.sale.collector.id) {
        id = String(row.sale.collector.id);
    }
    $('#payQuotaCollector').val(id).trigger('change');
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
    initPayQuotaEntregableSelect(row);
    initPayQuotaCollectorSelect();
    setPayQuotaCollectorDefault(row);
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
            payment_method: payMethod,
            collector: $('#payQuotaCollector').val() || window.ctasCollectDefaultCollectorId || '',
            worker_entregable: $('#payQuotaEntregable').val() || ''
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
    var base = (window.ctasCollectPrintBaseUrl || '/pos/frm/ctas/collect/print/voucher/') +
        String(paymentId) + '/' + String(voucher) + '/';
    if (voucher === 'constancia') {
        window.open(base + '?t=' + Date.now(), '_blank');
        return;
    }
    if (window.TerrafirmaPrint && typeof window.TerrafirmaPrint.open === 'function') {
        window.TerrafirmaPrint.open(base);
        return;
    }
    var url = base + '?format=html&auto=popup&t=' + Date.now();
    var features = 'width=1,height=1,left=0,top=0,toolbar=0,menubar=0,location=0,status=0';
    var printWin = window.open(url, 'terrafirma_print_' + paymentId, features);
    if (!printWin) {
        if (window.TerrafirmaPrint && typeof window.TerrafirmaPrint.printViaNavigate === 'function') {
            window.TerrafirmaPrint.printViaNavigate(url);
            return;
        }
        try {
            sessionStorage.setItem('terrafirma_print_return', window.location.pathname + window.location.search);
        } catch (e) {
            /* ignore */
        }
        window.location.href = base + '?format=html&auto=1&t=' + Date.now();
    }
}

function openTicketFormatModal(paymentId) {
    if (!paymentId) {
        return;
    }
    $('#ticketFormatPaymentId').val(paymentId);
    var $ticketModal = $('#myModalTicketFormat');
    if (!$ticketModal.parent().is('body')) {
        $ticketModal.appendTo('body');
    }
    if ($('#myModalPayments').hasClass('show')) {
        $('#myModalPayments').one('hidden.bs.modal.ticketFormat', function () {
            $ticketModal.modal('show');
        });
        $('#myModalPayments').modal('hide');
        return;
    }
    $ticketModal.modal('show');
}

function printTicketFormat(voucherType) {
    var paymentId = $('#ticketFormatPaymentId').val();
    if (!paymentId) {
        paymentId = lastQuotaPaymentId;
    }
    if (!paymentId) {
        return;
    }
    $('#myModalTicketFormat').modal('hide');
    $('#myModalPrintQuota').modal('hide');
    setTimeout(function () {
        openQuotaPaymentPrintForPayment(paymentId, voucherType);
    }, 300);
}

function escapeHtmlText(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

var pendingQuotaEditRow = null;

function updateEditQuotasSum() {
    var sum = 0;
    $('#editQuotasTableBody tr').each(function () {
        var v = parseFloat(String($(this).find('.edit-quota-amount').val() || '0').replace(',', '.'));
        if (!isNaN(v)) {
            sum += v;
        }
    });
    $('#editQuotasSumLabel').text('S/ ' + sum.toFixed(2));
}

function openEditQuotasAuthModal(row) {
    pendingQuotaEditRow = row;
    $('#supervisor_quota_password').val('');
    $('#myModalSupervisorQuotaEdit').modal('show');
}

function fillEditQuotasModal(row) {
    $('#editQuotasCtasCollectId').val(row.id);
    var clientLine = '—';
    if (row.sale && row.sale.client && row.sale.client.user) {
        clientLine = (row.sale.client.user.full_name || '') +
            ' / DNI ' + (row.sale.client.user.dni || '');
    }
    $('#editQuotasClientLine').text(clientLine);
    var saleTotal = row.sale && row.sale.total ? row.sale.total : row.debt;
    $('#editQuotasTotalLine').text(
        'Total venta: S/ ' + saleTotal + ' · Saldo pendiente: S/ ' + row.saldo
    );

    var tbody = $('#editQuotasTableBody');
    tbody.empty();
    (row.quota_plan || []).forEach(function (q) {
        var label = q.label || ('Cuota ' + q.num);
        if (q.num === 0) {
            label = 'Inicial';
        }
        var tr = $('<tr></tr>').attr('data-num', q.num);
        tr.append($('<td></td>').text(label));
        tr.append(
            $('<td></td>').html(
                '<input type="date" class="form-control form-control-sm edit-quota-date" value="' +
                escapeHtmlText(q.due_date || '') + '">'
            )
        );
        tr.append(
            $('<td></td>').html(
                '<input type="number" step="0.01" min="0" class="form-control form-control-sm edit-quota-amount" value="' +
                escapeHtmlText(q.amount || '0') + '">'
            )
        );
        tbody.append(tr);
    });
    updateEditQuotasSum();
    $('#myModalEditQuotas').modal('show');
}

function collectEditQuotasPlan() {
    var plan = [];
    $('#editQuotasTableBody tr').each(function () {
        var num = parseInt($(this).attr('data-num'), 10);
        plan.push({
            num: num,
            label: num === 0 ? 'Inicial' : 'Cuota ' + num,
            due_date: $(this).find('.edit-quota-date').val(),
            amount: $(this).find('.edit-quota-amount').val()
        });
    });
    return plan;
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
            {
                data: function (row, type) {
                    var u = row.sale && row.sale.client && row.sale.client.user;
                    var plain = u
                        ? ((u.full_name || '') + ' ' + (u.dni || '') + ' ' + (row.predio_reference || '')).trim()
                        : 'Consumidor final';
                    return plain;
                },
                render: function (data, type, row) {
                    if (type !== 'display') {
                        return data;
                    }
                    if (!$.isEmptyObject(row.sale.client) && row.sale.client.user) {
                        var u = row.sale.client.user;
                        var name = escapeHtmlText(u.full_name || '');
                        var dni = u.dni
                            ? '<br><small class="text-muted">DNI ' + escapeHtmlText(u.dni) + '</small>'
                            : '';
                        return name + dni + predioReferenceLine(row);
                    }
                    return 'Consumidor final';
                },
            },
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
                    if (qp) {
                        buttons += '<a rel="edit_quotas" class="btn btn-warning btn-xs btn-flat" title="Modificar cuotas (requiere Neo)"><i class="fas fa-key"></i></a> ';
                    }
                    buttons += '<a href="/pos/frm/ctas/collect/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a>';
                    return buttons;
                }
            },
            {
                targets: [1],
                class: 'text-center',
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

    $('#myModalPayQuota').appendTo('body');
    $('#myModalSupervisorQuotaEdit').appendTo('body');
    $('#myModalEditQuotas').appendTo('body');
    $('#myModalTicketFormat').appendTo('body');
    $('#myModalTicketFormat').on('hidden.bs.modal', function () {
        if ($('#myModalPayments').data('reopen-after-ticket')) {
            $('#myModalPayments').removeData('reopen-after-ticket');
            window.setTimeout(function () {
                $('#myModalPayments').modal('show');
            }, 150);
        }
    });

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
        .on('click', 'a[rel="edit_quotas"]', function () {
            $('.tooltip').remove();
            var tr = tblCtasCollect.cell($(this).closest('td, li')).index(),
                row = tblCtasCollect.row(tr.row).data();
            if (row) {
                openEditQuotasAuthModal(row);
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
            $('#myModalPayments').data('reopen-after-ticket', false);
            $('#myModalPayments').modal('show');
        });

    $(document)
        .off('click.ctasPrintPay', '#tblPayments a[rel="print_pay_ticket"]')
        .on('click.ctasPrintPay', '#tblPayments a[rel="print_pay_ticket"]', function (e) {
            e.preventDefault();
            e.stopPropagation();
            $('#myModalPayments').data('reopen-after-ticket', true);
            openTicketFormatModal($(this).attr('data-id') || $(this).data('id'));
        })
        .off('click.ctasPrintConstancia', '#tblPayments a[rel="print_pay_constancia"]')
        .on('click.ctasPrintConstancia', '#tblPayments a[rel="print_pay_constancia"]', function (e) {
            e.preventDefault();
            e.stopPropagation();
            openQuotaPaymentPrintForPayment($(this).attr('data-id') || $(this).data('id'), 'constancia');
        });

    $(document)
        .off('click.ctasDeletePay', '#tblPayments a[rel="delete"]')
        .on('click.ctasDeletePay', '#tblPayments a[rel="delete"]', function () {
            if (!tblPaymentsCtasCollect) {
                return;
            }
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
        });

    $('#btnSubmitPayQuota').on('click', function () {
        submitPayQuota();
    });

    $('#btnConfirmSupervisorQuotaEdit').on('click', function () {
        var authUrl = window.SUPERVISOR_QUOTA_EDIT_URL || '/security/verify-supervisor-quota-edit/';
        var $btn = $(this);
        $btn.prop('disabled', true);
        $.ajax({
            url: authUrl,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            dataType: 'json',
            data: {
                supervisor_username: $('#supervisor_quota_username').val(),
                supervisor_password: $('#supervisor_quota_password').val()
            },
            success: function (resp) {
                if (!resp.success) {
                    message_error(resp.error || 'No se pudo autorizar.');
                    return;
                }
                $('#myModalSupervisorQuotaEdit').modal('hide');
                if (pendingQuotaEditRow) {
                    fillEditQuotasModal(pendingQuotaEditRow);
                }
            },
            error: function (xhr) {
                var msg = 'Usuario o contraseña incorrectos.';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    msg = xhr.responseJSON.error;
                }
                message_error(msg);
            },
            complete: function () {
                $btn.prop('disabled', false);
            }
        });
    });

    $('#btnSaveEditQuotas').on('click', function () {
        var id = $('#editQuotasCtasCollectId').val();
        if (!id) {
            return;
        }
        var plan = collectEditQuotasPlan();
        var $btn = $(this);
        $btn.prop('disabled', true);
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            dataType: 'json',
            data: {
                action: 'save_quota_plan',
                id: id,
                quota_plan_json: JSON.stringify(plan)
            },
            success: function (resp) {
                if (resp.error) {
                    message_error(resp.error);
                    return;
                }
                $('#myModalEditQuotas').modal('hide');
                pendingQuotaEditRow = null;
                if (typeof toastr !== 'undefined') {
                    toastr.success('Plan de cuotas actualizado.');
                }
                if (tblCtasCollect) {
                    tblCtasCollect.ajax.reload(null, false);
                }
            },
            error: function (xhr) {
                var msg = 'No se pudo guardar el plan de cuotas.';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    msg = xhr.responseJSON.error;
                } else if (typeof xhr.responseText === 'string' && xhr.responseText) {
                    try {
                        var parsed = JSON.parse(xhr.responseText);
                        if (parsed.error) {
                            msg = parsed.error;
                        }
                    } catch (e) {}
                }
                message_error(msg);
            },
            complete: function () {
                $btn.prop('disabled', false);
            }
        });
    });

    $(document).on('input change', '#editQuotasTableBody .edit-quota-amount', function () {
        updateEditQuotasSum();
    });

    $(document).on('click', '.pay-quota-method', function () {
        setPayQuotaPaymentMethod($(this).data('value'));
    });

    $('#payQuotaEntregable').on('change', onPayQuotaEntregableChange);

    $('#btnPrintQuotaTicketTermica').on('click', function () {
        printTicketFormat('ticket-termica');
    });
    $('#btnPrintQuotaTicketRppos').on('click', function () {
        printTicketFormat('ticket-rppos');
    });
    $('#btnTicketFormatTermica').on('click', function () {
        printTicketFormat('ticket-termica');
    });
    $('#btnTicketFormatRppos').on('click', function () {
        printTicketFormat('ticket-rppos');
    });
    $('#btnPrintQuotaInvoice').on('click', function () {
        openQuotaPaymentPrint('constancia');
    });
});
