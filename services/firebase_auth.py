import os
import json
import firebase_admin
from firebase_admin import credentials, auth


def _init():
    if firebase_admin._apps:
        return
    sa_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not sa_raw:
        raise RuntimeError(
            "Variable FIREBASE_SERVICE_ACCOUNT_JSON no está configurada. "
            "Descarga el Service Account desde Firebase Console y pégala como JSON en esta variable."
        )
    sa_dict = json.loads(sa_raw)
    cred = credentials.Certificate(sa_dict)
    firebase_admin.initialize_app(cred)


_init()


def verify_token(id_token: str) -> dict:
    """Verifica un Firebase ID token y retorna el payload decodificado."""
    return auth.verify_id_token(id_token)
