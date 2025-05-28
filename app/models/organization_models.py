# app/models/organization_models.py
from pydantic import BaseModel, Field, conint
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class OrganizationSettingsAIUpdate(BaseModel):
    ai_brand_name: Optional[str] = Field(None, title="Nombre del Negocio/Marca para IA", max_length=255)
    ai_brand_industry: Optional[str] = Field(None, title="Industria o Nicho Específico para IA", max_length=255)
    ai_target_audience_description: Optional[str] = Field(None, title="Descripción de la Audiencia Objetivo para IA")
    ai_communication_tone: Optional[str] = Field(None, title="Tono de Comunicación Preferido para IA (incluye matices)", max_length=500)
    ai_brand_personality_tags: Optional[List[str]] = Field(None, title="Tags de Personalidad de la Marca para IA")
    ai_keywords_to_use: Optional[List[str]] = Field(None, title="Palabras/Frases Clave a Usar por la IA")

    class Config:
        from_attributes = True # o orm_mode = True en Pydantic v1


class OrganizationSettingsAIResponse(BaseModel):
    organization_id: UUID
    ai_brand_name: Optional[str] = None
    ai_brand_industry: Optional[str] = None
    ai_target_audience_description: Optional[str] = None
    ai_communication_tone: Optional[str] = None
    ai_brand_personality_tags: List[str] = [] 
    ai_keywords_to_use: List[str] = []      
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContentPreferencesUpdate(BaseModel):
    prefs_auto_hashtags_enabled: Optional[bool] = Field(None, title="Activar generación automática de hashtags")
    prefs_auto_hashtags_count: Optional[int] = Field(default=None, ge=0, le=15, title="Cantidad preferida de hashtags (0-15)" )
    prefs_auto_hashtags_strategy: Optional[str] = Field(None, title="Estrategia para hashtags", max_length=50)
    prefs_auto_emojis_enabled: Optional[bool] = Field(None, title="Activar generación automática de emojis")
    prefs_auto_emojis_style: Optional[str] = Field(None, title="Estilo de emojis preferido", max_length=50)

    class Config:
        from_attributes = True


class ContentPreferencesResponse(BaseModel):
    organization_id: UUID
    prefs_auto_hashtags_enabled: bool = True    
    prefs_auto_hashtags_count: int = 3          
    prefs_auto_hashtags_strategy: str = "mixtos" 
    prefs_auto_emojis_enabled: bool = True      
    prefs_auto_emojis_style: str = "sutil"      
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True