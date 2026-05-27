var fv;

document.addEventListener('DOMContentLoaded', function () {
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
                opening_amount: {
                    validators: {
                        notEmpty: {
                            message: 'Ingrese el monto inicial'
                        },
                        numeric: {
                            message: 'Use punto decimal (ej. 100.50)',
                            decimalSeparator: '.'
                        }
                    }
                },
                opened_at: {
                    validators: {
                        notEmpty: {
                            message: 'La fecha y hora de apertura es obligatoria'
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
                    FormValidation.utils.classSet(groupEle, {'has-success': false});
                }
                FormValidation.utils.classSet(e.element, {'is-valid': false});
            }
            const iconPlugin = fv.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            iconElement && (iconElement.style.display = 'none');
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(form.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach(function (messageEle) {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            submit_formdata_with_ajax_form(fv);
        });
});

$(function () {
    var $opened = $('input[name="opened_at"]');
    $opened.datetimepicker({
        useCurrent: true,
        format: 'YYYY-MM-DD HH:mm',
        locale: 'es',
        keepOpen: false,
    });
    $opened.on('change.datetimepicker', function () {
        fv.revalidateField('opened_at');
    });

    $('.select2').select2({
        theme: 'bootstrap4',
        language: "es"
    });

    $('select[name="company"]')
        .on('change', function () {
            if (fv) {
                fv.revalidateField('company');
            }
        });

    $('input[name="opening_amount"]').TouchSpin({
        min: 0,
        max: 10000000,
        step: 0.01,
        decimals: 2,
        boostat: 5,
        maxboostedstep: 10,
        prefix: '',
        verticalbuttons: true
    }).on('change', function () {
        fv.revalidateField('opening_amount');
    });
});
