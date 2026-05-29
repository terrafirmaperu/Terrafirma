var fv;
var input_datejoined;
var select_sale;
var tblProducts = null;
var pendingCancellationParameters = null;

function submitCancellationParameters(parameters) {
    submit_formdata_with_ajax('Notificación',
        '¿Estas seguro de realizar la siguiente acción?',
        pathname,
        parameters,
        function () {
            location.href = fv.form.getAttribute('data-url');
        },
    );
}

function requestRefundAuthorization(parameters) {
    $.ajax({
        url: pathname,
        type: 'POST',
        dataType: 'json',
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            action: 'sale_payment_summary',
            sale: select_sale.val()
        },
        success: function (resp) {
            if (resp && resp.error) {
                message_error(resp.error);
                return;
            }
            var paid = parseFloat(String(resp.paid_amount || '0').replace(',', '.'));
            if (isNaN(paid) || paid <= 0 || !resp.requires_authorization) {
                submitCancellationParameters(parameters);
                return;
            }
            pendingCancellationParameters = parameters;
            $('#refundPaidAmountLabel').text('S/ ' + paid.toFixed(2));
            $('#refund_supervisor_username').val('');
            $('#refund_supervisor_password').val('');
            $('#modalRefundAuthorization').modal('show');
        },
        error: function () {
            message_error('No se pudo verificar cuánto ha pagado esta venta.');
        }
    });
}

document.addEventListener('DOMContentLoaded', function (e) {
    const form = document.getElementById('frmForm');
    fv = FormValidation.formValidation(form, {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh',
                }),
            },
            fields: {
                sale: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione una venta'
                        }
                    }
                },
                date_joined: {
                    validators: {
                        notEmpty: {
                            message: 'La fecha es obligatoria'
                        },
                        date: {
                            format: 'YYYY-MM-DD',
                            message: 'La fecha no es válida'
                        }
                    }
                },
                valor: {
                    validators: {
                        numeric: {
                            message: 'El valor no es un número',
                            thousandsSeparator: '',
                            decimalSeparator: '.'
                        }
                    }
                },
                desc: {
                    validators: {}
                },
            },
        }
    )
        .on('core.element.validated', function (e) {
            if (e.valid) {
                const groupEle = FormValidation.utils.closest(e.element, '.form-group');
                if (groupEle) {
                    FormValidation.utils.classSet(groupEle, {
                        'has-success': false,
                    });
                }
                FormValidation.utils.classSet(e.element, {
                    'is-valid': false,
                });
            }
            const iconPlugin = fv.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            iconElement && (iconElement.style.display = 'none');
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(form.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach((messageEle) => {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            var parameters = new FormData($(fv.form)[0]);
            parameters.append('action', $('input[name="action"]').val());
            var products = devolution.getProducts();
            if (products.length === 0) {
                message_error('Debe tener al menos un item seleccionado para cancelar');
                return false;
            }
            for (var i = 0; i < products.length; i++) {
                if (!products[i].motive || $.trim(products[i].motive) === '') {
                    message_error('Ingrese el motivo de cada cancelación seleccionada.');
                    return false;
                }
                if (parseInt(products[i].amount_return) <= 0 || parseInt(products[i].amount_return) > parseInt(products[i].cant)) {
                    message_error('La cantidad a cancelar debe ser válida.');
                    return false;
                }
            }
            if (!tblProducts) {
                message_error('Seleccione una venta y cargue sus productos.');
                return false;
            }
            if (input_datejoined.val()) {
                parameters.set('date_joined', input_datejoined.val());
            }
            parameters.append('products', JSON.stringify(products));
            requestRefundAuthorization(parameters);
        });
});

var devolution = {
    listDetailProducts: function () {
        var id = select_sale.val();
        if ($.isEmptyObject(id)) {
            if (tblProducts !== null) {
                tblProducts.clear().draw();
            }
            return false;
        }
        tblProducts = $('#tblProducts').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            deferRender: true,
            paging: false,
            ordering: false,
            info: false,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'action': 'search_products_detail',
                    'id': id,
                },
                dataSrc: ""
            },
            columns: [
                {data: "id"},
                {data: "product.name"},
                {data: "cant"},
                {data: "amount_return"},
                {data: "motive"},
                {data: "state"},
            ],
            columnDefs: [
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.cant > 0) {
                            return '<input type="checkbox" class="form-control form-control-checkbox" name="state">';
                        }
                        return '---';
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.cant > 0) {
                            return '<input type="text" class="form-control" name="motive" disabled placeholder="Motivo de la cancelación" autocomplete="off">';
                        }
                        return '---';
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.cant > 0) {
                            return '<input type="text" class="form-control" name="amount_return" disabled value="0">';
                        }
                        return '---';
                    }
                },
            ],
            rowCallback: function (row, data, index) {
                var tr = $(row).closest('tr');
                tr.find('input[name="amount_return"]')
                    .TouchSpin({
                        min: 1,
                        max: data.cant,
                        verticalbuttons: true,
                    })
                    .keypress(function (e) {
                        return validate_form_text('numbers', e, null);
                    });
            },
            initComplete: function (settings, json) {

            }
        });
    },
    getProducts: function () {
        if (!tblProducts) {
            return [];
        }
        return tblProducts.rows().data().toArray().filter(value => value.state === 1 && value.amount_return > 0);
    }
}

$(function () {

    input_datejoined = $('input[name="date_joined"]');
    select_sale = $('select[name="sale"]');

    select_sale.select2({
        theme: "bootstrap4",
        language: 'es',
        allowClear: true,
        ajax: {
            delay: 250,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            url: pathname,
            data: function (params) {
                var queryParameters = {
                    term: params.term,
                    action: 'search_sale'
                }
                return queryParameters;
            },
            processResults: function (data) {
                return {
                    results: data
                };
            },
        },
        placeholder: 'Busque por venta, contrato, cliente o DNI',
        minimumInputLength: 0,
    })
        .on('select2:select', function (e) {
            fv.revalidateField('sale');
            devolution.listDetailProducts();
        })
        .on('select2:clear', function (e) {
            fv.revalidateField('sale');
            devolution.listDetailProducts();
        });

    input_datejoined.datetimepicker({
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
        // date: new moment().format("YYYY-MM-DD")
    });

    input_datejoined.on('change.datetimepicker', function () {
        fv.revalidateField('date_joined');
    });

    $('#btnAuthorizeRefund').on('click', function () {
        var username = $('#refund_supervisor_username').val();
        var password = $('#refund_supervisor_password').val();
        if (!username || !password) {
            message_error('Ingrese usuario y contraseña del supervisor.');
            return;
        }
        var $btn = $(this);
        $btn.prop('disabled', true);
        $.ajax({
            url: window.SUPERVISOR_REFUND_AUTH_URL || '/security/verify-supervisor-delete/',
            type: 'POST',
            dataType: 'json',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                supervisor_username: username,
                supervisor_password: password
            },
            success: function (resp) {
                if (!resp || !resp.success) {
                    message_error((resp && resp.error) || 'No se pudo autorizar.');
                    return;
                }
                $('#modalRefundAuthorization').modal('hide');
                if (pendingCancellationParameters) {
                    submitCancellationParameters(pendingCancellationParameters);
                    pendingCancellationParameters = null;
                }
            },
            error: function (xhr) {
                var msg = 'No se pudo autorizar.';
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

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="amount_return"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var row = tblProducts.row(tr.row).data();
            row.amount_return = parseInt($(this).val());
        })
        .on('keyup', 'input[name="motive"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var row = tblProducts.row(tr.row).data();
            row.motive = $(this).val();
        })
        .on('change', 'input[name="state"]', function () {
            var state = this.checked;
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            var row = tblProducts.row(tr.row).data();
            row.state = state ? 1 : 0;
            row.amount_return = state ? 1 : 0;
            if (!state) {
                row.motive = '';
            }
            $(tblProducts.row(tr.row).node()).find('input[name="amount_return"]').prop('disabled', !state);
            $(tblProducts.row(tr.row).node()).find('input[name="motive"]').prop('disabled', !state).val(state ? row.motive : '');
        });
});
