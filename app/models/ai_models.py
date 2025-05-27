# app/models/ai_models.py
from pydantic import BaseModel
from typing import List, Optional

class ContentIdeaResponse(BaseModel):
    titles: List[str]

# Podrías añadir más modelos aquí a medida que los necesites, por ejemplo:
# class GeneratedTitleResponse(BaseModel):
#     titles: List[str]

# class GeneratedPostTextResponse(BaseModel):
#     text_variations: List[str]

# class AIRequestParams(BaseModel): # Para peticiones más complejas desde el FE
#     main_idea: Optional[str] = None
#     # ... otros ...