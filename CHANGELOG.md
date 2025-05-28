## [No Lanzado] - 2025-05-28

### Added (Añadido)

*   **Gestión de Perfil de Usuario (API):**
    *   Modelos Pydantic (`ProfileUpdate`, `ProfileResponse`) para la gestión de datos del perfil de usuario.
    *   Endpoint `GET /api/v1/profiles/me` para obtener el perfil del usuario autenticado.
    *   Endpoint `PUT /api/v1/profiles/me` para actualizar el perfil del usuario.
*   **Endpoints para Preferencias de Contenido (API):**
    *   Modelos Pydantic (`ContentPreferencesUpdate`, `ContentPreferencesResponse`) y endpoints (`GET`, `PUT`) bajo `/api/v1/organization-settings/content-preferences/` para gestionar las preferencias de generación automática de hashtags y emojis.

### Changed (Cambiado)

*   **Consulta de Membresía en `get_current_user` (API):** Se adoptó de forma más definitiva la consulta que usa `.execute()` directamente (con `.order().limit(1)`) en lugar de `.maybe_single()`, para mejorar la estabilidad en la obtención del `organization_id` y evitar errores `204` intermitentes.

### Fixed (Corregido)

*   **Error de Recursión en Política RLS (DB):** Se confirmó que la causa del `APIError code='42P17'` (recursión infinita) residía en las políticas RLS de la tabla `organization_members`. Se recomendó deshabilitar/corregir dichas políticas.
*   **Errores en el Router de Perfiles (API):**
    *   Solucionado `TypeError` en la llamada a `supabase.auth.admin.get_user_by_id()` dentro del endpoint `GET /api/v1/profiles/me` al pasar el `user_id` como argumento posicional.
    *   Corregidos errores de sintaxis (`SyntaxError: unterminated string literal`) y otros errores de Pylance por código mal formateado en `profiles_router.py`.
*   **Error al Guardar Preferencias de Contenido (API):**
    *   Solucionado `AttributeError` causado por un campo duplicado (`prefs_auto_hashtags_enabled`) y la omisión del campo `prefs_auto_hashtags_count` en el modelo Pydantic `ContentPreferencesUpdate`. Esto impedía que la cantidad de hashtags se guardara correctamente.
*   **Errores de Atributo en Operaciones de Escritura de Posts (API):**
    *   Se refactorizaron los endpoints `create_post`, `update_post_partial` y `soft_delete_post` en `posts_router.py` para usar un patrón de ejecución de escritura robusto con `supabase-py`, eliminando `.select().single()` después de `insert()` o `update()` para evitar `AttributeError`.
*   **Errores de Importación de `APIError` (API):** Añadida la importación de `postgrest.exceptions.APIError` en los routers donde se usa para el manejo de excepciones.
*   **Errores de `NameError` en `main.py` (API):** Corregida la importación y registro del `ai_router`.

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