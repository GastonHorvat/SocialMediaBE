# URGENTE

## Prompts



## Endpoints

- El Generate post poost tiene que ser capaz de recibir: 
--- Consumir un template diferente para cada red social seleccionada
--- prompt_id opcional para cuando querramos guargar los prompts usados
--- original_post_id para cuando podamos clonarlos

- Todos los endpoints de ia:
--- Guardar log de generaciones, sobre todo modelo y tokens usados

## Base de Datos

- Storage: Como identificamos y borramos imagenes abandonadas?


# Backlog de Desarrollo del Backend - ContentFlow

### Épica 1: Expansión Multi-Plataforma (Prioridad Actual)
*Capitalizar la arquitectura de publicación para expandir rápidamente el valor del producto.*

-   [ ] **Tarea 1.1: Implementar Conexión y Publicación para X (Twitter).**
    -   **Descripción:** Replicar el proceso de integración de LinkedIn para la API de X. Esto incluye el registro de la app, la gestión del flujo OAuth 2.0, y la creación de un `twitter_service.py` que se integre con nuestro `publishing_service` (dispatcher).
    -   **Valor:** Muy Alto. Valida la escalabilidad de nuestra arquitectura y añade una red social clave.

-   [ ] **Tarea 1.2: Implementar Conexión y Publicación para Facebook/Instagram.**
    -   **Descripción:** Integrar la Graph API de Meta. Implica manejar la lógica de Cuentas de Negocio, Páginas de Facebook y permisos más complejos.
    -   **Valor:** Crítico. Son las plataformas más solicitadas por el mercado.

### Épica 2: Escalabilidad y Optimización de la Generación de Contenido
*Mejorar la calidad y flexibilidad del contenido generado por IA, el core de nuestro negocio.*

-   [ ] **Tarea 2.1: Migrar Plantillas de Prompts a la Base de Datos.**
    -   **Descripción:** Crear y poblar la tabla `prompt_templates`. Refactorizar los servicios de IA para que lean los prompts desde la DB en lugar de un archivo estático, permitiendo prompts específicos por red social y tipo de contenido.
    -   **Valor:** Muy Alto. Mejora radical de la calidad del producto.

### Épica 3: Gestión de Usuarios y Multi-tenencia
*Habilitar el crecimiento de la aplicación de un solo usuario a equipos colaborativos.*

-   [ ] **Tarea 3.1: Implementar Sistema de Invitaciones y Roles.**
    -   **Descripción:** Añadir la columna `role` a `organization_members`, crear la tabla `invitations`, e implementar los endpoints para invitar a nuevos miembros a una organización.
    -   **Valor:** Alto. Clave para el modelo de negocio SaaS y la adquisición de equipos.

### Épica 4: Mejora de la Experiencia de Desarrollo y Calidad de la API
*Refinar la API para mejorar la colaboración con el frontend y la mantenibilidad del código.*

-   [ ] **Tarea 4.1: Crear Endpoint de Opciones Dinámicas.**
    -   **Descripción:** Implementar `GET /api/v1/options/content-types` para que el frontend obtenga la lista de tipos de contenido dinámicamente.
    -   **Valor:** Medio. Mejora la calidad de vida del desarrollador del frontend y desacopla la UI de valores fijos.

-   [ ] **Tarea 4.2: Unificar la Lógica de Generación de Prompts para Imágenes.**
    -   **Descripción:** Refactorizar los endpoints `/generate-preview-image` y `/generate-image` para que usen una lógica de construcción de prompts compartida y consistente.
    -   **Valor:** Medio. Mejora la mantenibilidad y reduce la duplicación de código.

### Épica 5: Mejoras de Mantenimiento (Baja Prioridad)
*Tareas de limpieza técnica para mejorar la calidad general del código.*

-   [ ] **Tarea 5.1: Investigar y resolver los `307 Temporary Redirect`.**
    -   **Descripción:** Analizar y unificar el uso de la barra final (`/`) en las URLs de la API para eliminar redirecciones innecesarias.
    -   **Valor:** Bajo. Mejora marginal de la eficiencia de la red.