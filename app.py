import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"
CATEGORIAS = ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"]
UNIDADES = ["mL", "g", "mg", "L", "kg", "unidade"]
STATUS = ["Disponível", "Baixo", "Vencido", "Em uso"]

# Lista original dos 30 reagentes do projeto.
REAGENTES_INICIAIS = [
    ("Ácido Clorídrico (HCl)", "Ácido"),
    ("Ácido Sulfúrico (H2SO4)", "Ácido"),
    ("Ácido Nítrico (HNO3)", "Ácido"),
    ("Ácido Acético (CH3COOH)", "Ácido"),
    ("Hidróxido de Sódio (NaOH)", "Base"),
    ("Hidróxido de Amônio (NH4OH)", "Base"),
    ("Hidróxido de Cálcio (Ca(OH)2)", "Base"),
    ("Bicarbonato de Sódio (NaHCO3)", "Sal"),
    ("Cloreto de Sódio (NaCl)", "Sal"),
    ("Sulfato de Cobre II (CuSO4)", "Sal"),
    ("Nitrato de Prata (AgNO3)", "Sal"),
    ("Cloreto de Bário (BaCl2)", "Sal"),
    ("Carbonato de Sódio (Na2CO3)", "Sal"),
    ("Permanganato de Potássio (KMnO4)", "Sal"),
    ("Iodeto de Potássio (KI)", "Sal"),
    ("Cromato de Potássio (K2CrO4)", "Sal"),
    ("Água Destilada/Deionizada (H2O)", "Outro"),
    ("Álcool Etílico/Etanol (C2H5OH)", "Solvente"),
    ("Acetona (CH3COCH3)", "Solvente"),
    ("Hexano (C6H14)", "Solvente"),
    ("Fenolftaleína", "Indicador"),
    ("Metiloranje (Alaranjado de Metila)", "Indicador"),
    ("Azul de Bromotimol", "Indicador"),
    ("Solução de Amido", "Outro"),
    ("Peróxido de Hidrogênio (H2O2)", "Outro"),
    ("Glicerina/Glicerol", "Outro"),
    ("Ácido Ascórbico", "Ácido"),
    ("Sulfato de Magnésio (MgSO4) Anidro", "Sal"),
    ("Glicose (C6H12O6)", "Outro"),
    ("Nitrato de Amônio (NH4NO3)", "Sal"),
]


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reagentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT,
                quantidade REAL,
                unidade TEXT,
                local TEXT,
                validade TEXT,
                status TEXT,
                observacoes TEXT
            )
            """
        )
        # Carrega os 30 reagentes uma única vez, sem duplicá-los em cada visita.
        total = conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0]
        if total == 0:
            conn.executemany(
                """
                INSERT INTO reagentes
                    (nome, categoria, quantidade, unidade, local, validade, status, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (nome, categoria, 2, "unidade", "", "", "Disponível", "Reagente da lista inicial")
                    for nome, categoria in REAGENTES_INICIAIS
                ],
            )


def load_data():
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, nome, categoria, quantidade, unidade, local, validade, status, observacoes
               FROM reagentes ORDER BY nome COLLATE NOCASE"""
        ).fetchall()
    return [dict(row) for row in rows]


def add_reagent(nome, categoria, quantidade, unidade, local, validade, status, observacoes):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO reagentes
               (nome, categoria, quantidade, unidade, local, validade, status, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, categoria, quantidade, unidade, local, validade, status, observacoes),
        )


def update_reagent(reagent_id, nome, categoria, quantidade, unidade, local, validade, status, observacoes):
    with get_connection() as conn:
        conn.execute(
            """UPDATE reagentes
               SET nome=?, categoria=?, quantidade=?, unidade=?, local=?, validade=?, status=?, observacoes=?
               WHERE id=?""",
            (nome, categoria, quantidade, unidade, local, validade, status, observacoes, reagent_id),
        )


def delete_reagent(reagent_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM reagentes WHERE id=?", (reagent_id,))


init_db()
st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
st.title("LabInv — Inventário de Laboratório")
st.caption("Controle de estoque de reagentes químicos")

with st.sidebar:
    st.header("Cadastrar reagente")
    with st.form("form_reagente", clear_on_submit=True):
        nome = st.text_input("Nome do reagente")
        categoria = st.selectbox("Categoria", CATEGORIAS)
        quantidade = st.number_input("Quantidade", min_value=0.0, value=0.0, step=1.0)
        unidade = st.selectbox("Unidade", UNIDADES)
        local = st.text_input("Local de armazenamento")
        validade = st.date_input("Data de validade", value=None)
        status = st.selectbox("Status", STATUS)
        observacoes = st.text_area("Observações")
        if st.form_submit_button("Cadastrar"):
            if nome.strip():
                add_reagent(nome.strip(), categoria, quantidade, unidade, local.strip(),
                            validade.isoformat() if validade else "", status, observacoes.strip())
                st.success("Reagente cadastrado!")
                st.rerun()
            else:
                st.warning("Informe o nome do reagente.")

all_data = load_data()
df = pd.DataFrame(all_data)
st.subheader("Lista inicial de 30 reagentes e estoque")

with st.sidebar:
    st.subheader("Filtros")
    if not df.empty:
        categorias_disponiveis = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
        categoria_filtro = st.selectbox("Categoria", categorias_disponiveis)
        busca = st.text_input("Buscar pelo nome")
    else:
        categoria_filtro, busca = "Todas", ""

visiveis = df.copy()
if not visiveis.empty:
    if categoria_filtro != "Todas":
        visiveis = visiveis[visiveis["categoria"] == categoria_filtro]
    if busca.strip():
        visiveis = visiveis[visiveis["nome"].str.contains(busca.strip(), case=False, na=False)]

m1, m2, m3 = st.columns(3)
m1.metric("Reagentes cadastrados", len(df))
m2.metric("Quantidade total", float(df["quantidade"].sum()) if not df.empty else 0)
m3.metric("Categorias", int(df["categoria"].nunique()) if not df.empty else 0)

if visiveis.empty:
    st.info("Nenhum reagente encontrado.")
else:
    st.dataframe(
        visiveis[["nome", "categoria", "quantidade", "unidade", "local", "validade", "status"]],
        use_container_width=True,
        hide_index=True,
    )

if all_data:
    st.subheader("Atualizar quantidade, editar ou excluir")
    items_by_id = {int(item["id"]): item for item in all_data}
    selected_id = st.selectbox("Reagente", list(items_by_id),
                               format_func=lambda reagent_id: items_by_id[reagent_id]["nome"])
    item = items_by_id[selected_id]
    with st.form("editar_reagente"):
        nome_edit = st.text_input("Nome", value=item["nome"])
        categoria_edit = st.selectbox("Categoria", CATEGORIAS,
                                      index=CATEGORIAS.index(item["categoria"] if item["categoria"] in CATEGORIAS else "Outro"))
        quantidade_edit = st.number_input("Quantidade", min_value=0.0,
                                          value=float(item["quantidade"] or 0), step=1.0)
        unidade_edit = st.selectbox("Unidade", UNIDADES,
                                    index=UNIDADES.index(item["unidade"] if item["unidade"] in UNIDADES else "unidade"))
        local_edit = st.text_input("Local", value=item["local"] or "")
        try:
            validade_atual = date.fromisoformat(item["validade"]) if item["validade"] else None
        except ValueError:
            validade_atual = None
        validade_edit = st.date_input("Validade", value=validade_atual)
        status_edit = st.selectbox("Status", STATUS,
                                   index=STATUS.index(item["status"] if item["status"] in STATUS else "Disponível"))
        observacoes_edit = st.text_area("Observações", value=item["observacoes"] or "")
        salvar, excluir = st.columns(2)
        salvar_btn = salvar.form_submit_button("Salvar alterações")
        excluir_btn = excluir.form_submit_button("Excluir")
        if salvar_btn:
            if nome_edit.strip():
                update_reagent(selected_id, nome_edit.strip(), categoria_edit, quantidade_edit,
                               unidade_edit, local_edit.strip(),
                               validade_edit.isoformat() if validade_edit else "",
                               status_edit, observacoes_edit.strip())
                st.success("Reagente atualizado!")
                st.rerun()
            else:
                st.error("O nome não pode ficar vazio.")
        if excluir_btn:
            delete_reagent(selected_id)
            st.success("Reagente excluído.")
            st.rerun()
