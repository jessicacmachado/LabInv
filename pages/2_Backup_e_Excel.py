# Página extra do Streamlit: backup e exportação anual
# Este arquivo aparece automaticamente como uma nova página porque está na pasta `pages/`.

# BLOCO 1 — Bibliotecas e configurações
# sqlite3 conversa com o banco SQLite; pandas organiza as tabelas; openpyxl grava Excel.
import io
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# O app.py existente abre labinv.db a partir da pasta principal do projeto.
DB_PATH = Path.cwd() / "labinv.db"
# Este destino é uma pasta no computador/servidor onde o Streamlit está executando.
# Não significa que seja uma pasta do computador do visitante.
BACKUP_ROOT = Path.home() / "LabInv_Backups"
# Limite de retenção: manter no máximo 12 backups automáticos por ano (um por mês).
MAX_BACKUPS_PER_YEAR = 12


# BLOCO 2 — Função que lê as tabelas do banco
# SELECT * significa: buscar todas as colunas da tabela indicada.
def ler_tabela(nome_tabela):
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conexao:
        return pd.read_sql_query(f"SELECT * FROM {nome_tabela}", conexao)


# BLOCO 3 — Cria uma cópia consistente do arquivo SQLite
# O método backup() do SQLite copia o banco de forma segura, mesmo que esteja aberto.
def copiar_banco(destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as origem:
        with sqlite3.connect(destino) as copia:
            origem.backup(copia)


# BLOCO 4 — Backup automático mensal, limitado a 12 por ano
# Ele é verificado quando esta página abre. Não é um agendador que roda se o app estiver desligado.
def backup_mensal():
    agora = datetime.now()
    pasta_ano = BACKUP_ROOT / str(agora.year)
    pasta_ano.mkdir(parents=True, exist_ok=True)
    backups = sorted(pasta_ano.glob("labinv_backup_*.db"))

    # Se já existe uma cópia deste mês, não cria outra automaticamente.
    backup_deste_mes = any(
        arquivo.name.startswith(f"labinv_backup_{agora.year}{agora.month:02d}")
        for arquivo in backups
    )
    if not backup_deste_mes:
        nome = f"labinv_backup_{agora:%Y%m%d_%H%M%S}.db"
        copiar_banco(pasta_ano / nome)

    # Apaga apenas os backups mais antigos que excedam o limite anual configurado.
    backups = sorted(pasta_ano.glob("labinv_backup_*.db"))
    for arquivo_antigo in backups[:-MAX_BACKUPS_PER_YEAR]:
        arquivo_antigo.unlink(missing_ok=True)


# BLOCO 5 — Gera uma planilha Excel com inventário e histórico do ano escolhido
# A planilha baixada é uma fotografia dos dados naquele instante; não se atualiza depois do download.
def gerar_excel(ano):
    reagentes = ler_tabela("reagentes")
    historico = ler_tabela("historico")

    if not historico.empty and "data_hora" in historico.columns:
        datas = pd.to_datetime(historico["data_hora"], errors="coerce", utc=True)
        historico = historico.loc[datas.dt.year == ano].copy()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        reagentes.to_excel(escritor, index=False, sheet_name="Reagentes")
        historico.to_excel(escritor, index=False, sheet_name=f"Histórico {ano}")
    buffer.seek(0)
    return buffer.getvalue()


# BLOCO 6 — Interface da página
st.set_page_config(page_title="Backup e Excel | LabInv", page_icon="💾", layout="wide")
st.title("💾 Backup e exportação de registros")
st.caption("Baixe uma cópia dos registros ou consulte os dados em uma planilha Excel.")

# AVISO IMPORTANTE: em hospedagens na nuvem, o servidor pode apagar arquivos locais temporários.
st.warning(
    "A pasta de backup abaixo fica no computador/servidor que executa o aplicativo. "
    "Ela pode ser temporária e não é automaticamente a nuvem ou o pendrive do usuário. "
    "Baixe os arquivos e salve-os no seu computador, em um pendrive ou em uma pasta "
    "sincronizada com a nuvem."
)

if not DB_PATH.exists():
    st.error(f"Não encontrei o banco de dados em {DB_PATH}. Abra o aplicativo a partir da pasta do projeto.")
    st.stop()

# Cria no máximo uma cópia automática por mês, desde que esta página seja aberta nesse mês.
try:
    backup_mensal()
    st.success("Verificação mensal de backup concluída. A pasta mantém até 12 cópias por ano.")
except (OSError, sqlite3.Error) as erro:
    st.error(f"Não foi possível criar o backup automático neste servidor: {erro}")

# BLOCO 7 — Botão para baixar o banco SQLite original
# O usuário escolhe onde salvar o download no próprio navegador.
st.subheader("1. Baixar backup do banco")
try:
    with sqlite3.connect(DB_PATH) as origem:
        buffer_db = io.BytesIO()
        with sqlite3.connect(":memory:") as copia:
            origem.backup(copia)
            # Exporta a cópia em memória para um arquivo SQLite baixável.
            conteudo_db = copia.serialize()
    st.download_button(
        "⬇️ Baixar cópia do banco (.db)",
        data=conteudo_db,
        file_name=f"labinv_backup_{datetime.now():%Y%m%d_%H%M%S}.db",
        mime="application/x-sqlite3",
        help="Depois do download, mova o arquivo para um pendrive ou pasta de nuvem.",
    )
except (OSError, sqlite3.Error) as erro:
    st.error(f"Não foi possível preparar o arquivo do banco para download: {erro}")

# BLOCO 8 — Planilha anual com os reagentes atuais e movimentações daquele ano
st.subheader("2. Baixar planilha Excel")
ano_atual = datetime.now().year
anos_disponiveis = list(range(ano_atual, ano_atual - 10, -1))
ano_escolhido = st.selectbox("Ano do histórico", anos_disponiveis)
try:
    conteudo_excel = gerar_excel(ano_escolhido)
    st.download_button(
        f"📊 Baixar Excel de {ano_escolhido}",
        data=conteudo_excel,
        file_name=f"labinv_registros_{ano_escolhido}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="A planilha contém o inventário atual e o histórico do ano selecionado.",
    )
except (OSError, sqlite3.Error, ValueError) as erro:
    st.error(f"Não foi possível gerar a planilha: {erro}")

st.info(
    "A planilha é gerada quando você clica para baixar e não se atualiza sozinha depois. "
    "Para ter os dados mais recentes, faça um novo download."
)
