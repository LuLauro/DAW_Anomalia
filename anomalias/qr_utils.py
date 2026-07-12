import base64
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.conf import settings
from django.urls import reverse


def build_qr_code_data_uri(data):
    image = qrcode.make(data)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_absolute_target_url(request, path_with_query):
    if settings.QR_CODE_BASE_URL:
        return f"{settings.QR_CODE_BASE_URL.rstrip('/')}{path_with_query}"
    return request.build_absolute_uri(path_with_query)


def build_sala_anomalia_url(request, sala_id):
    return build_absolute_target_url(
        request,
        f"{reverse('anomalias:registar_anomalia')}?{urlencode({'sala': sala_id})}",
    )


def build_computador_anomalia_url(request, sala_id, computador_id):
    return build_absolute_target_url(
        request,
        f"{reverse('anomalias:registar_anomalia')}?"
        f"{urlencode({'sala': sala_id, 'pc': computador_id})}",
    )
