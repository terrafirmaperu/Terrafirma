var fv;
/*var input_birthdate;*/

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
                                    obj: form.querySelector('[name="dni"]').value,
                                    type: 'dni',
                                    action: 'validate_data'
                                };
                            },
                            message: 'El número de Dni ó cédula ya se encuentra registrado',
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
                                    obj: form.querySelector('[name="mobile"]').value,
                                    type: 'mobile',
                                    action: 'validate_data'
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
                                    obj: form.querySelector('[name="email"]').value,
                                    type: 'email',
                                    action: 'validate_data'
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
            if (window.ClientPredios && ClientPredios.submitFormWithProperties) {
                ClientPredios.submitFormWithProperties(fv, 'clientPrediosRoot');
            } else {
                submit_formdata_with_ajax_form(fv);
            }
        });
});

$(function () {
    var frm = $('#frmForm');
    var dniInput = frm.find('input[name="dni"]');
    var firstNameInput = frm.find('input[name="first_name"]');
    var lastNameInput = frm.find('input[name="last_name"]');

    if (dniInput.length && !frm.find('.btnLookupDni').length) {
        if (!dniInput.parent().hasClass('input-group')) {
            dniInput.wrap('<div class="input-group"></div>');
        }
        dniInput.after(
            '<div class="input-group-append">' +
            '<button type="button" class="btn btn-info btnLookupDni" title="Buscar por DNI">' +
            '<i class="fas fa-search"></i>' +
            '</button>' +
            '</div>'
        );
    }

    frm.on('click', '.btnLookupDni', function () {
        var dni = $.trim(dniInput.val());
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
                frm.find('.btnLookupDni').prop('disabled', true);
            },
            success: function (resp) {
                if (!resp.success) {
                    message_error(resp.error || 'No se pudieron obtener los datos del DNI');
                    return;
                }
                var data = resp.data || {};
                firstNameInput.val(data.first_name || '');
                lastNameInput.val(data.last_name || '');
                fv.revalidateField('first_name');
                fv.revalidateField('last_name');
                fv.revalidateField('dni');
            },
            error: function () {
                message_error('No se pudo consultar el API de DNI');
            },
            complete: function () {
                frm.find('.btnLookupDni').prop('disabled', false);
            }
        });
        return false;
    });

    /*input_birthdate = $('input[name="birthdate"]');

    input_birthdate.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
    });

    input_birthdate.datetimepicker('date', input_birthdate.val());

    input_birthdate.on('change.datetimepicker', function (e) {
        fv.revalidateField('birthdate');
    });*/

    $('input[name="first_name"]').keypress(function (e) {
        return validate_form_text('letters', e, null);
    });

    $('input[name="last_name"]').keypress(function (e) {
        return validate_form_text('letters', e, null);
    });

    $('input[name="dni"]').keypress(function (e) {
        return validate_form_text('numbers', e, null);
    });

    $('input[name="mobile"]').keypress(function (e) {
        return validate_form_text('numbers', e, null);
    });

});