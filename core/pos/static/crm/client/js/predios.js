(function (window) {
    'use strict';

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function departmentOptions(departments, selected) {
        var html = '<option value="">Seleccione departamento</option>';
        (departments || []).forEach(function (d) {
            var id = d.id || d[0] || '';
            var name = d.name || d[1] || id;
            var sel = id === selected ? ' selected' : '';
            html += '<option value="' + escapeHtml(id) + '"' + sel + '>' + escapeHtml(name) + '</option>';
        });
        return html;
    }

    function typeOptions(types, selected) {
        var html = '<option value="">Tipo de predio</option>';
        (types || []).forEach(function (t) {
            var id = t.id || t[0] || '';
            var name = t.name || t[1] || id;
            var sel = id === selected ? ' selected' : '';
            html += '<option value="' + escapeHtml(id) + '"' + sel + '>' + escapeHtml(name) + '</option>';
        });
        return html;
    }

    function productOptions(catalog, selected) {
        var html = '<option value="">Seleccione producto / servicio</option>';
        (catalog || []).forEach(function (p) {
            var id = p.id;
            var label = p.name;
            if (p.price_current) {
                label += ' — S/ ' + p.price_current;
            }
            var sel = String(id) === String(selected || '') ? ' selected' : '';
            html += '<option value="' + escapeHtml(id) + '" data-price="' + escapeHtml(p.price_current || '') + '"' + sel + '>' +
                escapeHtml(label) + '</option>';
        });
        return html;
    }

    var supervisorPredioUnlockUrl = window.SUPERVISOR_PREDIO_UNLOCK_URL || '/security/verify-supervisor-predio-unlock/';
    var supervisorPredioUnlockCallback = null;

    function getPredioUnlockUrl() {
        return window.SUPERVISOR_PREDIO_UNLOCK_URL || supervisorPredioUnlockUrl;
    }

    function isCardContractLocked(rootEl, card) {
        var state = rootEl._prediosState || {};
        var idInput = card.querySelector('.predio-id');
        var id = idInput ? String(idInput.value || '') : '';
        if (!id) {
            return false;
        }
        if ((state.pendingUnlockIds || []).indexOf(id) >= 0) {
            return false;
        }
        return (state.lockedIds || []).indexOf(id) >= 0;
    }

    function wouldRemoveLockedPredios(rootEl) {
        var state = rootEl._prediosState || {};
        var panel = getPanel(rootEl);
        var toggle = panel ? panel.querySelector('.client-predios-toggle') : null;
        if (toggle && !toggle.checked) {
            return (state.lockedIds || []).some(function (id) {
                return (state.pendingUnlockIds || []).indexOf(id) < 0;
            });
        }
        var kept = collect(rootEl).map(function (item) {
            return item.id ? String(item.id) : '';
        }).filter(Boolean);
        return (state.lockedIds || []).some(function (id) {
            if ((state.pendingUnlockIds || []).indexOf(id) >= 0) {
                return false;
            }
            return kept.indexOf(id) < 0;
        });
    }

    function bindSupervisorPredioUnlockModal() {
        if (window._supervisorPredioUnlockBound) {
            return;
        }
        window._supervisorPredioUnlockBound = true;
        $(document).on('click', '#btnConfirmSupervisorPredioUnlock', function () {
            var u = $('#supervisor_predio_username').val();
            var p = $('#supervisor_predio_password').val();
            var $btn = $(this);
            $btn.prop('disabled', true);
            $.ajax({
                url: getPredioUnlockUrl(),
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    supervisor_username: u,
                    supervisor_password: p
                },
                dataType: 'json',
                success: function (resp) {
                    if (resp.success) {
                        $('#modalSupervisorPredioUnlock').modal('hide');
                        $('#supervisor_predio_password').val('');
                        if (typeof supervisorPredioUnlockCallback === 'function') {
                            supervisorPredioUnlockCallback(true);
                        }
                        supervisorPredioUnlockCallback = null;
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
    }

    function requestSupervisorPredioUnlock(callback) {
        bindSupervisorPredioUnlockModal();
        supervisorPredioUnlockCallback = callback;
        $('#supervisor_predio_password').val('');
        $('#modalSupervisorPredioUnlock').modal('show');
    }

    function applyLockedCardState(card, locked) {
        if (!card || !locked) {
            return;
        }
        card.querySelectorAll('input, select, textarea').forEach(function (el) {
            if (el.classList.contains('predio-id')) {
                return;
            }
            if (el.tagName === 'SELECT') {
                el.disabled = true;
            } else {
                el.setAttribute('readonly', 'readonly');
            }
        });
    }

    function toggleCommunityFields(card) {
        if (!card) {
            return;
        }
        var enabled = card.querySelector('.predio-community-enabled');
        var fields = card.querySelector('.predio-community-fields');
        if (!enabled || !fields) {
            return;
        }
        fields.style.display = enabled.checked ? '' : 'none';
    }

    function updateProductHint(card) {
        var select = card.querySelector('.predio-product');
        var hint = card.querySelector('.predio-product-price-hint');
        if (!select || !hint) {
            return;
        }
        var opt = select.options[select.selectedIndex];
        if (!opt || !opt.value) {
            hint.textContent = 'Seleccione el producto con el precio que se usará al facturar este predio.';
            return;
        }
        var price = opt.getAttribute('data-price') || '';
        hint.textContent = price ? ('Precio de venta: S/ ' + price) : '';
    }

    function buildCardHtml(index, data, departments, types, productsCatalog) {
        data = data || {};
        var title = data.label ? escapeHtml(data.label) : ('Predio ' + (index + 1));
        var lockedBadge = data.contract_locked
            ? '<span class="badge badge-warning ml-2 client-predio-locked-badge" title="Contrato generado"><i class="fas fa-lock"></i> Contrato</span>'
            : '';
        return (
            '<div class="client-predio-card border rounded p-3 mb-3' + (data.contract_locked ? ' client-predio-card--locked' : '') + '" data-index="' + index + '">' +
            '<input type="hidden" class="predio-id" value="' + escapeHtml(data.id || '') + '">' +
            '<div class="d-flex justify-content-between align-items-center mb-2">' +
            '<strong class="client-predio-card-title">' + title + lockedBadge + '</strong>' +
            '<button type="button" class="btn btn-outline-danger btn-sm btn-remove-client-predio" title="Quitar predio">' +
            '<i class="fas fa-times"></i></button>' +
            '</div>' +
            '<div class="row">' +
            '<div class="col-md-12"><div class="form-group">' +
            '<label>Producto / servicio a facturar <span class="text-danger">*</span></label>' +
            '<select class="form-control predio-product">' +
            productOptions(productsCatalog, data.product_id || '') +
            '</select>' +
            '<small class="form-text text-muted predio-product-price-hint"></small>' +
            '</div></div>' +
            '<div class="col-md-6"><div class="form-group">' +
            '<label>Nombre / referencia</label>' +
            '<input type="text" class="form-control predio-label" placeholder="Ej. Terreno principal" value="' + escapeHtml(data.label || '') + '">' +
            '</div></div>' +
            '<div class="col-md-6"><div class="form-group">' +
            '<label>Tipo de predio</label>' +
            '<select class="form-control predio-type">' + typeOptions(types, data.predio_type || '') + '</select>' +
            '</div></div>' +
            '<div class="col-md-4"><div class="form-group">' +
            '<label>Departamento</label>' +
            '<select class="form-control predio-department">' + departmentOptions(departments, data.department || '') + '</select>' +
            '</div></div>' +
            '<div class="col-md-4"><div class="form-group">' +
            '<label>Provincia</label>' +
            '<input type="text" class="form-control predio-province" placeholder="Provincia" value="' + escapeHtml(data.province || '') + '">' +
            '</div></div>' +
            '<div class="col-md-4"><div class="form-group">' +
            '<label>Distrito</label>' +
            '<input type="text" class="form-control predio-district" placeholder="Distrito" value="' + escapeHtml(data.district || '') + '">' +
            '</div></div>' +
            '<div class="col-md-12"><div class="form-group form-check mb-2">' +
            '<input type="checkbox" class="form-check-input predio-community-enabled" id="predio-community-enabled-' + index + '"' +
            (data.community_location_enabled ? ' checked' : '') + '>' +
            '<label class="form-check-label" for="predio-community-enabled-' + index + '">' +
            'Registrar comunidad y centro poblado</label>' +
            '</div></div>' +
            '<div class="col-md-12 predio-community-fields"' +
            (data.community_location_enabled ? '' : ' style="display:none;"') + '>' +
            '<div class="row">' +
            '<div class="col-md-6"><div class="form-group">' +
            '<label>Comunidad</label>' +
            '<input type="text" class="form-control predio-community" placeholder="Comunidad" value="' + escapeHtml(data.community || '') + '">' +
            '</div></div>' +
            '<div class="col-md-6"><div class="form-group">' +
            '<label>Centro poblado</label>' +
            '<input type="text" class="form-control predio-population-center" placeholder="Centro poblado" value="' + escapeHtml(data.population_center || '') + '">' +
            '</div></div>' +
            '</div></div>' +
            '<div class="col-md-12"><div class="form-group">' +
            '<label>Dirección del predio</label>' +
            '<input type="text" class="form-control predio-address" placeholder="Dirección" value="' + escapeHtml(data.address || '') + '">' +
            '</div></div>' +
            '<div class="col-md-3"><div class="form-group">' +
            '<label>Lote</label>' +
            '<input type="text" class="form-control predio-lot" value="' + escapeHtml(data.lot_number || '') + '">' +
            '</div></div>' +
            '<div class="col-md-3"><div class="form-group">' +
            '<label>Manzana</label>' +
            '<input type="text" class="form-control predio-block" value="' + escapeHtml(data.block || '') + '">' +
            '</div></div>' +
            '<div class="col-md-3"><div class="form-group">' +
            '<label>Nº partida</label>' +
            '<input type="text" class="form-control predio-registry" value="' + escapeHtml(data.registry_number || '') + '">' +
            '</div></div>' +
            '<div class="col-md-3"><div class="form-group">' +
            '<label>Área (m²)</label>' +
            '<input type="text" class="form-control predio-area" value="' + escapeHtml(data.area || '') + '">' +
            '</div></div>' +
            '<div class="col-md-3"><div class="form-group">' +
            '<label>Perímetro (ml)</label>' +
            '<input type="text" class="form-control predio-perimeter" value="' + escapeHtml(data.perimeter || '') + '">' +
            '</div></div>' +
            '</div></div>'
        );
    }

    function getPanel(rootEl) {
        return rootEl.closest('.client-predios-panel');
    }

    function syncRemoveButtons(rootEl) {
        var cards = rootEl.querySelectorAll('.client-predio-card');
        var unlockedCount = 0;
        cards.forEach(function (card) {
            if (!isCardContractLocked(rootEl, card)) {
                unlockedCount += 1;
            }
        });
        rootEl.querySelectorAll('.btn-remove-client-predio').forEach(function (btn) {
            var card = btn.closest('.client-predio-card');
            if (card && isCardContractLocked(rootEl, card)) {
                btn.style.display = '';
                btn.title = 'Requiere autorización de supervisor';
                btn.classList.add('btn-remove-locked-predio');
            } else {
                btn.classList.remove('btn-remove-locked-predio');
                btn.title = 'Quitar predio';
                btn.style.display = unlockedCount > 1 ? '' : 'none';
            }
        });
    }

    function reindexTitles(rootEl) {
        rootEl.querySelectorAll('.client-predio-card').forEach(function (card, idx) {
            var labelInput = card.querySelector('.predio-label');
            var titleEl = card.querySelector('.client-predio-card-title');
            var labelVal = labelInput ? $.trim(labelInput.value) : '';
            if (titleEl) {
                titleEl.textContent = labelVal || ('Predio ' + (idx + 1));
            }
            card.setAttribute('data-index', idx);
        });
    }

    function addCard(rootEl, data) {
        var state = rootEl._prediosState;
        var index = rootEl.querySelectorAll('.client-predio-card').length;
        var wrap = document.createElement('div');
        wrap.innerHTML = buildCardHtml(index, data, state.departments, state.types, state.productsCatalog);
        var card = wrap.firstElementChild;
        rootEl.appendChild(card);
        updateProductHint(card);
        toggleCommunityFields(card);
        if (data.contract_locked) {
            card.classList.add('client-predio-card--locked');
            applyLockedCardState(card, true);
        }
        syncRemoveButtons(rootEl);
        reindexTitles(rootEl);
    }

    function setLinked(panel, linked) {
        var rootEl = panel.querySelector('.client-predios-root');
        var addBtn = panel.querySelector('.btn-add-client-predio');
        var toggle = panel.querySelector('.client-predios-toggle');
        if (toggle) {
            toggle.checked = linked;
        }
        if (rootEl) {
            rootEl.style.display = linked ? '' : 'none';
        }
        if (addBtn) {
            addBtn.style.display = linked ? '' : 'none';
        }
        if (linked && rootEl && rootEl.querySelectorAll('.client-predio-card').length === 0) {
            addCard(rootEl, {});
        }
    }

    function collect(rootEl) {
        var panel = getPanel(rootEl);
        var toggle = panel ? panel.querySelector('.client-predios-toggle') : null;
        if (toggle && !toggle.checked) {
            return [];
        }
        var items = [];
        rootEl.querySelectorAll('.client-predio-card').forEach(function (card) {
            items.push({
                id: (card.querySelector('.predio-id') || {}).value || null,
                label: (card.querySelector('.predio-label') || {}).value || '',
                predio_type: (card.querySelector('.predio-type') || {}).value || '',
                department: (card.querySelector('.predio-department') || {}).value || '',
                province: (card.querySelector('.predio-province') || {}).value || '',
                district: (card.querySelector('.predio-district') || {}).value || '',
                community_location_enabled: (card.querySelector('.predio-community-enabled') || {}).checked || false,
                community: (card.querySelector('.predio-community') || {}).value || '',
                population_center: (card.querySelector('.predio-population-center') || {}).value || '',
                address: (card.querySelector('.predio-address') || {}).value || '',
                lot_number: (card.querySelector('.predio-lot') || {}).value || '',
                block: (card.querySelector('.predio-block') || {}).value || '',
                registry_number: (card.querySelector('.predio-registry') || {}).value || '',
                area: (card.querySelector('.predio-area') || {}).value || '',
                perimeter: (card.querySelector('.predio-perimeter') || {}).value || '',
                product_id: (card.querySelector('.predio-product') || {}).value || '',
            });
        });
        return items;
    }

    function validateProperties(rootEl) {
        var panel = getPanel(rootEl);
        var toggle = panel ? panel.querySelector('.client-predios-toggle') : null;
        if (toggle && !toggle.checked) {
            return true;
        }
        var cards = rootEl.querySelectorAll('.client-predio-card');
        if (!cards.length) {
            return true;
        }
        for (var i = 0; i < cards.length; i++) {
            var productSel = cards[i].querySelector('.predio-product');
            if (!productSel || !productSel.value) {
                message_error('Seleccione el producto / servicio de cada predio vinculado.');
                if (productSel) {
                    productSel.focus();
                }
                return false;
            }
        }
        return true;
    }

    function init(rootEl, options) {
        if (!rootEl) {
            return;
        }
        options = options || {};
        var panel = getPanel(rootEl);
        var initial = options.initial || [];
        rootEl._prediosState = {
            departments: options.departments || [],
            types: options.types || [],
            productsCatalog: options.productsCatalog || [],
            lockedIds: initial.filter(function (p) {
                return p && p.contract_locked && p.id;
            }).map(function (p) {
                return String(p.id);
            }),
            pendingUnlockIds: [],
        };
        rootEl.innerHTML = '';
        if (initial.length) {
            initial.forEach(function (item) {
                addCard(rootEl, item);
            });
            setLinked(panel, true);
        } else {
            setLinked(panel, false);
        }

        if (panel && !panel._prediosBound) {
            panel._prediosBound = true;
            panel.addEventListener('change', function (e) {
                if (e.target.classList.contains('client-predios-toggle')) {
                    if (!e.target.checked && wouldRemoveLockedPredios(rootEl)) {
                        e.target.checked = true;
                        requestSupervisorPredioUnlock(function (ok) {
                            if (!ok) {
                                return;
                            }
                            (rootEl._prediosState.lockedIds || []).forEach(function (id) {
                                if ((rootEl._prediosState.pendingUnlockIds || []).indexOf(id) < 0) {
                                    rootEl._prediosState.pendingUnlockIds.push(id);
                                }
                            });
                            e.target.checked = false;
                            setLinked(panel, false);
                            rootEl.innerHTML = '';
                        });
                        return;
                    }
                    setLinked(panel, e.target.checked);
                    if (!e.target.checked) {
                        rootEl.innerHTML = '';
                    }
                }
                if (e.target.classList.contains('predio-product')) {
                    var card = e.target.closest('.client-predio-card');
                    if (card) {
                        updateProductHint(card);
                    }
                }
                if (e.target.classList.contains('predio-community-enabled')) {
                    toggleCommunityFields(e.target.closest('.client-predio-card'));
                }
            });
            panel.addEventListener('click', function (e) {
                if (e.target.closest('.btn-add-client-predio')) {
                    addCard(rootEl, {});
                }
                var removeBtn = e.target.closest('.btn-remove-client-predio');
                if (removeBtn) {
                    var card = removeBtn.closest('.client-predio-card');
                    if (!card) {
                        return;
                    }
                    if (isCardContractLocked(rootEl, card)) {
                        requestSupervisorPredioUnlock(function (ok) {
                            if (!ok) {
                                return;
                            }
                            var idInput = card.querySelector('.predio-id');
                            if (idInput && idInput.value) {
                                rootEl._prediosState.pendingUnlockIds.push(String(idInput.value));
                            }
                            card.remove();
                            syncRemoveButtons(rootEl);
                            reindexTitles(rootEl);
                        });
                        return;
                    }
                    card.remove();
                    syncRemoveButtons(rootEl);
                    reindexTitles(rootEl);
                }
            });
            panel.addEventListener('input', function (e) {
                if (e.target.classList.contains('predio-label')) {
                    reindexTitles(rootEl);
                }
            });
        }
    }

    function renderSalePropertiesList(containerEl, clientData) {
        if (!containerEl) {
            return;
        }
        var props = (clientData && clientData.properties) ? clientData.properties : [];
        if (!props.length) {
            containerEl.innerHTML = '<p class="text-muted small mb-0">Este cliente no tiene predios vinculados.</p>';
            return;
        }
        var html = '<div class="list-group list-group-flush sale-client-predios-list">';
        props.forEach(function (p, idx) {
            var title = (p.label || '').trim() || ('Predio ' + (idx + 1));
            var typeName = p.predio_type_display || p.predio_type || '';
            var parts = [];
            if (typeName) {
                parts.push(typeName);
            }
            if (p.lot_number) {
                parts.push('Lote ' + escapeHtml(p.lot_number));
            }
            if (p.block) {
                parts.push('Mz. ' + escapeHtml(p.block));
            }
            var loc = [p.district, p.province, p.department].filter(Boolean).join(' — ');
            if (loc) {
                parts.push(escapeHtml(loc));
            }
            if (p.community_location_enabled) {
                if (p.community) {
                    parts.push('Com. ' + escapeHtml(p.community));
                }
                if (p.population_center) {
                    parts.push('C.P. ' + escapeHtml(p.population_center));
                }
            }
            if (p.address) {
                parts.push(escapeHtml(p.address));
            }
            var productLine = '';
            if (p.product_name) {
                productLine = '<div class="mt-1"><span class="badge badge-info">' + escapeHtml(p.product_name) + '</span>' +
                    (p.product_price ? ' <span class="text-success font-weight-bold">S/ ' + escapeHtml(p.product_price) + '</span>' : '') +
                    '</div>';
            } else {
                productLine = '<p class="small text-warning mb-1 mt-1">Sin producto vinculado — edite el cliente para asignar uno.</p>';
            }
            var inProcess = !!(p.in_process || p.contract_locked);
            var processBadge = '';
            if (inProcess) {
                var procLabel = (p.process_label || 'Ya generado en el sistema').trim();
                var procTitle = (p.block_message || procLabel).trim();
                processBadge = '<span class="badge badge-danger sale-predio-in-process ml-1" title="' +
                    escapeHtml(procTitle) + '"><i class="fas fa-ban"></i> ' + escapeHtml(procLabel) + '</span>';
            }
            var billBtn = '';
            if (p.product_sale && typeof window.vents !== 'undefined' && !inProcess) {
                billBtn = '<button type="button" class="btn btn-sm btn-primary mt-1 btn-add-predio-to-sale" data-predio-index="' + idx + '">' +
                    '<i class="fas fa-cart-plus"></i> Agregar a factura</button>';
            } else if (inProcess && p.product_sale) {
                billBtn = '<p class="small text-danger mb-0 mt-1 sale-predio-in-process-hint font-weight-bold">' +
                    '<i class="fas fa-exclamation-triangle"></i> Ya no se puede generar la misma asesoría: ' +
                    'venta y trámite ya registrados en el sistema.</p>';
            }
            var itemClass = 'list-group-item px-0 py-2' + (inProcess ? ' sale-predio-item--in-process' : '');
            html += '<div class="' + itemClass + '">' +
                '<div class="font-weight-bold d-flex flex-wrap align-items-center">' + escapeHtml(title) + processBadge + '</div>' +
                '<div class="small text-muted">' + (parts.join(' · ') || 'Sin detalle de ubicación') + '</div>' +
                productLine + billBtn +
                '</div>';
        });
        html += '</div>';
        containerEl.innerHTML = html;
        containerEl._salePredioProps = props;
    }

    function addPredioProductToSale(containerEl, index) {
        var props = (containerEl && containerEl._salePredioProps) ? containerEl._salePredioProps : [];
        var p = props[index];
        if (!p || !p.product_sale || typeof window.vents === 'undefined') {
            return;
        }
        if (p.in_process || p.contract_locked) {
            var alertText = (p.block_message || p.process_label ||
                'Este predio ya tiene venta y asesoría en el sistema. No puede repetir el mismo trámite.');
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'warning',
                    title: 'Predio ya registrado',
                    text: alertText,
                    confirmButtonText: 'Entendido',
                });
            } else if (typeof message_error === 'function') {
                message_error(alertText);
            } else {
                window.alert(alertText);
            }
            return;
        }
        var item = $.extend({cant: 1}, p.product_sale);
        item.client_property_id = p.id;
        var ids = vents.get_products_ids();
        if (ids.indexOf(item.id) !== -1) {
            message_error('Este producto ya está en el detalle de la factura.');
            return;
        }
        vents.add_product(item);
        if (typeof message_success === 'function') {
            message_success('Producto agregado a la factura.');
        }
    }

    function proceedSubmitFormWithProperties(fv, rootId) {
        var form = fv.form;
        var parameters = new FormData($(form)[0]);
        var root = document.getElementById(rootId || 'clientPrediosRoot');
        if (root) {
            if (!validateProperties(root)) {
                return;
            }
            parameters.set('properties_json', JSON.stringify(collect(root)));
        }
        $.confirm({
            theme: 'material',
            title: 'Confirmación',
            icon: 'fas fa-info-circle',
            content: '¿Esta seguro de realizar la siguiente acción?',
            columnClass: 'small',
            typeAnimated: true,
            cancelButtonClass: 'btn-primary',
            draggable: true,
            dragWindowBorder: false,
            buttons: {
                info: {
                    text: 'Si',
                    btnClass: 'btn-primary',
                    action: function () {
                        $.ajax({
                            url: pathname,
                            data: parameters,
                            type: 'POST',
                            dataType: 'json',
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            processData: false,
                            contentType: false,
                            success: function (request) {
                                if (!request.hasOwnProperty('error')) {
                                    location.href = fv.form.getAttribute('data-url');
                                    return false;
                                }
                                message_error(request.error);
                            },
                            error: function (jqXHR, textStatus, errorThrown) {
                                message_error(errorThrown + ' ' + textStatus);
                            }
                        });
                    }
                },
                danger: {
                    text: 'No',
                    btnClass: 'btn-red'
                }
            }
        });
    }

    function submitFormWithProperties(fv, rootId) {
        var root = document.getElementById(rootId || 'clientPrediosRoot');
        if (root && !validateProperties(root)) {
            return;
        }
        if (root && wouldRemoveLockedPredios(root)) {
            requestSupervisorPredioUnlock(function (ok) {
                if (ok) {
                    proceedSubmitFormWithProperties(fv, rootId);
                }
            });
            return;
        }
        proceedSubmitFormWithProperties(fv, rootId);
    }

    window.ClientPredios = {
        init: init,
        collect: collect,
        renderSalePropertiesList: renderSalePropertiesList,
        submitFormWithProperties: submitFormWithProperties,
        addPredioProductToSale: addPredioProductToSale,
    };

    window.submit_client_form_with_properties = function (fv) {
        submitFormWithProperties(fv, 'clientPrediosRoot');
    };
})(window);
