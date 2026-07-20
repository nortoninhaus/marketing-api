# Product Requirements Document (PRD) - Inhaus Marketing Data API v5.0

## 1. Introducción
### 1.1 Objetivo del Documento
Este PRD detalla las especificaciones de la API unificada de Inhaus para la agregación de datos de 14 plataformas de marketing y analítica, optimizada para agentes de IA y agencias de rendimiento.

### 1.2 Visión General del Producto
Una API multi-tenant y modular que normaliza datos de plataformas como Meta, Google, TikTok y LinkedIn, permitiendo el acceso programático y automático a métricas de marketing mediante una interfaz única y un servidor MCP (Model Context Protocol).

## 2. Metas y Objetivos
- **Unificación:** Consolidar 14+ plataformas en un solo endpoint.
- **Agent-Ready:** Facilitar que agentes de IA realicen llamadas a herramientas estructuradas.
- **Escalabilidad:** Soportar cientos de clientes y cuentas dinámicamente.
- **Confiabilidad:** Implementar reintentos automáticos y manejo de errores robusto.

## 3. Audiencia
- **Agentes de IA:** Herramientas que necesitan consultar datos de marketing de forma autónoma.
- **Agencias de Performance:** Equipos que requieren reportes automatizados y multi-cuenta.
- **Desarrolladores:** Usuarios que construyen tableros de control personalizados.

## 4. Requisitos Funcionales
- **Conectores Multi-plataforma:** Soporte para Meta (Ads/Organic), Google (Ads/GA4/YouTube/Play), TikTok, LinkedIn, Pinterest, Shopify, etc.
- **Resolución de Identidad:** Mapeo dinámico de `client_id`, `user_id` y `account_id` para resolver credenciales.
- **Endpoints de Datos:**
  - `campaign-data`: Consulta por plataforma.
  - `batch`: Consultas concurrentes multi-plataforma.
  - `comments`: Extracción de comentarios de posts sociales.
- **Servidor MCP:** Exposición de herramientas para LLMs (list_platforms, get_marketing_data, etc.).
- **Dashboard:** Visualización de salud y métricas vía Streamlit.

## 5. Requisitos No Funcionales
- **Seguridad:** Autenticación por API Key y aislamiento de credenciales por usuario.
- **Rendimiento:** Ejecución asíncrona de llamadas SDK síncronas mediante thread pools.
- **Observabilidad:** Logs detallados, metadata de request_id y timestamps en cada respuesta.

## 6. Arquitectura Técnica
- **Backend:** FastAPI (Python).
- **Modelado:** Pydantic para validación y normalización.
- **Almacenamiento:** Firestore para credenciales y BigQuery para sinks de datos.
- **Infraestructura:** Docker y Google Cloud Platform.
