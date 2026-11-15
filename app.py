# ==============================================================
# BLOCO 0: IMPORTAÇÕES E CONFIGURAÇÃO INICIAL
# ==============================================================

import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"

# ==============================================================
# BLOCO 1: CLASSES — HERANÇA E POLIMORFISMO
# ==============================================================

class Reagente:
    """Classe base para representar reagentes em geral."""

    def __init__(self, nome, quantidade):
        self.nome = nome
        self.quantidade = quantidade

    def exibir_detalhes(self):
        return {
            "Nome": self.nome,
            "Quantidade": self.quantidade,
        }


class ReagenteBasico(Reagente):
    """Representa os reagentes iniciais do sistema."""

    def exibir_detalhes(self):
        return {
            "Nome": self.nome,
            "Tipo": "Básico",
            "Quantidade": self.quantidade,
        }


class ReagentePersonalizado(Reagente):
    """Representa reagentes cadastrados pelo usuário."""

    def exibir_detalhes(self):
        return {
            "Nome": self.nome,
            "Tipo": "Personalizado",
            "Quantidade": self.quantidade,
        }


# ==============================================================
# BLOCO 2: BANCO DE DADOS — CONEXÃO E CRIAÇÃO DE TABELAS
# ==============================================================

REAGENTES_INICIAIS = [
    "1. Ácido Clorídrico (HCl)",
    "2. Ácido Sulfúrico (H2SO4)",
    "3. Ácido Nítrico (HNO3)",
    "4. Ácido Acético (CH3COOH)",
    "5. Hidróxido de Sódio (NaOH)",
    "6. Hidróxido de Amônio (NH4OH)",
    "7. Hidróxido de Cálcio (Ca(OH)2)",
    "8. Bicarbonato de Sódio (NaHCO3)",
    "9. Cloreto de Sódio (NaCl)",
    "10. Sulfato de Cobre II (CuSO4)",
    "11. Nitrato de Prata (AgNO3)",
    "12. Cloreto de Bário (BaCl2)",
    "13. Carbonato de Sódio (Na2CO3)",
    "14. Permanganato de Potássio (KMnO4)",
    "15. Iodeto de Potássio (KI)",
    "16. Cromato de Potássio (K2CrO4)",
    "17. Água Destilada/Deionizada (H2O)",
    "18. Álcool Etílico/Etanol (C2H5OH)",
    "19. Acetona (CH3COCH3)",
    "20. Hexano (C6H14)",
    "21. Fenolftaleína",
    "22. Metiloranje (Alaranjado de Metila)",
    "23. Azul de Bromotimol",
    "24. Solução de Amido",
    "25. Peróxido de Hidrogênio (H2O2)",
    "26. Glicerina/Glicerol",
    "27. Ácido Ascórbico",
    "28. Sulfato de Magnésio (MgSO4) Anidro",
    "29. Glicose (C6H12O6)",
    "30. Nitrato de Amônio (NH4NO3)",
]


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria a tabela principal e insere a lista inicial de reagentes."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reagentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            categoria TEXT,
            quantidade INTEGER,
            unidade TEXT,
            local TEXT,
            validade TEXT,
            status TEXT,
            observacoes TEXT,
            created_at TEXT,
            updated_at TEXT,
            updated_by TEXT
        )
        """
    )

    total = conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0]
    if total == 0:
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.executemany(
            """
            INSERT INTO reagentes (
                nome, categoria, quantidade, unidade, local, validade, status,
                observacoes, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    nome,
                    "Geral",
                    2,
                    "unidade",
                    "Estoque inicial",
                    "",
                    "Disponível",
                    "Reagente carregado automaticamente",
                    agora,
                    agora,
                    "Sistema",
                )
                for nome in REAGENTES_INICIAIS
            ],
        )

    conn.commit()
    conn.close()


# ==============================================================
# BLOCO 3: FUNÇÕES DE LEITURA E ESCRITA
# ==============================================================


def load_data():
    """Carrega os reagentes e devolve uma lista de dicionários."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM reagentes
        ORDER BY nome COLLATE NOCASE
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_reagent(nome, categoria, quantidade, unidade, local, validade, status, observacoes, updated_by):
    """Adiciona um novo reagente ao banco."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO reagentes (
            nome, categoria, quantidade, unidade, local, validade, status,
            observacoes, created_at, updated_at, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nome,
            categoria,
            quantidade,
            unidade,
            local,
            validade,
            status,
            observacoes,
            agora,
            agora,
            updated_by,
        ),
    )
    conn.commit()
    conn.close()


def update_reagent(reagente_id, nome, categoria, quantidade, unidade, local, validade, status, observacoes, updated_by):
    """Atualiza um reagente existente e registra quem alterou."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    conn.execute(
        """
        UPDATE reagentes
        SET nome = ?,
            categoria = ?,
            quantidade = ?,
            unidade = ?,
            local = ?,
            validade = ?,
            status = ?,
            observacoes = ?,
            updated_at = ?,
            updated_by = ?
        WHERE id = ?
        """,
        (
            nome,
            categoria,
            quantidade,
            unidade,
            local,
            validade,
            status,
            observacoes,
            agora,
            updated_by,
            reagente_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_reagent(reagente_id):
    """Remove um reagente da tabela."""
    conn = get_connection()
    conn.execute("DELETE FROM reagentes WHERE id = ?", (reagente_id,))
    conn.commit()
    conn.close()


def gerar_resumo(df):
    """Calcula indicadores para a tela de resumo."""
    total_itens = int(df["quantidade"].sum()) if not df.empty else 0
    reagentes_baixo = int((df["quantidade"] <= 5).sum()) if not df.empty else 0
    categorias = df["categoria"].nunique() if not df.empty else 0
    return total_itens, reagentes_baixo, categorias


# ==============================================================
# BLOCO 4: CONFIGURAÇÃO DO STREAMLIT
# ==============================================================

st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")

# Inicializa o banco ao abrir a aplicação.
init_db()

# ==============================================================
# BLOCO 5: INTERFACE WEB — LAYOUT E ABAS
# ==============================================================

st.title("LabInv - Inventário de Laboratório")
st.caption("Controle de reagentes e materiais de laboratório")

# Campo para registrar quem está alterando o material.
with st.sidebar:
    st.header("Usuário / responsável")
    responsavel = st.text_input("Nome do responsável", value="Usuário")

# Cadastro por sidebar
with st.sidebar:
    st.header("Cadastrar reagente")
    with st.form("form_reagente", clear_on_submit=True):
        nome = st.text_input("Nome do reagente")
        categoria = st.selectbox("Categoria", ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"])
        quantidade = st.number_input("Quantidade", min_value=0, value=0, step=1)
        unidade = st.selectbox("Unidade", ["mL", "g", "mg", "L", "kg", "unidade"])
        local = st.text_input("Local de armazenamento")
        validade = st.date_input("Data de validade", min_value=datetime.now().date())
        status = st.selectbox("Status", ["Disponível", "Baixo", "Vencido", "Em uso"])
        observacoes = st.text_area("Observações")
        enviado = st.form_submit_button("Salvar reagente")

        if enviado:
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
                    responsavel.strip() or "Usuário",
                )
                st.success("Reagente cadastrado com sucesso!")
                st.rerun()
            else:
                st.warning("Informe o nome do reagente.")

# Carrega dados
raw_data = load_data()
df = pd.DataFrame(raw_data)

# Filtros
with st.sidebar:
    st.subheader("Filtros")
    if not df.empty:
        categorias = ["Todos"] + sorted(df["categoria"].dropna().unique().tolist())
        categoria_filtro = st.selectbox("Categoria", categorias)
        status_filtro = st.selectbox("Status", ["Todos", "Disponível", "Baixo", "Vencido", "Em uso"])
        busca = st.text_input("Buscar por nome")
    else:
        categoria_filtro = "Todos"
        status_filtro = "Todos"
        busca = ""

if not df.empty:
    filtrado = df.copy()
    if categoria_filtro != "Todos":
        filtrado = filtrado[filtrado["categoria"] == categoria_filtro]
    if status_filtro != "Todos":
        filtrado = filtrado[filtrado["status"] == status_filtro]
    if busca.strip():
        filtrado = filtrado[filtrado["nome"].str.contains(busca.strip(), case=False, na=False)]
else:
    filtrado = pd.DataFrame(columns=[
        "id", "nome", "categoria", "quantidade", "unidade", "local", "validade", "status", "observacoes",
        "created_at", "updated_at", "updated_by"
    ])

# Resumo
col1, col2, col3 = st.columns(3)
resumo_total, resumo_baixo, resumo_categorias = gerar_resumo(filtrado)
col1.metric("Total em estoque", resumo_total)
col2.metric("Itens em nível baixo", resumo_baixo)
col3.metric("Categorias", resumo_categorias)

# ==============================================================
# BLOCO 6: TABELA PRINCIPAL E AÇÕES DE EDIÇÃO
# ==============================================================

# Aba principal com lista dos reagentes
lista_tab, editar_tab = st.tabs(["📋 Lista de reagentes", "✏️ Editar reagente"])

with lista_tab:
    if filtrado.empty:
        st.info("Nenhum reagente encontrado para os filtros aplicados.")
    else:
        st.dataframe(
            filtrado[["nome", "categoria", "quantidade", "unidade", "local", "validade", "status", "updated_at", "updated_by"]],
            use_container_width=True,
            hide_index=True,
        )

with editar_tab:
    if df.empty:
        st.info("Ainda não há reagentes cadastrados.")
    else:
        itens = {int(item["id"]): item for item in load_data()}
        selected_id = st.selectbox(
            "Selecione o reagente para editar",
            options=list(itens.keys()),
            format_func=lambda x: itens[x]["nome"],
        )

        item = itens[selected_id]
        with st.form("edit_reagente"):
            st.write(f"Editando: {item['nome']}")
            nome_edit = st.text_input("Nome", value=item["nome"])
            categoria_edit = st.selectbox(
                "Categoria",
                ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"],
                index=["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"].index(item["categoria"] or "Outro"),
            )
            quantidade_edit = st.number_input("Quantidade", min_value=0, value=int(item["quantidade"] or 0), step=1)
            unidade_edit = st.selectbox(
                "Unidade",
                ["mL", "g", "mg", "L", "kg", "unidade"],
                index=["mL", "g", "mg", "L", "kg", "unidade"].index(item["unidade"] or "unidade"),
            )
            local_edit = st.text_input("Local", value=item["local"] or "")
            validade_edit = st.date_input(
                "Validade",
                value=datetime.strptime(item["validade"], "%Y-%m-%d").date() if item.get("validade") else datetime.now().date(),
            )
            status_edit = st.selectbox(
                "Status",
                ["Disponível", "Baixo", "Vencido", "Em uso"],
                index=["Disponível", "Baixo", "Vencido", "Em uso"].index(item["status"] or "Disponível"),
            )
            observacoes_edit = st.text_area("Observações", value=item["observacoes"] or "")

            col1, col2 = st.columns(2)
            salvar = col1.form_submit_button("Salvar alterações")
            excluir = col2.form_submit_button("Excluir reagente")

            if salvar:
                if nome_edit.strip():
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
                        responsavel.strip() or "Usuário",
                    )
                    st.success("Reagente atualizado com sucesso!")
                    st.rerun()
                else:
                    st.error("O nome do reagente não pode ficar vazio.")

            if excluir:
                delete_reagent(selected_id)
                st.success("Reagente excluído.")
                st.rerun()

# ==============================================================
# BLOCO 7: DADOS DE AUDITORIA
# ==============================================================

st.subheader("Histórico de alterações")
if df.empty:
    st.caption("Nenhuma alteração registrada até o momento.")
else:
    registros = df[["nome", "updated_at", "updated_by"]].copy()
    registros = registros.rename(columns={
        "nome": "Reagente",
        "updated_at": "Última atualização",
        "updated_by": "Responsável",
    })
    st.dataframe(registros, use_container_width=True, hide_index=True)

# Fim do arquivo
