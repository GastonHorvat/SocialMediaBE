# app/services/ai_content_generator.py
import google.generativeai as genai
from app.core.config import Settings
from typing import Dict, Any, List

# --- IMPORTAR LAS PLANTILLAS DE PROMPTS ---
from app.prompts import templates as prompt_templates
# --- FIN DE LA IMPORTACIÓN ---

model = None # Variable global para el modelo

def init_gemini_model(api_key: str):
    global model
    if model is None:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            print("INFO: Modelo Gemini inicializado correctamente.")
        except Exception as e:
            print(f"ERROR: Falló la inicialización del modelo Gemini: {e}")
            model = None


async def generate_text_with_gemini(prompt: str) -> str:
    global model
    if model is None:
        print("ERROR: El modelo Gemini no está inicializado. Llama a init_gemini_model primero.")
        raise RuntimeError("El modelo Gemini no está inicializado.")

    try:
        # print(f"DEBUG_GEMINI: Enviando prompt (len: {len(prompt)}):\n{prompt[:200]}...") # Muestra más del prompt
        response = await model.generate_content_async(prompt)
        # print(f"DEBUG_GEMINI: Respuesta cruda de Gemini (text): {response.text}")
        return response.text
    except Exception as e:
        print(f"ERROR: Ocurrió un error durante la generación con Gemini: {e}")
        raise RuntimeError(f"Error en la generación con Gemini: {e}") from e


def build_prompt_for_ideas(org_settings: Dict[str, Any]) -> str:
    """
    Construye un prompt para Gemini para generar 3 ideas conceptuales para posts
    basado en la configuración de la organización, usando una plantilla.
    """
    # Extraer y preparar los valores de org_settings con fallbacks
    brand_name = org_settings.get('ai_brand_name', 'nuestra marca')
    industry = org_settings.get('ai_brand_industry', 'nuestra industria')
    audience = org_settings.get('ai_target_audience_description', 'nuestra audiencia objetivo')
    
    personality_tags_list = org_settings.get('ai_brand_personality_tags', [])
    # Unir la lista en una cadena; si está vacía, usar un string por defecto
    personality_tags_str = ", ".join(tag.strip() for tag in personality_tags_list if tag.strip()) if personality_tags_list else "un estilo general y amigable"
    
    keywords_list = org_settings.get('ai_keywords_to_use', [])
    keywords_str = ", ".join(keyword.strip() for keyword in keywords_list if keyword.strip()) if keywords_list else "temas de interés general para la audiencia"

    communication_tone = org_settings.get('ai_communication_tone', 'neutral y útil')

    # Usar el método .format() para rellenar la plantilla
    # o f-strings si prefieres (pero .format es más explícito con los nombres de placeholder)
    try:
        prompt = prompt_templates.IDEA_GENERATION_V1.format(
            brand_name=brand_name,
            industry=industry,
            audience=audience,
            communication_tone=communication_tone,
            personality_tags_str=personality_tags_str,
            keywords_str=keywords_str
        )
    except KeyError as e:
        print(f"ERROR_PROMPT_FORMAT: Falta una clave en la plantilla IDEA_GENERATION_V1 o en los datos de formateo: {e}")
        # Podrías lanzar una excepción o devolver un prompt por defecto genérico
        # Por ahora, relanzamos para que se note el error de configuración del prompt.
        raise ValueError(f"Error al formatear la plantilla de prompt: clave {e} faltante.") from e
    
    # print(f"DEBUG_PROMPT: Prompt construido para ideas (desde plantilla):\n{prompt}")
    return prompt.strip()


def parse_gemini_idea_titles(gemini_response_text: str) -> List[str]:
    if not gemini_response_text:
        return []
    parsed_items = [item.strip() for item in gemini_response_text.splitlines() if item.strip()]
    return parsed_items[:3]