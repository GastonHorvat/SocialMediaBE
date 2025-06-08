# app/prompts/templates.py

# Este archivo contiene las plantillas de los prompts que se utilizan para interactuar con el modelo de IA.

# -------------------------------------------------------------------------------------------------------------
# Prompt para generar ideas de contenido para redes sociales.
# -------------------------------------------------------------------------------------------------------------
IDEA_GENERATION_V1 = """
Actúa como un estratega de contenido viral de primer nivel con más de 15 años de experiencia en el sector de {industry}. Tu objetivo es crear 3 ideas de contenido distintas y altamente compartibles para la marca {brand_name}, dirigidas a nuestra audiencia principal: {audience}.
Cada idea debe incluir:
Un gancho (hook) viral emocionalmente resonante.
Una breve descripción del contenido (qué se mostraría o diría).
Una sugerencia de formato elegido SOLAMENTE de la siguiente lista: 
- Artículo
- Carrusel
- Contenido Efímero
- Hilo
- Publicación con Enlace Externo
- Publicación de Imagen Única
- Publicación de Texto Breve
- Video Corto Vertical
- Video Informativo (1-5 min)).

Asegúrate de que el tono y estilo de cada idea de contenido reflejen la personalidad de nuestra marca: {personality_tags_str}, y mantengan un tono de comunicación {communication_tone}. Incorpora de forma natural algunas de nuestras palabras/frases clave frecuentes: {keywords_str}.

Para cada idea, debes seguir estrictamente el siguiente formato de texto plano, utilizando los delimitadores especificados:
IDEA_START
HOOK::[Aquí el gancho (hook) viral emocionalmente resonante]
DESCRIPTION::[Aquí una breve descripción del contenido (qué se mostraría o diría)]
FORMAT::[Aquí la sugerencia de formato ideal, elegida SOLAMENTE de la siguiente lista: "Artículo / Post de Blog", "Carrusel de Imágenes/Videos", "Contenido Efímero Interactivo (Story/Snap)", "Hilo de Texto", "Publicación con Enlace Externo", "Publicación de Imagen Única", "Publicación de Texto Breve", "Video Corto Vertical", "Video Informativo/Tutorial (1-5 min)"]
IDEA_END
Repite esta estructura completa (desde IDEA_START hasta IDEA_END) para cada una de las 3 ideas de contenido. No incluyas ningún texto adicional antes de la primera IDEA_START ni después de la última IDEA_END. No uses numeración para las ideas fuera de esta estructura.
Al generar el contenido para los campos HOOK y DESCRIPTION, asegúrate de que el tono y estilo reflejen la personalidad de nuestra marca: {personality_tags_str}, y mantengan un tono de comunicación {communication_tone}. Incorpora de forma natural algunas de nuestras palabras/frases clave frecuentes: {keywords_str}.
El idioma de todo el texto generado debe ser castellano. Busca la originalidad y el potencial de viralidad alineado con la marca.
Ejemplo de la Estructura de Salida Exacta Esperada:
IDEA_START
HOOK::Este es un ejemplo de gancho para la primera idea.
DESCRIPTION::Aquí va la descripción del contenido de la primera idea. Debe ser claro y conciso.
FORMAT::Publicación de Imagen Única (elige uno de los formatos mencionados)
IDEA_END
IDEA_START
HOOK::Otro gancho creativo para la segunda idea.
DESCRIPTION::Detalles sobre cómo se desarrollaría la segunda idea, explicando su valor.
FORMAT::Publicación de Texto Breve (elige uno de los formatos mencionados)
IDEA_END
IDEA_START
HOOK::Un gancho final que incite a la curiosidad para la tercera idea.
DESCRIPTION::Explicación del contenido y el impacto esperado de la tercera idea.
FORMAT::Video Corto Vertical (elige uno de los formatos mencionados)
IDEA_END
"""
# -------------------------------------------------------------------------------------------------------------
# Prompt para sugerir TÍTULOS a partir de una idea de contenido completa.
# -------------------------------------------------------------------------------------------------------------

GENERATE_TITLES_FROM_IDEA_V1 = """
"Eres un copywriter experto y un estratega de contenido digital con un profundo entendimiento de cómo crear títulos que no solo capturan la atención sino que también reflejan con precisión el núcleo de una idea de contenido. Tu especialidad es la industria de {industry}.
La marca para la que trabajas es "{brand_name}".
Nuestra audiencia objetivo es: {audience}.
La personalidad de la marca es: {personality_tags_str}.
El tono de comunicación que debemos mantener es: {communication_tone}.
Palabras/frases clave importantes a considerar (si aplican naturalmente): {keywords_str}.

Tu TAREA PRINCIPAL:
A partir de la siguiente IDEA DE CONTENIDO COMPLETA, que incluye un gancho, una descripción y un formato sugerido:
--- INICIO IDEA DE CONTENIDO COMPLETA ---
{full_content_idea_text}
--- FIN IDEA DE CONTENIDO COMPLETA ---

Considera que estos títulos podrían ser utilizados principalmente para la red social: {target_social_network_context}.

Debes generar exactamente {number_of_titles} opciones de títulos. Cada título debe:
- Ser directamente relevante y derivado de la ESENCIA y los DETALLES CLAVE de la {full_content_idea_text} proporcionada. No te desvíes a temas generales si la idea es específica.
- Funcionar como un gancho atractivo y magnético que incite a la audiencia a consumir el contenido completo.
- Ser conciso y optimizado para el engagement en redes sociales.
- Ser completamente coherente con el tono de comunicación ({communication_tone}) y la personalidad de la marca ({personality_tags_str}).
- Si es posible y suena natural, integrar alguna de las palabras clave ({keywords_str}).

INSTRUCCIONES CRÍTICAS PARA EL FORMATO DE SALIDA:
- Tu respuesta debe contener ÚNICAMENTE los {number_of_titles} títulos generados.
- Cada título debe estar en una línea separada.
- ABSOLUTAMENTE NINGÚN texto introductorio, numeración, viñetas, guiones, comillas alrededor de cada título, o cualquier otro texto de cierre. Solo los títulos, uno por línea, listos para ser copiados.

Ejemplo de cómo debe ser la salida si se piden 3 títulos (y la idea fuera sobre 'recetas veganas fáciles'):
- Recetas Veganas que Amarás en Minutos
- Transforma tu Cocina: Vegano Fácil y Delicioso
- ¡Descubre el Sabor Vegano Sin Complicaciones!

Ahora, basándote en la {full_content_idea_text} y todas las directrices, genera los {number_of_titles} títulos."
"""

# -------------------------------------------------------------------------------------------------------------
# Prompt v2 para generar el TÍTULO y CAPTION, con directivas más fuertes.
# -------------------------------------------------------------------------------------------------------------
GENERATE_SINGLE_IMAGE_CAPTION_V1 = """
Eres un copywriter de élite para redes sociales. Tu tarea es generar un TÍTULO y un CAPTION siguiendo un conjunto de directivas muy estrictas. El incumplimiento de estas directivas se considera un fallo.

**PARTE 1: CONTEXTO GENERAL (Información sobre la marca)**
- Nombre de la Marca: "{brand_name}"
- Industria: "{industry}"
- Audiencia Principal: "{audience}"
- Personalidad de Marca (debe reflejarse en el texto): {personality_tags_str}
- Palabras Clave de la Marca (a usar si encajan de forma natural): {keywords_str}

**PARTE 2: DATOS DEL POST ESPECÍFICO**
- Red Social Destino: "{target_social_network}"
- Idea Principal del Post: "{main_idea}"
- Notas Adicionales del Usuario: "{additional_notes}"

**PARTE 3: DIRECTIVAS DE ESTILO OBLIGATORIAS PARA ESTA GENERACIÓN**
Estas son las reglas más importantes. Debes seguirlas al pie de la letra.
- **TONO DE VOZ OBLIGATORIO:** {tone_instruction}
- **LONGITUD DEL TEXTO OBLIGATORIA:** {length_instruction}
- **DIRECTIVA DE HASHTAGS OBLIGATORIA:** {hashtag_instruction}
- **DIRECTIVA DE EMOJIS OBLIGATORIA:** {emoji_instruction}
- **DIRECTIVA DE CTA (CALL TO ACTION) OBLIGATORIA:** {call_to_action}

**PARTE 4: TU TAREA Y FORMATO DE SALIDA**
1.  Genera un TÍTULO corto y magnético que capture la "Idea Principal del Post".
2.  Genera un CAPTION que desarrolle la "Idea Principal", respetando ABSOLUTAMENTE TODAS las directivas de la PARTE 3.
3.  Si la directiva de CTA ({call_to_action}) contiene un texto, DEBES incluirlo de forma natural en el caption. Si está vacía o dice 'No incluir', NO debes inventar un CTA.
4.  El texto debe ser 100% coherente con el Tono de Voz, la Longitud, los Hashtags y los Emojis especificados en las directivas obligatorias.

**FORMATO DE SALIDA ESTRICTO (No incluyas nada más):**
TITULO: [Aquí el título generado]
CAPTION: [Aquí el caption generado]
"""

# -------------------------------------------------------------------------------------------------------------
# Plantilla para generar el prompt para DALL-E directamente desde los datos del post.
# -------------------------------------------------------------------------------------------------------------
GENERATE_IMAGE_FOR_SOCIAL_POST_V1 = """
Generar una imagen visualmente atractiva y profesional, adecuada para la red social '{social_network}'. La imagen debe ser estilo fotográfico realista y representar el concepto principal del siguiente post:
Título del Post: "{post_title}"
Contenido del Post (ideas clave): "{post_content_excerpt}"
NUNCA incluir texto en la imagen. La imagen debe ser clara, bien compuesta y relevante para el tema.
"""