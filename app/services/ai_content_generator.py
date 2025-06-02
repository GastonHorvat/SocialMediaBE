# app/services/ai_content_generator.py
import google.generativeai as genai
import json # Necesario para el parser si el LLM devolviera JSON, pero para delimitado no lo usamos directamente.
import logging
import asyncio # Para ejecutar llamadas síncronas en un hilo separado

from typing import List, Dict, Any, Optional
from app.prompts import templates as prompt_templates
from app.models.ai_models import GeneratedIdeaDetail
from app.core.config import settings # Para la API Key si necesitamos reconfigurar
from typing import Optional, Dict, Any, List  # Asegúrate de tener todas las importaciones necesarias
from uuid import UUID
from app.prompts import templates as prompt_templates # Importar al inicio del módulo
from app.models.ai_models import GeneratedIdeaDetail, GenerateTitlesFromFullIdeaRequest

logger = logging.getLogger(__name__)


# --- NUEVA FUNCIÓN PARA CONSTRUIR PROMPT DE TÍTULOS ---
def build_prompt_for_titles(
    org_settings: Dict[str, Any],
    request_data: GenerateTitlesFromFullIdeaRequest # Usamos el nuevo modelo de petición
) -> str:
    """
    Construye un prompt para Gemini para generar títulos basados en una idea de contenido completa
    y la configuración de la organización.
    """
    # print(f"DEBUG_BUILD_TITLES_PROMPT: org_settings: {org_settings}")
    # print(f"DEBUG_BUILD_TITLES_PROMPT: request_data: {request_data}")

    # Extraer datos de org_settings con fallbacks
    brand_name = org_settings.get('ai_brand_name', 'esta marca')
    industry = org_settings.get('ai_brand_industry', 'su industria general')
    audience = org_settings.get('ai_target_audience_description', 'su audiencia')
    communication_tone = org_settings.get('ai_communication_tone', 'un tono efectivo')
    
    personality_tags_list = org_settings.get('ai_brand_personality_tags', [])
    personality_tags_str = ", ".join(tag.strip() for tag in personality_tags_list if isinstance(tag, str) and tag.strip()) if personality_tags_list else "general"
    
    keywords_list = org_settings.get('ai_keywords_to_use', [])
    keywords_str = ", ".join(keyword.strip() for keyword in keywords_list if isinstance(keyword, str) and keyword.strip()) if keywords_list else "temas relevantes"

    # Extraer datos de request_data
    full_content_idea_text = request_data.full_content_idea_text
    
    # Manejar target_social_network opcional
    target_social_network_context = request_data.target_social_network if request_data.target_social_network else "múltiples redes sociales"
    
    number_of_titles_to_generate = request_data.number_of_titles # Ya tiene default 3 en el modelo Pydantic

    try:
        prompt_template_string = prompt_templates.GENERATE_TITLES_FROM_IDEA_V1
        
        prompt = prompt_template_string.format(
            industry=industry,
            brand_name=brand_name,
            audience=audience,
            communication_tone=communication_tone,
            personality_tags_str=personality_tags_str,
            keywords_str=keywords_str,
            full_content_idea_text=full_content_idea_text,
            target_social_network_context=target_social_network_context,
            number_of_titles=number_of_titles_to_generate
        )
    except AttributeError:
        print("ERROR_BUILD_TITLES_PROMPT: La plantilla 'GENERATE_TITLES_FROM_IDEA_V1' no se encontró.")
        raise ValueError("Plantilla de prompt para títulos no encontrada.")
    except KeyError as e:
        print(f"ERROR_BUILD_TITLES_PROMPT: Falta una clave en la plantilla o datos de formateo: {e}")
        raise ValueError(f"Error al formatear la plantilla de prompt para títulos: clave {e} faltante.")
    
    # print(f"DEBUG_BUILD_TITLES_PROMPT: Prompt final (primeros 300):\n{prompt[:300]}...")
    return prompt.strip()

# --- FIN NUEVA FUNCIÓN ---

def parse_lines_to_list(llm_response_text: str, max_items: Optional[int] = None) -> List[str]:
    """
    Parsea una respuesta de texto del LLM que contiene items uno por línea.
    """
    if not llm_response_text or not llm_response_text.strip():
        return []
    
    items = [item.strip() for item in llm_response_text.splitlines() if item.strip()]
    
    if max_items is not None:
        return items[:max_items]
    return items

def build_prompt_for_ideas(org_settings: Dict[str, Any]) -> str:
    """
    Construye un prompt para Gemini para generar 3 ideas conceptuales para posts
    basado en la configuración de la organización, usando una plantilla.
    """
    # --- LOG F: VERIFICAR ORG_SETTINGS RECIBIDOS EN EL SERVICIO ---
    # print(f"DEBUG_BUILD_PROMPT_IDEAS: org_settings recibidos: {org_settings}") # Puedes activar este si es necesario

    # Extraer y preparar los valores de org_settings con fallbacks descriptivos
    # y usando los nombres de campo correctos de tu tabla organization_settings
    brand_name = org_settings.get('ai_brand_name', 'esta marca/negocio')
    industry = org_settings.get('ai_brand_industry', 'su industria/nicho')
    audience = org_settings.get('ai_target_audience_description', 'su audiencia objetivo') # Nombre corregido
    
    # Para personality_tags y keywords, que son TEXT[] en la DB y List[str] en Pydantic/Python
    personality_tags_list = org_settings.get('ai_brand_personality_tags', []) # Nombre corregido
    personality_tags_str = ", ".join(tag.strip() for tag in personality_tags_list if isinstance(tag, str) and tag.strip()) if personality_tags_list else "un estilo general y amigable"
    
    keywords_list = org_settings.get('ai_keywords_to_use', []) # Nombre corregido
    keywords_str = ", ".join(keyword.strip() for keyword in keywords_list if isinstance(keyword, str) and keyword.strip()) if keywords_list else "temas de interés general para la audiencia"

    communication_tone = org_settings.get('ai_communication_tone', 'un tono neutral y útil')

    try:
        # Acceder a la plantilla importada
        prompt_template_string = prompt_templates.IDEA_GENERATION_V1     
        prompt = prompt_template_string.format(
            brand_name=brand_name,
            industry=industry,
            audience=audience,
            communication_tone=communication_tone,
            personality_tags_str=personality_tags_str,
            keywords_str=keywords_str
        )
    except AttributeError:
        # Esto pasaría si IDEA_GENERATION_V1 no está definido en app.prompts.templates
        print("ERROR_BUILD_PROMPT_IDEAS: La plantilla 'IDEA_GENERATION_V1' no se encontró en app.prompts.templates.")
        raise ValueError("Plantilla de prompt para ideas no encontrada.") # O devuelve un prompt por defecto muy genérico
    except KeyError as e:
        print(f"ERROR_BUILD_PROMPT_IDEAS: Falta una clave en la plantilla IDEA_GENERATION_V1 o en los datos de formateo: {e}")
        raise ValueError(f"Error al formatear la plantilla de prompt para ideas: clave {e} faltante.") from e
    
    # --- LOG G (Opcional pero útil para depurar el prompt final): ---
    # print(f"DEBUG_BUILD_PROMPT_IDEAS: Prompt final construido (longitud: {len(prompt)}). Primeros 500 chars:\n{prompt[:500]}")
    # if len(prompt) > 500:
    # print("DEBUG_BUILD_PROMPT_IDEAS: ... (prompt continúa) ...")
    # Para ver el prompt completo si es muy largo:
    # print(f"DEBUG_BUILD_PROMPT_IDEAS_FULL:\n{prompt}")

    return prompt.strip()

def parse_gemini_idea_titles(llm_response: str) -> List[str]:
    """Parsea la respuesta del LLM para extraer los títulos de las ideas."""
    if not llm_response or not llm_response.strip():
        return []
    # Asume que cada idea está en una nueva línea
    titles = [line.strip() for line in llm_response.splitlines() if line.strip()]
    logger.debug(f"Títulos de ideas parseados: {titles}")
    return titles

def parse_delimited_text_to_ideas(llm_response_text: str) -> List[GeneratedIdeaDetail]:
    if not llm_response_text or not llm_response_text.strip():
        print("WARN_PARSE_DELIMITED: Respuesta del LLM vacía o solo espacios.")
        return []

    parsed_ideas_list: List[GeneratedIdeaDetail] = []
    current_idea_dict: Dict[str, str] = {} 
    
    lines = llm_response_text.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line: 
            continue

        if line == "IDEA_START":
            if current_idea_dict: # Si hay una idea anterior no guardada (ej. sin IDEA_END)
                try:
                    # Pasar el diccionario directamente para que Pydantic maneje el alias
                    idea_obj = GeneratedIdeaDetail.model_validate(current_idea_dict)
                    parsed_ideas_list.append(idea_obj)
                except Exception as e_pydantic:
                    print(f"WARN_PARSE_DELIMITED: Idea parcial no válida (al encontrar nuevo IDEA_START). Error: {e_pydantic}. Parts: {current_idea_dict}")
            current_idea_dict = {} 
            continue
        
        if line == "IDEA_END":
            if current_idea_dict: 
                try:
                    # Pasar el diccionario directamente
                    idea_obj = GeneratedIdeaDetail.model_validate(current_idea_dict)
                    parsed_ideas_list.append(idea_obj)
                except Exception as e_pydantic:
                    print(f"WARN_PARSE_DELIMITED: Idea al final de IDEA_END no válida. Error: {e_pydantic}. Parts: {current_idea_dict}")
            current_idea_dict = {} 
            continue

        if line.startswith("HOOK::"):
            current_idea_dict["hook"] = line[len("HOOK::"):].strip()
        elif line.startswith("DESCRIPTION::"):
            # Guardar en el dict con la clave que Pydantic espera (el alias "description")
            current_idea_dict["description"] = line[len("DESCRIPTION::"):].strip() 
        elif line.startswith("FORMAT::"):
            current_idea_dict["suggested_format"] = line[len("FORMAT::"):].strip()
    
    # Añadir la última idea si el texto no terminó con IDEA_END pero tenía contenido
    if current_idea_dict: # Si current_idea_dict no está vacío
        try:
            # Pasar el diccionario directamente
            idea_obj = GeneratedIdeaDetail.model_validate(current_idea_dict)
            parsed_ideas_list.append(idea_obj)
        except Exception as e_pydantic:
             print(f"WARN_PARSE_DELIMITED: Última idea (sin IDEA_END explícito) no válida. Error: {e_pydantic}. Parts: {current_idea_dict}")

    return parsed_ideas_list[:3] # Devolver hasta 3 ideas

def build_prompt_for_single_image_caption(org_settings: Dict[str, Any], request_data: Any) -> str:
    """Construye el prompt para generar caption de imagen única."""
    # Asumiendo que 'request_data' es tu modelo Pydantic GenerateSingleImageCaptionRequest
    from app.prompts.templates import GENERATE_SINGLE_IMAGE_CAPTION_V1 # Asumiendo plantilla

    brand_name = org_settings.get('ai_brand_name', 'N/A')
    industry = org_settings.get('ai_brand_industry', 'N/A')
    audience = org_settings.get('ai_target_audience', 'N/A')
    communication_tone = org_settings.get('ai_communication_tone', 'neutral')
    
    personality_tags = org_settings.get('ai_personality_tags', [])
    keywords = org_settings.get('ai_keywords', [])
    personality_tags_str = ", ".join(personality_tags) if isinstance(personality_tags, list) else str(personality_tags)
    keywords_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)

    prompt = GENERATE_SINGLE_IMAGE_CAPTION_V1.format(
        brand_name=brand_name,
        industry=industry,
        audience=audience,
        communication_tone=communication_tone,
        personality_tags_str=personality_tags_str,
        keywords_str=keywords_str,
        target_social_network=getattr(request_data, 'target_social_network', 'N/A'),
        main_idea=getattr(request_data, 'main_idea', ''),
        image_description=getattr(request_data, 'image_description', ''),
        call_to_action=getattr(request_data, 'call_to_action', ''),
        additional_notes=getattr(request_data, 'additional_notes', '')
    )
    logger.debug(f"Prompt para caption construido: {prompt[:200]}...")
    return prompt

def parse_title_and_caption_from_llm(llm_response: str) -> Dict[str, Optional[str]]:
    """Parsea la respuesta del LLM para extraer título y caption."""
    # Ejemplo de implementación, ajusta según el formato de respuesta de tu LLM
    title: Optional[str] = None
    caption: Optional[str] = None
    
    lines = llm_response.splitlines()
    for line in lines:
        line_lower = line.lower()
        if line_lower.startswith("titulo:"):
            title = line[len("titulo:"):].strip()
        elif line_lower.startswith("caption:"):
            caption = line[len("caption:"):].strip()
            # Si el caption puede ser multilínea y el formato lo asegura,
            # podrías necesitar una lógica más compleja para capturar todo el caption.
            # Por ahora, asume que el caption principal está en la línea que empieza con "caption:".
            # Si el caption puede continuar en líneas siguientes, se podría hacer esto:
            # caption_start_index = lines.index(line)
            # caption = "\n".join(lines[caption_start_index:])[len("caption:"):].strip()
            # break # Asumiendo que después del caption no hay más info relevante en este formato
    
    logger.debug(f"Parseado de LLM: Título='{title}', Caption='{caption[:50] if caption else None}...'.")
    return {"title": title, "content_text": caption}


# --- Lógica de Inicialización y Generación de Texto ---

def _ensure_text_model_initialized() -> bool:
    """
    Asegura que el modelo de texto esté inicializado.
    Retorna True si el modelo está listo, False si falla la inicialización.
    """
    global _text_model
    if _text_model is not None:
        logger.debug("Modelo de texto Gemini ya está inicializado.")
        return True

    # Verificar si genai está configurado con una API key
    genai_is_configured = (
        hasattr(genai, '_config') and 
        genai._config and 
        hasattr(genai._config, 'api_key') and 
        genai._config.api_key
    )

    if not genai_is_configured:
        logger.error("genai no está configurado con API key antes de intentar inicializar el modelo de texto.")
        # Intento de reconfiguración como último recurso
        if settings.GOOGLE_API_KEY:
            logger.warning("Intentando reconfigurar genai desde _ensure_text_model_initialized...")
            try:
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                # Re-verificar después del intento
                genai_is_configured = (
                    hasattr(genai, '_config') and 
                    genai._config and 
                    hasattr(genai._config, 'api_key') and 
                    genai._config.api_key
                )
                if not genai_is_configured:
                    logger.error("Falló la reconfiguración de emergencia de genai para el modelo de texto.")
                    return False
                logger.info("Reconfiguración de emergencia de genai para texto exitosa.")
            except Exception as e_reconfig:
                logger.error(f"Error en reconfiguración de emergencia de genai para texto: {e_reconfig}")
                return False
        else:
            logger.error("No hay GOOGLE_API_KEY en settings para intentar reconfigurar genai para texto.")
            return False
    
    try:
        # Define el nombre de tu modelo de TEXTO. Puedes hacerlo configurable si quieres.
        text_model_name = getattr(settings, 'GEMINI_TEXT_MODEL_NAME', "gemini-2.0-flash-lite")
        logger.info(f"Inicializando modelo de texto Gemini: {text_model_name}")
        _text_model = genai.GenerativeModel(model_name=text_model_name)
        logger.info(f"Modelo de texto Gemini '{text_model_name}' inicializado exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error crítico al inicializar el modelo de texto Gemini '{text_model_name}': {e}", exc_info=True)
        _text_model = None # Asegurar que _text_model es None si falla
        return False

async def generate_text_with_gemini(prompt: str, **kwargs) -> str:
    try:
        text_model_name = getattr(settings, 'GEMINI_TEXT_MODEL_NAME', "gemini-2.0-flash-lite")
        logger.info(f"Generando texto con modelo '{text_model_name}' y prompt: {prompt[:100]}...")
        
        # Crear el modelo aquí. La librería debería usar la GOOGLE_API_KEY del entorno.
        model = genai.GenerativeModel(model_name=text_model_name)
        
        response = await asyncio.to_thread(model.generate_content, prompt)

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            reason_message = response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason.name
            logger.warning(f"Prompt de texto bloqueado. Razón: {reason_message}")
            raise RuntimeError(f"El prompt para generar texto fue bloqueado por la IA: {reason_message}")
        
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            generated_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
            if generated_text:
                return generated_text.strip()
        
        if hasattr(response, 'text') and response.text:
            return response.text.strip()
            
        logger.warning("Respuesta de Gemini para texto no contenía formato esperado.")
        raise RuntimeError("Respuesta inesperada o vacía del modelo de IA para texto.")

    except Exception as e:
        logger.error(f"Error durante la generación de texto con Gemini: {e}", exc_info=True)
        if isinstance(e, RuntimeError): raise
        raise RuntimeError(f"Ocurrió un error en la comunicación con el modelo de IA para texto: {str(e)}")


# --- Función para crear borrador de post (asumiendo que sigue aquí) ---
# Esta función interactúa con Supabase, no directamente con el LLM para generar texto.

async def create_draft_post_from_ia(
    supabase_client: Any, # Debería ser SupabaseClient pero para evitar import circular si está en db
    author_id: UUID,
    organization_id: UUID,
    post_create_data: Any # Debería ser PostCreate
) -> Dict[str, Any]:
    """
    Crea un borrador de post en la base de datos.
    """
    logger.info(f"Intentando crear borrador de post para org {organization_id} por autor {author_id}")
    
    # Convertir el modelo Pydantic a un diccionario para la inserción
    # Usar model_dump() para Pydantic v2, o .dict() para Pydantic v1
    try:
        if hasattr(post_create_data, 'model_dump'):
            data_to_insert = post_create_data.model_dump(exclude_unset=True) # Pydantic v2
        else:
            data_to_insert = post_create_data.dict(exclude_unset=True) # Pydantic v1
    except Exception as e_model_conv:
        logger.error(f"Error convirtiendo post_create_data a dict: {e_model_conv}")
        raise RuntimeError(f"Error interno preparando datos del post: {e_model_conv}")

    # Añadir/Sobrescribir author_user_id y organization_id para asegurar que son los correctos del usuario autenticado
    data_to_insert['author_user_id'] = str(author_id)
    data_to_insert['organization_id'] = str(organization_id)
    # Asegurar que el status es 'draft' si este endpoint siempre crea borradores
    data_to_insert['status'] = 'draft'

    logger.debug(f"Datos a insertar para el post: {data_to_insert}")

    try:
        response = await asyncio.to_thread(
            supabase_client.table("posts")
            .insert(data_to_insert)
            .execute
        )
        
        if not response.data:
            logger.error(f"Supabase no devolvió datos al crear el post. Respuesta: {response}")
            # Podrías revisar response.error si existe
            error_message = "Error al crear el post en la base de datos: no se recibieron datos."
            if hasattr(response, 'error') and response.error:
                error_message = f"Error de Supabase al crear post: {response.error.message}"
            raise RuntimeError(error_message)
            
        logger.info(f"Post creado exitosamente con ID: {response.data[0].get('id')}")
        return response.data[0] # Devuelve el primer (y único) post creado
        
    except Exception as e: # Captura más genérica para errores de DB o asyncio
        logger.error(f"Excepción al crear post en Supabase: {e}", exc_info=True)
        raise RuntimeError(f"No se pudo guardar el borrador del post: {str(e)}")
    
from app.prompts import templates as prompt_templates # Asegúrate que esté importado



# ... GENERA el prompt para DALL-E directamente desde los datos del post ...

def build_dalle_prompt_from_post_data(
    post_title: Optional[str],
    post_content_text: str,
    social_network: str, # Red social para contextualizar el estilo/formato
    max_content_excerpt_length: int = 200, # Aumentado un poco para más contexto
) -> str:
    """
    Construye un prompt para DALL-E directamente desde los datos del post
    (título, contenido, red social) usando una plantilla.
    """
    title_str = post_title or "No se proporcionó un título específico para el post"
    
    if post_content_text and len(post_content_text) > max_content_excerpt_length:
        excerpt = post_content_text[:max_content_excerpt_length].strip().replace("\n", " ") + "..."
    elif post_content_text:
        excerpt = post_content_text.strip().replace("\n", " ")
    else:
        excerpt = "El contenido del post no proporcionó detalles adicionales."
        # Si el contenido es vital, podrías incluso lanzar un error o devolver un prompt que indique que falta información.

    try:
        final_dalle_prompt = prompt_templates.GENERATE_IMAGE_FOR_SOCIAL_POST_V1.format(
            social_network=social_network,
            post_title=title_str,
            post_content_excerpt=excerpt
        )
        logger.info(f"Prompt para DALL-E construido: {final_dalle_prompt}") # Loguear el prompt final
        return final_dalle_prompt.strip()
    except KeyError as e:
        logger.error(f"KeyError en plantilla GENERATE_IMAGE_FOR_SOCIAL_POST_V1: {e}", exc_info=True)
        # Fallback muy genérico si la plantilla falla
        return f"Una imagen de estilo fotográfico realista sobre: {title_str} - {excerpt}. Adecuada para {social_network}."