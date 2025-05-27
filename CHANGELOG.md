## [No Lanzado] - 2025-05-26

Esta sección agrupa el desarrollo inicial, mejoras estructurales y correcciones hasta la fecha.

### Added (Añadido)

*   **Modelo de Datos Orientado a Organizaciones:**
    *   Introducción de las tablas `public.organizations`, `public.organization_members`, y `public.organization_settings`...
*   **Automatización en Creación de Usuario:**
    *   Nuevo trigger `handle_new_user_with_organization`...
*   **Ampliación de Tipos de Proveedores Sociales:**
    *   El ENUM `public.social_media_provider` ha sido extendido...
*   **Autenticación de Usuarios (API):**
    *   Endpoint `POST /api/v1/auth/token`...
*   **Gestión de Posts (API):**
    *   Modelos Pydantic: `PostCreate`, `PostUpdate`, `PostResponse`, `TokenData`.
    *   Endpoints CRUD para `/api/v1/posts/`...
*   **Configuración de Organización para IA (API):**
    *   Modelos Pydantic para Identidad de Marca IA (`OrganizationSettingsAIUpdate`, `OrganizationSettingsAIResponse`).
    *   Endpoints `GET` y `PUT` en `/api/v1/organization-settings/ai-identity/`.
    *   Modelos Pydantic para Preferencias de Contenido (`ContentPreferencesUpdate`, `ContentPreferencesResponse`).
    *   Endpoints `GET` y `PUT` en `/api/v1/organization-settings/content-preferences/`.
*   **Generación de Contenido con IA (Google Gemini - API):**
    *   Integración con Google Gemini...
*   **Gestión de Perfil de Usuario (API):**  <-- NUEVO
    *   Modelos Pydantic `ProfileUpdate` y `ProfileResponse` para la gestión de datos del perfil de usuario.
    *   Endpoint `GET /api/v1/profiles/me` para obtener el perfil del usuario autenticado (incluyendo `full_name`, `avatar_url`, `timezone` de la tabla `profiles` y `email` de `auth.users`).
    *   Endpoint `PUT /api/v1/profiles/me` para que el usuario autenticado actualice su información de perfil (`full_name`, `avatar_url`, `timezone`).
*   **Configuración del Proyecto FastAPI:**
    *   Estructura de proyecto estándar...

### Changed (Cambiado)

*   **Estructura de Tablas Existentes:**
    *   `public.profiles`: Simplificada para preferencias personales del usuario.
    *   ...
*   **Lógica de `get_current_user`:**
    *   Modificada para consultar `organization_members`...
*   **Rutas de Endpoints de Settings (API):**
    *   Rutas para identidad de marca IA movidas a `/api/v1/organization-settings/ai-identity/`.
    *   ...
*   **Constraint en `organization_settings` (DB):**
    *   Ajustada la `CHECK constraint` para `prefs_auto_emojis_style`...

### Fixed (Corregido)

*   **Múltiples Errores de Autenticación y Acceso a Datos (API):**
    *   Resueltos problemas con `TokenData`...
*   **Problemas con Políticas RLS:**
    *   Identificada y corregida una política RLS recursiva...
*   **Conflictos de Dependencias:**
    *   Manejados conflictos entre `python-jose`...
*   **Errores de `async/await` (API):**
    *   Corregidos `TypeError` por uso incorrecto de `await`...
*   **Consistencia en la Obtención de `organization_id`:** Se estabilizó la lógica...
*   **Validación de Modelos Pydantic:** Corregida la anotación de tipo para campos con restricciones numéricas (ej. `conint`) en `ContentPreferencesUpdate` para resolver error de Pylance "Call expression not allowed in type expression". <-- NUEVO
*   **Llamada a Supabase Auth Admin API:** Corregido `TypeError` en `get_current_user_profile` al llamar a `supabase.auth.admin.get_user_by_id()` usando el argumento `user_id` posicionalmente en lugar de como keyword argument. <-- NUEVO

### Security (Seguridad)

*   **Protección de `search_path` en Funciones PostgreSQL:**
    *   Establecido explícitamente el `search_path`...
*   **Consolidación y Revisión de Políticas RLS (DB):**
    *   Políticas RLS para `public.posts` consolidadas...
*   **Recomendaciones de Configuración de Supabase Auth:**
    *   Se recomienda habilitar "Leaked Password Protection".
    *   ...

---