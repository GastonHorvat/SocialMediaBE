# app/services/ai_prompt_helpers.py

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def get_brand_identity_context(org_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae y formatea la identidad de marca básica desde la configuración de la organización.
    """
    context = {}
    context['brand_name'] = org_settings.get('ai_brand_name', 'la marca')
    context['industry'] = org_settings.get('ai_brand_industry', 'la industria')
    context['audience'] = org_settings.get('ai_target_audience_description', 'la audiencia objetivo')
    context['communication_tone'] = org_settings.get('ai_communication_tone', 'neutral')
    
    personality_tags_list = org_settings.get('ai_brand_personality_tags', [])
    context['personality_tags_str'] = ", ".join(tag for tag in personality_tags_list if tag)
    
    keywords_list = org_settings.get('ai_keywords_to_use', [])
    context['keywords_str'] = ", ".join(keyword for keyword in keywords_list if keyword)
    
    return context

def get_stylistic_context(
    org_settings: Dict[str, Any],
    request_data: Optional[Any] = None
) -> Dict[str, str]:
    """
    Determina las instrucciones de estilo (tono, longitud), aplicando overrides del usuario.
    """
    context = {}
    base_communication_tone = org_settings.get('ai_communication_tone', 'neutral')

    # Tono de Voz: El del request pisa al de la organización
    final_tone = base_communication_tone
    if request_data and hasattr(request_data, 'voice_tone') and request_data.voice_tone:
        final_tone = request_data.voice_tone
    context['tone_instruction'] = final_tone
    
    # Longitud del Contenido: Solo si viene en el request
    length_instruction = "La longitud es flexible, usa tu criterio profesional para adaptarla a la idea y la red social."
    if request_data and hasattr(request_data, 'content_length') and request_data.content_length:
        length_instruction = f"El texto debe tener una longitud de tipo '{request_data.content_length}'."
    context['length_instruction'] = length_instruction
    
    return context

def get_formatting_context(org_settings: Dict[str, Any]) -> Dict[str, str]:
    """
    Determina las instrucciones de formato final (hashtags, emojis) basadas en la configuración.
    """
    context = {}

    # Lógica Condicional para Hashtags
    if org_settings.get('prefs_auto_hashtags_enabled') is True:
        count = org_settings.get('prefs_auto_hashtags_count', 3)
        strategy = org_settings.get('prefs_auto_hashtags_strategy', 'relevante')
        context['hashtag_instruction'] = f"Incluye aproximadamente {count} hashtags, siguiendo una estrategia de '{strategy}'."
    else:
        context['hashtag_instruction'] = "No incluyas ningún hashtag."

    # Lógica Condicional para Emojis
    if org_settings.get('prefs_auto_emojis_enabled') is True:
        style = org_settings.get('prefs_auto_emojis_style', 'sutil')
        context['emoji_instruction'] = f"Incorpora emojis de forma {style}."
    else:
        context['emoji_instruction'] = "No incluyas ningún emoji."
        
    return context