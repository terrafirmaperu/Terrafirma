var tblSale;
var input_daterange;

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
            {data: "client.user.full_name"},
            {data: "payment_condition.name"},
            {data: "payment_method.name"},
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
                    if (row.payment_condition.id === 'credito') {
                        return '<span class="badge badge-warning">' + row.payment_condition.name + '</span>';
                    }
                    return '<span class="badge badge-success">' + row.payment_condition.name + '</span>';
                }
            },
            {
                targets: [5, 6, 7],
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
                    buttons += '<a href="/pos/crm/sale/print/voucher/' + row.id + '/?t=' + Date.now() + '" target="_blank" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-file-pdf"></i></a> ';
                    var cbn = String(row.contract_docx_basename || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;');
                    buttons += '<a href="#" class="btn btn-success btn-xs btn-flat" rel="contract" data-sale-id="' + row.id + '" data-contract-basename="' + cbn + '" title="Ver contrato en ventana"><i class="fas fa-file-signature"></i> Ver contrato</a> ';
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
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'action': 'search_detproducts',
                        'id': row.id
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
            if (row.client && row.client.client_code) {
                invoice.push({'id': 'Cód. cliente', 'name': row.client.client_code});
            }
            invoice.push({'id': 'Cliente', 'name': row.client.user.full_name});
            invoice.push({'id': 'Forma de Pago', 'name': row.payment_condition.name});
            invoice.push({'id': 'Método de Pago', 'name': row.payment_method.name});
            invoice.push({'id': 'Subtotal', 'name': 'S/ ' + row.subtotal});
            invoice.push({'id': 'Igv', 'name': row.igv + ' %'});
            invoice.push({'id': 'Total Igv', 'name': 'S/ ' + row.total_igv});
            invoice.push({'id': 'Descuento', 'name': row.dscto + ' %'});
            invoice.push({'id': 'Total Descuento', 'name': 'S/ ' + row.total_dscto});
            invoice.push({'id': 'Total a pagar', 'name': 'S/ ' + row.total});
            if (row.payment_method.id === 'efectivo') {
                invoice.push({'id': 'Efectivo', 'name': 'S/ ' + row.cash});
                invoice.push({'id': 'Vuelto', 'name': 'S/ ' + row.change});
            } else if (row.payment_method.id === 'yape' || row.payment_method.id === 'plin') {
                invoice.push({'id': 'Monto pagado', 'name': 'S/ ' + row.total});
            } else if (row.payment_method.id === 'tarjeta_debito_credito') {
                invoice.push({'id': 'Número de tarjeta', 'name': row.card_number});
                invoice.push({'id': 'Titular de tarjeta', 'name': row.titular});
                invoice.push({'id': 'Monto a debitar', 'name': 'S/ ' + row.amount_debited});
            } else if (row.payment_method.id === 'efectivo_yape') {
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
        });

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
