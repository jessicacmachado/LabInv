import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reagentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT,
            quantidade INTEGER,
            unidade TEXT,
            local TEXT,
            validade TEXT,
            status TEXT,
            observacoes TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def load_data():
    conn = get_connection()
    data = conn.execute(
        """
        SELECT id, nome, categoria, quantidade, unidade, local, validade, status, observacoes
        FROM reagentes
        ORDER BY nome ASC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in data]


def add_reagent(nome, categoria, quantidade, unidade, local, validade, status, observacoes):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO reagentes (nome, categoria, quantidade, unidade, local, validade, status, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (nome, categoria, quantidade, unidade, local, validade, status, observacoes),
    )
    conn.commit()
    conn.close()


def update_reagent(reagente_id, nome, categoria, quantidade, unidade, local, validade, status, observacoes):
    conn = get_connection()
    conn.execute(
        """
        UPDATE reagentes
        SET nome = ?, categoria = ?, quantidade = ?, unidade = ?, local = ?, validade = ?, status = ?, observacoes = ?
        WHERE id = ?
        """,
        (nome, categoria, quantidade, unidade, local, validade, status, observacoes, reagente_id),
    )
    conn.commit()
    conn.close()


def delete_reagent(reagente_id):
    conn = get_connection()
    conn.execute("DELETE FROM reagentes WHERE id = ?", (reagente_id,))
    conn.commit()
    conn.close()


def generate_summary(df):
    total_itens = int(df["quantidade"].sum()) if not df.empty else 0
    reagentes_baixo = int((df["quantidade"] <= 5).sum()) if not df.empty else 0
    categorias = df["categoria"].nunique() if not df.empty else 0
    return total_itens, reagentes_baixo, categorias


# Inicialização
init_db()

st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
st.title("LabInv - Inventário de Laboratório")
st.caption("Controle de reagentes e materiais de laboratório")

# Sidebar para cadastro e edição
with st.sidebar:
    st.header("Cadastrar reagente")
    with st.form("form_reagente", clear_on_submit=True):
        nome = st.text_input("Nome do reagente")
        categoria = st.selectbox(
            "Categoria",
            ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"],
        )
        quantidade = st.number_input("Quantidade", min_value=0, value=0, step=1)
        unidade = st.selectbox("Unidade", ["mL", "g", "mg", "L", "kg", "unidade"])
        local = st.text_input("Local de armazenamento")
        validade = st.date_input("Data de validade", min_value=datetime.now().date())
        status = st.selectbox("Status", ["Disponível", "Baixo", "Vencido", "Em uso"])
        observacoes = st.text_area("Observações")
        submitted = st.form_submit_button("Salvar")

        if submitted:
            if nome.strip():
                add_reagent(
                    nome.strip(),
                    categoria,
                    int(quantidade),
                    unidade,
                    local.strip(),
                    validade.isoformat(),
                    status,
                    observacoes.strip(),
                )
                st.success("Reagente cadastrado com sucesso!")
            else:
                st.warning("Informe o nome do reagente.")

# Filtros
raw_data = load_data()
df = pd.DataFrame(raw_data)

if not df.empty:
    st.sidebar.subheader("Filtros")
    categorias = ["Todos"] + sorted(df["categoria"].dropna().unique().tolist())
    categoria_filtro = st.sidebar.selectbox("Categoria", categorias)
    status_filtro = st.sidebar.selectbox(
        "Status",
        ["Todos", "Disponível", "Baixo", "Vencido", "Em uso"],
    )

    if categoria_filtro != "Todos":
        df = df[df["categoria"] == categoria_filtro]
    if status_filtro != "Todos":
        df = df[df["status"] == status_filtro]
else:
    df = pd.DataFrame(
        columns=["id", "nome", "categoria", "quantidade", "unidade", "local", "validade", "status", "observacoes"]
    )

# Resumo
col1, col2, col3 = st.columns(3)
resumo_total, resumo_baixo, resumo_categorias = generate_summary(df)

col1.metric("Total em estoque", resumo_total)
col2.metric("Itens em nível baixo", resumo_baixo)
col3.metric("Categorias", resumo_categorias)

# Tabela principal
if df.empty:
    st.info("Ainda não há reagentes cadastrados. Use o painel lateral para adicionar o primeiro item.")
else:
    st.subheader("Reagentes cadastrados")
    st.dataframe(
        df[["nome", "categoria", "quantidade", "unidade", "local", "validade", "status"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Ações")
    selected_id = st.selectbox(
        "Selecione o reagente para editar ou remover",
        options=[int(item["id"]) for item in load_data()],
        format_func=lambda x: next(
            item["nome"] for item in load_data() if int(item["id"]) == x
        ),
    )

    item = next((row for row in load_data() if int(row["id"]) == selected_id), None)
    if item:
        with st.form("edit_reagente"):
            st.write(f"Editando: {item['nome']}")
            nome_edit = st.text_input("Nome", value=item["nome"])
            categoria_edit = st.selectbox(
                "Categoria",
                ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"],
                index=["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"].index(item["categoria"] or "Outro"),
            )
            quantidade_edit = st.number_input("Quantidade", min_value=0, value=int(item["quantidade"] or 0), step=1)
            unidade_edit = st.selectbox("Unidade", ["mL", "g", "mg", "L", "kg", "unidade"], index=["mL", "g", "mg", "L", "kg", "unidade"].index(item["unidade"] or "unidade"))
            local_edit = st.text_input("Local", value=item["local"] or "")
            validade_edit = st.date_input("Validade", value=datetime.strptime(item["validade"], "%Y-%m-%d").date() if item.get("validade") else datetime.now().date())
            status_edit = st.selectbox("Status", ["Disponível", "Baixo", "Vencido", "Em uso"], index=["Disponível", "Baixo", "Vencido", "Em uso"].index(item["status"] or "Disponível"))
            observacoes_edit = st.text_area("Observações", value=item["observacoes"] or "")

            col_edit, col_delete = st.columns([1, 1])
            update_btn = col_edit.form_submit_button("Salvar alterações")
            delete_btn = col_delete.form_submit_button("Excluir")

            if update_btn:
                update_reagent(
                    selected_id,
                    nome_edit.strip(),
                    categoria_edit,
                    int(quantidade_edit),
                    unidade_edit,
                    local_edit.strip(),
                    validade_edit.isoformat(),
                    status_edit,
                    observacoes_edit.strip(),
                )
                st.success("Reagente atualizado com sucesso!")
                st.rerun()

            if delete_btn:
                delete_reagent(selected_id)
                st.success("Reagente removido com sucesso!")
                st.rerun()
