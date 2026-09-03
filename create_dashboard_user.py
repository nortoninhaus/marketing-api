#!/usr/bin/env python3

from getpass import getpass

from google.api_core.exceptions import AlreadyExists

from dashboard.auth import get_firestore_client, hash_dashboard_password
from dashboard.config import DASHBOARD_USERS_COLLECTION


def main():
    username = input("Documento (username): ").strip()
    if not username or "/" in username:
        raise SystemExit("El username no puede estar vacío ni contener '/'.")

    password = getpass("Password: ")
    if not password:
        raise SystemExit("El password no puede estar vacío.")

    can_dl = input("Permitir descargas de reportes (s/N): ").strip().lower() in ("s", "si", "y", "yes", "true")
    can_bench = input("Permitir ver competidores/benchmarking (s/N): ").strip().lower() in ("s", "si", "y", "yes", "true")

    user = {
        "active": True,
        "client_id": "client_1",
        "user_id": "user_1",
        "can_download": can_dl,
        "can_benchmark": can_bench,
        "password_hash": hash_dashboard_password(password),
        "accounts": {
            "meta_ads": ["act_1314422010193648"],
            "tiktok_ads": ["7535519175259783184"],
        },
    }

    try:
        get_firestore_client().collection(DASHBOARD_USERS_COLLECTION).document(username).create(user)
    except AlreadyExists:
        raise SystemExit(f"El usuario '{username}' ya existe; no fue modificado.")

    print(f"Usuario '{username}' creado correctamente.")


if __name__ == "__main__":
    main()
