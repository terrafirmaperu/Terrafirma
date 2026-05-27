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
                closing_amount_counted: {
                    validators: {
                        notEmpty: {
                            message: 'Ingrese el monto contado'
                        },
                        numeric: {
                            message: 'Use punto decimal (ej. 100.50)',
                            decimalSeparator: '.'
                        }
                    }
                },
                close_at: {
                    validators: {
                        notEmpty: {
                            message: 'La fecha y hora de cierre es obligatoria'
                        }
                    }
                },
                closing_amount_expected: {
                    validators: {
                        numeric: {
                            message: 'Use punto decimal',
                            decimalSeparator: '.'
                        }
                    }
                },
                difference_amount: {
                    validators: {
                        numeric: {
                            message: 'Use punto decimal',
                            decimalSeparator: '.'
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
    var $closeAt = $('input[name="close_at"]');
    $closeAt.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD HH:mm',
        locale: 'es',
        keepOpen: false,
    });
    $closeAt.on('change.datetimepicker', function () {
        fv.revalidateField('close_at');
    });

    $('input[name="closing_amount_counted"], input[name="closing_amount_expected"], input[name="difference_amount"]').TouchSpin({
        min: 0,
        max: 10000000,
        step: 0.01,
        decimals: 2,
        boostat: 5,
        maxboostedstep: 10,
        verticalbuttons: true
    }).on('change', function () {
        var name = $(this).attr('name');
        if (fv) {
            fv.revalidateField(name);
        }
    });
});
