document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('frmForm');
    let pendingSubmitFv = null;

    const fv = FormValidation.formValidation(form, {
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
                name: {
                    validators: {
                        notEmpty: {},
                        stringLength: {min: 2},
                        remote: {
                            url: pathname,
                            data: function () {
                                return {
                                    obj: form.querySelector('[name="name"]').value,
                                    type: 'name',
                                    action: 'validate_data'
                                };
                            },
                            message: 'El nombre ya se encuentra registrado',
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
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
        .on('core.form.valid', function () {
            if (window.COLLECTOR_USER_IS_SUPERUSER) {
                submit_formdata_with_ajax_form(fv);
                return;
            }
            pendingSubmitFv = fv;
            $('#supervisor_collector_password').val('');
            $('#modalSupervisorCollectorSave').modal('show');
        });

    $('#btnConfirmSupervisorCollectorSave').on('click', function () {
        var $btn = $(this);
        $btn.prop('disabled', true);
        $.ajax({
            url: window.SUPERVISOR_COLLECTOR_SAVE_URL || '/security/verify-supervisor-collector-save/',
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            data: {
                supervisor_username: $('#supervisor_collector_username').val(),
                supervisor_password: $('#supervisor_collector_password').val()
            },
            dataType: 'json',
            success: function (resp) {
                if (resp.success && pendingSubmitFv) {
                    $('#modalSupervisorCollectorSave').modal('hide');
                    submit_formdata_with_ajax_form(pendingSubmitFv);
                    pendingSubmitFv = null;
                } else {
                    message_error(resp.error || 'No se pudo autorizar.');
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
});

$(function () {
    $('input[name="name"]').keypress(function (e) {
        return validate_form_text('letters', e, null);
    });
});
