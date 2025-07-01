# CHANGELOG BE

# Changelog

## [No Lanzado] - 2025-06-19 (Sesión de Estabilización de Arquitectura)

### 🛠 Mejoras y Cambios Técnicos

*   **Re-Arquitectura Completa del Flujo OAuth 2.0 (LinkedIn):**
    *   Se ha reemplazado por completo la dependencia de la librería `authlib` para la orquestación del flujo. Se ha implementado un flujo **manual y explícito** que sigue la especificación de LinkedIn al pie de la letra, usando `httpx` para el intercambio de tokens.
    *   Esta decisión elimina la "magia" y las capas de abstracción que causaban errores impredecibles (`ValueError`, `TypeError`, `401 invalid_client`), dándonos **control total y transparencia** sobre el proceso.

*   **Implementación de Gestión de Estado OAuth en Base de Datos:**
    *   Se ha adoptado una estrategia **stateless** a nivel de aplicación, la cual es el estándar de oro para arquitecturas robustas.
    *   Se creó y se integró un nuevo servicio (`oauth_state_service.py`) y una tabla (`oauth_states`) para persistir de forma segura y temporal el `state` y el `code_verifier` (PKCE).
    *   **Resultado:** Esta arquitectura es inmune a los problemas de `CookieNotFound` y a las redirecciones (`307`) que plagaron las implementaciones anteriores.

*   **Consolidación de la Arquitectura de Servicios:**
    *   Se ha establecido un patrón claro para la creación de nuevos servicios, asegurando que las dependencias (`supabase_client`) se importen directamente y los constructores se mantengan simples, solucionando errores de `TypeError` en la inicialización.

### 🐛 Correcciones de Errores

*   **Solucionado Error Crítico `401 invalid_client`:**
    *   Se ha resuelto el bloqueo final del flujo de LinkedIn. El error `Client authentication failed` fue solucionado al abandonar la capa de abstracción de `authlib` y construir una petición `POST` manual y explícita al endpoint `accessToken`, asegurando que todos los parámetros requeridos (`client_id`, `client_secret`, etc.) se envíen correctamente.

*   **Erradicados Errores `ValueError` y `TypeError` en Flujo OAuth:**
    *   Se han eliminado por completo los errores recurrentes `ValueError: too many values to unpack` y `TypeError: 'str' object cannot be interpreted as an integer` al reemplazar las llamadas ambiguas a `authlib` por la nueva implementación manual.

*   **Resueltos Errores de Arranque del Servidor (`NameError`, `ImportError`):**
    *   Se han solucionado todos los errores que impedían el reinicio del servidor, incluyendo la corrección de rutas de importación (`app.services.social.oauth_state_service`) y la adición de `__init__.py` en los directorios de servicios para que Python los reconozca como paquetes válidos.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Changelog

## [No Lanzado] - 2025-06-17

### ✨ Nuevas Características y Mejoras Funcionales

*   **Implementado Flujo de Conexión OAuth 2.0 para LinkedIn:**
    *   Se ha desarrollado la arquitectura completa para que los usuarios conecten sus cuentas de LinkedIn. El flujo sigue el estándar **Authorization Code Grant con PKCE**, asegurando la máxima seguridad para una aplicación SPA.
    *   **Estado de la Implementación:** El flujo de autorización (`/connect` y `/callback`) está **técnicamente completado y validado hasta el punto de la autorización del usuario**. Actualmente se encuentra bloqueado por un error `401 invalid_client` por parte de la API de LinkedIn, indicando un problema de configuración o de estado de la aplicación en el portal de desarrolladores de LinkedIn, no un fallo en el código.

*   **Gestión de Conexiones Sociales desde la API:**
    *   Se han añadido los endpoints `GET /api/v1/connections` y `DELETE /api/v1/connections/{id}` para que la interfaz de usuario pueda listar y eliminar las conexiones sociales de una organización, proporcionando un ciclo de vida completo para la gestión de integraciones.

### 🛠 Mejoras y Cambios Técnicos

*   **Arquitectura de Estado OAuth Robusta (Basada en DB):**
    *   Se implementó una estrategia de gestión de estado **stateless** para el flujo OAuth. En lugar de depender de cookies de sesión frágiles, el `state` y el `code_verifier` (PKCE) se persisten temporalmente en una tabla `oauth_states` en la base de datos.
    *   Este patrón es a prueba de redirecciones, previene ataques CSRF de forma robusta y elimina por completo los problemas de `CookieNotFound` que experimentamos.

*   **Refactorización del Flujo OAuth para Arquitectura SPA+API:**
    *   Se re-arquitecturó el endpoint `/connect` para seguir el patrón correcto de API + SPA. El backend ahora construye la `authorization_url` manualmente y la devuelve en un cuerpo JSON, dando control total al frontend sobre la redirección y eliminando los errores de CORS.

*   **Centralización de Clientes OAuth:**
    *   Se ha creado un módulo `app/core/oauth_clients.py` para centralizar la configuración de todos los clientes de API de terceros (`authlib`), mejorando la mantenibilidad y rompiendo dependencias circulares.

*   **Seguridad y Consistencia en la Capa de Acceso a Datos:**
    *   Se realizó una auditoría y refactorización para asegurar el uso correcto de `async/await` en toda la aplicación. Las funciones de servicio que interactúan con la base de datos (usando `supabase-py` síncrono) son ahora correctamente `def`, mientras que los endpoints del router y las llamadas de red (`httpx`) son `async def`, eliminando una clase entera de errores `TypeError` y `RuntimeWarning`.

*   **Estrategia de Encriptación de Tokens en el Backend:**
    *   Se ha establecido y consolidado una política clara donde los tokens de acceso y refresco (cuando se obtengan) se encriptarán y desencriptarán exclusivamente en la capa de la aplicación (Python) usando la librería `cryptography`, asegurando que los datos sensibles nunca se almacenen en texto plano en la base de datos.

### 🐛 Correcciones de Errores

*   **Solucionado Error de Validación `422 Unprocessable Content` en Creación de Posts:**
    *   Se ha resuelto un bug crítico donde el backend fallaba al crear el segundo post en una generación múltiple.
    *   La causa era un `ValidationError` de Pydantic. Se corrigió el endpoint `/ai/generate-single-image-caption` para validar y convertir explícitamente el `content_type` (string) recibido del frontend al `ContentTypeEnum` interno antes de crear el objeto `PostCreate`.

*   **Resueltos Múltiples Errores de `ImportError` y `NameError`:**
    *   Se han solucionado numerosos errores de importación y de nombres no definidos a lo largo de la refactorización, incluyendo la adición de archivos `__init__.py` faltantes y la corrección de rutas de importación, resultando en una base de código que ahora compila y se ejecuta de forma estable.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-06-09

### ✨ Nuevas Características y Mejoras Funcionales

*   **Implementado Flujo Completo de Conexión y Publicación para LinkedIn:**
    *   Se ha desarrollado la capacidad completa para que los usuarios conecten sus cuentas de LinkedIn de forma segura usando el flujo OAuth2 con PKCE.
    *   La plataforma ahora puede publicar posts de texto y de imagen en nombre del usuario a través de una conexión autorizada.

*   **Gestión de Conexiones Sociales desde la API:**
    *   Se han añadido endpoints para que la interfaz de usuario pueda listar y eliminar las conexiones sociales de una organización, proporcionando un ciclo de vida completo para la gestión de integraciones.

*   **Refresco Automático de Tokens de Acceso:**
    *   Se ha implementado una lógica de "just-in-time" para refrescar automáticamente los tokens de acceso de LinkedIn que están a punto de expirar.
    *   Esto garantiza la longevidad y robustez de las conexiones, mejorando drásticamente la experiencia del usuario al evitar la necesidad de re-autenticaciones manuales frecuentes.

*   **Publicación de Posts con Imágenes en LinkedIn:**
    *   Se ha extendido la funcionalidad de publicación para incluir soporte para imágenes. El sistema ahora maneja el flujo de subida de medios de 3 pasos de la API de LinkedIn de forma transparente.

### 🛠 Mejoras y Cambios Técnicos

*   **Arquitectura de Servicios de Publicación Modular y Escalable (Patrón Dispatcher):**
    *   Se ha refactorizado la lógica de publicación. En lugar de llamar a servicios específicos de cada plataforma desde los routers, se ha creado un `publishing_service.py` que actúa como un "dispatcher".
    *   Este servicio central determina la plataforma de destino y delega la tarea al servicio especialista correspondiente (`linkedin_service`, etc.). Esto simplifica enormemente la adición de nuevas plataformas en el futuro.

*   **Implementada Seguridad a Nivel de Recurso (Multi-Tenancy):**
    *   Se ha creado una nueva dependencia de FastAPI reutilizable (`get_valid_connection_for_user`) para proteger los endpoints.
    *   Esta dependencia verifica que cualquier intento de usar una conexión social solo sea permitido si el usuario autenticado pertenece a la misma organización que la conexión, previniendo el acceso no autorizado a recursos entre tenants.

*   **Estrategia de Encriptación de Tokens en el Backend:**
    *   Se ha establecido una política clara donde los tokens de acceso y refresco se encriptan y desencriptan exclusivamente en la capa de la aplicación (Python) usando la librería `cryptography`. La base de datos solo almacena texto cifrado, mejorando la seguridad de los datos sensibles.

*   **Refactorización y Creación de Módulos de API Dedicados:**
    *   Se ha reorganizado la estructura del proyecto para una mayor claridad. La lógica de conexiones y publicación ahora reside en módulos dedicados (`connections_router.py`, `publishing_router.py`) dentro de una nueva subcarpeta `social`, separando la lógica de integración de la lógica de gestión de contenido principal.

### 🐛 Correcciones de Errores

*   **Resuelto Conflicto de Dependencias Crítico (`resolution-too-deep`):**
    *   Se ha reestructurado y limpiado por completo el archivo `requirements.txt` para eliminar dependencias duplicadas, redundantes y de bajo nivel con versiones fijas.
    *   Se ha establecido una estrategia de definir únicamente las dependencias de alto nivel, permitiendo que `pip` resuelva un árbol de dependencias consistente y estable, solucionando los fallos de instalación del entorno.

*   **Solucionados Múltiples Errores de Importación en el Código:**
    *   Se han corregido numerosos archivos (`connections_router.py`, `publishing_service.py`, etc.) que tenían importaciones faltantes o incorrectas, asegurando que todos los módulos sean autocontenidos y funcionales.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-06-08

### 🚀 Mejoras de Arquitectura y Refactorización

*   **Centralización de la Lógica de Contexto de IA con `ai_prompt_helpers.py`:**
    *   Se creó un nuevo módulo de servicio (`app/services/ai_prompt_helpers.py`) para centralizar la lógica de construcción de contexto para los prompts de IA.
    *   Este servicio encapsula la fusión de la configuración de la organización con las preferencias específicas del usuario (ej. tono de voz, longitud), aplicando la lógica de negocio correcta.
    *   Los servicios `ai_content_generator.py` y `ai_image_generator.py` fueron refactorizados para usar estos helpers, eliminando código duplicado y mejorando la consistencia y mantenibilidad.

*   **Estandarización de Tipos de Contenido (`ContentTypeEnum`):**
    *   Se introdujo un `Enum` (`ContentTypeEnum`) como fuente única de verdad para los tipos de contenido, reemplazando el uso de strings genéricos.
    *   Se implementó una estrategia de validación manual en los endpoints de entrada (`POST`, `PATCH`) para asegurar que solo se acepten las claves del `Enum` (ej. `IMAGE_POST`).
    *   El modelo de respuesta `PostResponse` fue enriquecido con un campo calculado (`content_type_display`) para devolver el valor legible para humanos al frontend, mejorando la experiencia del desarrollador del FE.

### ✨ Nuevas Características y Mejoras Funcionales

*   **Implementación Completa de Preferencias de Usuario por Generación:**
    *   El backend ahora acepta y procesa correctamente las preferencias de "Tono de voz" y "Longitud del contenido" enviadas desde el frontend.
    *   Se mejoraron las plantillas de prompts para dar mayor énfasis a estas directivas y aumentar la fiabilidad de la respuesta de la IA.
    *   La lógica para incluir hashtags y emojis ahora respeta correctamente la configuración de la organización (`prefs_auto_hashtags_enabled`, etc.).

### 🐛 Correcciones de Errores

*   **Solucionado Error de Serialización de `datetime` y `UUID`:**
    *   Se corrigió un `TypeError` crítico en el endpoint `PATCH /api/v1/posts/{post_id}` que ocurría al intentar actualizar campos de tipo `datetime` o `UUID`.
    *   Se implementó una conversión explícita a string (`.isoformat()` para `datetime`, `str()` para `UUID`) antes de enviar el payload a la base de datos.

*   **Solucionados Múltiples Errores de `NameError`:**
    *   Se corrigieron errores de `NameError` en varios routers y servicios (`posts.py`, `ai_content_generator.py`, `ai_image_generator.py`) causados por importaciones faltantes o eliminadas incorrectamente durante la refactorización (ej. `logger`, `Any`, `HttpUrl`).
    *   Se organizaron las importaciones siguiendo las convenciones de PEP 8 para mejorar la legibilidad.

*   **Corregido `KeyError` en Plantillas de Prompt:**
    *   Se solucionó un `KeyError` que ocurría al intentar formatear una plantilla de prompt que esperaba un placeholder (`{image_description}`) que ya no se proveía, eliminando la referencia de la plantilla.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-06-07

### ✨ Nuevas Características y Mejoras Funcionales 

*   **Respeto por el Título del Usuario en Generación de Captions (`POST /api/v1/ai/generate-single-image-caption`):**
    *   Se implementó una nueva lógica de negocio para priorizar el título proporcionado por el usuario.
    *   Si el payload de la petición incluye un `title`, este se usará para crear el post. El título generado por la IA solo se usará como fallback si el usuario no proveyó uno.
    *   Se actualizó el modelo Pydantic `GenerateSingleImageCaptionRequest` para aceptar formalmente los campos `title`, `prompt_id`, `generation_group_id` y `original_post_id`, permitiendo una creación de posts más rica y con mejor trazabilidad desde la UI.

### 🛠 Mejoras y Cambios Técnicos 

*   **Cambio Estratégico de Bucket de Almacenamiento para Medios:**
    *   Tras una depuración exhaustiva que reveló problemas de permisos persistentes e irresolubles en el bucket `content.flow.media`, se tomó la decisión estratégica de abandonarlo.
    *   Se modificó la constante `POST_MEDIA_BUCKET` en `app/services/storage_service.py` para apuntar permanentemente al nuevo bucket `media.content`, que ha demostrado ser funcional y no presentar problemas de RLS para el rol `service_role`.
    *   Esto resuelve de forma definitiva los errores 500 y 403 que ocurrían al confirmar imágenes de WIP.

*   **Refactorización del Endpoint de Perfil de Usuario (`GET /api/v1/profiles/me`):**
    *   Se corrigió una llamada a la API de Supabase en `profiles_router.py`, eliminando un `TypeError` que ocurría al llamar a `supabase.auth.admin.get_user_by_id()` con un argumento nombrado incorrecto.

### 🐛 Correcciones de Errores 

*   **Solucionado `TypeError: Object of type UUID is not JSON serializable`:**
    *   Se identificó y corrigió un bug crítico que causaba errores 500 al intentar enviar datos con campos de tipo `UUID` a Supabase.
    *   El error fue resuelto en dos lugares clave:
        1.  En el endpoint `PATCH /api/v1/posts/{post_id}` (`posts.py`), asegurando que todos los campos UUID en el payload de actualización se conviertan a `string` antes de la llamada a la DB.
        2.  En el servicio `create_draft_post_from_ia` (`ai_content_generator.py`), que es utilizado por los endpoints de IA. Se implementó la misma lógica de conversión de `UUID` a `string` para prevenir el error durante la creación de nuevos posts.

*   **Implementada Salvaguarda de API para Generación de Imágenes:**
    *   Se añadió una validación en el endpoint `POST /api/v1/ai/posts/{post_id}/generate-image`.
    *   Ahora la API comprueba el `content_type` del post antes de generar una imagen. Si el tipo no es `image`, la API devuelve un error `400 Bad Request`, previniendo que se generen imágenes para posts de solo texto y proveyendo un feedback claro al cliente.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-06-05

### ✨ Nuevas Características y Mejoras Funcionales 

*   **Endpoint para Subida de Previsualizaciones de Usuario por Backend (`POST /api/v1/posts/{post_id}/upload-wip-preview`):**
    *   Se implementó un nuevo endpoint que permite al frontend enviar un archivo de imagen. El backend se encarga de:
        *   Validar el archivo (tipo, y preparación para validación de tamaño).
        *   Limpiar la carpeta `/wip/` del post en el bucket `post.previews`.
        *   Subir la nueva imagen de previsualización a la carpeta `/wip/` usando la `service_role_key` (evitando problemas de RLS para la subida del frontend a esta ubicación temporal).
    *   Devuelve una `GeneratePreviewImageResponse` con los detalles de la imagen en `/wip/`, similar al endpoint de generación IA.
    *   Esto simplifica la lógica del frontend para las previsualizaciones subidas por el usuario.

*   **Clarificación de Flujos de Creación de Posts con Imágenes:**
    *   Se confirmó que la creación de posts (`POST /api/v1/posts/`) no acepta imagen inicial; la imagen se asocia mediante un `PATCH` posterior con `media_url` y `media_storage_path` después de que el FE sube la imagen a la ubicación final en `post_media`.
    *   Se detalló el flujo para que el FE maneje la creación de posts en lote (para múltiples redes) manteniendo consistencia de título e imagen, utilizando el `PATCH` para asignar la imagen final a cada post.

*   **Preparación para Tono de Voz y Longitud de Contenido en IA:**
    *   Se planificó la modificación de los endpoints de IA (específicamente el que genera texto para posts, como `POST /api/v1/ai/generate-single-image-caption`) para aceptar parámetros `voice_tone` y `content_length_preference` en el payload. (Implementación de esta lógica en los prompts de IA y modelos de request pendiente o en curso).

*   **Asignación de `generation_group_id`:**
    *   Se confirmó que el endpoint `PATCH /api/v1/posts/{post_id}` puede actualizar el campo `generation_group_id` si se incluye en el payload (asumiendo que el modelo `PostUpdate` lo permite).
    *   Se discutieron opciones para que el FE asigne este ID a posts creados en lote (ya sea en cada creación o mediante `PATCH`es individuales).

### 🛠 Mejoras y Cambios Técnicos 

*   **Manejo de `async/await` con `supabase-py` (DB y Storage):**
    *   Se identificó que varios métodos del SDK de `supabase-py` v2.15.1 (como `.execute()` para DB después de ciertos constructores, y `.upload()`, `.list()`, `.remove()` para Storage) se comportan de manera síncrona en el entorno actual o devuelven objetos no directamente "awaitables".
    *   Se aplicó consistentemente la eliminación de `await` para las llamadas directas a `.execute()` de la base de datos.
    *   Se aplicó `asyncio.to_thread` a las llamadas síncronas del SDK de Supabase Storage (`.upload()`, `.list()`, `.remove()`) dentro de las funciones `async def` del `storage_service.py` para evitar el bloqueo del event loop de FastAPI y resolver `TypeError`s.

*   **Depuración y Refinamiento de Políticas RLS para Supabase Storage:**
    *   Se trabajó extensamente en la depuración de errores `403 Forbidden: new row violates RLS` y `500 DatabaseError` (con `sql_state_code: "42501"`) al intentar subir archivos desde el frontend al bucket `post.previews`.
    *   Se identificó que la causa raíz probable es la falta de permisos `SELECT` para el rol `authenticated` en las tablas `public.organization_members` y/o `public.posts`, necesarios para que las subconsultas `EXISTS` dentro de las políticas RLS de `storage.objects` se ejecuten correctamente.
    *   Se proveyeron y probaron políticas `GRANT SELECT` a nivel de columna y políticas RLS `FOR SELECT` más permisivas (temporalmente) en `organization_members` y `posts` para diagnosticar.
    *   Se eliminó un error de "infinite recursion" en las políticas RLS de `organization_members` al simplificar la política `SELECT`.
    *   Se crearon políticas `INSERT` y `UPDATE` específicas `TO supabase_storage_admin` para `storage.objects` en el bucket `post.previews` para asegurar que el rol del sistema pueda escribir físicamente si la política del usuario lo permite.

*   **Ajustes en Routers (`posts.py`, `profiles.py`):**
    *   Se corrigieron las firmas de varios endpoints en `posts.py` para usar `*` para keyword-only arguments, mejorando la compatibilidad con Pylance y la claridad.
    *   Se aseguró que el endpoint `GET /api/v1/profiles/me` devuelva `organization_id` y `role` al frontend, tomándolos de `TokenData`.

*   **Corrección de Errores de Importación y Nombres:**
    *   Resueltos `ImportError` relacionados con `SupabaseClient` y `Client`.
    *   Corregidos `NameError` y `AttributeError` por nombres incorrectos de modelos o funciones.

### 🐛 Correcciones de Errores 

*   Solucionado `RuntimeError: Form data requires "python-multipart" to be installed` al añadir la dependencia `python-multipart` para el manejo de subida de archivos en FastAPI.
*   Resueltos múltiples `TypeError` relacionados con el uso incorrecto de `await` con métodos síncronos del SDK de `supabase-py`.
*   Identificada la causa de errores `403 Forbidden: new row violates RLS` en la subida de storage desde el frontend, apuntando a la necesidad de permisos `SELECT` adecuados para el rol `authenticated` en tablas referenciadas por las políticas RLS de `storage.objects`. (Solución en progreso o aplicada).

### ⚠️ Notas 

*   La depuración de las políticas RLS para la subida directa de previsualizaciones por el usuario desde el frontend ha sido compleja. La solución de que el backend maneje estas subidas a `/wip/` proporciona un camino más robusto y controlado.
*   Se recomienda una revisión y limpieza de la gestión de entornos virtuales y dependencias del proyecto para asegurar consistencia.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-06-04

### 🛠 Mejoras y Cambios Técnicos 

*   **Ajustes en la Gestión de Configuración (`app/core/config.py`):**
    *   Se ha modificado la forma en que se cargan y se definen los valores por defecto para las configuraciones de OpenAI (modelo, tamaño, calidad de imagen). Ahora se prioriza la carga desde el archivo `.env`, y la clase `Settings` define estos campos como requeridos si no se proveen valores por defecto en el código, mejorando la claridad sobre las dependencias de configuración.
    *   Se simplificó la carga de variables de entorno delegando más responsabilidad a `pydantic-settings` para la lectura del archivo `.env`.

*   **Refinamiento de Modelos Pydantic (`app/models/post_models.py` y otros):**
    *   Se aseguró la consistencia con Pydantic V2, utilizando `model_config = ConfigDict(...)` y `model_validate()` donde corresponde.
    *   Se añadió el campo `preview_content_type` a `GeneratePreviewImageResponse` y `content_type` a `ConfirmWIPImageDetails` para un manejo más preciso de los tipos MIME de las imágenes de previsualización.

*   **Servicio de Generación de Imágenes IA (`app/services/ai_image_generator.py`):**
    *   Se creó la nueva función `generate_and_upload_ai_image_to_wip` específicamente para el flujo de generación de previsualizaciones con IA que se almacenan en la carpeta `/wip/`. Esta función encapsula la generación de la imagen y su subida al bucket de previsualizaciones.
    *   Se modificó la función existente `generate_image_from_prompt` (utilizada por `ai_router.py`) para que:
        *   Devuelva también el `storage_path` de la imagen final almacenada en `post_media`.
        *   Utilice `storage_service.get_post_media_storage_path()` para una estructura de ruta de archivo final más robusta y única.
        *   Utilice `storage_service.upload_file_bytes_to_storage()` para la subida, manteniendo la consistencia con otros servicios.
    *   La función `generate_image_base64_only` ahora obtiene los parámetros de configuración de la IA (modelo, tamaño, calidad) directamente desde `settings`.

*   **Servicio de Storage (`app/services/storage_service.py`):**
    *   Se ajustó el manejo de llamadas asíncronas al SDK de `supabase-py` v2.x. Se identificó que varios métodos del SDK (como `.upload()`, `.list()`, y potencialmente `.remove()`, `.move()`) se comportan de manera síncrona en el entorno actual o devuelven objetos no directamente "awaitables".
    *   Se aplicó (o se está en proceso de aplicar) `asyncio.to_thread` a estas llamadas síncronas del SDK dentro de las funciones `async def` del servicio para evitar el bloqueo del event loop de FastAPI y resolver `TypeError`s relacionados.
    *   Se actualizaron las constantes de nombres de bucket (`POST_MEDIA_BUCKET`, `POST_PREVIEWS_BUCKET`) para que coincidan con los nombres reales en el proyecto Supabase (`content.flow.media`, `post.previews`).
    *   La función `move_file_in_storage` ahora acepta `content_type_for_destination` para asegurar el tipo MIME correcto al mover archivos entre buckets.

*   **Routers (`app/api/v1/routers/posts.py`, `app/api/v1/routers/ai_router.py`):**
    *   **`posts.py`:**
        *   Se corrigieron las firmas de los endpoints para alinearse con las mejores prácticas de FastAPI y resolver advertencias de Pylance (uso de `*` para keyword-only arguments).
        *   Se ajustaron las llamadas a los métodos de base de datos de Supabase (ej. `.execute()`) para que no usen `await` si se ha determinado que son síncronas en el entorno actual, previniendo `TypeError`s.
        *   Se añadieron logs detallados (niveles `INFO` y `DEBUG` con prefijos como `PATCH_LOG`, `TIMING`) a los nuevos endpoints de imágenes y al `PATCH` modificado para facilitar la depuración de flujos complejos y la identificación de cuellos de botella.
        *   Se corrigieron `NameError` por nombres incorrectos de modelos de respuesta (ej. `PreviewImageWIPResponse` vs `GeneratePreviewImageResponse`).
        *   Se corrigieron `AttributeError` por nombres incorrectos de funciones de servicio (ej. `delete_all_files_in_folder`).
    *   **`ai_router.py`:** El endpoint `POST /posts/{post_id}/generate-image` fue modificado para que, al llamar a `generate_image_from_prompt`, reciba y guarde tanto `media_url` como el nuevo `media_storage_path` en la base de datos.
    *   **`profiles.py` (o donde esté `/profiles/me`):** Se realizaron ajustes para asegurar que el endpoint `GET /api/v1/profiles/me` devuelva `organization_id` y `role` (obtenidos de `TokenData`) al frontend, facilitando al cliente la construcción de rutas y la lógica de permisos.
    *   **`main.py`:** Se añadió la configuración de `CORSMiddleware` para manejar las solicitudes Cross-Origin del frontend y resolver errores de política CORS.

### 🐛 Correcciones de Errores 

*   Resueltos múltiples `TypeError`, `ImportError`, `NameError`, y `AttributeError` que surgieron durante la implementación y prueba de las nuevas funcionalidades de gestión de imágenes, relacionados con el manejo de `async/await` con `supabase-py`, la carga de configuraciones, y la definición/llamada de funciones y modelos.
*   Corregido el error "Bucket not found" en Supabase Storage asegurando que los nombres de bucket en el código coincidan con los existentes en Supabase.
*   Se está trabajando en resolver errores `500 (Internal Server Error)` provenientes de Supabase Storage relacionados con políticas RLS, asegurando que el rol `authenticated` tenga los permisos de `SELECT` necesarios en las tablas `public.organization_members` y `public.posts`.

### ⚠️ Notas 

*   La interacción con `supabase-py` v2.15.1 en un entorno `async` ha requerido ajustes finos, tratando varias operaciones del SDK como síncronas y usando `asyncio.to_thread` cuando es necesario para el I/O de storage.
*   La depuración de las políticas RLS de Supabase Storage para las subidas directas del frontend está en curso.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## [No Lanzado] - 2025-06-03

### ✨ Nuevas Características (Features)

*   **Gestión Avanzada de Imágenes para Posts (Flujo WIP):** Se ha implementado un sistema completo para manejar la imagen principal de los posts, incluyendo la generación por IA y la subida por el usuario, con un flujo de previsualización "Work In Progress" (WIP).
    *   Los usuarios ahora pueden generar una imagen de previsualización mediante IA para un post existente. Esta imagen se almacena temporalmente en una carpeta `/wip/` dentro del bucket `post_previews`.
    *   Los usuarios pueden subir su propia imagen de previsualización, que también se gestiona a través de la carpeta `/wip/`, reemplazando cualquier previsualización anterior.
    *   Al guardar un post, los usuarios pueden confirmar la imagen de la carpeta `/wip/` para que se convierta en la imagen principal del post. Esto implica mover la imagen al bucket `post_media` y actualizar las referencias del post.
    *   Si un post se guarda sin confirmar la imagen en `/wip/`, dicha imagen de previsualización se descarta automáticamente.
    *   Se permite eliminar la imagen principal de un post, lo que también limpia cualquier previsualización en `/wip/`.
    *   El proceso de creación de posts sigue un flujo de dos pasos: primero se crea el post con texto, y luego el frontend sube la imagen directamente a la ubicación final en `post_media` y actualiza el post mediante un `PATCH`.
    *   **Nuevos Endpoints en `posts.py`:**
        *   `POST /api/v1/posts/{post_id}/generate-preview-image`: Para generar una imagen IA y colocarla en `/wip/`.
        *   `POST /api/v1/posts/{post_id}/prepare-wip-for-user-upload`: Para limpiar la carpeta `/wip/` antes de que el usuario suba su propia previsualización.
    *   **Mejoras en `PATCH /api/v1/posts/{post_id}`:** Lógica robusta para confirmar imágenes desde `/wip/`, borrar la imagen principal, y limpiar la carpeta `/wip/` según corresponda. Incluye compensación de storage si la actualización de la base de datos falla después de una operación de imagen.
    *   **Mejoras en `DELETE /api/v1/posts/{post_id}` (Soft Delete):** Ahora también limpia la imagen principal asociada en `post_media` y cualquier imagen en la carpeta `/wip/` del post.

### 🛠 Mejoras y Cambios Técnicos (Improvements & Changes)

*   **Servicio de Storage (`storage_service.py`):** Se ha creado un nuevo servicio dedicado para todas las interacciones con Supabase Storage (subir, mover, listar, borrar archivos y carpetas), utilizando las capacidades `async` de `supabase-py` v2.x.
*   **Servicio de Generación de Imágenes IA (`ai_image_generator.py`):**
    *   Se añadió la función `generate_and_upload_ai_image_to_wip` para el nuevo flujo de previsualización.
    *   Se modificó la función `generate_image_from_prompt` (usada por `ai_router.py`) para que devuelva el `storage_path` de la imagen final y utilice una estructura de path más robusta y única en `post_media`.
    *   Los parámetros de configuración de la IA para imágenes (modelo, tamaño, calidad) ahora se leen desde `app/core/config.py` (`settings`), permitiendo una gestión centralizada.
*   **Modelos Pydantic (`post_models.py`):**
    *   Actualizados a la sintaxis de Pydantic V2.
    *   Nuevos modelos (`ConfirmWIPImageDetails`, `GeneratePreviewImageRequest`, `GeneratePreviewImageResponse`) para soportar el nuevo flujo.
    *   `PostUpdate` y `PostResponse` actualizados para incluir campos relacionados con la gestión de imágenes (`confirm_wip_image_details`, `media_storage_path`, `content_type` para imágenes).
*   **Campo `media_storage_path` en DB:** Se añadió el campo `media_storage_path` a la tabla `posts` para almacenar la ruta interna de la imagen principal en Supabase Storage, mejorando la robustez en operaciones de borrado y actualización.
*   **Refinamiento de Rutas de Storage:**
    *   Imágenes finales en: `post_media/{org_id}/posts/{post_id}/images/{uuid}.{ext}`.
    *   Imágenes de previsualización en: `post_previews/{org_id}/posts/{post_id}/wip/preview_active.{ext}`.

### ⚠️ Notas (Notes)

*   El endpoint `POST /api/v1/ai/posts/{post_id}/generate-image` (en `ai_router.py`) sigue generando y asignando una imagen principal directamente al post, pero ahora guarda también el `media_storage_path`. Se considera una refactorización futura para integrarlo completamente con el flujo `/wip/` si se desea una consistencia total.
*   Se recomienda revisar y asegurar una gestión consistente de entornos virtuales para el proyecto.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

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