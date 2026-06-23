ALLOWED_CERT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
MAX_CERT_BYTES = 10 * 1024 * 1024


def _validate_cert_file(uploaded):
    if not uploaded:
        return
    name = uploaded.name or ''
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext not in ALLOWED_CERT_EXTENSIONS:
        raise ValueError('El archivo debe ser PDF, JPG o PNG.')
    if uploaded.size > MAX_CERT_BYTES:
        raise ValueError('El archivo no debe superar 10 MB.')


def _clear_spouse_fields(client):
    client.spouse_first_name = ''
    client.spouse_last_name = ''
    client.spouse_dni = ''


def _clear_all_marital_documents(client):
    _clear_spouse_fields(client)
    client.marriage_certificate = None
    client.death_certificate = None
    client.divorce_certificate = None
    client.separation_certificate = None


def _save_optional_file(client, request, field_name):
    uploaded = request.FILES.get(field_name)
    if uploaded:
        _validate_cert_file(uploaded)
        setattr(client, field_name, uploaded)


def apply_client_marital_extras(client, request):
    """Datos de cónyuge y documentos civiles: opcionales según estado civil."""
    status = client.marital_status or ''
    if status == 'casado':
        client.spouse_first_name = (request.POST.get('spouse_first_name') or '').strip()
        client.spouse_last_name = (request.POST.get('spouse_last_name') or '').strip()
        client.spouse_dni = (request.POST.get('spouse_dni') or '').strip()
        _save_optional_file(client, request, 'marriage_certificate')
        client.death_certificate = None
        client.divorce_certificate = None
        client.separation_certificate = None
    elif status == 'viudo':
        _clear_spouse_fields(client)
        _save_optional_file(client, request, 'death_certificate')
        client.marriage_certificate = None
        client.divorce_certificate = None
        client.separation_certificate = None
    elif status == 'divorciado':
        _clear_spouse_fields(client)
        _save_optional_file(client, request, 'divorce_certificate')
        client.marriage_certificate = None
        client.death_certificate = None
        client.separation_certificate = None
    elif status == 'separado':
        _clear_spouse_fields(client)
        _save_optional_file(client, request, 'separation_certificate')
        client.marriage_certificate = None
        client.death_certificate = None
        client.divorce_certificate = None
    else:
        _clear_all_marital_documents(client)
