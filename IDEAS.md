# URGENTE

## Prompts



## Endpoints

- El Generate post poost tiene que ser capaz de recibir: 
--- Titulo que el usuario le manda, y el modelo tiene que respetarlo sin cambios
--- Consumir un template diferente para cada red social seleccionada
--- prompt_id opcional para cuando querramos guargar los prompts usados
--- generation_grouo_id para que los posts generados juntos queden agrupados
--- original_post_id para cuando podamos clonarlos
--- Consumir un template diferente para cada red social seleccionada

- Todos los endpoints de ia:
--- Guardar log de generaciones, sobre todo modelo y tokens usados

## Base de Datos

- Storage: Como identificamos y borramos imagenes abandonadas?


Implementar sugerencia de titulos!!!

Asunto: Nuevo Endpoint para Generar Títulos de Posts con IA
Hola equipo de Frontend,
Hemos añadido un nuevo endpoint para generar sugerencias de títulos basadas en una idea de contenido existente.
Endpoint: POST /api/v1/ai/generate-titles-from-idea
Funcionalidad:
Cuando el usuario ha seleccionado o tiene una "idea de contenido" (que probablemente incluya un hook, una descripción y un formato sugerido, como las que devuelve el endpoint /content-ideas), este nuevo endpoint tomará ese texto completo de la idea y generará varias opciones de títulos.
Petición (Request Body - JSON):
El frontend debe enviar un objeto JSON con los siguientes campos:
{
  "full_content_idea_text": "AQUÍ_VA_EL_TEXTO_COMPLETO_DE_LA_IDEA_SELECCIONADA_POR_EL_USUARIO",
  "target_social_network": "Instagram", // Opcional: La red social para la que son los títulos (ej. "Twitter", "LinkedIn", "Blog Post")
  "number_of_titles": 3 // Opcional: Cuántos títulos generar (default en backend es 3, puede ser entre 1 y 5)
}
Use code with caution.
Json
full_content_idea_text (string, mandatorio): El texto completo de la idea generada previamente.
target_social_network (string, opcional): Puede ayudar a la IA a adaptar la longitud o estilo del título.
number_of_titles (integer, opcional): Cuántas opciones de título se desean. El backend tiene un default (3) y un máximo (5).
Respuesta Exitosa (200 OK):
Un objeto JSON con la siguiente estructura:
{
  "titles": [
    "Título Sugerido 1 generado por IA",
    "Otra Opción de Título Muy Buena",
    "Un Tercer Título Impactante"
  ],
  "original_full_idea_text": "EL_MISMO_TEXTO_DE_LA_IDEA_QUE_SE_ENVIÓ_EN_LA_PETICIÓN"
}
Use code with caution.
Json
titles: Un array de strings, cada uno siendo una sugerencia de título.
original_full_idea_text: Se devuelve para referencia, para que la UI pueda mostrar claramente para qué idea son los títulos.
Flujo Sugerido en el Frontend:
El usuario tiene una "idea de contenido" (obtenida del endpoint /content-ideas o escrita por él).
El usuario indica que quiere generar títulos para esa idea (ej. un botón "Sugerir Títulos").
El frontend toma el texto completo de esa idea.
(Opcional) El frontend puede permitir al usuario especificar la red social o la cantidad de títulos.
Se hace una petición POST a /api/v1/ai/generate-titles-from-idea con el cuerpo JSON descrito arriba, enviando el access_token en la cabecera Authorization.
Se muestran los titles recibidos al usuario para que seleccione uno.
Manejo de Errores:
Manejar los códigos de estado HTTP habituales (401, 403, 400, 500, 502, 503). El detail del error dará más información.