from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agentTaskManager.agent import root_agent

app = FastAPI()

templates = Jinja2Templates(directory="agentTaskManager/templates")


class ChatRequest(BaseModel):
    mensagem: str


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.post("/chat")
def chat(data: ChatRequest):
    resposta = root_agent.run(data.mensagem)

    return {
        "resposta": str(resposta)
    }