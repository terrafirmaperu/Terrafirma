var tblProducts;
var tblSearchProducts;
var current_date;

var fvPurchase;

var input_datejoined;
var input_endcredit;
var input_searchproducts;
var inputCredit;
var select_paymentcondition;

var purchase = {
    details: {
        products: [],
    },
    calculate_invoice: function () {
        $.each(this.details.products, function (i, item) {
            item.cant = parseInt(item.cant);
            item.subtotal = item.cant * parseFloat(item.price);
        });
    },
    list_products: function () {
        this.calculate_invoice();
        tblProducts = $('#tblProducts').DataTable({
            //responsive: true,
            //autoWidth: false,
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
                {data: "category.name"},
                {data: "cant"},
                {data: "price"},
                {data: "subtotal"},
            ],
            columnDefs: [
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control input-sm" style="width: 100px;" autocomplete="off" name="cant" value="' + row.cant + '">';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/ ' + parseFloat(data).toFixed(2);
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
                        max: 10000000,
                        verticalbuttons: true,
                    })
                    .keypress(function (e) {
                        return validate_form_text('numbers', e, null);
                    });
            },
            initComplete: function (settings, json) {
                $("[data-toggle='tooltip']").tooltip();
            },
        });
    },
    get_products_ids: function () {
        return this.details.products.map(value => value.id);
    },
    add_product: function (item) {
        this.details.products.push(item);
        this.list_products();
    },
};


document.addEventListener('DOMContentLoaded', function (e) {
    const frmPurchase = document.getElementById('frmPurchase');
    fvPurchase = FormValidation.formValidation(frmPurchase, {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                excluded: new FormValidation.plugins.Excluded(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh',
                }),
            },
            fields: {
                payment_condition: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione una forma de pago'
                        },
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
                end_credit: {
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
            const iconPlugin = fvPurchase.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            iconElement && (iconElement.style.display = 'none');
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(frmPurchase.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach((messageEle) => {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            var parameters = new FormData($(fvPurchase.form)[0]);
            parameters.append('action', $('input[name="action"]').val());
            parameters.append('end_credit', input_endcredit.val());
            if (purchase.details.products.length === 0) {
                message_error('Debe tener al menos un item en el detalle');
                return false;
            }
            parameters.append('products', JSON.stringify(purchase.details.products));
            submit_formdata_with_ajax('Notificación',
                '¿Estas seguro de realizar la siguiente acción?',
                pathname,
                parameters,
                function () {
                    location.href = fvPurchase.form.getAttribute('data-url');
                },
            );
        });
});

$(function () {

    inputCredit = $('.inputCredit');
    current_date = new moment().format("YYYY-MM-DD");
    input_datejoined = $('input[name="date_joined"]');
    input_endcredit = $('input[name="end_credit"]');
    input_searchproducts = $('input[name="searchproducts"]');
    select_paymentcondition = $('select[name="payment_condition"]');

    $('.select2').select2({
        theme: 'bootstrap4',
        language: "es",
    });

    /* Products */

    input_searchproducts.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                data: {
                    'action': 'search_products',
                    'term': request.term,
                    'ids': JSON.stringify(purchase.get_products_ids()),
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
        min_length: 3,
        delay: 300,
        select: function (event, ui) {
            event.preventDefault();
            $(this).blur();
            ui.item.cant = 1;
            purchase.add_product(ui.item);
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
            purchase.details.products[tr.row].cant = parseInt($(this).val());
            purchase.calculate_invoice();
            $('td:eq(5)', tblProducts.row(tr.row).node()).html('S/ ' + purchase.details.products[tr.row].subtotal.toFixed(2));
        })
        .on('change', 'input[name="price"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            purchase.details.products[tr.row].price = parseFloat($(this).val());
            purchase.calculate_invoice();
            $('td:eq(5)', tblProducts.row(tr.row).node()).html('S/ ' + purchase.details.products[tr.row].subtotal.toFixed(2));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            purchase.details.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            //purchase.list_products();
            $('.tooltip').remove();
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
                    'ids': JSON.stringify(purchase.get_products_ids()),
                },
                dataSrc: ""
            },
            //paging: false,
            //ordering: false,
            //info: false,
            scrollX: true,
            scrollCollapse: true,
            columns: [
                {data: "name"},
                {data: "category.name"},
                {data: "price"},
                {data: "pvp"},
                {data: "stock"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-3, -4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/ ' + parseFloat(data).toFixed(2);
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<span class="badge badge-secondary">N/A</span>'
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="add" class="btn btn-success btn-flat btn-xs"><i class="fas fa-plus"></i></a>'
                    }
                }
            ],
            rowCallback: function (row, data, index) {
                // Stock eliminado
            },
        });
        $('#myModalSearchProducts').modal('show');
    });

    $('#myModalSearchProducts').on('shown.bs.modal', function () {
        purchase.list_products();
    });

    $('#tblSearchProducts tbody')
        .off()
        .on('click', 'a[rel="add"]', function () {
        var row = tblSearchProducts.row($(this).parents('tr')).data();
        row.cant = 1;
        purchase.add_product(row);
        tblSearchProducts.row($(this).parents('tr')).remove().draw();
    });

    $('.btnRemoveAllProducts').on('click', function () {
        if (purchase.details.products.length === 0) return false;
        dialog_action('Notificación', '¿Estas seguro de eliminar todos los items de tu detalle?', function () {
            purchase.details.products = [];
            purchase.list_products();
        }, function () {

        });
    });


    $('input[name="ruc"]').keypress(function (e) {
        return validate_form_text('numbers', e, null);
    });

    $('input[name="mobile"]').keypress(function (e) {
        return validate_form_text('numbers', e, null);
    });

    /* Form */

    select_paymentcondition
        .on('change.select2', function () {
            fvPurchase.revalidateField('payment_condition');
            var id = $(this).val();
            var start_date = input_datejoined.val();
            input_endcredit.datetimepicker('minDate', start_date);
            input_endcredit.datetimepicker('date', start_date);
            inputCredit.hide();
            if (id === 'credito') {
                inputCredit.show();
            }
        });

    input_datejoined.datetimepicker({
        format: 'YYYY-MM-DD',
        useCurrent: false,
        locale: 'es',
        orientation: 'bottom',
        keepOpen: false
    });

    input_datejoined.on('change.datetimepicker', function (e) {
        fvPurchase.revalidateField('date_joined');
        input_endcredit.datetimepicker('minDate', e.date);
        input_endcredit.datetimepicker('date', e.date);
    });

    input_endcredit.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
        minDate: current_date
    });

    input_endcredit.datetimepicker('date', input_endcredit.val());

    input_endcredit.on('change.datetimepicker', function (e) {
        fvPurchase.revalidateField('end_credit');
    });

    inputCredit.hide();

    $('i[data-field="searchproducts"]').hide();
});