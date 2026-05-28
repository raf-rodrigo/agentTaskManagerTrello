from google.adk.agents.llm_agent import Agent
from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo

import os
import re

load_dotenv()

# CREDENCIAIS
API_KEY = os.getenv('TRELLO_API_KEY')
API_SECRET = os.getenv('TRELLO_API_SECRET')
TOKEN = os.getenv('TRELLO_TOKEN')

TZ = ZoneInfo("America/Sao_Paulo")
BOARD_NAME = "LLIEGE"


def get_temporal_context():
    now = datetime.now(TZ)
    return now.strftime('%Y-%m-%d %H:%M:%S')


def formatar_due_date(due_date):
    try:
        data = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        data = datetime.strptime(due_date, '%Y-%m-%d')

    data = data.replace(
        hour=23,
        minute=59,
        second=0,
        tzinfo=TZ
    )

    return data.isoformat()


def client_trello():
    return TrelloClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        token=TOKEN,
    )


def buscar_board(client, nome_board=BOARD_NAME):
    boards = client.list_boards()

    board = next(
        (b for b in boards if b.name.strip().upper() == nome_board.strip().upper()),
        None
    )

    if board is None:
        raise Exception(f"Board '{nome_board}' não encontrado. Boards disponíveis: {[b.name for b in boards]}")

    return board


def buscar_lista_por_nome(lists, nome):
    nome = nome.strip().upper()

    for lista in lists:
        if lista.name.strip().upper() == nome:
            return lista

    nomes_disponiveis = [lista.name for lista in lists]
    raise Exception(f"Lista '{nome}' não encontrada. Listas disponíveis: {nomes_disponiveis}")


def buscar_lista_por_nomes(lists, nomes):
    nomes_normalizados = [n.strip().upper() for n in nomes]

    for lista in lists:
        if lista.name.strip().upper() in nomes_normalizados:
            return lista

    nomes_disponiveis = [lista.name for lista in lists]
    raise Exception(f"Lista destino não encontrada. Esperado uma destas: {nomes}. Listas disponíveis: {nomes_disponiveis}")


def create_card(name_task: str, description_task: str, due_date: str) -> str:
    print("TOOL create_card FOI CHAMADA")

    try:
        client = client_trello()
        my_board = buscar_board(client)

        lists = my_board.list_lists()
        my_list = buscar_lista_por_nome(lists, nome="A FAZER")

        card = my_list.add_card(
            name=name_task,
            desc=description_task,
            due=formatar_due_date(due_date),
        )

        print("Card criado:", card.id)

        return f"Card criado com sucesso no Trello: {card.name}"

    except Exception as e:
        print("Erro ao criar card:", str(e))
        return f"Erro ao criar card no Trello: {str(e)}"


def listar_tarefas(status: str = "todas"):
    try:
        client = client_trello()
        my_board = buscar_board(client)

        lists = my_board.list_lists()
        status_normalizado = (status or "todas").strip().lower()

        if status_normalizado == 'todas':
            listas_filtradas = lists
        elif status_normalizado == 'a fazer':
            listas_filtradas = [l for l in lists if l.name.strip().upper() == 'A FAZER']
        elif status_normalizado == 'desenvolvimento':
            listas_filtradas = [l for l in lists if l.name.strip().upper() == 'DESENVOLVIMENTO']
        elif status_normalizado == 'validação lliège':
            listas_filtradas = [l for l in lists if l.name.strip().upper() == 'VALIDAÇÃO LLIÈGE']
        elif status_normalizado == 'validação hml':
            listas_filtradas = [l for l in lists if l.name.strip().upper() == 'VALIDAÇÃO HML']
        elif status_normalizado == 'aprovada deploy':
            listas_filtradas = [l for l in lists if l.name.strip().upper() == 'APROVADA DEPLOY']
        elif status_normalizado == 'cancelada':
            listas_filtradas = [l for l in lists if l.name.strip().upper() == 'CANCELADA']
        else:
            return "Status não reconhecido. Status disponíveis: Todas, A Fazer, Desenvolvimento, Validação LLiège, Validação HML, Aprovada Deploy, Cancelada."

        resultado = []

        for lista in listas_filtradas:
            cards = lista.list_cards()
            for card in cards:
                resultado.append(
                    {
                        'nome': card.name,
                        'descrição': getattr(card, "description", getattr(card, "desc", "")),
                        'vencimento': card.due,
                        'status': lista.name,
                        'due_date': card.due,
                    }
                )

        return resultado

    except Exception as e:
        return f"Erro ao listar tarefas: {str(e)}"


def calcular_tempo_comercial(inicio: datetime, fim: datetime):
    """
    Conta somente segunda a sexta, das 08:00 às 18:00.
    Observação: 13:00 não pausa, pois você informou 08 às 13 e 13 às 18.
    """
    if fim <= inicio:
        return timedelta(0)

    total = timedelta(0)
    dia_atual = inicio.date()

    while dia_atual <= fim.date():
        if dia_atual.weekday() < 5:
            inicio_expediente = datetime.combine(dia_atual, dt_time(8, 0), tzinfo=TZ)
            fim_expediente = datetime.combine(dia_atual, dt_time(18, 0), tzinfo=TZ)

            inicio_contagem = max(inicio, inicio_expediente)
            fim_contagem = min(fim, fim_expediente)

            if inicio_contagem < fim_contagem:
                total += fim_contagem - inicio_contagem

        dia_atual += timedelta(days=1)

    return total


def formatar_tempo(delta: timedelta):
    total_minutos = int(delta.total_seconds() // 60)
    horas = total_minutos // 60
    minutos = total_minutos % 60

    return f"{horas}h {minutos}min"


def obter_descricao_card(card):
    return getattr(card, "description", getattr(card, "desc", "")) or ""


def atualizar_descricao_card(card, descricao):
    if hasattr(card, "set_description"):
        card.set_description(descricao)
    else:
        card.set_desc(descricao)


def pegar_inicio_desenvolvimento(card):
    descricao = obter_descricao_card(card)

    match = re.search(r"\[INICIO_DESENVOLVIMENTO:(.*?)\]", descricao)

    if not match:
        return None

    try:
        return datetime.fromisoformat(match.group(1))
    except ValueError:
        return None


def salvar_inicio_desenvolvimento(card, data_inicio):
    descricao = obter_descricao_card(card)

    descricao = re.sub(
        r"\[INICIO_DESENVOLVIMENTO:.*?\]",
        "",
        descricao
    ).strip()

    nova_descricao = f"{descricao}\n\n[INICIO_DESENVOLVIMENTO:{data_inicio.isoformat()}]"

    atualizar_descricao_card(card, nova_descricao.strip())


def limpar_inicio_desenvolvimento(card):
    descricao = obter_descricao_card(card)

    nova_descricao = re.sub(
        r"\[INICIO_DESENVOLVIMENTO:.*?\]",
        "",
        descricao
    ).strip()

    atualizar_descricao_card(card, nova_descricao)


def adicionar_comentario(card, texto):
    if hasattr(card, "comment"):
        card.comment(texto)
    else:
        card.add_comment(texto)


def mudar_status_tarefa(nome_da_task: str, novo_status: str, observacao: str = ""):
    """
    Muda o card de lista/status.
    Quando entra em Desenvolvimento, salva o início da contagem.
    Quando sai de Desenvolvimento, calcula o tempo útil e comenta no card.
    """

    try:
        client = client_trello()
        my_board = buscar_board(client)
        lists = my_board.list_lists()

        status_map = {
            "a fazer": ["A FAZER", "TO DO"],
            "desenvolvimento": ["DESENVOLVIMENTO", "EM ANDAMENTO", "IN PROGRESS", "DOING"],
            "em andamento": ["DESENVOLVIMENTO", "EM ANDAMENTO", "IN PROGRESS", "DOING"],
            "validação lliège": ["VALIDAÇÃO LLIÈGE", "VALIDACAO LLIEGE"],
            "validação hml": ["VALIDAÇÃO HML", "VALIDACAO HML"],
            "aprovada deploy": ["APROVADA DEPLOY"],
            "concluída": ["APROVADA DEPLOY", "CONCLUÍDAS", "CONCLUIDAS", "DONE"],
            "concluídas": ["APROVADA DEPLOY", "CONCLUÍDAS", "CONCLUIDAS", "DONE"],
            "cancelada": ["CANCELADA"]
        }

        status_normalizado = novo_status.strip().lower()
        nomes_lista_destino = status_map.get(status_normalizado)

        if not nomes_lista_destino:
            return (
                "Status inválido. Use: A Fazer, Desenvolvimento, Validação LLiège, "
                "Validação HML, Aprovada Deploy ou Cancelada."
            )

        lista_destino = buscar_lista_por_nomes(lists, nomes_lista_destino)

        card_encontrado = None
        lista_origem = None

        for lista in lists:
            cards = lista.list_cards()
            card_encontrado = next(
                (c for c in cards if c.name.strip().lower() == nome_da_task.strip().lower()),
                None
            )

            if card_encontrado:
                lista_origem = lista
                break

        if not card_encontrado:
            return f"Tarefa '{nome_da_task}' não encontrada em nenhuma lista."

        data_agora = datetime.now(TZ)
        inicio_desenvolvimento = pegar_inicio_desenvolvimento(card_encontrado)

        destino_eh_desenvolvimento = lista_destino.name.strip().upper() == "DESENVOLVIMENTO"
        origem_eh_desenvolvimento = lista_origem.name.strip().upper() == "DESENVOLVIMENTO"

        if destino_eh_desenvolvimento:
            if not inicio_desenvolvimento:
                salvar_inicio_desenvolvimento(card_encontrado, data_agora)

            comentario = (
                f"Status alterado para '{lista_destino.name}'.\n"
                f"Início da contagem: {data_agora.strftime('%d/%m/%Y %H:%M')}."
            )

            if observacao:
                comentario += f"\n\nObservação: {observacao}"

            adicionar_comentario(card_encontrado, comentario)

        elif origem_eh_desenvolvimento and inicio_desenvolvimento:
            tempo_util = calcular_tempo_comercial(inicio_desenvolvimento, data_agora)
            tempo_formatado = formatar_tempo(tempo_util)

            comentario = (
                f"Status alterado para '{lista_destino.name}'.\n"
                f"Tempo útil em desenvolvimento: {tempo_formatado}.\n"
                f"Período: {inicio_desenvolvimento.strftime('%d/%m/%Y %H:%M')} "
                f"até {data_agora.strftime('%d/%m/%Y %H:%M')}."
            )

            if observacao:
                comentario += f"\n\nObservação: {observacao}"

            adicionar_comentario(card_encontrado, comentario)
            limpar_inicio_desenvolvimento(card_encontrado)

        else:
            comentario = f"Status alterado para '{lista_destino.name}'."

            if observacao:
                comentario += f"\n\nObservação: {observacao}"

            adicionar_comentario(card_encontrado, comentario)

        card_encontrado.change_list(lista_destino.id)

        return f"Tarefa '{nome_da_task}': '{lista_origem.name}' -> '{lista_destino.name}' com sucesso."

    except Exception as e:
        return f"Erro ao mudar status da tarefa: {str(e)}"


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='''
                Agente inteligente de gerenciamento de tarefas integrado ao Trello.
                Responsável por criar, listar, atualizar e acompanhar atividades diárias,
                controlando status das tarefas, tempo de execução em horário comercial
                e histórico de observações dos cards.
                ''',
    instruction="""
            Você é um agente de gerenciamento de atividades diárias para o usuário.
            Sua função é receber uma tarefa e criar card no Trello com o nome da tarefa e descrição.
            Você deve perguntar quais são as tarefas que serão feitas no dia atual e criar um card para cada tarefa.
            Quando o usuário informar uma tarefa do dia, você DEVE chamar obrigatoriamente a tool create_card.
            Nunca diga que criou o card se a tool create_card não retornar sucesso.
            Se a tool retornar erro, mostre o erro ao usuário.

            Fluxo de status:
            - Quando o usuário informar que irá começar uma tarefa, use a tool mudar_status_tarefa com novo_status='desenvolvimento'.
            - Quando a tarefa sair de desenvolvimento, use mudar_status_tarefa com o próximo status informado pelo usuário.
            - Ao sair de desenvolvimento, a tool calcula o tempo útil em horário comercial: segunda a sexta, das 08:00 às 18:00.
            - Quando o usuário informar observações do que foi realizado, passe o texto no parâmetro observacao.
            - Quando informado tarefa cancelada, use mudar_status_tarefa com novo_status='cancelada'.

            Suas atribuições:
            - Criar card no Trello com nome, descrição e vencimento;
            - Listar todas as tarefas ou filtrar por status;
            - Mudar tarefas de status no Trello;
            - Cronometrar tempo útil de execução quando a tarefa estiver em desenvolvimento;
            - Adicionar comentários no card com tempo útil e observações;
            - Gerar contexto temporal com get_temporal_context.
    """,
    tools=[
        get_temporal_context,
        create_card,
        listar_tarefas,
        mudar_status_tarefa
    ],
)