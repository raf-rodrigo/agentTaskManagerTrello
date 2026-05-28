from fastapi import FastAPI
from pydantic import BaseModel

from agentTaskManager.agent import root_agent

app = FastAPI()


class ChatRequest(BaseModel):
    mensagem: str


@app.get("/")
def home():
    return {"status": "online"}


@app.post("/chat")
def chat(data: ChatRequest):

    resposta = root_agent.run(data.mensagem)

    return {
        "resposta": str(resposta)
    }