from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import logging

from agentTaskManager.agent import root_agent

app = FastAPI()

templates = Jinja2Templates(directory="agentTaskManager/templates")
logger = logging.getLogger(__name__)

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


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "agent_name": AGENT_DISPLAY_NAME,
            "agent_description": AGENT_DESCRIPTION,
        }
    )


@app.post("/chat")
def chat(data: ChatRequest):
    try:
        resposta = root_agent.run(data.mensagem)

        return {
            "resposta": formatar_resposta(resposta),
            "agent": AGENT_DISPLAY_NAME,
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