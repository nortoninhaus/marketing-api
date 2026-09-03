import os
import json
import time
import hmac
import hashlib
import jwt
import streamlit as st
import streamlit.components.v1 as components
from google.cloud import firestore

from dashboard.config import (
    FIREBASE_PROJECT_ID,
    DASHBOARD_USERS_COLLECTION,
    DASHBOARD_JWT_SECRET,
    DASHBOARD_JWT_HOURS,
    DASHBOARD_AUTH_COOKIE,
    DASHBOARD_AUTH_QUERY_PARAM,
    PASSWORD_ALGORITHM,
    PASSWORD_ITERATIONS
)

_firestore_client = None


def get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client(project=FIREBASE_PROJECT_ID)
    return _firestore_client


def hash_dashboard_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_dashboard_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
        return hmac.compare_digest(digest, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def normalize_dashboard_accounts(raw_accounts):
    accounts = {}
    if isinstance(raw_accounts, dict):
        for platform, values in raw_accounts.items():
            values = [values] if isinstance(values, str) else values
            if not isinstance(values, list):
                continue
            clean_values = [str(value).strip() for value in values if value is not None and str(value).strip()]
            if clean_values:
                accounts[str(platform).strip()] = clean_values
    elif isinstance(raw_accounts, list):
        for item in raw_accounts:
            if isinstance(item, dict):
                platform = str(item.get("platform") or "*").strip()
                account_id = str(item.get("account_id") or item.get("id") or "").strip()
            else:
                platform = "*"
                account_id = str(item).strip()
            if account_id:
                accounts.setdefault(platform, []).append(account_id)
    return accounts


def authenticate_dashboard_user(username, password):
    username = (username or "").strip()
    if not username or "/" in username or not password:
        return None
    doc = get_firestore_client().collection(DASHBOARD_USERS_COLLECTION).document(username).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    if data.get("active") is False or not verify_dashboard_password(password, data.get("password_hash")):
        return None
    return {
        "username": username,
        "client_id": data.get("client_id"),
        "user_id": data.get("user_id") or data.get("api_user_id") or username,
        "accounts": normalize_dashboard_accounts(data.get("accounts", {})),
        "can_download": bool(data.get("can_download", False)),
    }


def create_dashboard_token(user):
    now = int(time.time())
    payload = {**user, "iat": now, "exp": now + DASHBOARD_JWT_HOURS * 3600}
    return jwt.encode(payload, DASHBOARD_JWT_SECRET, algorithm="HS256")


def decode_dashboard_token(token):
    try:
        return jwt.decode(token, DASHBOARD_JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def dashboard_query_token():
    token = st.query_params.get(DASHBOARD_AUTH_QUERY_PARAM, "")
    return token[0] if isinstance(token, list) else token


def clear_dashboard_query_token():
    try:
        del st.query_params[DASHBOARD_AUTH_QUERY_PARAM]
    except KeyError:
        pass


def dashboard_auth_cookie_bridge(token=None, clear=False, reload_page=False):
    cookie_name = json.dumps(DASHBOARD_AUTH_COOKIE)
    query_name = json.dumps(DASHBOARD_AUTH_QUERY_PARAM)
    max_age = DASHBOARD_JWT_HOURS * 3600
    token_value = json.dumps(token or "")
    clear_value = "true" if clear else "false"
    reload_value = "true" if reload_page else "false"
    components.html(f"""
    <script>
    (() => {{
        const parentWindow = window.parent;
        const cookieName = {cookie_name};
        const queryName = {query_name};
        const token = {token_value};
        const clearCookie = {clear_value};
        const reloadPage = {reload_value};
        const secure = parentWindow.location.protocol === "https:" ? "; Secure" : "";
        const cookieAttrs = "; Max-Age={max_age}; Path=/; SameSite=Lax" + secure;
        const params = new URLSearchParams(parentWindow.location.search);
        const cookie = parentWindow.document.cookie.split("; ").find(row => row.startsWith(cookieName + "="));

        if (clearCookie) {{
            parentWindow.document.cookie = cookieName + "=; Max-Age=0; Path=/; SameSite=Lax" + secure;
            params.delete(queryName);
            const url = parentWindow.location.pathname + (params.toString() ? "?" + params.toString() : "") + parentWindow.location.hash;
            parentWindow.postMessage({{ type: "inhaus-navigate", url: url }}, "*");
            return;
        }}

        if (token) {{
            parentWindow.document.cookie = cookieName + "=" + encodeURIComponent(token) + cookieAttrs;
            if (reloadPage) {{
                params.delete(queryName);
                const url = parentWindow.location.pathname + (params.toString() ? "?" + params.toString() : "") + parentWindow.location.hash;
                parentWindow.postMessage({{ type: "inhaus-navigate", url: url }}, "*");
            }}
            return;
        }}

        if (cookie && !params.has(queryName)) {{
            params.set(queryName, decodeURIComponent(cookie.split("=").slice(1).join("=")));
            const url = parentWindow.location.pathname + "?" + params.toString() + parentWindow.location.hash;
            parentWindow.postMessage({{ type: "inhaus-navigate", url: url }}, "*");
        }}
    }})();
    </script>
    """, height=0, width=0)


def dashboard_allowed_account_ids(user, platform_key):
    accounts = user.get("accounts", {})
    allowed = list(dict.fromkeys(accounts.get(platform_key, []) + accounts.get("*", [])))
    return None if "*" in allowed else allowed


def filter_dashboard_connections(connections, user, platform_key):
    allowed = dashboard_allowed_account_ids(user, platform_key)
    if allowed is None:
        return connections
    allowed_set = set(allowed)
    return [connection for connection in connections if str(connection.get("account_id")) in allowed_set]


def connection_account_label(connection, platform_key):
    account_id = str(connection.get("account_id") or "").strip()
    account_name = str(connection.get("account_name") or connection.get("name") or connection.get("display_name") or "").strip()
    if not account_name or account_name == account_id:
        account_name = f"Cuenta Meta {account_id}" if platform_key == "meta_ads" else "Cuenta"
    return f"{account_name} ({account_id})"


def log_login_event(username: str):
    from dashboard.analytics import log_analytics_event
    log_analytics_event("login", user_id=username, details={"auth_method": "form"})


def require_dashboard_login(theme_icon, on_theme_change):
    session_token = st.session_state.get("dashboard_auth_token")
    if not session_token:
        dashboard_auth_cookie_bridge()
    query_token = dashboard_query_token()
    token = session_token or query_token
    user = decode_dashboard_token(token) if token else None
    if user:
        if "can_download" not in user:
            try:
                doc = get_firestore_client().collection(DASHBOARD_USERS_COLLECTION).document(user.get("username", "")).get()
                user["can_download"] = bool(doc.to_dict().get("can_download", False)) if doc.exists else False
                token = create_dashboard_token(user)
                dashboard_auth_cookie_bridge(token)
            except Exception:
                user["can_download"] = False
        st.session_state["dashboard_auth_token"] = token
        st.session_state["dashboard_user"] = user
        if query_token:
            clear_dashboard_query_token()
            st.rerun()
        dashboard_auth_cookie_bridge(token)
        return user

    if token:
        st.session_state.pop("dashboard_auth_token", None)
        st.session_state.pop("dashboard_user", None)
        clear_dashboard_query_token()
        dashboard_auth_cookie_bridge(clear=True)
        st.stop()

    with st.container(horizontal_alignment="right"):
        st.button(
            theme_icon,
            key="theme_switch_button",
            help="Cambiar tema",
            on_click=on_theme_change,
        )

    with st.container(horizontal_alignment="center"):
        with st.container(border=True, width=480, key="login_card"):
            with st.container(horizontal_alignment="center", gap=None):
                st.html("""
                    <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg"
                         alt="Inhaus" class="inhaus-login-logo"
                         style="display:block;width:180px;margin:0 auto 0.75rem;">
                """)
                st.markdown("## Acceso al dashboard", text_alignment="center")
                st.caption(
                    "Ingresa tus credenciales para consultar tus reportes de pauta.",
                    text_alignment="center",
                )

            with st.form("dashboard_login_form", border=False):
                username = st.text_input(
                    "Usuario",
                    placeholder="Ingresa tu usuario",
                    autocomplete="username",
                    icon=":material/person:",
                )
                password = st.text_input(
                    "Contraseña",
                    type="password",
                    placeholder="Ingresa tu contraseña",
                    autocomplete="current-password",
                    icon=":material/lock:",
                )
                submitted = st.form_submit_button(
                    "Ingresar al dashboard",
                    type="primary",
                    icon=":material/login:",
                    width="stretch",
                )

            if submitted:
                try:
                    user = authenticate_dashboard_user(username, password)
                except Exception as exc:
                    st.error(f"No se pudo validar el usuario en Firebase: {exc}")
                else:
                    if user:
                        log_login_event(username)
                        token = create_dashboard_token(user)
                        st.session_state["dashboard_auth_token"] = token
                        st.session_state["dashboard_user"] = user
                        st.session_state["query_run"] = False
                        st.query_params[DASHBOARD_AUTH_QUERY_PARAM] = token
                        st.rerun()
                    st.error("Usuario o contraseña incorrectos.")

    st.stop()


def dashboard_auth_self_check():
    stored = hash_dashboard_password("secret")
    assert verify_dashboard_password("secret", stored)
    assert not verify_dashboard_password("wrong", stored)
    token = create_dashboard_token({"username": "demo", "client_id": "client_1", "user_id": "user_1", "accounts": {"meta_ads": ["act_1"]}})
    assert decode_dashboard_token(token)["accounts"]["meta_ads"] == ["act_1"]
