import streamlit as st
import streamlit.components.v1 as components

from dashboard.auth import get_firestore_client
from dashboard.config import DASHBOARD_USERS_COLLECTION


def has_seen_onboarding_persisted(user=None):
    if st.session_state.get("has_seen_onboarding", False):
        return True
    try:
        if st.context.cookies.get("inhaus_onboarding_seen") in ("true", "1"):
            st.session_state["has_seen_onboarding"] = True
            return True
    except Exception:
        pass
    if user and user.get("has_seen_onboarding", False):
        st.session_state["has_seen_onboarding"] = True
        return True
    return False


def persist_onboarding_seen_to_client(username=None):
    st.session_state["has_seen_onboarding"] = True
    components.html("""
    <script>
    (() => {
        const setSeen = () => {
            try { localStorage.setItem("inhaus_onboarding_seen", "true"); } catch(e) {}
            try {
                if (window.parent) {
                    window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                    if (window.parent.__inhausExpandSidebar) {
                        window.parent.__inhausExpandSidebar();
                    }
                }
            } catch(e) {}
            try {
                if (window.top) {
                    window.top.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.top.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                    if (window.top.__inhausExpandSidebar) {
                        window.top.__inhausExpandSidebar();
                    }
                }
            } catch(e) {}
            try { document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax"; } catch(e) {}
        };
        setSeen();
        setTimeout(setSeen, 200);
        setTimeout(setSeen, 600);
    })();
    </script>
    """, height=0, width=0)
    st.html("""
    <script>
    (() => {
        try {
            window.localStorage.setItem("inhaus_onboarding_seen", "true");
            document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
        } catch (_) {}
        try {
            if (window.parent && window.parent !== window) {
                window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
            }
        } catch (_) {}
    })();
    </script>
    """, unsafe_allow_javascript=True)
    if username:
        try:
            get_firestore_client().collection(DASHBOARD_USERS_COLLECTION).document(username).update({"has_seen_onboarding": True})
        except Exception:
            pass


@st.dialog("🚀 Guía de Inicio: Dashboard de Pauta", width="medium")
def show_onboarding_dialog(current_username=None):
    components.html("""
    <script>
    (() => {
        const setSeen = () => {
            try { localStorage.setItem("inhaus_onboarding_seen", "true"); } catch(e) {}
            try {
                if (window.parent) {
                    window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                }
            } catch(e) {}
            try {
                if (window.parent) {
                    window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                    if (window.parent.__inhausExpandSidebar) {
                        window.parent.__inhausExpandSidebar();
                    }
                }
            } catch(e) {}
            try {
                if (window.top) {
                    window.top.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.top.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                    if (window.top.__inhausExpandSidebar) {
                        window.top.__inhausExpandSidebar();
                    }
                }
            } catch(e) {}
            try { document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax"; } catch(e) {}
        };
        setSeen();
        setTimeout(setSeen, 200);
        setTimeout(setSeen, 600);
    })();
    </script>
    """, height=0, width=0)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.25rem;">
        <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg"
             alt="Inhaus" class="inhaus-login-logo" style="display:block; width:160px; margin:0 auto 0.6rem;">
        <div style="font-size: 0.88rem; opacity: 0.85; font-weight: 500;">
            Desarrollado por <b>Inhaus</b> para el beneficio y gestión estratégica de sus clientes.
        </div>
    </div>

    ### ¡Bienvenido al Dashboard de Marketing! 👋
    
    Esta herramienta te permite consultar y auditar en tiempo real el rendimiento de tus campañas publicitarias y canales orgánicos.
    
    ---
    #### 1️⃣ Selección de Cuentas y Accesos
    * **Selección de Plataforma:** En el menú lateral izquierdo, elige una o más plataformas (**Meta Ads, TikTok Ads, Google Ads**, etc.).
    * **Cuentas Conectadas:** Despliega el menú para elegir la cuenta publicitaria que deseas consultar.
    * 💡 **¿Necesitas acceso a más cuentas?**
      * Los usuarios no pueden agregar cuentas directamente; únicamente pueden seleccionar las cuentas a las que el administrador les ha otorgado acceso previo.
      * Si necesitas acceso a cuentas adicionales, solicítalo a la persona que te dio acceso o envía un correo solicitando la habilitación a **dpineda@inhauscorp.com**.

    ---
    #### 2️⃣ Configurar Métricas y Fechas
    * **Métricas Inteligentes:** El sistema ya selecciona por defecto las métricas oficiales recomendadas (incluyendo reproducciones de video, seguidores ganados y visitas al perfil en TikTok). Puedes añadir más escribiendo en el buscador.
    * **Comparativa Automática:** Al elegir tu rango de fechas, el dashboard calculará automáticamente la variación porcentual frente al mes anterior completo equivalente.
    """, unsafe_allow_html=True)
    if st.button("¡Entendido, comenzar a explorar!", type="primary", width="stretch"):
        persist_onboarding_seen_to_client(current_username)
        components.html("""
        <script>
        try {
            if (window.parent && window.parent.__inhausExpandSidebar) {
                window.parent.__inhausExpandSidebar();
            }
        } catch(_) {}
        try {
            if (window.top && window.top.__inhausExpandSidebar) {
                window.top.__inhausExpandSidebar();
            }
        } catch(_) {}
        </script>
        """, height=0, width=0)
        st.rerun()
