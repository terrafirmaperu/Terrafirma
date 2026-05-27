(function (window, $) {
    'use strict';

    var FALLBACK_UBIGEO = {
        'Amazonas': {'Chachapoyas': ['Chachapoyas', 'Asuncion', 'Balsas'], 'Bagua': ['Bagua', 'Aramango', 'Copallin']},
        'Ancash': {'Huaraz': ['Huaraz', 'Independencia', 'Jangas'], 'Santa': ['Chimbote', 'Nuevo Chimbote', 'Coishco']},
        'Apurimac': {'Abancay': ['Abancay', 'Chacoche', 'Tamburco'], 'Andahuaylas': ['Andahuaylas', 'San Jeronimo', 'Talavera']},
        'Arequipa': {'Arequipa': ['Arequipa', 'Cerro Colorado', 'Paucarpata'], 'Camana': ['Camana', 'Mariscal Caceres', 'Ocona']},
        'Ayacucho': {'Huamanga': ['Ayacucho', 'Carmen Alto', 'San Juan Bautista'], 'Huanta': ['Huanta', 'Luricocha', 'Santillana']},
        'Cajamarca': {'Cajamarca': ['Cajamarca', 'Asuncion', 'Banos del Inca'], 'Jaen': ['Jaen', 'Bellavista', 'Colasay']},
        'Callao': {'Callao': ['Callao', 'Bellavista', 'La Perla']},
        'Cusco': {'Cusco': ['Cusco', 'San Jeronimo', 'San Sebastian'], 'La Convencion': ['Santa Ana', 'Echarate', 'Maranura']},
        'Huancavelica': {'Huancavelica': ['Huancavelica', 'Acobambilla', 'Yauli'], 'Tayacaja': ['Pampas', 'Acostambo', 'Ahuaycha']},
        'Huanuco': {'Huanuco': ['Huanuco', 'Amarilis', 'Pillco Marca'], 'Leoncio Prado': ['Rupa-Rupa', 'Daniel Alomia Robles', 'Luyando']},
        'Ica': {'Ica': ['Ica', 'La Tinguina', 'Parcona'], 'Pisco': ['Pisco', 'Humay', 'San Andres']},
        'Junin': {'Huancayo': ['Huancayo', 'El Tambo', 'Chilca'], 'Chanchamayo': ['Chanchamayo', 'Perene', 'Pichanaqui']},
        'La Libertad': {'Trujillo': ['Trujillo', 'El Porvenir', 'La Esperanza'], 'Chepen': ['Chepen', 'Pacanga', 'Pueblo Nuevo']},
        'Lambayeque': {'Chiclayo': ['Chiclayo', 'Jose Leonardo Ortiz', 'La Victoria'], 'Lambayeque': ['Lambayeque', 'Mochumi', 'Morrope']},
        'Lima': {'Lima': ['Lima', 'Ate', 'Comas', 'Los Olivos', 'San Juan de Lurigancho', 'Surco'], 'Huaral': ['Huaral', 'Aucallama', 'Chancay'], 'Cañete': ['San Vicente de Canete', 'Asia', 'Imperial']},
        'Loreto': {'Maynas': ['Iquitos', 'Belen', 'Punchana'], 'Alto Amazonas': ['Yurimaguas', 'Balsapuerto', 'Lagunas']},
        'Madre de Dios': {'Tambopata': ['Tambopata', 'Inambari', 'Laberinto'], 'Manu': ['Manu', 'Fitzcarrald', 'Huepetuhe']},
        'Moquegua': {'Mariscal Nieto': ['Moquegua', 'Carumas', 'Cuchumbaya'], 'Ilo': ['Ilo', 'El Algarrobal', 'Pacocha']},
        'Pasco': {'Pasco': ['Chaupimarca', 'Yanacancha', 'Tinyahuarco'], 'Oxapampa': ['Oxapampa', 'Villa Rica', 'Pozuzo']},
        'Piura': {'Piura': ['Piura', 'Castilla', 'Catacaos'], 'Sullana': ['Sullana', 'Bellavista', 'Marcavelica']},
        'Puno': {'Puno': ['Puno', 'Acora', 'Atuncolla'], 'San Roman': ['Juliaca', 'Cabana', 'Caracoto']},
        'San Martin': {'Moyobamba': ['Moyobamba', 'Calzada', 'Soritor'], 'Tarapoto': ['Tarapoto', 'La Banda de Shilcayo', 'Morales']},
        'Tacna': {'Tacna': ['Tacna', 'Alto de la Alianza', 'Ciudad Nueva'], 'Jorge Basadre': ['Locumba', 'Ilabaya', 'Ite']},
        'Tumbes': {'Tumbes': ['Tumbes', 'Corrales', 'San Jacinto'], 'Zarumilla': ['Zarumilla', 'Aguas Verdes', 'Papayal']},
        'Ucayali': {'Coronel Portillo': ['Calleria', 'Campoverde', 'Manantay'], 'Padre Abad': ['Aguaytia', 'Irazola', 'Neshuya']}
    };
    var UBIGEO_SOURCE_URL = '/static/data/peru_ubigeos_full.json';
    var ubigeoCache = null;
    var ubigeoPromise = null;

    function normalizeText(s) {
        return String(s || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function normalizeUbigeoFromApi(raw) {
        var out = {};
        // Formato ya normalizado: { DEP: { PROV: [DIST...] } }
        if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
            Object.keys(raw).forEach(function (dep) {
                var depName = String(dep || '').trim();
                if (!depName) return;
                out[depName] = {};
                var provsObj = raw[dep] || {};
                Object.keys(provsObj).forEach(function (prov) {
                    var provName = String(prov || '').trim();
                    if (!provName) return;
                    var dists = provsObj[prov] || [];
                    if (!Array.isArray(dists)) dists = [];
                    out[depName][provName] = dists
                        .map(function (d) { return String(d || '').trim(); })
                        .filter(Boolean);
                });
            });
            return out;
        }
        if (!Array.isArray(raw)) return out;
        raw.forEach(function (depItem) {
            var depName = (depItem && (depItem.name || depItem.departamento || depItem.department || depItem.label) || '').trim();
            if (!depName) return;
            out[depName] = {};
            var provs = depItem.provinces || depItem.provincias || depItem.province || [];
            if (!Array.isArray(provs)) provs = [];
            provs.forEach(function (provItem) {
                var provName = (provItem && (provItem.name || provItem.provincia || provItem.province || provItem.label) || '').trim();
                if (!provName) return;
                var dists = provItem.districts || provItem.distritos || provItem.district || [];
                if (!Array.isArray(dists)) dists = [];
                out[depName][provName] = dists.map(function (d) {
                    if (typeof d === 'string') return d;
                    return (d && (d.name || d.distrito || d.district || d.label) || '').trim();
                }).filter(Boolean);
            });
        });
        return out;
    }

    function getUbigeoData() {
        if (ubigeoCache) {
            return Promise.resolve(ubigeoCache);
        }
        if (ubigeoPromise) {
            return ubigeoPromise;
        }
        ubigeoPromise = fetch(UBIGEO_SOURCE_URL, {method: 'GET'})
            .then(function (resp) {
                if (!resp.ok) throw new Error('UBIGEO API HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (json) {
                var normalized = normalizeUbigeoFromApi(json);
                ubigeoCache = Object.keys(normalized).length ? normalized : FALLBACK_UBIGEO;
                return ubigeoCache;
            })
            .catch(function () {
                ubigeoCache = FALLBACK_UBIGEO;
                return ubigeoCache;
            });
        return ubigeoPromise;
    }

    function buildKeyMap(obj) {
        var map = {};
        Object.keys(obj || {}).forEach(function (k) {
            map[normalizeText(k)] = k;
        });
        return map;
    }

    function setOptions($select, placeholder, values) {
        $select.empty();
        $select.append($('<option>', {value: '', text: placeholder}));
        (values || []).forEach(function (value) {
            $select.append($('<option>', {value: value, text: value}));
        });
    }

    window.initPeruUbigeoForForm = function (formSelector) {
        var $form = $(formSelector);
        if (!$form.length) return;

        var $dep = $form.find('select[name="department"]');
        var $prov = $form.find('select[name="province"]');
        var $dist = $form.find('select[name="district"]');
        if (!$dep.length || !$prov.length || !$dist.length) return;

        var currentDep = $dep.val() || '';
        var currentProv = $prov.val() || '';
        var currentDist = $dist.val() || '';

        function refreshProvinces(data, keepValue) {
            var dep = $dep.val() || '';
            var depKeyMap = buildKeyMap(data);
            var realDep = depKeyMap[normalizeText(dep)] || dep;
            var provinces = realDep && data[realDep] ? Object.keys(data[realDep]).sort() : [];
            setOptions($prov, 'Seleccione provincia', provinces);
            if (keepValue && provinces.indexOf(keepValue) >= 0) $prov.val(keepValue);
        }

        function refreshDistricts(data, keepValue) {
            var dep = $dep.val() || '';
            var prov = $prov.val() || '';
            var depKeyMap = buildKeyMap(data);
            var realDep = depKeyMap[normalizeText(dep)] || dep;
            var provKeyMap = buildKeyMap((data[realDep] || {}));
            var realProv = provKeyMap[normalizeText(prov)] || prov;
            var districts = realDep && realProv && data[realDep] && data[realDep][realProv] ? data[realDep][realProv] : [];
            setOptions($dist, 'Seleccione distrito', districts);
            if (keepValue && districts.indexOf(keepValue) >= 0) $dist.val(keepValue);
        }

        getUbigeoData().then(function (data) {
            refreshProvinces(data, currentProv);
            refreshDistricts(data, currentDist);

            $dep.off('change.peruUbigeo').on('change.peruUbigeo', function () {
                refreshProvinces(data, '');
                refreshDistricts(data, '');
            });

            $prov.off('change.peruUbigeo').on('change.peruUbigeo', function () {
                refreshDistricts(data, '');
            });
        });
    };
})(window, window.jQuery);
