from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agentTaskManager.agent import root_agent

app = FastAPI()

templates = Jinja2Templates(directory="agentTaskManager/templates")

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
    resposta = root_agent.run(data.mensagem)

    return {
        "resposta": formatar_resposta(resposta),
        "agent": AGENT_DISPLAY_NAME,
    }