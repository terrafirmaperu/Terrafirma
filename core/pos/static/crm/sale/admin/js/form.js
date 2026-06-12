var current_date;

var fvSale;
var fvClient;
var pendingRedirectAfterContrata = null;
var pendingContractSaleId = null;
var pendingContractDocxBasename = null;
var pendingContractPaymentCondition = null;

var select_client;
/*var input_birthdate;*/
var select_paymentcondition;
var select_paymentmethod;
var input_cash;
var input_cardnumber;
var input_amountdebited;
var input_titular;
var input_change;

var tblSearchProducts;
var tblProducts;

var input_searchproducts;
var input_endcredit;
var input_endcredit_year;
var input_endcredit_month;
var input_endcredit_day;
var input_custom_endcredit_enabled;
var inputs_vents;

var vents = {
    details: {
        subtotal: 0.00,
        igv: 0.00,
        total_igv: 0.00,
        dscto: 0.00,
        total_dscto: 0.00,
        total: 0.00,
        cash: 0.00,
        change: 0.00,
        products: [],
    },
    calculate_invoice: function () {
        var total = 0.00;
        $.each(this.details.products, function (i, item) {
            item.cant = parseInt(item.cant);
            item.subtotal = item.cant * parseFloat(item.price_current);
            item.total_dscto = (parseFloat(item.dscto) / 100) * item.subtotal;
            item.total = item.subtotal - item.total_dscto;
            total += item.total;
        });

        var inclusiveSum = total;
        vents.details.dscto = parseFloat($('input[name="dscto"]').val()) || 0;
        vents.details.total_dscto = inclusiveSum * (vents.details.dscto / 100);
        var amountPayable = inclusiveSum - vents.details.total_dscto;
        var rate = (parseFloat(vents.details.igv) || 0) / 100;
        if (rate > 0) {
            vents.details.subtotal = amountPayable / (1 + rate);
            vents.details.total_igv = amountPayable - vents.details.subtotal;
        } else {
            vents.details.subtotal = amountPayable;
            vents.details.total_igv = 0;
        }
        vents.details.total = amountPayable;
        vents.details.subtotal = parseFloat(vents.details.subtotal.toFixed(2));
        vents.details.total_igv = parseFloat(vents.details.total_igv.toFixed(2));
        vents.details.total = parseFloat(vents.details.total.toFixed(2));

        $('input[name="subtotal"]').val(vents.details.subtotal.toFixed(2));
        $('input[name="igv"]').val(vents.details.igv.toFixed(2));
        $('input[name="total_igv"]').val(vents.details.total_igv.toFixed(2));
        $('input[name="total_dscto"]').val(vents.details.total_dscto.toFixed(2));
        $('input[name="total"]').val(vents.details.total.toFixed(2));
        $('input[name="amount"]').val(vents.details.total.toFixed(2));
        if (typeof window.updateCreditCuotasHelp === 'function') {
            window.updateCreditCuotasHelp();
        }
        if (typeof fvSale !== 'undefined' && $('select[name="payment_condition"]').val() === 'credito') {
            fvSale.revalidateField('credit_down_payment');
        }
    },
    list_products: function () {
        this.calculate_invoice();
        tblProducts = $('#tblProducts').DataTable({
            //responsive: true,
            autoWidth: false,
            destroy: true,
            data: this.details.products,
            ordering: false,
            lengthChange: false,
            searching: false,
            paginate: false,
            scrollX: true,
            scrollCollapse: true,
            columns: [
                {data: "id"},
                {data: "name"},
                {data: "cant"},
                {data: "price_current"},
                {data: "subtotal"},
                {data: "dscto"},
                {data: "total_dscto"},
                {data: "total"},
            ],
            columnDefs: [
                {
                    targets: [-6],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control input-sm" style="width: 100px;" autocomplete="off" name="cant" value="' + row.cant + '">';
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control input-sm" style="width: 100px;" autocomplete="off" name="dscto_unitary" value="' + row.dscto + '">';
                    }
                },
                {
                    targets: [-1, -2, -4, -5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/ ' + parseFloat(data).toFixed(2);
                    }
                },
                {
                    targets: [0],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="remove" class="btn btn-danger btn-flat btn-xs"><i class="fas fa-times"></i></a>';
                    }
                },
            ],
            rowCallback: function (row, data, index) {
                var tr = $(row).closest('tr');
                tr.find('input[name="cant"]')
                    .TouchSpin({
                        min: 1,
                        max: 1000000,
                        verticalbuttons: true
                    })
                    .keypress(function (e) {
                        return validate_form_text('numbers', e, null);
                    });

                tr.find('input[name="dscto_unitary"]')
                    .TouchSpin({
                        min: 0.00,
                        max: 100,
                        step: 0.01,
                        decimals: 2,
                        boostat: 5,
                        verticalbuttons: true,
                        maxboostedstep: 10,
                    })
                    .keypress(function (e) {
                        return validate_decimals($(this), e);
                    });
            },
            initComplete: function (settings, json) {

            },
        });
    },
    get_products_ids: function () {
        return this.details.products.map(value => value.id);
    },
    add_product: function (item) {
        var listEl = document.getElementById('saleClientPropertiesList');
        var props = (listEl && listEl._salePredioProps) ? listEl._salePredioProps : [];
        var blocked = null;
        var availableForProduct = [];
        props.forEach(function (p) {
            if (blocked) {
                return;
            }
            if (item.client_property_id) {
                if (String(p.id) === String(item.client_property_id) && (p.in_process || p.contract_locked)) {
                    blocked = p;
                }
                return;
            }
            if (String(p.product_id) === String(item.id) && (p.in_process || p.contract_locked)) {
                return;
            }
            if (String(p.product_id) === String(item.id) && !(p.in_process || p.contract_locked)) {
                availableForProduct.push(p);
            }
        });
        if (!item.client_property_id && availableForProduct.length > 0) {
            var selectPredioMsg = 'Este cliente tiene predios disponibles para este servicio. Agregue el producto desde "Predios vinculados" para asociarlo al predio correcto.';
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'info',
                    title: 'Seleccione el predio',
                    text: selectPredioMsg,
                    confirmButtonText: 'Entendido',
                });
            } else if (typeof message_error === 'function') {
                message_error(selectPredioMsg);
            }
            return false;
        }
        if (blocked) {
            var alertText = blocked.block_message || blocked.process_label ||
                'Este predio ya tiene venta y asesoría en el sistema. No puede generar la misma asesoría otra vez.';
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'warning',
                    title: 'Predio ya registrado',
                    text: alertText,
                    confirmButtonText: 'Entendido',
                });
            } else if (typeof message_error === 'function') {
                message_error(alertText);
            }
            return false;
        }
        this.details.products.push(item);
        this.list_products();
        return true;
    },
};

function parseIsoDateOnly(iso) {
    if (!iso) return null;
    var parts = String(iso).split('-');
    if (parts.length !== 3) return null;
    var y = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    var d = parseInt(parts[2], 10);
    if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
    var dt = new Date(y, m - 1, d);
    if (dt.getFullYear() !== y || dt.getMonth() !== (m - 1) || dt.getDate() !== d) return null;
    dt.setHours(0, 0, 0, 0);
    return dt;
}

function toIsoDateOnly(dt) {
    var y = dt.getFullYear();
    var m = String(dt.getMonth() + 1).padStart(2, '0');
    var d = String(dt.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + d;
}

function validateSaleProductsBeforeSave(done) {
    var clientId = $('select[name="client"]').val();
    if (!clientId) {
        done(true);
        return;
    }
    $.ajax({
        url: pathname,
        type: 'POST',
        dataType: 'json',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
        },
        data: {
            action: 'validate_sale_products',
            client_id: clientId,
            products: JSON.stringify(vents.details.products),
        },
        success: function (res) {
            if (res.error) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'No se puede generar la misma asesoría',
                        html: String(res.error).replace(/\n/g, '<br>'),
                        confirmButtonText: 'Entendido',
                    });
                } else if (typeof message_error === 'function') {
                    message_error(res.error);
                }
                done(false);
                return;
            }
            done(true);
        },
    }).fail(function () {
        if (typeof message_error === 'function') {
            message_error('No se pudo validar si el predio ya tiene venta registrada.');
        }
        done(false);
    });
}

document.addEventListener('DOMContentLoaded', function (e) {
    const frmClient = document.getElementById('frmClient');
    fvClient = FormValidation.formValidation(frmClient, {
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
                first_name: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 2,
                        },
                    }
                },
                last_name: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 2,
                        },
                    }
                },
                dni: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 7,
                            max: 12
                        },
                        digits: {},
                        remote: {
                            url: pathname,
                            data: function () {
                                return {
                                    obj: frmClient.querySelector('[name="dni"]').value,
                                    type: 'dni',
                                        client_id: $('#modal_existing_client_id').val() || '',
                                    action: 'validate_client'
                                };
                            },
                            message: 'El número de Dni o cédula ya se encuentra registrado',
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                        }
                    }
                },
                mobile: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 7
                        },
                        digits: {},
                        remote: {
                            url: pathname,
                            data: function () {
                                return {
                                    obj: frmClient.querySelector('[name="mobile"]').value,
                                    type: 'mobile',
                                    client_id: $('#modal_existing_client_id').val() || '',
                                    action: 'validate_client'
                                };
                            },
                            message: 'El número de teléfono ya se encuentra registrado',
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                        }
                    }
                },
                email: {
                    validators: {
                        regexp: {
                            regexp: /^$|^([a-z0-9_+&*-]+(?:\.[a-z0-9_+&*-]+)*)@([a-z0-9-]+\.)+[a-z]{2,}$/i,
                            message: 'El formato email no es correcto'
                        },
                        remote: {
                            url: pathname,
                            data: function () {
                                return {
                                    obj: frmClient.querySelector('[name="email"]').value,
                                    type: 'email',
                                    client_id: $('#modal_existing_client_id').val() || '',
                                    action: 'validate_client'
                                };
                            },
                            message: 'El email ya se encuentra registrado',
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                        }
                    }
                },
                address: {
                    validators: {
                        stringLength: {
                            min: 4,
                        }
                    }
                },
                department: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione un departamento'
                        }
                    }
                },
                province: {
                    validators: {
                        notEmpty: {
                            message: 'Ingrese una provincia'
                        },
                        stringLength: {
                            min: 2
                        }
                    }
                },
                district: {
                    validators: {
                        notEmpty: {
                            message: 'Ingrese un distrito'
                        },
                        stringLength: {
                            min: 2
                        }
                    }
                },
                /*image: {
                    validators: {
                        file: {
                            extension: 'jpeg,jpg,png',
                            type: 'image/jpeg,image/png',
                            maxFiles: 1,
                            message: 'Introduce una imagen válida'
                        }
                    }
                },*/
                /*birthdate: {
                    validators: {
                        notEmpty: {
                            message: 'La fecha es obligatoria'
                        },
                        date: {
                            format: 'YYYY-MM-DD',
                            message: 'La fecha no es válida'
                        }
                    },
                },*/
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
            const iconPlugin = fvClient.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            iconElement && (iconElement.style.display = 'none');
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(frmClient.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach((messageEle) => {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            var parameters = new FormData(fvClient.form);
            parameters.append('action', 'create_client');
            var modalRoot = document.getElementById('modalClientPrediosRoot');
            if (modalRoot && window.ClientPredios) {
                parameters.set('properties_json', JSON.stringify(ClientPredios.collect(modalRoot)));
            }
            submit_formdata_with_ajax('Notificación', '¿Estas seguro de realizar la siguiente acción?', pathname,
                parameters,
                function (request) {
                    var optionText = request.text || (request.user.full_name + ' / ' + request.user.dni);
                    select_client.find('option[value="' + request.id + '"]').remove();
                    var newOption = new Option(optionText, request.id, false, true);
                    select_client.append(newOption).trigger('change');
                    var listEl = document.getElementById('saleClientPropertiesList');
                    if (request && request.id && listEl && window.ClientPredios) {
                        $('#saleClientPropertiesWrap').show();
                        ClientPredios.renderSalePropertiesList(listEl, request);
                    }
                    fvSale.revalidateField('client');
                    $('#myModalClient').modal('hide');
                }
            );
        });
});

document.addEventListener('DOMContentLoaded', function (e) {
    function validateChange() {
        var cash = parseFloat(input_cash.val())
        var method_payment = select_paymentmethod.val();
        var total = parseFloat(vents.details.total);
        if (method_payment === 'efectivo') {
            if (cash < total) {
                return {valid: false, message: 'El efectivo debe ser mayor o igual al total a pagar'};
            }
        } else if (method_payment === 'efectivo_tarjeta') {
            var amount_debited = (total - cash);
            input_amountdebited.val(amount_debited.toFixed(2));
        }
        return {valid: true};
    }

    const frmSale = document.getElementById('frmSale');
    fvSale = FormValidation.formValidation(frmSale, {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                // excluded: new FormValidation.plugins.Excluded(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh',
                }),
            },
            fields: {
                client: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione un cliente'
                        },
                    }
                },
                end_credit: {
                    validators: {
                        notEmpty: {
                            enabled: false,
                            message: 'La fecha es obligatoria'
                        },
                        date: {
                            format: 'YYYY-MM-DD',
                            message: 'La fecha no es válida'
                        },
                        callback: {
                            callback: function (input) {
                                if ($('select[name="payment_condition"]').val() !== 'credito') {
                                    return {valid: true};
                                }
                                if (!$('#toggleCustomEndCredit').is(':checked')) {
                                    return {valid: true};
                                }
                                var endRaw = (input.value || '').trim();
                                if (!endRaw) {
                                    return {valid: false, message: 'La fecha es obligatoria'};
                                }
                                var base = parseIsoDateOnly(current_date);
                                var end = parseIsoDateOnly(endRaw);
                                if (!base || !end) {
                                    return {valid: false, message: 'La fecha no es válida'};
                                }
                                var daysDiff = Math.round((end.getTime() - base.getTime()) / 86400000);
                                if (daysDiff <= 0) {
                                    return {valid: false, message: 'Debe ser posterior a la fecha de venta'};
                                }
                                if (daysDiff === 1) {
                                    return {valid: false, message: 'El plazo no puede ser de 1 solo día'};
                                }
                                var n = parseInt(($('input[name="credit_quota_count"]').val() || '1').trim(), 10) || 1;
                                if (daysDiff < n) {
                                    return {
                                        valid: false,
                                        message: 'Para ' + n + ' cuota(s), el plazo debe ser al menos de ' + n + ' día(s)'
                                    };
                                }
                                return {valid: true};
                            }
                        }
                    }
                },
                payment_condition: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione una forma de pago'
                        },
                    }
                },
                payment_method: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione un método de pago'
                        },
                    }
                },
                type_voucher: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione un tipo de comprobante'
                        },
                    }
                },
                card_number: {
                    validators: {
                        notEmpty: {
                            enabled: false,
                        },
                        regexp: {
                            regexp: /^\d{4}\s\d{4}\s\d{4}\s\d{4}$/,
                            message: 'Debe ingresar un numéro de tarjeta en el siguiente formato 1234 5678 9103 2247'
                        },
                        stringLength: {
                            min: 2,
                            max: 19,
                        },
                    }
                },
                titular: {
                    validators: {
                        notEmpty: {
                            enabled: false,
                        },
                        stringLength: {
                            min: 3,
                        },
                    }
                },
                amount_debited: {
                    validators: {
                        notEmpty: {
                            enabled: false,
                        },
                        numeric: {
                            message: 'El valor no es un número',
                            thousandsSeparator: '',
                            decimalSeparator: '.'
                        },
                        callback: {
                            callback: function (input) {
                                if ($('select[name="payment_condition"]').val() !== 'credito') {
                                    return {valid: true};
                                }
                                if ($('#credit_down_payment_method').val() !== 'tarjeta_debito_credito') {
                                    return {valid: true};
                                }
                                var rawIni = ($('input[name="credit_down_payment"]').val() || '').trim().replace(',', '.');
                                var inicial = parseFloat(rawIni);
                                var amt = parseFloat((input.value || '').trim().replace(',', '.'));
                                if (isNaN(amt)) {
                                    return {valid: false, message: 'Ingrese el monto a debitar'};
                                }
                                if (isNaN(inicial) || inicial <= 0) {
                                    return {valid: true};
                                }
                                if (Math.abs(amt - inicial) > 0.009) {
                                    return {valid: false, message: 'Debe coincidir con la inicial'};
                                }
                                return {valid: true};
                            }
                        },
                    }
                },
                cash: {
                    validators: {
                        notEmpty: {},
                        numeric: {
                            message: 'El valor no es un número',
                            thousandsSeparator: '',
                            decimalSeparator: '.'
                        }
                    }
                },
                change: {
                    validators: {
                        notEmpty: {},
                        callback: {
                            //message: 'El cambio no puede ser negativo',
                            callback: function (input) {
                                return validateChange();
                            }
                        }
                    }
                },
                credit_down_payment: {
                    validators: {
                        callback: {
                            callback: function (input) {
                                if ($('select[name="payment_condition"]').val() !== 'credito') {
                                    return {valid: true};
                                }
                                var raw = (input.value || '').trim().replace(',', '.');
                                var num = parseFloat(raw);
                                if (raw === '' || isNaN(num)) {
                                    return {valid: false, message: 'Ingrese un importe válido'};
                                }
                                if (num < 0) {
                                    return {valid: false, message: 'La inicial no puede ser negativa'};
                                }
                                var total = parseFloat(vents.details.total);
                                if (num >= total) {
                                    return {valid: false, message: 'La inicial debe ser menor que el total'};
                                }
                                return {valid: true};
                            }
                        }
                    }
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
            const iconPlugin = fvSale.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            iconElement && (iconElement.style.display = 'none');
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(frmSale.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach((messageEle) => {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            var parameters = new FormData($(fvSale.form)[0]);
            parameters.append('action', $('input[name="action"]').val());
            parameters.append('payment_method', select_paymentmethod.val());
            parameters.append('payment_condition', select_paymentcondition.val());
            parameters.append('end_credit', input_endcredit.val());
            parameters.append('cash', input_cash.val());
            parameters.append('change', input_change.val());
            parameters.append('card_number', input_cardnumber.val());
            parameters.append('titular', input_titular.val());
            parameters.append('dscto', $('input[name="dscto"]').val());
            parameters.append('amount_debited', input_amountdebited.val());
            parameters.append('credit_quota_count', $('input[name="credit_quota_count"]').val());
            parameters.append('credit_down_payment', $('input[name="credit_down_payment"]').val());
            parameters.append('credit_down_payment_method', $('#credit_down_payment_method').val());
            if (vents.details.products.length === 0) {
                message_error('Debe tener al menos un item en el detalle de la venta');
                $('.nav-tabs a[href="#menu1"]').tab('show');
                return false;
            }
            parameters.append('products', JSON.stringify(vents.details.products));
            let urlrefresh = fvSale.form.getAttribute('data-url');
            validateSaleProductsBeforeSave(function (ok) {
                if (!ok) {
                    return;
                }
                submit_formdata_with_ajax('Notificación',
                    '¿Estas seguro de realizar la siguiente acción?',
                    pathname,
                    parameters,
                    function (request) {
                        dialog_action('Notificación', '¿Desea Imprimir el Comprobante?', function () {
                            window.open('/pos/crm/sale/print/voucher/' + request.id + '/?t=' + Date.now(), '_blank');
                            openContrataModal(request, urlrefresh);
                        }, function () {
                            openContrataModal(request, urlrefresh);
                        });
                    },
                );
            });
        });
});

function printInvoice(id) {
    var printWindow = window.open("/pos/crm/sale/print/voucher/" + id + "/?t=" + Date.now(), 'Print', 'left=200, top=200, width=950, height=500, toolbar=0, resizable=0');
    printWindow.addEventListener('load', function () {
        printWindow.print();
    }, true);
}

function openContrataModal(saleData, urlrefresh) {
    pendingRedirectAfterContrata = urlrefresh || null;
    var saleId = saleData && saleData.id ? saleData.id : '—';
    pendingContractSaleId = saleId;
    pendingContractDocxBasename = (saleData && saleData.contract_docx_basename) ? saleData.contract_docx_basename : null;
    pendingContractPaymentCondition = saleData && saleData.payment_condition ? saleData.payment_condition : null;
    if (pendingContractPaymentCondition === 'credito') {
        $('#btnCronogramaPrint').show();
    } else {
        $('#btnCronogramaPrint').hide();
    }
    $('#myModalContrata').modal('show');
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

function scheduleDocxFilenameFromXhr(xhr, saleId) {
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
    var xf = xhr.getResponseHeader('X-Schedule-Filename');
    if (xf && xf.trim()) {
        return xf.trim();
    }
    return 'CRONOGRAMA_PAGOS_' + saleId + '.docx';
}

function downloadBlobFile(blob, filename) {
    var u = window.URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = u;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(u);
}

function downloadPaymentSchedule(saleId) {
    if (!saleId || saleId === '—' || pendingContractPaymentCondition !== 'credito') {
        return;
    }
    $.ajax({
        url: '/pos/crm/sale/print/payment-schedule/' + saleId + '/',
        type: 'GET',
        xhrFields: { responseType: 'blob' },
        success: function (blob, status, xhr) {
            if (xhr.status === 204) {
                return;
            }
            var ct = (xhr.getResponseHeader('Content-Type') || '').toLowerCase();
            if (ct.indexOf('text/html') >= 0 || ct.indexOf('text/plain') >= 0) {
                alert('No se pudo descargar el cronograma de pagos.');
                return;
            }
            downloadBlobFile(blob, scheduleDocxFilenameFromXhr(xhr, saleId));
        },
        error: function () {
            alert('No se pudo descargar el cronograma de pagos.');
        }
    });
}

function finalizeContrataFlow() {
    $('#myModalContrata').modal('hide');
    if (pendingRedirectAfterContrata) {
        location.href = pendingRedirectAfterContrata;
    }
}

function printContrataDraft() {
    if (!pendingContractSaleId || pendingContractSaleId === '—') {
        alert('No se encontró la venta para generar la contrata.');
        return;
    }
    var saleId = pendingContractSaleId;
    var url = '/pos/crm/sale/print/contract/' + saleId + '/';
    var suggested = pendingContractDocxBasename || '';
    $.ajax({
        url: url,
        type: 'GET',
        xhrFields: { responseType: 'blob' },
        success: function (blob, status, xhr) {
            var ct = (xhr.getResponseHeader('Content-Type') || '').toLowerCase();
            if (ct.indexOf('text/html') >= 0) {
                alert('No se pudo descargar el contrato. Revise la sesión o los permisos.');
                return;
            }
            var fname = contractDocxFilenameFromXhr(xhr, saleId, suggested);
            downloadBlobFile(blob, fname);
        },
        error: function () {
            alert('No se pudo descargar el contrato.');
        }
    });
}

function hideRowsVents(values) {
    $.each(values, function (key, value) {
        if (value.enable) {
            $(inputs_vents[value.pos]).show();
        } else {
            $(inputs_vents[value.pos]).hide();
        }
    });
}

$(function () {

    current_date = new moment().format("YYYY-MM-DD");
    input_searchproducts = $('input[name="searchproducts"]');
    select_client = $('select[name="client"]');
    /*input_birthdate = $('input[name="birthdate"]');*/
    input_endcredit = $('input[name="end_credit"]');
    input_endcredit_year = $('input[name="end_credit_year"]');
    input_endcredit_month = $('input[name="end_credit_month"]');
    input_endcredit_day = $('input[name="end_credit_day"]');
    input_custom_endcredit_enabled = $('#toggleCustomEndCredit');
    select_paymentcondition = $('select[name="payment_condition"]');
    select_paymentmethod = $('select[name="payment_method"]');
    // Solo la grilla de "método de pago" de contado lleva is-disabled en crédito; no la de inicial.
    var payMethodGrid = $('.factora-pay-method-grid').not('.factora-credit-inicial-grid');
    var payMethodCards = payMethodGrid.find('.factora-pay-card');

    function updatePayMethodCardsActive() {
        if (!payMethodGrid.length) {
            return;
        }
        var v = select_paymentmethod.val();
        payMethodCards.removeClass('active').attr('aria-pressed', 'false');
        payMethodCards.filter('[data-value="' + v + '"]').addClass('active').attr('aria-pressed', 'true');
    }

    payMethodCards.on('click', function () {
        if (select_paymentmethod.prop('disabled')) {
            return;
        }
        var val = $(this).data('value');
        select_paymentmethod.val(val).trigger('change');
    });

    input_cardnumber = $('input[name="card_number"]');
    input_amountdebited = $('input[name="amount_debited"]');
    input_cash = $('input[name="cash"]');
    input_change = $('input[name="change"]');
    input_titular = $('input[name="titular"]');
    inputs_vents = $('.rowVents');

    window.syncCreditInicialMethodUi = function () {
        var wrap = $('.credit-inicial-metodo-wrap');
        var hidden = $('#credit_down_payment_method');
        if (!wrap.length || !hidden.length) {
            return;
        }
        if ($('select[name="payment_condition"]').val() !== 'credito') {
            wrap.hide();
            hidden.val('efectivo');
            return;
        }
        var raw = ($('input[name="credit_down_payment"]').val() || '').trim().replace(',', '.');
        var inicial = parseFloat(raw);
        if (isNaN(inicial) || raw === '' || inicial <= 0) {
            wrap.hide();
            hidden.val('efectivo');
            $('.credit-inicial-pay').removeClass('active').attr('aria-pressed', 'false');
            $('.credit-inicial-pay[data-value="efectivo"]').addClass('active').attr('aria-pressed', 'true');
            hideRowsVents([
                {'pos': 0, 'enable': false},
                {'pos': 1, 'enable': false},
                {'pos': 2, 'enable': true},
                {'pos': 3, 'enable': true},
            ]);
            if (typeof fvSale !== 'undefined') {
                fvSale.disableValidator('card_number');
                fvSale.disableValidator('titular');
                fvSale.disableValidator('amount_debited');
            }
            input_cardnumber.val('');
            input_titular.val('');
            input_amountdebited.val('0.00');
            return;
        }
        wrap.show();
        var v = hidden.val() || 'efectivo';
        var allowed = ['efectivo', 'yape', 'plin', 'tarjeta_debito_credito'];
        if (allowed.indexOf(v) < 0) {
            v = 'efectivo';
            hidden.val(v);
        }
        $('.credit-inicial-pay').removeClass('active').attr('aria-pressed', 'false');
        $('.credit-inicial-pay[data-value="' + v + '"]').addClass('active').attr('aria-pressed', 'true');

        var showTarjeta = v === 'tarjeta_debito_credito';
        hideRowsVents([
            {'pos': 0, 'enable': false},
            {'pos': 1, 'enable': showTarjeta},
            {'pos': 2, 'enable': true},
            {'pos': 3, 'enable': true},
        ]);
        if (typeof fvSale !== 'undefined') {
            if (showTarjeta) {
                fvSale.enableValidator('card_number');
                fvSale.enableValidator('titular');
                fvSale.enableValidator('amount_debited');
                input_amountdebited.val(inicial.toFixed(2));
                fvSale.revalidateField('card_number');
                fvSale.revalidateField('titular');
                fvSale.revalidateField('amount_debited');
            } else {
                fvSale.disableValidator('card_number');
                fvSale.disableValidator('titular');
                fvSale.disableValidator('amount_debited');
                input_cardnumber.val('');
                input_titular.val('');
                input_amountdebited.val('0.00');
            }
        }
    };

    function getSaleBaseDate() {
        return parseIsoDateOnly(current_date) || new Date();
    }

    function setCreditEndDateInputs(isoDate) {
        var dt = parseIsoDateOnly(isoDate);
        if (!dt) return;
        if (input_endcredit_year.length) input_endcredit_year.val(dt.getFullYear());
        if (input_endcredit_month.length) input_endcredit_month.val(dt.getMonth() + 1);
        if (input_endcredit_day.length) input_endcredit_day.val(dt.getDate());
        if (input_endcredit.length) input_endcredit.val(toIsoDateOnly(dt));
    }

    function isCustomEndCreditEnabled() {
        return !!(input_custom_endcredit_enabled.length && input_custom_endcredit_enabled.is(':checked'));
    }

    function syncCustomEndCreditUi() {
        var enabled = isCustomEndCreditEnabled() && select_paymentcondition.val() === 'credito';
        input_endcredit_year.prop('disabled', !enabled);
        input_endcredit_month.prop('disabled', !enabled);
        input_endcredit_day.prop('disabled', !enabled);
    }

    function syncCreditEndDateHiddenFromParts() {
        if (!input_endcredit.length) return null;
        var y = parseInt((input_endcredit_year.val() || '').trim(), 10);
        var m = parseInt((input_endcredit_month.val() || '').trim(), 10);
        var d = parseInt((input_endcredit_day.val() || '').trim(), 10);
        if (isNaN(y) || isNaN(m) || isNaN(d)) {
            input_endcredit.val('');
            return null;
        }
        var dt = new Date(y, m - 1, d);
        if (dt.getFullYear() !== y || dt.getMonth() !== (m - 1) || dt.getDate() !== d) {
            input_endcredit.val('');
            return null;
        }
        var iso = toIsoDateOnly(dt);
        input_endcredit.val(iso);
        return dt;
    }

    window.updateCreditCuotasHelp = function () {
        var help = $('#creditCuotasHelp');
        var scheduleWrap = $('#creditCuotasSchedule');
        var scheduleList = $('#creditCuotasScheduleList');
        if (!help.length) {
            window.syncCreditInicialMethodUi();
            return;
        }
        if ($('select[name="payment_condition"]').val() !== 'credito') {
            help.text('');
            if (scheduleWrap.length) scheduleWrap.hide();
            window.syncCreditInicialMethodUi();
            return;
        }
        var total = parseFloat(vents.details.total) || 0;
        var raw = ($('input[name="credit_down_payment"]').val() || '').trim().replace(',', '.');
        var inicial = parseFloat(raw);
        if (isNaN(inicial) || raw === '') {
            inicial = 0;
        }
        var n = parseInt($('input[name="credit_quota_count"]').val(), 10) || 1;
        n = Math.max(1, Math.min(60, n));
        $('input[name="credit_quota_count"]').val(n);
        var restante = Math.max(0, total - inicial);
        var porCuota = n > 0 ? restante / n : restante;

        var baseDt = getSaleBaseDate();
        var customEnabled = isCustomEndCreditEnabled();
        var endDt = null;
        if (customEnabled) {
            endDt = syncCreditEndDateHiddenFromParts();
        }
        if (!endDt) {
            endDt = new Date(baseDt.getTime() + 25 * n * 86400000);
            if (!customEnabled) {
                setCreditEndDateInputs(toIsoDateOnly(endDt));
            }
        }
        var diffDays = Math.round((endDt.getTime() - baseDt.getTime()) / 86400000);
        var avgDays = n > 0 ? (diffDays / n) : 0;
        var lastDueDate = toIsoDateOnly(endDt);
        help.text(
            'Saldo después de la inicial: S/ ' + restante.toFixed(2) +
            ' · Referencia por cuota (~): S/ ' + porCuota.toFixed(2) +
            (customEnabled
                ? ' · Intervalo promedio: ' + avgDays.toFixed(1) + ' días (manual)'
                : ' · Intervalo fijo: 25 días')
        );

        if (scheduleWrap.length && scheduleList.length) {
            scheduleList.empty();
            for (var i = 1; i <= n; i++) {
                var due;
                if (customEnabled) {
                    var stepDays = Math.round((diffDays * i) / n);
                    due = new Date(baseDt.getTime() + (stepDays * 86400000));
                } else {
                    due = new Date(baseDt.getTime() + (25 * i) * 86400000);
                }
                var dateStr = toIsoDateOnly(due);
                var label = 'Cuota ' + i + ': ' + dateStr +
                    ' — S/ ' + porCuota.toFixed(2);
                scheduleList.append('<li><i class="fas fa-calendar-alt text-info mr-1"></i>' + label + '</li>');
            }
            scheduleWrap.show();
        }

        if (!customEnabled && lastDueDate && input_endcredit.length) {
            input_endcredit.val(lastDueDate);
        }

        syncCustomEndCreditUi();
        window.syncCreditInicialMethodUi();
    };

    $('.credit-inicial-pay').on('click', function () {
        var val = $(this).data('value');
        $('#credit_down_payment_method').val(val);
        $('.credit-inicial-pay').removeClass('active').attr('aria-pressed', 'false');
        $(this).addClass('active').attr('aria-pressed', 'true');
        window.updateCreditCuotasHelp();
    });

    vents.details.igv = parseFloat($('input[name="igv"]').val());

    $('.select2').select2({
        theme: 'bootstrap4',
        language: "es",
    });

    /* Product */

    input_searchproducts.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                data: {
                    'action': 'search_products',
                    'term': request.term,
                    'ids': JSON.stringify(vents.get_products_ids()),
                },
                dataType: "json",
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                beforeSend: function () {

                },
                success: function (data) {
                    response(data);
                }
            });
        },
        minLength: 1,
        delay: 60,
        select: function (event, ui) {
            event.preventDefault();
            $(this).blur();
            ui.item.cant = 1;
            vents.add_product(ui.item);
            $(this).val('').focus();
        }
    });

    $('.btnClearProducts').on('click', function () {
        input_searchproducts.val('').focus();
    });

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="cant"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            vents.details.products[tr.row].cant = parseInt($(this).val());
            vents.calculate_invoice();
            $('td:eq(4)', tblProducts.row(tr.row).node()).html('S/ ' + vents.details.products[tr.row].subtotal.toFixed(2));
            $('td:eq(7)', tblProducts.row(tr.row).node()).html('S/ ' + vents.details.products[tr.row].total.toFixed(2));
        })
        .on('change', 'input[name="dscto_unitary"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            vents.details.products[tr.row].dscto = parseFloat($(this).val());
            vents.calculate_invoice();
            $('td:eq(6)', tblProducts.row(tr.row).node()).html('S/ ' + vents.details.products[tr.row].total_dscto.toFixed(2));
            $('td:eq(7)', tblProducts.row(tr.row).node()).html('S/ ' + vents.details.products[tr.row].total.toFixed(2));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            vents.details.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
        });

    $('.btnSearchProducts').on('click', function () {
        tblSearchProducts = $('#tblSearchProducts').DataTable({
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
                    'action': 'search_products',
                    'term': input_searchproducts.val(),
                    'ids': JSON.stringify(vents.get_products_ids()),
                },
                dataSrc: ""
            },
            scrollX: true,
            scrollCollapse: true,
            columns: [
                {data: "name"},
                {data: "category.name"},
                {data: "pvp"},
                {data: "price_promotion"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [2, 3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/ ' + parseFloat(data).toFixed(2);
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="add" class="btn btn-success btn-flat btn-xs"><i class="fas fa-plus"></i></a>';
                    }
                }
            ],
            rowCallback: function (row, data, index) {

            },
        });
        $('#myModalSearchProducts').modal('show');
    });

    $('#tblSearchProducts tbody')
        .off()
        .on('click', 'a[rel="add"]', function () {
            var row = tblSearchProducts.row($(this).parents('tr')).data();
            row.cant = 1;
            vents.add_product(row);
            tblSearchProducts.row($(this).parents('tr')).remove().draw();
        });

    $('.btnRemoveAllProducts').on('click', function () {
        if (vents.details.products.length === 0) return false;
        dialog_action('Notificación', '¿Estas seguro de eliminar todos los items de tu detalle?', function () {
            vents.details.products = [];
            vents.list_products();
        });
    });

    /* Client */

    select_client.select2({
        theme: "bootstrap4",
        language: 'es',
        allowClear: true,
        // dropdownParent: modal_sale,
        ajax: {
            delay: 120,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            url: pathname,
            data: function (params) {
                var queryParameters = {
                    term: params.term,
                    action: 'search_client'
                }
                return queryParameters;
            },
            processResults: function (data) {
                return {
                    results: data
                };
            },
        },
        placeholder: 'Ingrese una descripción',
        minimumInputLength: 1,
    })
        .on('select2:select', function (e) {
            fvSale.revalidateField('client');
            var clientData = e.params && e.params.data ? e.params.data : null;
            var wrap = $('#saleClientPropertiesWrap');
            var listEl = document.getElementById('saleClientPropertiesList');
            if (clientData && clientData.id && listEl && window.ClientPredios) {
                wrap.show();
                ClientPredios.renderSalePropertiesList(listEl, clientData);
            }
        })
        .on('select2:clear', function (e) {
            fvSale.revalidateField('client');
            $('#saleClientPropertiesWrap').hide();
            var listEl = document.getElementById('saleClientPropertiesList');
            if (listEl) {
                listEl.innerHTML = '';
            }
        });

    $('.btnAddClient').on('click', function () {
        /*input_birthdate.datetimepicker('date', new Date());*/
        $('#myModalClient').modal('show');
    });

    var modalClientForm = $('#frmClient');
    var modalDniInput = modalClientForm.find('input[name="dni"]');
    var modalFirstNameInput = modalClientForm.find('input[name="first_name"]');
    var modalLastNameInput = modalClientForm.find('input[name="last_name"]');
    var modalExistingClientInput = $('#modal_existing_client_id');

    function syncSaleClientSelection(clientData) {
        if (!clientData || !clientData.id) {
            return;
        }
        var text = clientData.text || (
            clientData.user
                ? ((clientData.user.full_name || '') + ' / ' + (clientData.user.dni || '')).trim()
                : ''
        );
        var newOption = new Option(text, clientData.id, false, true);
        select_client.find('option[value="' + clientData.id + '"]').remove();
        select_client.append(newOption).trigger('change');
        var wrap = $('#saleClientPropertiesWrap');
        var listEl = document.getElementById('saleClientPropertiesList');
        if (listEl && window.ClientPredios) {
            wrap.show();
            ClientPredios.renderSalePropertiesList(listEl, clientData);
        }
        fvSale.revalidateField('client');
    }

    function fillExistingClientForm(clientData) {
        if (!clientData || !clientData.id) {
            return;
        }
        modalExistingClientInput.val(clientData.id);
        if (clientData.user) {
            modalClientForm.find('[name="first_name"]').val(clientData.user.first_name || '');
            modalClientForm.find('[name="last_name"]').val(clientData.user.last_name || '');
            modalClientForm.find('[name="dni"]').val(clientData.user.dni || '');
            modalClientForm.find('[name="email"]').val(clientData.user.email || '');
        }
        modalClientForm.find('[name="mobile"]').val(clientData.mobile || '');
        modalClientForm.find('[name="department"]').val(clientData.department || '').trigger('change');
        modalClientForm.find('[name="province"]').val(clientData.province || '');
        modalClientForm.find('[name="district"]').val(clientData.district || '');
        modalClientForm.find('[name="address"]').val(clientData.address || '');

        var modalRoot = document.getElementById('modalClientPrediosRoot');
        if (modalRoot && window.ClientPredios) {
            ClientPredios.init(modalRoot, {
                initial: clientData.properties || [],
                types: window.__salePredioTypes || [],
                departments: window.__salePredioDepartments || [],
                productsCatalog: window.__salePredioProducts || [],
            });
        }
        syncSaleClientSelection(clientData);
        ['first_name', 'last_name', 'dni', 'email', 'mobile', 'department', 'province', 'district', 'address'].forEach(function (field) {
            try {
                fvClient.revalidateField(field);
            } catch (e) {}
        });
        if (typeof toastr !== 'undefined') {
            toastr.info('Cliente registrado cargado. Puede agregar o actualizar sus predios.');
        }
    }

    if (modalDniInput.length && !modalClientForm.find('.btnLookupDni').length) {
        if (!modalDniInput.parent().hasClass('input-group')) {
            modalDniInput.wrap('<div class="input-group"></div>');
        }
        modalDniInput.after(
            '<div class="input-group-append">' +
            '<button type="button" class="btn btn-info btnLookupDni" title="Buscar por DNI">' +
            '<i class="fas fa-search"></i>' +
            '</button>' +
            '</div>'
        );
    }

    modalClientForm.on('click', '.btnLookupDni', function () {
        var dni = $.trim(modalDniInput.val());
        if (dni.length < 7 || dni.length > 12) {
            message_error('Ingrese un DNI válido entre 7 y 12 dígitos');
            return false;
        }
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            dataType: 'json',
            data: {
                action: 'lookup_dni',
                dni: dni
            },
            beforeSend: function () {
                modalClientForm.find('.btnLookupDni').prop('disabled', true);
            },
            success: function (resp) {
                if (!resp.success) {
                    message_error(resp.error || 'No se pudieron obtener los datos del DNI');
                    return;
                }
                if (resp.existing_client && resp.client) {
                    fillExistingClientForm(resp.client);
                    return;
                }
                var data = resp.data || {};
                modalFirstNameInput.val(data.first_name || '');
                modalLastNameInput.val(data.last_name || '');
                fvClient.revalidateField('first_name');
                fvClient.revalidateField('last_name');
                fvClient.revalidateField('dni');
            },
            error: function () {
                message_error('No se pudo consultar el API de DNI');
            },
            complete: function () {
                modalClientForm.find('.btnLookupDni').prop('disabled', false);
            }
        });
        return false;
    });

    $('#myModalClient').on('hidden.bs.modal', function () {
        modalExistingClientInput.val('');
        fvClient.resetForm(true);
        var modalRoot = document.getElementById('modalClientPrediosRoot');
        if (modalRoot && window.ClientPredios) {
            ClientPredios.init(modalRoot, {
                initial: [],
                types: window.__salePredioTypes || [],
                departments: window.__salePredioDepartments || [],
                productsCatalog: window.__salePredioProducts || [],
            });
        }
    });

    $('#saleClientPropertiesList').on('click', '.btn-add-predio-to-sale', function () {
        var idx = $(this).data('predio-index');
        var listEl = document.getElementById('saleClientPropertiesList');
        if (listEl && window.ClientPredios) {
            ClientPredios.addPredioProductToSale(listEl, idx);
        }
    });

    $('#btnContrataPrint').on('click', function () {
        printContrataDraft();
    });
    $('#btnCronogramaPrint').on('click', function () {
        downloadPaymentSchedule(pendingContractSaleId);
    });
    $('#btnContrataDone, #btnContrataSkip').on('click', function () {
        finalizeContrataFlow();
    });

    $('input[name="dni"]').keypress(function (e) {
        return validate_form_text('numbers', e, null);
    });

    $('input[name="mobile"]').keypress(function (e) {
        return validate_form_text('numbers', e, null);
    });


    /*input_birthdate.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
        maxDate: current_date
    });

    input_birthdate.on('change.datetimepicker', function (e) {
        fvClient.revalidateField('birthdate');
    });*/

    /* Sale */

    select_paymentcondition
        .on('change', function () {
            var id = $(this).val();
            hideRowsVents([
                {'pos': 0, 'enable': false},
                {'pos': 1, 'enable': false},
                {'pos': 2, 'enable': false},
                {'pos': 3, 'enable': false}
            ]);
            fvSale.disableValidator('card_number');
            fvSale.disableValidator('titular');
            fvSale.disableValidator('amount_debited');
            fvSale.disableValidator('cash');
            fvSale.disableValidator('change');
            switch (id) {
                case "contado":
                    fvSale.disableValidator('end_credit');
                    if (input_custom_endcredit_enabled.length) {
                        input_custom_endcredit_enabled.prop('checked', false);
                    }
                    fvSale.enableValidator('payment_method');
                    select_paymentmethod.prop('disabled', false).val('efectivo').trigger('change');
                    payMethodGrid.removeClass('is-disabled');
                    window.updateCreditCuotasHelp();
                    break;
                case "credito":
                    fvSale.enableValidator('end_credit');
                    fvSale.disableValidator('payment_method');
                    select_paymentmethod.val('efectivo');
                    hideRowsVents([{'pos': 2, 'enable': true}, {'pos': 3, 'enable': true}]);
                    select_paymentmethod.prop('disabled', true);
                    payMethodGrid.addClass('is-disabled');
                    $('.factora-credit-inicial-grid').removeClass('is-disabled');
                    updatePayMethodCardsActive();
                    fvSale.revalidateField('credit_down_payment');
                    window.updateCreditCuotasHelp();
                    break;
            }
            syncCustomEndCreditUi();
        });

    select_paymentmethod.on('change', function () {
        var id = $(this).val();
        hideRowsVents([
            {'pos': 0, 'enable': false},
            {'pos': 1, 'enable': false},
            {'pos': 2, 'enable': false},
            {'pos': 3, 'enable': false}
        ]);
        input_cash.val(input_cash.val());
        input_amountdebited.val('0.00');
        switch (id) {
            case "efectivo":
                fvSale.enableValidator('change');
                fvSale.disableValidator('card_number');
                fvSale.disableValidator('titular');
                fvSale.disableValidator('amount_debited');
                input_cash.trigger("touchspin.updatesettings", {max: 100000000});
                hideRowsVents([{'pos': 0, 'enable': true}, {'pos': 3, 'enable': select_paymentcondition.val() === 'credito'}]);
                break;
            case "yape":
            case "plin":
                input_cash.val('0.00');
                input_change.val('0.00');
                input_cardnumber.val('');
                input_titular.val('');
                input_amountdebited.val('0.00');
                fvSale.disableValidator('change');
                fvSale.disableValidator('card_number');
                fvSale.disableValidator('titular');
                fvSale.disableValidator('amount_debited');
                if (select_paymentcondition.val() === 'credito') {
                    hideRowsVents([{'pos': 2, 'enable': true}, {'pos': 3, 'enable': true}]);
                }
                break;
            case "tarjeta_debito_credito":
                fvSale.disableValidator('change');
                fvSale.enableValidator('card_number');
                fvSale.enableValidator('titular');
                fvSale.enableValidator('amount_debited');
                input_amountdebited.val(vents.details.total.toFixed(2));
                input_titular.val('');
                hideRowsVents([
                    {'pos': 1, 'enable': true},
                    {'pos': 3, 'enable': select_paymentcondition.val() === 'credito'}
                ]);
                break;
            case "efectivo_tarjeta":
                input_change.val('0.00');
                fvSale.enableValidator('change');
                fvSale.enableValidator('card_number');
                fvSale.enableValidator('titular');
                fvSale.enableValidator('amount_debited');
                input_cash.trigger("touchspin.updatesettings", {max: vents.details.total});
                hideRowsVents([
                    {'pos': 0, 'enable': true},
                    {'pos': 1, 'enable': true},
                    {'pos': 3, 'enable': select_paymentcondition.val() === 'credito'}
                ]);
                break;
        }
        updatePayMethodCardsActive();
    });

    input_cash
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            verticalbuttons: true,
            maxboostedstep: 10,
        })
        .off('change').on('change touchspin.on.min touchspin.on.max', function () {
        var paymentmethod = select_paymentmethod.val();
        fvSale.revalidateField('cash');
        var total = parseFloat(vents.details.total);
        switch (paymentmethod) {
            case "efectivo_tarjeta":
                fvSale.revalidateField('amount_debited');
                fvSale.revalidateField('change');
                //input_change.val('0.00');
                break;
            case "efectivo":
                var cash = parseFloat($(this).val());
                var change = cash - total;
                input_change.val(change.toFixed(2));
                fvSale.revalidateField('change');
                break;
        }
        return false;
    })
        .keypress(function (e) {
            return validate_decimals($(this), e);
        });

    input_cardnumber
        .on('keypress', function (e) {
            fvSale.revalidateField('card_number');
            return validate_form_text('numbers_spaceless', e, null);
        })
        .on('keyup', function (e) {
            var number = $(this).val();
            var number_nospaces = number.replace(/ /g, "");
            if (number_nospaces.length % 4 === 0 && number_nospaces.length > 0 && number_nospaces.length < 16) {
                number += ' ';
            }
            $(this).val(number);
        });

    input_titular.on('keypress', function (e) {
        return validate_form_text('letters', e, null);
    });

    input_amountdebited.on('change blur', function () {
        if ($('select[name="payment_condition"]').val() === 'credito'
            && $('#credit_down_payment_method').val() === 'tarjeta_debito_credito') {
            fvSale.revalidateField('amount_debited');
        }
    });

    if (input_endcredit_year.length && input_endcredit_month.length && input_endcredit_day.length) {
        var initialEnd = parseIsoDateOnly(input_endcredit.val());
        if (!initialEnd) {
            var fallback = new Date(getSaleBaseDate().getTime() + 25 * 86400000);
            initialEnd = fallback;
        }
        setCreditEndDateInputs(toIsoDateOnly(initialEnd));
        input_endcredit_year.add(input_endcredit_month).add(input_endcredit_day).on('change blur keyup', function () {
            syncCreditEndDateHiddenFromParts();
            fvSale.revalidateField('end_credit');
            window.updateCreditCuotasHelp();
        });
    }

    input_custom_endcredit_enabled.on('change', function () {
        syncCustomEndCreditUi();
        window.updateCreditCuotasHelp();
        fvSale.revalidateField('end_credit');
    });

    input_endcredit.on('change', function () {
        fvSale.revalidateField('end_credit');
    });

    $('input[name="dscto"]')
        .TouchSpin({
            min: 0.00,
            max: 100,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            verticalbuttons: true,
            maxboostedstep: 10,
        })
        .on('change touchspin.on.min touchspin.on.max', function () {
            var dscto = $(this).val();
            if (dscto === '') {
                $(this).val('0.00');
            }
            vents.calculate_invoice();
        })
        .keypress(function (e) {
            return validate_decimals($(this), e);
        });

    $('.btnProforma').on('click', function () {
        if (vents.details.products.length === 0) {
            message_error('Debe tener al menos un item en el detalle para poder crear una proforma');
            return false;
        }

        var parameters = {
            'action': 'create_proforma',
            'vents': JSON.stringify(vents.details)
        };

        $.ajax({
            url: pathname,
            data: parameters,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            xhrFields: {
                responseType: 'blob'
            },
            success: function (request) {
                if (!request.hasOwnProperty('error')) {
                    var d = new Date();
                    var date_now = d.getFullYear() + "_" + d.getMonth() + "_" + d.getDay();
                    var a = document.createElement("a");
                    document.body.appendChild(a);
                    a.style = "display: none";
                    const blob = new Blob([request], {type: 'application/pdf'});
                    const url = URL.createObjectURL(blob);
                    a.href = url;
                    a.download = "download_pdf_" + date_now + ".pdf";
                    a.click();
                    window.URL.revokeObjectURL(url);
                    return false;
                }
                message_error(request.error);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                message_error(errorThrown + ' ' + textStatus);
            }
        });
    });

    hideRowsVents([
        {'pos': 0, 'enable': true},
        {'pos': 1, 'enable': false},
        {'pos': 2, 'enable': false},
        {'pos': 3, 'enable': false}
    ]);

    window.syncCreditInicialMethodUi();

    $('input[name="credit_quota_count"]').on('change keyup blur', function () {
        window.updateCreditCuotasHelp();
        fvSale.revalidateField('credit_down_payment');
        fvSale.revalidateField('end_credit');
    });

    $('input[name="credit_down_payment"]').on('change blur keyup', function () {
        window.updateCreditCuotasHelp();
        fvSale.revalidateField('credit_down_payment');
    }).keypress(function (e) {
        return validate_decimals($(this), e);
    });

    updatePayMethodCardsActive();
    syncCustomEndCreditUi();

    $('i[data-field="client"]').hide();
    $('i[data-field="searchproducts"]').hide();
});