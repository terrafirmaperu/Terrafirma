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
                    validators: {
                        notEmpty: {message: 'Indique el proveedor'},
                    }
                },
                api_url: {
                    validators: {
                        notEmpty: {message: 'Ingrese la URL'},
                    }
                },
                api_timeout: {
                    validators: {
                        notEmpty: {message: 'Indique el tiempo de espera'},
                        between: {
                            min: 3,
                            max: 60,
                            message: 'Entre 3 y 60 segundos',
                        },
                    }
                },
            },
        }
    )
        .on('core.form.valid', function () {
            submit_formdata_with_ajax_form(fv);
        });
});

$(function () {
    $('#btnTestDni').on('click', function () {
        var dni = $.trim($('#testDniInput').val());
        if (!dni) {
            $('#testDniResult').text('Ingrese un DNI de prueba.');
            return;
        }
        var $btn = $(this);
        $btn.prop('disabled', true);
        $('#testDniResult').text('Consultando...');
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            dataType: 'json',
            data: {
                action: 'test_dni',
                test_dni: dni,
            },
            success: function (resp) {
                if (!resp.success) {
                    $('#testDniResult').text(resp.error || 'Error en la consulta');
                    return;
                }
                var d = resp.data || {};
                $('#testDniResult').text(
                    'OK — ' + (d.first_name || '') + ' ' + (d.last_name || '') + ' (DNI ' + (d.dni || dni) + ')'
                );
            },
            error: function () {
                $('#testDniResult').text('No se pudo probar la consulta.');
            },
            complete: function () {
                $btn.prop('disabled', false);
            }
        });
    });
});
