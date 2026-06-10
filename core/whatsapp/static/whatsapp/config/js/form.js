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
                provider_name: {
                    validators: {notEmpty: {message: 'Indique el proveedor'}},
                },
                phone_number_id: {
                    validators: {notEmpty: {message: 'Ingrese el Phone Number ID'}},
                },
                api_version: {
                    validators: {notEmpty: {message: 'Indique la versión de API'}},
                },
                api_timeout: {
                    validators: {
                        notEmpty: {message: 'Indique el tiempo de espera'},
                        between: {min: 5, max: 120, message: 'Entre 5 y 120 segundos'},
                    },
                },
            },
        }
    ).on('core.form.valid', function () {
        submit_formdata_with_ajax_form(fv);
    });
});

$(function () {
    $('#btnTestApi').on('click', function () {
        var phone = $.trim($('#testPhoneInput').val());
        var $btn = $(this);
        $btn.prop('disabled', true);
        $('#testApiResult').text('Probando…');
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            dataType: 'json',
            data: {action: 'test_api', test_phone: phone},
            success: function (resp) {
                if (!resp.ok) {
                    $('#testApiResult').text(resp.error || 'Error en la prueba');
                    return;
                }
                $('#testApiResult').text(resp.message || 'Conexión correcta.');
            },
            error: function () {
                $('#testApiResult').text('No se pudo probar la API.');
            },
            complete: function () {
                $btn.prop('disabled', false);
            }
        });
    });
});
