# app/prompts/templates.py

# Este archivo contiene las plantillas de los prompts que se utilizan para interactuar con el modelo de IA.

# -------------------------------------------------------------------------------------------------------------
# Prompt para generar ideas de contenido para redes sociales.
# -------------------------------------------------------------------------------------------------------------
IDEA_GENERATION_V1 = """
Eres un estratega de contenido experto en redes sociales. Tu tarea es generar ideas para posts, no solo títulos.
Para la marca "{brand_name}", que opera en la industria de "{industry}" y se dirige a "{audience}", genera exactamente 3 ideas conceptuales distintas para posts en redes sociales.

Cada idea debe ser una breve descripción del concepto o el ángulo del post (1-2 frases concisas por idea). No escribas el post completo, solo la esencia de la idea.
Piensa en el "qué" y el "por qué" del post, más que en el titular exacto.

El tono de comunicación deseado es "{communication_tone}".
La personalidad de la marca se describe como: {personality_tags_str}.
Considera las siguientes palabras clave o temas: {keywords_str}.

Formato de respuesta deseado:
Devuelve únicamente las 3 ideas. Cada idea debe estar en una nueva línea, sin numeración, viñetas, ni texto introductorio o de cierre.
Ejemplo de cómo debería ser una idea:
"Un post explicando cómo [un concepto clave de la industria] puede resolver [un problema común de la audiencia], usando una analogía simple y un gráfico."
"Una serie de historias interactivas preguntando a la audiencia sobre sus mayores desafíos relacionados con [tema relevante], y ofreciendo un pequeño consejo en la última historia."
"Un video corto testimonial de un cliente satisfecho destacando cómo [producto/servicio de la marca] le ayudó a lograr [un resultado específico]."

Por favor, genera 3 ideas siguiendo este formato.
"""

# -------------------------------------------------------------------------------------------------------------
# Prompt para generar el TÍTULO y CAPTION para una publicación de imagen única.
# -------------------------------------------------------------------------------------------------------------
GENERATE_SINGLE_IMAGE_CAPTION_V1 = """
Eres un copywriter experto en redes sociales, especializado en crear TÍTULOS atractivos y CAPTIONS persuasivos para publicaciones con imágenes.

**Contexto de la Marca:**
- Nombre de la Marca/Negocio: "{brand_name}"
- Industria/Nicho: "{industry}"
- Audiencia Objetivo: "{audience}"
- Tono de Comunicación General: "{communication_tone}"
- Personalidad de Marca (tags): {personality_tags_str}
- Palabras Clave Importantes para la Marca: {keywords_str}

**Información Específica para Este Post:**
- Red Social Destino: "{target_social_network}"
- Idea Principal/Mensaje Clave del Post: "{main_idea}"
- Descripción de la Imagen (si está disponible, si no, se generará contenido basado en la idea principal): "{image_description}"
- Llamado a la Acción (CTA) Sugerido (si lo hay): "{call_to_action}"
- Notas Adicionales del Usuario: "{additional_notes}"

**Tu Tarea:**
Genera un TÍTULO atractivo y un CAPTION (texto descriptivo) para una publicación en redes sociales.
El contenido debe estar primordialmente basado en la "Idea Principal/Mensaje Clave del Post" y el "Contexto de la Marca".
Si se proporcionó una "Descripción de la Imagen", utilízala para asegurar que el texto sea coherente con el visual. Si la descripción es genérica o no está disponible, enfócate en desarrollar la "Idea Principal" de forma convincente.

El TÍTULO debe ser:
- Conciso (idealmente menos de 10-15 palabras).
- Captar la atención e incitar a leer el caption.
- Reflejar la "Idea Principal".

El CAPTION debe ser:
1. Desarrollar la "Idea Principal" de forma clara y atractiva.
2. Estar alineado con la identidad de la marca (tono, personalidad, palabras clave).
3. Ser adecuado para la red social "{target_social_network}".
4. Ser capaz de generar engagement (interacción).
5. Si se proporcionó un CTA, intégralo de forma natural. Si no, considera si un CTA genérico apropiado (ej. "Más información", "Visita nuestra web") podría encajar o si es mejor omitirlo según el contexto.
6. EVITA generar placeholders como "[Describir imagen aquí]" o frases que indiquen que no tienes la descripción de la imagen. Si no hay descripción específica, crea el mejor contenido posible basándote en la IDEA PRINCIPAL.

**Instrucciones de Formato:**
- Devuelve la respuesta en el siguiente formato EXACTO, sin ningún texto adicional antes o después:
TITULO: [Aquí el título generado]
CAPTION: [Aquí el caption generado]

- No generes hashtags ni emojis a menos que el tono ("{communication_tone}") o la personalidad ("{personality_tags_str}") lo sugieran muy fuertemente y de forma implícita. El foco principal es el texto del mensaje.
- Escribe como si fueras el gestor de redes sociales de "{brand_name}".

**Ejemplo de un buen output (solo como referencia de formato y estilo, no de contenido específico):**
TITULO: Innovación que Transforma Tu Día
CAPTION: Descubre cómo nuestra última solución puede simplificar tu rutina y potenciar tus resultados. Pensado para ti, que buscas {{beneficio clave}}. ✨ Más detalles en el link de nuestra bio. #Innovacion #{{PalabraClaveRelevante}}

Ahora, genera el TÍTULO y el CAPTION para la solicitud descrita arriba.
"""

# -------------------------------------------------------------------------------------------------------------
# Plantilla para generar el prompt para DALL-E directamente desde los datos del post.
# -------------------------------------------------------------------------------------------------------------
GENERATE_IMAGE_FOR_SOCIAL_POST_V1 = """
Generar una imagen visualmente atractiva y profesional, adecuada para la red social '{social_network}'. La imagen debe ser estilo fotográfico realista y representar el concepto principal del siguiente post:
Título del Post: "{post_title}"
Contenido del Post (ideas clave): "{post_content_excerpt}"
Evitar incluir texto visible en la imagen. La imagen debe ser clara, bien compuesta y relevante para el tema.
"""