#!/usr/bin/env python3
"""Manage dashboard user accounts and platform permissions in Firestore."""

import argparse
import json
import sys

from dashboard.auth import get_firestore_client
from dashboard.config import DASHBOARD_USERS_COLLECTION


def list_users():
    db = get_firestore_client()
    docs = list(db.collection(DASHBOARD_USERS_COLLECTION).stream())
    if not docs:
        print("No se encontraron usuarios en la colección.")
        return
    print("\n=== Usuarios del Dashboard ===")
    for doc in docs:
        data = doc.to_dict() or {}
        print(f"\nUsuario: {doc.id}")
        print(f"  Activo: {data.get('active', True)}")
        print(f"  Client ID: {data.get('client_id')}")
        print(f"  User ID: {data.get('user_id')}")
        print(f"  Descargas permitidas (can_download): {data.get('can_download', False)}")
        print(f"  Cuentas / Permisos: {json.dumps(data.get('accounts', {}), indent=4)}")


def update_user_download_permission(username: str, can_download: bool):
    db = get_firestore_client()
    doc_ref = db.collection(DASHBOARD_USERS_COLLECTION).document(username)
    doc = doc_ref.get()
    if not doc.exists:
        print(f"Error: El usuario '{username}' no existe en Firestore.")
        sys.exit(1)
    doc_ref.update({"can_download": can_download})
    print(f"Permiso de descargas actualizado: {username} -> can_download = {can_download}")


def update_user_accounts(username: str, accounts: dict):
    db = get_firestore_client()
    doc_ref = db.collection(DASHBOARD_USERS_COLLECTION).document(username)
    doc = doc_ref.get()
    if not doc.exists:
        print(f"Error: El usuario '{username}' no existe en Firestore.")
        sys.exit(1)
    doc_ref.update({"accounts": accounts})
    print(f"Permisos actualizados con éxito para '{username}':")
    print(json.dumps(accounts, indent=2))


def add_platform_account(username: str, platform_key: str, account_id: str):
    db = get_firestore_client()
    doc_ref = db.collection(DASHBOARD_USERS_COLLECTION).document(username)
    doc = doc_ref.get()
    if not doc.exists:
        print(f"Error: El usuario '{username}' no existe.")
        sys.exit(1)
    data = doc.to_dict() or {}
    accounts = data.get("accounts", {})
    if platform_key not in accounts:
        accounts[platform_key] = []
    if account_id not in accounts[platform_key]:
        accounts[platform_key].append(account_id)
    doc_ref.update({"accounts": accounts})
    print(f"Cuenta '{account_id}' agregada a '{platform_key}' para el usuario '{username}'.")
    print(json.dumps(accounts, indent=2))


def set_admin_all(username: str):
    update_user_accounts(username, {"*": ["*"]})


def main():
    parser = argparse.ArgumentParser(description="Administrar permisos y cuentas de usuarios en Firestore")
    parser.add_argument("--list", action="store_true", help="Listar todos los usuarios y sus permisos")
    parser.add_argument("--user", type=str, help="Nombre de usuario a modificar")
    parser.add_argument("--add-account", nargs=2, metavar=("PLATFORM", "ACCOUNT_ID"), help="Agregar cuenta a una plataforma")
    parser.add_argument("--set-all", action="store_true", help="Dar acceso total a todas las plataformas y cuentas (*)")
    parser.add_argument("--set-download", choices=["true", "false"], help="Habilitar o deshabilitar descargas (can_download)")
    
    args = parser.parse_args()

    if args.list:
        list_users()
        return

    if args.user:
        if args.set_download is not None:
            update_user_download_permission(args.user, args.set_download.lower() == "true")
        if args.set_all:
            set_admin_all(args.user)
            return
        if args.add_account:
            add_platform_account(args.user, args.add_account[0], args.add_account[1])
            return
        if args.set_download is not None:
            return

    parser.print_help()


if __name__ == "__main__":
    main()
