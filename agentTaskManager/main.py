from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from google.adk.runners import InMemoryRunner
from google.genai import types
import logging
import uuid
import os

from agentTaskManager.agent import root_agent

app = FastAPI()

templates = Jinja2Templates(directory="agentTaskManager/templates")
logger = logging.getLogger(__name__)
runner = InMemoryRunner(agent=root_agent)

security = HTTPBasic()

def verificar_credenciais(credentials: HTTPBasicCredentials = Depends(security)):
    user_esperado = os.getenv("AGENT_USER", "admin")
    pass_esperada = os.getenv("AGENT_PASSWORD")
    
    # Se a senha não estiver configurada no ambiente (ex: desenvolvimento local), libera o acesso
    if not pass_esperada:
        return credentials.username
        
    if credentials.username == user_esperado and credentials.password == pass_esperada:
        return credentials.username
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acesso negado. Usuário ou senha incorretos.",
        headers={"WWW-Authenticate": "Basic"},
    )

AGENT_DISPLAY_NAME = "Agente principal"
AGENT_DESCRIPTION = getattr(root_agent, "description", "")


def formatar_resposta(resultado):
    for atributo in ("text", "output_text", "content", "message", "response"):
        valor = getattr(resultado, atributo, None)
        if valor:
            return str(valor)

    if isinstance(resultado, dict):
        for chave in ("text", "output_text", "content", "message", "response"):
            valor = resultado.get(chave)
            if valor:
                return str(valor)

    return str(resultado)


class ChatRequest(BaseModel):
    mensagem: str
    session_id: str | None = None


@app.get("/")
def home(request: Request, username: str = Depends(verificar_credenciais)):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "agent_name": AGENT_DISPLAY_NAME,
            "agent_description": AGENT_DESCRIPTION,
        }
    )


def extrair_texto_evento(evento):
    if not evento or not evento.message or not evento.message.parts:
        return ""

    partes_texto = [parte.text for parte in evento.message.parts if getattr(parte, "text", None)]
    return "\n".join(partes_texto).strip()


@app.post("/chat")
async def chat(data: ChatRequest, username: str = Depends(verificar_credenciais)):
    try:
        session_id = data.session_id or str(uuid.uuid4())
        mensagem = types.Content(parts=[types.Part(text=data.mensagem)])
        resposta_final = ""

        async for event in runner.run_async(
            user_id="web-user",
            session_id=session_id,
            new_message=mensagem,
        ):
            if event.is_final_response():
                texto_evento = extrair_texto_evento(event)
                if texto_evento:
                    resposta_final = texto_evento

        return {
            "resposta": resposta_final or "Sem resposta do agente.",
            "agent": AGENT_DISPLAY_NAME,
            "session_id": session_id,
        }
    except Exception as exc:
        logger.exception("Erro ao processar mensagem do chat")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Erro ao processar a solicitação do agente.",
                "error": str(exc),
                "agent": AGENT_DISPLAY_NAME,
            },
        )