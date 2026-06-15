var tblSale;
var input_daterange;

function saleAdminAjaxUrl() {
    if (typeof window.saleAdminListPostUrl === 'string' && window.saleAdminListPostUrl.length) {
        return window.saleAdminListPostUrl;
    }
    return pathname;
}

function openTerrafirmaPrintUrl(baseUrl) {
    if (!baseUrl) {
        return;
    }
    if (window.TerrafirmaPrint && typeof window.TerrafirmaPrint.open === 'function') {
        window.TerrafirmaPrint.open(baseUrl);
        return;
    }
    var url = baseUrl + (baseUrl.indexOf('?') >= 0 ? '&' : '?') +
        'format=html&auto=popup&t=' + Date.now();
    var features = 'width=1,height=1,left=0,top=0,toolbar=0,menubar=0,location=0,status=0';
    var printWin = window.open(url, 'terrafirma_print_' + Date.now(), features);
    if (!printWin && window.TerrafirmaPrint && typeof window.TerrafirmaPrint.printViaNavigate === 'function') {
        window.TerrafirmaPrint.printViaNavigate(url);
    }
}

function openSaleVoucherPrint(saleId, voucher) {
    if (!saleId) {
        return;
    }
    var base = '/pos/crm/sale/print/voucher/' + String(saleId) + '/' + String(voucher) + '/';
    openTerrafirmaPrintUrl(base);
}

function openSaleTicketFormatModal(saleId) {
    if (!saleId) {
        return;
    }
    $('#saleTicketFormatId').val(saleId);
    var $modal = $('#myModalSaleTicketFormat');
    if (!$modal.parent().is('body')) {
        $modal.appendTo('body');
    }
    $modal.modal('show');
}

function printSaleTicketFormat(voucherType) {
    var saleId = $('#saleTicketFormatId').val();
    if (!saleId) {
        return;
    }
    $('#myModalSaleTicketFormat').modal('hide');
    openSaleVoucherPrint(saleId, voucherType);
}

function contractDocxFilenameFromXhr(xhr, saleId, suggestedBasename) {
    var disp = xhr.getResponseHeader('Content-Disposition');
    if (disp) {
        var m = disp.match(/filename\*=UTF-8''([^;]+)/i)
            || disp.match(/filename="([^"]+)"/i)
            || disp.match(/filename=([^;\s]+)/i);
        if (m) {
            try {
                return decodeURIComponent(m[1].replace(/"/g, '').trim());
            } catch (e) {
                return m[1].replace(/"/g, '').trim();
            }
        }
    }
    var xf = xhr.getResponseHeader('X-Contract-Filename');
    if (xf && xf.trim()) {
        return xf.trim();
    }
    if (suggestedBasename) {
        return String(suggestedBasename);
    }
    return 'CONTRATO_' + saleId + '.docx';
}

function openSaleContractModal(saleId, contractBasename) {
    if (!saleId) {
        return;
    }
    var previewUrl = '/pos/crm/sale/print/contract/preview/' + saleId + '/?embed=1&t=' + Date.now();
    $('#contractPreviewFrame').attr('src', previewUrl);
    $('#btnContractDownload').data('sale-id', saleId);
    $('#btnContractDownload').data('contractBasename', contractBasename || '');
    $('#myModalContract').modal('show');
}

function downloadSaleContractDocx(saleId) {
    if (!saleId) {
        return;
    }
    var url = '/pos/crm/sale/print/contract/' + saleId + '/';
    var $btn = $('#btnContractDownload');
    $btn.prop('disabled', true);
    $.ajax({
        url: url,
        type: 'GET',
        xhrFields: { responseType: 'blob' },
        success: function (blob, status, xhr) {
            var ct = (xhr.getResponseHeader('Content-Type') || '').toLowerCase();
            if (ct.indexOf('text/html') >= 0) {
                if (typeof message_error === 'function') {
                    message_error('No se pudo descargar el contrato. Revise la sesión o los permisos.');
                } else {
                    alert('No se pudo descargar el contrato.');
                }
                return;
            }
            var suggested = $btn.data('contractBasename') || '';
            var fname = contractDocxFilenameFromXhr(xhr, saleId, suggested);
            var u = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = u;
            a.download = fname;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(u);
        },
        error: function (xhr) {
            var msg = 'No se pudo descargar el contrato.';
            if (xhr && xhr.responseText && xhr.responseText.length && xhr.responseText.length < 800) {
                var t = xhr.responseText.trim();
                if (t && t.indexOf('<') !== 0) {
                    msg = t;
                }
            }
            if (typeof message_error === 'function') {
                message_error(msg);
            } else {
                alert(msg);
            }
        },
        complete: function () {
            $btn.prop('disabled', false);
        }
    });
}

function getData(all) {
    var parameters = {
        'action': 'search',
        'start_date': input_daterange.data('daterangepicker').startDate.format('YYYY-MM-DD'),
        'end_date': input_daterange.data('daterangepicker').endDate.format('YYYY-MM-DD'),
        'csrfmiddlewaretoken': typeof csrftoken !== 'undefined' ? csrftoken : ''
    };

    if (all) {
        parameters['start_date'] = '';
        parameters['end_date'] = '';
    }

    tblSale = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: saleAdminAjaxUrl(),
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: parameters,
            error: function (xhr) {
                var msg = 'Error de comunicación con el servidor';
                if (xhr && xhr.status) {
                    msg += ' (HTTP ' + xhr.status + ')';
                }
                if (xhr && xhr.responseText && xhr.responseText.trim().indexOf('<') === 0) {
                    msg += '. Respuesta HTML en lugar de JSON (¿sesión o CSRF?).';
                }
                if (typeof message_error === 'function') {
                    message_error(msg);
                } else {
                    alert(msg);
                }
            },
            dataSrc: function (json) {
                if (!json) {
                    return [];
                }
                if (json.error !== undefined && json.error !== null) {
                    if (typeof message_error === 'function') {
                        message_error(String(json.error));
                    } else {
                        alert(String(json.error));
                    }
                    return [];
                }
                if (!Array.isArray(json)) {
                    if (typeof message_error === 'function') {
                        message_error('Respuesta inválida del servidor (se esperaba una lista de ventas).');
                    }
                    return [];
                }
                return json;
            }
        },
        columns: [
            {data: "id"},
            {
                data: 'sale_code',
                className: 'text-nowrap',
                render: function (data, type, row) {
                    return row.sale_code || '—';
                }
            },
            {
                data: 'contract_code',
                className: 'text-nowrap',
                render: function (data, type, row) {
                    return row.contract_code || '—';
                }
            },
            {
                data: null,
                render: function (data, type, row) {
                    if (!row.client || !row.client.user) {
                        return '';
                    }
                    return row.client.user.full_name || '';
                }
            },
            {data: "payment_condition.name"},
            {
                data: null,
                render: function (data, type, row) {
                    if (!row.collector || !row.collector.full_name) {
                        return '<span class="text-muted">—</span>';
                    }
                    return row.collector.full_name;
                }
            },
            {data: "payment_method.name"},
            {data: "credit_down_payment"},
            {data: "type_voucher.name"},
            {data: "date_joined"},
            {data: "total"},
            {data: "id"},
        ],
        columnDefs: [
            {
                targets: [4],
                class: 'text-center',
                render: function (data, type, row) {
                    var pc = row.payment_condition || {};
                    var pid = pc.id;
                    var pname = pc.name != null ? pc.name : '';
                    if (pid === 'credito') {
                        return '<span class="badge badge-warning">' + pname + '</span>';
                    }
                    return '<span class="badge badge-success">' + pname + '</span>';
                }
            },
            {
                targets: [6],
                class: 'text-center',
                render: function (data, type, row) {
                    return data;
                }
            },
            {
                targets: [7],
                class: 'text-center',
                render: function (data, type, row) {
                    if (!row.payment_condition || row.payment_condition.id !== 'credito') {
                        return '<span class="text-muted">—</span>';
                    }
                    var ini = parseFloat(String(row.credit_down_payment || '0').replace(',', '.'));
                    if (!ini || isNaN(ini)) {
                        return '<span class="text-muted">—</span>';
                    }
                    var m = row.credit_down_payment_method && row.credit_down_payment_method.name
                        ? row.credit_down_payment_method.name
                        : '';
                    var html = '<span>S/ ' + ini.toFixed(2) + '</span>';
                    if (m) {
                        html += '<br><small class="text-muted">' + m + '</small>';
                    }
                    return html;
                }
            },
            {
                targets: [8, 9],
                class: 'text-center',
                render: function (data, type, row) {
                    return data;
                }
            },
            {
                targets: [-2],
                class: 'text-center',
                render: function (data, type, row) {
                    return 'S/ ' + parseFloat(data).toFixed(2);
                }
            },
            {
                targets: [-1],
                class: 'text-center',
                render: function (data, type, row) {
                    var buttons = '';
                    buttons += '<a class="btn btn-info btn-xs btn-flat" rel="detail"><i class="fas fa-folder-open"></i></a> ';
                    buttons += '<a href="#" class="btn btn-primary btn-xs btn-flat" rel="print_voucher" data-id="' + row.id + '" data-voucher-type="' + (row.type_voucher && row.type_voucher.id ? row.type_voucher.id : 'ticket') + '"><i class="fas fa-print"></i></a> ';
                    var cbn = String(row.contract_docx_basename || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;');
                    buttons += '<a href="#" class="btn btn-success btn-xs btn-flat" rel="contract" data-sale-id="' + row.id + '" data-contract-basename="' + cbn + '" title="Ver contrato en ventana"><i class="fas fa-file-signature"></i> Ver contrato</a> ';
                    if (row.is_voided) {
                        buttons += '<span class="badge badge-secondary ml-1">Anulada</span> ';
                    } else {
                        buttons += '<a href="/pos/crm/sale/admin/delete/' + row.id + '/" class="btn btn-warning btn-xs btn-flat" title="Anular venta"><i class="fas fa-ban"></i></a> ';
                    }
                    return buttons;
                }
            },
        ],
        rowCallback: function (row, data, index) {

        },
        initComplete: function (settings, json) {

        }
    });
}

$(function () {

    input_daterange = $('input[name="date_range"]');

    $('#data tbody')
        .off()
        .on('click', 'a[rel="detail"]', function () {
            $('.tooltip').remove();
            var tr = tblSale.cell($(this).closest('td, li')).index();
            var row = tblSale.row(tr.row).data();
            $('#tblDetails').DataTable({
                // responsive: true,
                // autoWidth: false,
                destroy: true,
                ajax: {
                    url: saleAdminAjaxUrl(),
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'action': 'search_detproducts',
                        'id': row.id,
                        'csrfmiddlewaretoken': typeof csrftoken !== 'undefined' ? csrftoken : ''
                    },
                    dataSrc: ""
                },
                scrollX: true,
                scrollCollapse: true,
                columns: [
                    {data: "product.name"},
                    {data: "product.category.name"},
                    {data: "price"},
                    {data: "cant"},
                    {data: "subtotal"},
                    {data: "dscto"},
                    {data: "total_dscto"},
                    {data: "total"},
                ],
                columnDefs: [
                    {
                        targets: [-1, -2, -4, -6],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return 'S/ ' + parseFloat(data).toFixed(2);
                        }
                    },
                    {
                        targets: [-3],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return parseFloat(data).toFixed(2) + '%';
                        }
                    },
                    {
                        targets: [-5],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return data;
                        }
                    }
                ]
            });

            var invoice = [];
            invoice.push({'id': 'Cód. venta', 'name': row.sale_code || '—'});
            invoice.push({'id': 'Cód. contrato', 'name': row.contract_code || '—'});
            var clientName = (row.client && row.client.user && row.client.user.full_name) ? row.client.user.full_name : '—';
            invoice.push({'id': 'Cliente', 'name': clientName});
            if (row.client && row.client.client_code) {
                invoice.push({'id': 'Cód. cliente', 'name': row.client.client_code});
            }
            invoice.push({'id': 'Forma de Pago', 'name': (row.payment_condition && row.payment_condition.name) || '—'});
            if (row.collector && row.collector.full_name) {
                invoice.push({'id': 'Lugar de cobro', 'name': row.collector.full_name});
            }
            invoice.push({'id': 'Método de Pago', 'name': (row.payment_method && row.payment_method.name) || '—'});
            if (row.payment_condition && row.payment_condition.id === 'credito') {
                invoice.push({'id': 'Vencimiento crédito', 'name': row.end_credit});
                invoice.push({'id': 'Cuotas programadas', 'name': String(row.credit_quota_count || 1)});
                var iniDet = parseFloat(String(row.credit_down_payment || '0').replace(',', '.'));
                if (iniDet && !isNaN(iniDet)) {
                    var iniMet = row.credit_down_payment_method && row.credit_down_payment_method.name
                        ? row.credit_down_payment_method.name
                        : '';
                    invoice.push({
                        'id': 'Inicial',
                        'name': 'S/ ' + parseFloat(iniDet).toFixed(2) + (iniMet ? ' (' + iniMet + ')' : '')
                    });
                }
            }
            invoice.push({'id': 'Subtotal', 'name': 'S/ ' + row.subtotal});
            invoice.push({'id': 'Igv', 'name': row.igv + ' %'});
            invoice.push({'id': 'Total Igv', 'name': 'S/ ' + row.total_igv});
            invoice.push({'id': 'Descuento', 'name': row.dscto + ' %'});
            invoice.push({'id': 'Total Descuento', 'name': 'S/ ' + row.total_dscto});
            invoice.push({'id': 'Total a pagar', 'name': 'S/ ' + row.total});
            if (row.payment_method && row.payment_method.id === 'efectivo') {
                invoice.push({'id': 'Efectivo', 'name': 'S/ ' + row.cash});
                invoice.push({'id': 'Vuelto', 'name': 'S/ ' + row.change});
            } else if (row.payment_method && (row.payment_method.id === 'yape' || row.payment_method.id === 'plin')) {
                invoice.push({'id': 'Monto pagado', 'name': 'S/ ' + row.total});
            } else if (row.payment_method && row.payment_method.id === 'tarjeta_debito_credito') {
                invoice.push({'id': 'Número de tarjeta', 'name': row.card_number});
                invoice.push({'id': 'Titular de tarjeta', 'name': row.titular});
                invoice.push({'id': 'Monto a debitar', 'name': 'S/ ' + row.amount_debited});
            } else if (row.payment_method && row.payment_method.id === 'efectivo_yape') {
                invoice.push({'id': 'Efectivo', 'name': 'S/ ' + row.cash});
                invoice.push({'id': 'Yape', 'name': 'S/ ' + row.amount_debited});
            }

            $('#tblInvoice').DataTable({
                responsive: true,
                autoWidth: false,
                destroy: true,
                data: invoice,
                paging: false,
                ordering: false,
                info: false,
                columns: [
                    {data: "id"},
                    {data: "name"},
                ],
                columnDefs: [
                    {
                        targets: [0, 1],
                        class: 'text-left',
                        render: function (data, type, row) {
                            return data;
                        }
                    },
                ]
            });

            $('.nav-tabs a[href="#home"]').tab('show');

            $('#myModalDetails').modal('show');
        })
        .on('click', 'a[rel="contract"]', function (e) {
            e.preventDefault();
            openSaleContractModal($(this).data('sale-id'), $(this).attr('data-contract-basename') || '');
        })
        .on('click', 'a[rel="print_voucher"]', function (e) {
            e.preventDefault();
            var saleId = $(this).data('id');
            var voucherType = $(this).data('voucher-type') || 'ticket';
            if (voucherType === 'ticket') {
                openSaleTicketFormatModal(saleId);
            } else {
                openSaleVoucherPrint(saleId, 'ticket');
            }
        });

    $('#btnSaleTicketFormatTermica').on('click', function () {
        printSaleTicketFormat('ticket-termica');
    });
    $('#btnSaleTicketFormatRppos').on('click', function () {
        printSaleTicketFormat('ticket-rppos');
    });

    $('#myModalSaleTicketFormat').appendTo('body');

    $('#myModalContract').on('hidden.bs.modal', function () {
        $('#contractPreviewFrame').attr('src', 'about:blank');
    });

    $('#btnContractDownload').on('click', function () {
        downloadSaleContractDocx($(this).data('sale-id'));
    });

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
});
