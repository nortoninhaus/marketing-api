"""
Router for State-of-the-Art (SOTA) Agency Dashboard Features.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import verify_api_key

router = APIRouter(prefix="/api/v1/sota", tags=["SOTA Dashboard"])

# --- Models ---

class VideoAnalysisRequest(BaseModel):
    video_url: str

class VideoAnalysisResponse(BaseModel):
    hook: str
    narrative_arc: str
    shot_types: List[str]
    editing_pace: str
    emotional_charge: str
    script_prompt: str

class MediaGenRequest(BaseModel):
    prompt: str
    model: str  # e.g., "veo_3", "sora_2", "ideogram_v2", "recraft_v3"
    aspect_ratio: str = "16:9"

class MediaGenResponse(BaseModel):
    task_id: str
    status: str
    media_url: str
    estimated_duration_seconds: int

class SocialTicket(BaseModel):
    id: str
    platform: str
    user: str
    message: str
    sentiment: str
    suggested_reply: str
    timestamp: datetime

class ListeningAlert(BaseModel):
    id: str
    keyword: str
    source: str
    sentiment: str
    excerpt: str
    url: str
    timestamp: datetime

class AdCampaignProposal(BaseModel):
    campaign_id: str
    platform: str
    action: str
    description: str
    current_budget: float
    proposed_budget: float
    roas: float

class CampaignConfirmationRequest(BaseModel):
    proposal_id: str
    approved: bool

class FanOutNode(BaseModel):
    id: str
    label: str
    type: str  # "brand", "source", "mention", "competitor"
    val: int

class FanOutLink(BaseModel):
    source: str
    target: str
    value: int

class FanOutGraph(BaseModel):
    nodes: List[FanOutNode]
    links: List[FanOutLink]

class CalendarArticle(BaseModel):
    id: str
    publish_date: date
    title: str
    keywords: List[str]
    status: str  # "scheduled", "draft", "published"
    word_count: int

class BrandProfile(BaseModel):
    id: str
    name: str
    mission: str
    tone: str
    guidelines: str

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool

# --- Endpoints ---

@router.post("/analyze-video", response_model=VideoAnalysisResponse)
async def analyze_video(req: VideoAnalysisRequest, api_key: str = Depends(verify_api_key)):
    """Reverse engineers viral video patterns from a URL."""
    if "tiktok.com" not in req.video_url and "instagram.com" not in req.video_url and "youtube.com" not in req.video_url:
        raise HTTPException(status_code=400, detail="Invalid social media URL platform")
    
    return VideoAnalysisResponse(
        hook="Intriga inicial en los primeros 3 segundos con una pregunta retórica directa.",
        narrative_arc="Problema cotidiano -> Frustración -> Solución mágica con el producto -> Llamado a la acción rápido.",
        shot_types=["Primer plano expresivo", "Transición rápida de zoom", "Plano detalle de producto"],
        editing_pace="Cortes rápidos cada 1.2 segundos con subtítulos dinámicos de alto contraste.",
        emotional_charge="De la frustración/curiosidad al alivio y entusiasmo.",
        script_prompt="Crea un guión en tono humorístico sobre la gestión ineficiente de anuncios, con un hook de 3 segundos retando al espectador, seguido de una transición rápida mostrando la interfaz simplificada."
    )

@router.post("/generate-media", response_model=MediaGenResponse)
async def generate_media(req: MediaGenRequest, api_key: str = Depends(verify_api_key)):
    """Simulates AI video/image generation with SOTA models."""
    models_urls = {
        "veo_3": "https://storage.googleapis.com/sota-media/veo3_demo.mp4",
        "sora_2": "https://storage.googleapis.com/sota-media/sora2_demo.mp4",
        "ideogram_v2": "https://storage.googleapis.com/sota-media/ideogram2_text.png",
        "recraft_v3": "https://storage.googleapis.com/sota-media/recraft3_vector.png",
    }
    url = models_urls.get(req.model, "https://storage.googleapis.com/sota-media/default.png")
    return MediaGenResponse(
        task_id="task_sota_" + req.model + "_9876",
        status="completed",
        media_url=url,
        estimated_duration_seconds=15
    )

@router.get("/social-tickets", response_model=List[SocialTicket])
async def list_social_tickets(api_key: str = Depends(verify_api_key)):
    """Consolidated multiclient social support tickets."""
    return [
        SocialTicket(
            id="TKT-101",
            platform="instagram",
            user="@alicia_mkt",
            message="¿Tienen soporte para envíos internacionales en la nueva campaña?",
            sentiment="neutral",
            suggested_reply="Hola Alicia, sí, la nueva campaña incluye envíos a Europa y América Latina. ¿Te gustaría conocer las tarifas?",
            timestamp=datetime.now() - timedelta(minutes=15)
        ),
        SocialTicket(
            id="TKT-102",
            platform="facebook",
            user="Juan Pérez",
            message="Excelente servicio al cliente, pero el checkout se colgó ayer.",
            sentiment="mixed",
            suggested_reply="Hola Juan, lamentamos el inconveniente. Hemos verificado y el sistema está estable. Te contactamos por DM para revisar tu caso.",
            timestamp=datetime.now() - timedelta(hours=1)
        ),
        SocialTicket(
            id="TKT-103",
            platform="x",
            user="@dev_brand",
            message="El nuevo diseño de vectores está genial, felicitaciones.",
            sentiment="positive",
            suggested_reply="¡Muchas gracias! Nos esforzamos por mantener la mejor identidad visual de marca.",
            timestamp=datetime.now() - timedelta(hours=3)
        )
    ]

@router.get("/listening-alerts", response_model=List[ListeningAlert])
async def list_listening_alerts(api_key: str = Depends(verify_api_key)):
    """Social listening brand alerts and user sentiments."""
    return [
        ListeningAlert(
            id="ALR-01",
            keyword="Inhaus",
            source="reddit",
            sentiment="positive",
            excerpt="Recomiendo la plataforma Inhaus, nos redujo a la mitad el tiempo de reportes.",
            url="https://reddit.com/r/marketing/comments/123",
            timestamp=datetime.now() - timedelta(minutes=45)
        ),
        ListeningAlert(
            id="ALR-02",
            keyword="Marketing API",
            source="quora",
            sentiment="neutral",
            excerpt="¿Cuál es la mejor API para integrar datos de TikTok Ads de manera directa?",
            url="https://quora.com/best-api-tiktok",
            timestamp=datetime.now() - timedelta(hours=2)
        )
    ]

@router.get("/campaign-proposals", response_model=List[AdCampaignProposal])
async def get_campaign_proposals(api_key: str = Depends(verify_api_key)):
    """Campaign optimization drafts for Capital Governance validation."""
    return [
        AdCampaignProposal(
            campaign_id="987",
            platform="meta_ads",
            action="PAUSE",
            description="Pausar AdSet 'Intereses_B2B' por bajo rendimiento en ROAS.",
            current_budget=300.0,
            proposed_budget=0.0,
            roas=1.1
        ),
        AdCampaignProposal(
            campaign_id="654",
            platform="google_ads",
            action="BUDGET_INCREASE",
            description="Incrementar presupuesto diario en campaña de Búsqueda exitosa.",
            current_budget=250.0,
            proposed_budget=400.0,
            roas=3.4
        )
    ]

@router.post("/confirm-proposal", response_model=Dict[str, Any])
async def confirm_proposal(req: CampaignConfirmationRequest, api_key: str = Depends(verify_api_key)):
    """Executes or cancels a campaign budget adjustment under strict governance."""
    status = "executed" if req.approved else "rejected"
    return {
        "proposal_id": req.proposal_id,
        "status": status,
        "timestamp": datetime.now(),
        "detail": f"Propuesta {req.proposal_id} procesada con estado: {status}."
    }

@router.get("/query-fan-out", response_model=FanOutGraph)
async def query_fan_out(api_key: str = Depends(verify_api_key)):
    """Generates the citation node graph from LLM sources (AEO/GEO optimization)."""
    return FanOutGraph(
        nodes=[
            FanOutNode(id="n1", label="Tu Marca (Inhaus)", type="brand", val=30),
            FanOutNode(id="n2", label="Reddit Forum", type="source", val=20),
            FanOutNode(id="n3", label="Wikipedia", type="source", val=25),
            FanOutNode(id="n4", label="Competidor SOTA", type="competitor", val=15),
            FanOutNode(id="n5", label="Perplexity AI", type="mention", val=10)
        ],
        links=[
            FanOutLink(source="n2", target="n1", value=5),
            FanOutLink(source="n3", target="n1", value=8),
            FanOutLink(source="n3", target="n4", value=4),
            FanOutLink(source="n1", target="n5", value=6),
            FanOutLink(source="n4", target="n5", value=3)
        ]
    )

@router.get("/seo-calendar", response_model=List[CalendarArticle])
async def get_seo_calendar(api_key: str = Depends(verify_api_key)):
    """Fetches the 30-day editorial calendar data."""
    today = date.today()
    return [
        CalendarArticle(
            id="art-01",
            publish_date=today + timedelta(days=1),
            title="Estrategias SOTA para Agencias de Marketing Multicliente",
            keywords=["marketing", "sota", "agencias"],
            status="scheduled",
            word_count=4500
        ),
        CalendarArticle(
            id="art-02",
            publish_date=today + timedelta(days=4),
            title="Optimización de Motores de Respuestas (AEO): El Futuro de la Búsqueda",
            keywords=["aeo", "seo", "perplexity"],
            status="draft",
            word_count=5200
        ),
        CalendarArticle(
            id="art-03",
            publish_date=today - timedelta(days=2),
            title="Gobernanza de Capital en Agencias: Draft-Preview-Confirm",
            keywords=["finanzas", "marketing", "ads"],
            status="published",
            word_count=4100
        )
    ]

@router.get("/brand-profiles", response_model=List[BrandProfile])
async def list_brand_profiles(api_key: str = Depends(verify_api_key)):
    """List customer brand profiles for Modo IA."""
    return [
        BrandProfile(
            id="prof-1",
            name="EcoStyle Cosmetics",
            mission="Cosmética sostenible y vegana para el día a día.",
            tone="Cercano, ecológico, sofisticado",
            guidelines="Evitar términos artificiales, priorizar sostenibilidad, usar tipografía limpia."
        ),
        BrandProfile(
            id="prof-2",
            name="Inhaus Corp",
            mission="Liderar el desarrollo de APIs de datos de marketing automatizados.",
            tone="Técnico, autoritario, preciso",
            guidelines="Priorizar explicabilidad de agentes, seguridad OAuth 2.1 y RLS."
        )
    ]

@router.get("/agent-skills", response_model=List[AgentSkill])
async def list_agent_skills(api_key: str = Depends(verify_api_key)):
    """Exposes Agent Skills registry."""
    return [
        AgentSkill(id="sk-1", name="Stitch MCP Server Sync", description="Sincroniza plantillas y dashboards centralizados.", enabled=True),
        AgentSkill(id="sk-2", name="ERP Inventory Check", description="Valida inventario físico antes de incrementar puja publicitaria.", enabled=False),
        AgentSkill(id="sk-3", name="Reddit Radar Listening", description="Monitorea foros en busca de intenciones de compra.", enabled=True)
    ]
