# CHANGELOG BE

## [No Lanzado] - 2025-06-02

### Added (Añadido)

*   **Generación de Títulos para Ideas de Contenido con IA (API):**
    *   Modelo Pydantic de petición `GenerateTitlesFromFullIdeaRequest` para recibir el texto completo de una idea de contenido, la red social objetivo (opcional) y el número de títulos deseados.
    *   Modelo Pydantic de respuesta `GeneratedTitlesResponse` para devolver la lista de títulos generados y el texto de la idea original.
    *   Plantilla de prompt `GENERATE_TITLES_FROM_IDEA_V1` en `app/prompts/templates.py` diseñada para instruir al LLM en la creación de múltiples opciones de títulos.
    *   Función de servicio `build_prompt_for_titles` en `app/services/ai_content_generator.py` para construir el prompt dinámicamente usando la plantilla, los settings de la organización y la idea de contenido proporcionada.
    *   Endpoint `POST /api/v1/ai/generate-titles-from-idea` que utiliza el contexto de la organización y el texto de una idea para generar un número configurable de sugerencias de títulos.
    *   Función de parseo genérica `parse_lines_to_list` (anteriormente `parse_gemini_idea_titles`) en `app/services/ai_content_generator.py` para extraer listas de texto de respuestas del LLM formateadas línea por línea.

### Fixed (Corregido)

*   **Modelo Pydantic `PostCreate` (API):** Se eliminó la declaración del campo `organization_id` como requerido en el modelo `PostCreate`, ya que este valor se obtiene del usuario autenticado y se añade en el backend antes de la inserción en la base de datos. Esto solucionó un `ValidationError` al instanciar `PostCreate` en los endpoints de generación de contenido que crean posts.
*   **Errores de Importación y Definición de Modelos (API):**
    *   Corregido `ImportError` por `GeneratedIdeaDetail` no encontrado en `ai_content_generator.py` asegurando su correcta definición en `ai_models.py`.
    *   Solucionado `NameError` por `GeneratedTitlesResponse` no definido en `ai_router.py` al momento de decorar el endpoint, asegurando el orden de importación/definición.
    *   Corregido `AttributeError` en `build_prompt_for_titles` por intentar acceder a una constante de plantilla de prompt con un nombre incorrecto.
    *   Resueltos errores de sintaxis y Pylance por código mal formateado (indentación, paréntesis, strings sin cerrar) en `ai_models.py` y `profiles_router.py`.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-05-31

### Added (Añadido)

*   **Servicio Dedicado para Generación de Imágenes con IA (`app/services/ai_image_generator.py`):**
    *   Función `generate_image_base64_only`: Interactúa con OpenAI (DALL-E) para generar una imagen a partir de un prompt de texto, devolviendo la imagen codificada en Base64.
    *   Función `generate_image_from_prompt`: Orquesta el flujo completo de generación de imágenes:
        1.  Llama a `generate_image_base64_only` para obtener los datos de la imagen.
        2.  Decodifica la imagen Base64.
        3.  Sube la imagen (como `.png`) a Supabase Storage al bucket `content.flow.media` bajo el path estructurado `{organization_id}/{post_id}.png`. La opción `upsert` está habilitada.
        4.  Obtiene y devuelve la URL pública de la imagen almacenada.
    *   Incluye inicialización del cliente AsyncOpenAI y manejo de errores detallado para las interacciones con la API de OpenAI y Supabase Storage.
*   **Servicio de Generación de Contenido (`app/services/ai_content_generator.py`):**
    *   Función `build_dalle_prompt_from_post_data`: Construye un prompt de texto optimizado para DALL-E, basándose dinámicamente en el título, un extracto del contenido y la red social de un post existente. Utiliza la nueva plantilla `GENERATE_IMAGE_FOR_SOCIAL_POST_V1`.
*   **Endpoints de IA para Imágenes (`app/api/v1/routers/ai_router.py`):**
    *   **`POST /api/v1/ai/generate-image`:**
        *   Permite a los usuarios generar una imagen a partir de un prompt de texto arbitrario.
        *   Devuelve la imagen codificada en Base64 (`ImageGenerationResponse`) sin guardarla permanentemente ni asociarla a un post.
        *   Utiliza el servicio `generate_image_base64_only`.
    *   **`POST /api/v1/ai/posts/{post_id}/generate-image`:**
        *   Permite generar una imagen automáticamente para un post existente.
        *   Recupera los datos del post (`title`, `content_text`, `social_network`).
        *   Llama a `build_dalle_prompt_from_post_data` para crear el prompt para DALL-E.
        *   Llama al servicio `generate_image_from_prompt` para generar la imagen, subirla y obtener su URL.
        *   Actualiza el campo `media_url` del post con la URL de la imagen.
        *   Devuelve el `PostResponse` del post actualizado.
*   **Nueva Plantilla de Prompt (`app/prompts/templates.py`):**
    *   `GENERATE_IMAGE_FOR_SOCIAL_POST_V1`: Plantilla para crear prompts para DALL-E basados en el contenido de un post.

### Changed (Cambiado)

*   **Endpoint `POST /api/v1/ai/posts/{post_id}/generate-image` (API):** Modificado para no requerir un `prompt` en el cuerpo de la solicitud; el prompt para la generación de la imagen ahora se construye automáticamente a partir del contenido del post.

### Fixed (Corregido)

*   **Error de Permisos en Supabase Storage (RLS):** Identificado que la ausencia de políticas RLS en el bucket `content.flow.media` causaba errores `403 new row violates row-level security policy` al intentar subir imágenes. Se recomendó la creación de políticas que otorguen al `service_role` los permisos necesarios para `INSERT`, `UPDATE`, `SELECT`, y `DELETE` en el bucket. *(Acción de configuración en Supabase pendiente por el usuario).*
*   **Errores de Importación y `TypeError` (API y Servicios):** Resueltos problemas relacionados con nombres de funciones incorrectos en las importaciones y argumentos faltantes en las llamadas a funciones entre el router y los servicios de IA.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-05-29

### Added (Añadido)

*   **Generación de Contenido para Imagen Única (API):**
    *   Endpoint `POST /api/v1/ai/generate-single-image-caption` para generar un título y un caption utilizando IA, basados en la configuración de la organización y los inputs del usuario.
    *   El contenido generado se guarda automáticamente como un nuevo Post en estado `draft`.
    *   Se implementó la lógica `parse_title_and_caption_from_llm` para extraer el título y el caption de la respuesta estructurada del LLM.

### Fixed (Corregido)

*   **Error de Importación en `ai_router.py` (API):** Solucionado un `ImportError` que impedía importar `create_draft_post_from_ia` desde `app/services/ai_content_generator.py` debido a la ausencia de dicha función en el módulo de servicio. La función fue añadida y los imports correspondientes verificados.
*   **Error `KeyError` en Formateo de Plantilla de Prompt (Servicio IA):** Corregido un `KeyError` en la plantilla `GENERATE_SINGLE_IMAGE_CAPTION_V1` al escapar correctamente las llaves literales (`{{ }}`) en el texto de ejemplo, evitando que el método `.format()` de Python las interpretara como placeholders no provistos.
*   **Error 405 Method Not Allowed en Endpoint de IA (API):** Identificado y corregido el uso incorrecto del método HTTP (`GET` en lugar de `POST`) en las pruebas del endpoint `/api/v1/ai/generate-single-image-caption`.

### Changed (Cambiado)

*   **Estructura y Documentación de `ai_content_generator.py` (Servicio IA):** Se reorganizó el archivo en secciones lógicas y se añadió documentación (`docstrings`) a las funciones para mejorar la legibilidad y el mantenimiento.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

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

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

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