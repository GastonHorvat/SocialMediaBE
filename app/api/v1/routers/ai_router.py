# app/api/v1/routers/ai_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any 
from uuid import UUID

from app.db.supabase_client import get_supabase_client, Client as SupabaseClient
from app.api.v1.dependencies.auth import get_current_user, TokenData
from app.models.ai_models import ContentIdeaResponse
from app.services.ai_content_generator import (
    build_prompt_for_ideas,
    generate_text_with_gemini,
    parse_gemini_idea_titles
)
# from app.core.config import settings # No se usa directamente aquí si Gemini se inicializa en startup

# Asumiendo supabase-py >= 2.0, que usa postgrest-py
from postgrest.exceptions import APIError # Necesaria si get_organization_settings la usara, pero no lo hace directamente


router = APIRouter()

async def get_organization_settings(
    organization_id: UUID,
    supabase: SupabaseClient
) -> Dict[str, Any]:
    """Función helper para obtener y validar organization_settings."""
    # La verificación de si organization_id es None se hace ahora en el endpoint llamador.
    
    response = supabase.table("organization_settings").select("*").eq("organization_id", str(organization_id)).maybe_single().execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron configuraciones de organización para la ID: {organization_id}. Por favor, completa la configuración de IA de tu organización."
        )
            
    return response.data


@router.post(
    "/content-ideas",
    response_model=ContentIdeaResponse,
    summary="Generar Ideas de Contenido con IA",
    description="Genera 3 títulos para ideas de contenido basadas en la configuración de la organización.",
    tags=["AI Content Generation"]
)
async def generate_content_ideas(
    current_user: TokenData = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Usuario no asociado a una organización activa para generar ideas."
        )

    try:
        org_settings = await get_organization_settings(current_user.organization_id, supabase)
    except APIError as e: # Si get_organization_settings tuviera un problema con la librería PostgREST
        print(f"ERROR_AI_ROUTER: APIError al obtener organization_settings: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Error al contactar la base de datos para configuraciones.")


    if not org_settings.get('ai_brand_name') or not org_settings.get('ai_brand_industry'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La configuración de la organización debe incluir al menos 'Nombre de la marca (ai_brand_name)' e 'Industria (ai_brand_industry)' para generar ideas."
        )

    prompt = build_prompt_for_ideas(org_settings)
    
    try:
        gemini_response_text = await generate_text_with_gemini(prompt)
    except RuntimeError as e: # Captura el error específico de generate_text_with_gemini
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e: # Captura general por si acaso
        print(f"ERROR_AI_ROUTER: Excepción inesperada llamando a Gemini: {type(e).__name__} - {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error inesperado al generar contenido con IA.")

    idea_titles = parse_gemini_idea_titles(gemini_response_text)

    if not idea_titles:
        print(f"WARN_AI_ROUTER: Gemini no devolvió los títulos esperados o el parseo falló. Respuesta cruda: '{gemini_response_text}'")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La IA no pudo generar ideas de contenido en este momento o la respuesta fue inválida."
        )
        
    return ContentIdeaResponse(titles=idea_titles)