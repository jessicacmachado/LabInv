# ==============================================================
# LabInv — Controle de Estoque de Reagentes Químicos
# Interface Streamlit com lista, retiradas, devoluções, cadastro e histórico.
# Login por senha removido; o nome do responsável é informado na barra lateral.
# ==============================================================

import json
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"

reagentes_basicos = [
    "1. Ácido Clorídrico (HCl)", "2. Ácido Sulfúrico (H2SO4)",
    "3. Ácido Nítrico (HNO3)", "4. Ácido Acético (CH3COOH)",
    "5. Hidróxido de Sódio (NaOH)", "6. Hidróxido de Amônio (NH4OH)",
    "7. Hidróxido de Cálcio (Ca(OH)2)", "8. Bicarbonato de Sódio (NaHCO3)",
    "9. Cloreto de Sódio (NaCl)", "10. Sulfato de Cobre II (CuSO4)",
    "11. Nitrato de Prata (AgNO3)", "12. Cloreto de Bário (BaCl2)",
    "13. Carbonato de Sódio (Na2CO3)", "14. Permanganato de Potássio (KMnO4)",
    "15. Iodeto de Potássio (KI)", "16. Cromato de Potássio (K2CrO4)",
    "17. Água Destilada/Deionizada (H2O)", "18. Álcool Etílico/Etanol (C2H5OH)",
    "19. Acetona (CH3COCH3)", "20. Hexano (C6H14)", "21. Fenolftaleína",
    "22. Metiloranje (Alaranjado de Metila)", "23. Azul de Bromotimol",
    "24. Solução de Amido", "25. Peróxido de Hidrogênio (H2O2)",
    "26. Glicerina/Glicerol", "27. Ácido Ascórbico",
    "28. Sulfato de Magnésio (MgSO4) Anidro", "29. Glicose (C6H12O6)",
    "30. Nitrato de Amônio (NH4NO3)",
]


class Reagente:
    def __init__(self, nome, quantidade):
        self.nome = nome
        self.quantidade = quantidade

    def exibir_detalhes(self):
        return {"Nome": self.nome, "Quantidade disponível": self.quantidade}


class ReagenteBasico(Reagente):
    def exibir_detalhes(self):
        return {"Nome": self.nome, "Tipo": "Reagente básico", "Quantidade disponível": self.quantidade}


class ReagentePersonalizado(Reagente):
    def exibir_detalhes(self):
        return {"Nome": self.nome, "Tipo": "Reagente personalizado", "Quantidade disponível": self.quantidade}


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reagentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            categoria TEXT,
            quantidade REAL NOT NULL DEFAULT 2,
            unidade TEXT DEFAULT 'unidade',
            local TEXT DEFAULT '',
            validade TEXT DEFAULT '',
            status TEXT DEFAULT 'Disponível',
            observacoes TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            updated_by TEXT
        )"""
    )
    existentes = {row["name"] for row in conn.execute("PRAGMA table_info(reagentes)").fetchall()}
    colunas = {
        "categoria": "TEXT", "quantidade": "REAL NOT NULL DEFAULT 2",
        "unidade": "TEXT DEFAULT 'unidade'", "local": "TEXT DEFAULT ''",
        "validade": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'Disponível'",
        "observacoes": "TEXT DEFAULT ''", "created_at": "TEXT",
        "updated_at": "TEXT", "updated_by": "TEXT",
    }
    for nome_coluna, tipo_coluna in colunas.items():
        if nome_coluna not in existentes:
            conn.execute(f"ALTER TABLE reagentes ADD COLUMN {nome_coluna} {tipo_coluna}")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reagente_id INTEGER,
            nome_reagente TEXT NOT NULL,
            acao TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            detalhes TEXT NOT NULL
        )"""
    )
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute(
        """UPDATE reagentes SET created_at=COALESCE(created_at, ?),
           updated_at=COALESCE(updated_at, ?),
           updated_by=COALESCE(updated_by, 'Registro anterior')""",
        (agora, agora),
    )
    if conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0] == 0:
        conn.executemany(
            """INSERT OR IGNORE INTO reagentes
               (nome, categoria, quantidade, unidade, local, validade, status,
                observacoes, created_at, updated_at, updated_by)
               VALUES (?, 'Geral', 2, 'unidade', 'Estoque inicial', '', 'Disponível',
                       'Reagente básico do programa original', ?, ?, 'Sistema')""",
            [(nome, agora, agora) for nome in reagentes_basicos],
        )
    conn.commit()
    conn.close()


def listar_reagentes():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM reagentes ORDER BY id").fetchall()]


def buscar_reagente(parte_nome):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM reagentes WHERE nome LIKE ? ORDER BY id", (f"%{parte_nome}%",)
        ).fetchall()]


def registrar_historico(conn, reagente_id, nome, acao, responsavel, detalhes):
    data_hora = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO historico (reagente_id, nome_reagente, acao, data_hora, responsavel, detalhes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (reagente_id, nome, acao, data_hora, responsavel, json.dumps(detalhes, ensure_ascii=False)),
    )


def cadastrar_reagente(nome, categoria, quantidade, unidade, local, validade, status, observacoes, responsavel):
    conn = get_connection()
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    cursor = conn.execute(
        """INSERT INTO reagentes
           (nome, categoria, quantidade, unidade, local, validade, status,
            observacoes, created_at, updated_at, updated_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nome, categoria, quantidade, unidade, local, validade, status, observacoes, agora, agora, responsavel),
    )
    registrar_historico(conn, cursor.lastrowid, nome, "Cadastro", responsavel,
                        {"quantidade inicial": quantidade, "unidade": unidade})
    conn.commit()
    conn.close()


def atualizar_reagente(reagente_id, dados, responsavel, acao="Edição"):
    conn = get_connection()
    anterior = conn.execute("SELECT * FROM reagentes WHERE id=?", (reagente_id,)).fetchone()
    if anterior is None:
        conn.close()
        return False
    anterior = dict(anterior)
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    campos = ["nome", "categoria", "quantidade", "unidade", "local", "validade", "status", "observacoes"]
    conn.execute(
        """UPDATE reagentes SET nome=?, categoria=?, quantidade=?, unidade=?, local=?, validade=?,
           status=?, observacoes=?, updated_at=?, updated_by=? WHERE id=?""",
        (dados["nome"], dados["categoria"], dados["quantidade"], dados["unidade"], dados["local"],
         dados["validade"], dados["status"], dados["observacoes"], agora, responsavel, reagente_id),
    )
    diferencas = {campo: {"antes": anterior.get(campo), "depois": dados[campo]}
                  for campo in campos if anterior.get(campo) != dados[campo]}
    if diferencas:
        registrar_historico(conn, reagente_id, dados["nome"], acao, responsavel, diferencas)
    conn.commit()
    conn.close()
    return True


def excluir_reagente(reagente_id, responsavel):
    conn = get_connection()
    linha = conn.execute("SELECT * FROM reagentes WHERE id=?", (reagente_id,)).fetchone()
    if linha is None:
        conn.close()
        return False
    item = dict(linha)
    registrar_historico(conn, reagente_id, item["nome"], "Exclusão", responsavel,
                        {"reagente removido": item})
    conn.execute("DELETE FROM reagentes WHERE id=?", (reagente_id,))
    conn.commit()
    conn.close()
    return True


def carregar_historico():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM historico ORDER BY id DESC").fetchall()]


st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
init_db()
with st.sidebar:
    st.subheader("Identificação do responsável")
    responsavel_atual = st.text_input("Seu nome", value="", key="responsavel_sessao").strip() or "Usuário"

st.title("🧪 LabInv — Controle de Estoque de Reagentes Químicos")
st.caption("Inventário de laboratório | Herança, polimorfismo e SQLite")
registros = listar_reagentes()
col1, col2, col3 = st.columns(3)
col1.metric("Reagentes cadastrados", len(registros))
col2.metric("Quantidade total", sum(float(item["quantidade"] or 0) for item in registros))
col3.metric("Reagentes básicos", sum(item["nome"] in reagentes_basicos for item in registros))

aba_lista, aba_retirada, aba_devolucao, aba_cadastro, aba_historico = st.tabs(
    ["📋 Lista", "📤 Retirar", "📥 Devolver / repor", "➕ Cadastrar", "🕘 Histórico"]
)

with aba_lista:
    st.subheader("Lista de reagentes cadastrados")
    termo = st.text_input("Buscar pelo nome ou parte do nome", key="busca_lista")
    resultados = buscar_reagente(termo) if termo.strip() else listar_reagentes()
    if resultados:
        tabela = []
        for item in resultados:
            classe = ReagenteBasico if item["nome"] in reagentes_basicos else ReagentePersonalizado
            linha = classe(item["nome"], item["quantidade"]).exibir_detalhes()
            linha.update({"Categoria": item.get("categoria") or "Geral", "Unidade": item.get("unidade") or "unidade",
                          "Local": item.get("local") or "", "Validade": item.get("validade") or "",
                          "Status": item.get("status") or "Disponível", "Atualizado em": item.get("updated_at") or "",
                          "Responsável": item.get("updated_by") or ""})
            tabela.append(linha)
        st.dataframe(pd.DataFrame(tabela), use_container_width=True, hide_index=True)
        st.caption(f"Total de reagentes exibidos: {len(resultados)}")
    else:
        st.info("Nenhum reagente encontrado.")

with aba_retirada:
    st.subheader("Retirada de reagente")
    with st.form("form_retirada"):
        termo = st.text_input("Nome ou parte do nome", key="termo_retirada")
        candidatos = buscar_reagente(termo) if termo.strip() else listar_reagentes()
        if candidatos:
            nomes = [item["nome"] for item in candidatos]
            nome = st.selectbox("Reagente", nomes, key="nome_retirada")
            quantidade = st.number_input("Quantidade a retirar", min_value=0.1, value=1.0, step=0.5)
            confirmar = st.form_submit_button("Confirmar retirada")
            if confirmar:
                item = next(row for row in listar_reagentes() if row["nome"] == nome)
                saldo = float(item["quantidade"] or 0)
                if saldo >= quantidade:
                    dados = {"nome": item["nome"], "categoria": item.get("categoria") or "Geral",
                             "quantidade": saldo - quantidade, "unidade": item.get("unidade") or "unidade",
                             "local": item.get("local") or "", "validade": item.get("validade") or "",
                             "status": item.get("status") or "Disponível", "observacoes": item.get("observacoes") or ""}
                    atualizar_reagente(item["id"], dados, responsavel_atual, "Retirada")
                    st.success(f"Retirada realizada. Saldo: {dados['quantidade']:g} {dados['unidade']}.")
                    st.rerun()
                else:
                    st.error(f"Estoque insuficiente. Disponível: {saldo:g} {item.get('unidade') or 'unidade'}.")
        else:
            st.info("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar retirada", disabled=True)

with aba_devolucao:
    st.subheader("Devolução ou reposição de reagente")
    with st.form("form_devolucao"):
        termo = st.text_input("Nome ou parte do nome", key="termo_devolucao")
        candidatos = buscar_reagente(termo) if termo.strip() else listar_reagentes()
        if candidatos:
            nomes = [item["nome"] for item in candidatos]
            nome = st.selectbox("Reagente", nomes, key="nome_devolucao")
            quantidade = st.number_input("Quantidade a devolver / repor", min_value=0.1, value=1.0, step=0.5)
            confirmar = st.form_submit_button("Confirmar devolução")
            if confirmar:
                item = next(row for row in listar_reagentes() if row["nome"] == nome)
                dados = {"nome": item["nome"], "categoria": item.get("categoria") or "Geral",
                         "quantidade": float(item["quantidade"] or 0) + quantidade,
                         "unidade": item.get("unidade") or "unidade", "local": item.get("local") or "",
                         "validade": item.get("validade") or "", "status": item.get("status") or "Disponível",
                         "observacoes": item.get("observacoes") or ""}
                atualizar_reagente(item["id"], dados, responsavel_atual, "Devolução / reposição")
                st.success(f"Devolução registrada. Novo saldo: {dados['quantidade']:g} {dados['unidade']}.")
                st.rerun()
        else:
            st.info("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar devolução", disabled=True)

with aba_cadastro:
    st.subheader("Cadastrar reagente personalizado")
    with st.form("form_cadastro", clear_on_submit=True):
        nome_novo = st.text_input("Nome e fórmula do reagente")
        categoria = st.selectbox("Categoria", ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"])
        quantidade = st.number_input("Quantidade inicial", min_value=0.0, value=2.0, step=0.5)
        unidade = st.selectbox("Unidade", ["mL", "g", "mg", "L", "kg", "unidade"])
        local = st.text_input("Local de armazenamento")
        validade = st.date_input("Validade (opcional)", value=None)
        status = st.selectbox("Status", ["Disponível", "Baixo", "Vencido", "Em uso"])
        observacoes = st.text_area("Observações")
        cadastrar = st.form_submit_button("Cadastrar reagente")
        if cadastrar:
            nome_novo = nome_novo.strip()
            if not nome_novo:
                st.error("O nome não pode ficar vazio.")
            elif any(row["nome"].casefold() == nome_novo.casefold() for row in listar_reagentes()):
                st.warning("Esse reagente já está cadastrado.")
            else:
                try:
                    cadastrar_reagente(nome_novo, categoria, quantidade, unidade, local.strip(),
                                       validade.isoformat() if validade else "", status,
                                       observacoes.strip(), responsavel_atual)
                    st.success("Reagente cadastrado com sucesso.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Não foi possível cadastrar: já existe um reagente com esse nome.")

    st.divider()
    st.subheader("Editar ou excluir reagente")
    lista_atual = listar_reagentes()
    if lista_atual:
        por_nome = {item["nome"]: item for item in lista_atual}
        nome_editar = st.selectbox("Selecione um reagente", list(por_nome), key="selecionar_edicao")
        item = por_nome[nome_editar]
        with st.form("form_edicao"):
            nome_editado = st.text_input("Nome", value=item["nome"])
            categorias = ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro", "Geral"]
            categoria_atual = item.get("categoria") or "Geral"
            if categoria_atual not in categorias:
                categorias.append(categoria_atual)
            categoria_editada = st.selectbox("Categoria", categorias, index=categorias.index(categoria_atual))
            quantidade_editada = st.number_input("Quantidade", min_value=0.0, value=float(item["quantidade"] or 0), step=0.5)
            unidades = ["mL", "g", "mg", "L", "kg", "unidade"]
            unidade_atual = item.get("unidade") or "unidade"
            unidade_editada = st.selectbox("Unidade", unidades,
                                           index=unidades.index(unidade_atual) if unidade_atual in unidades else unidades.index("unidade"))
            local_editado = st.text_input("Local", value=item.get("local") or "")
            validade_editada = st.text_input("Validade (AAAA-MM-DD)", value=item.get("validade") or "")
            statuses = ["Disponível", "Baixo", "Vencido", "Em uso"]
            status_atual = item.get("status") or "Disponível"
            status_editado = st.selectbox("Status", statuses, index=statuses.index(status_atual) if status_atual in statuses else 0)
            observacoes_editadas = st.text_area("Observações", value=item.get("observacoes") or "")
            salvar, excluir = st.columns(2)
            salvar_clicado = salvar.form_submit_button("Salvar alterações")
            excluir_clicado = excluir.form_submit_button("Excluir reagente")
            if salvar_clicado:
                if not nome_editado.strip():
                    st.error("O nome não pode ficar vazio.")
                else:
                    dados = {"nome": nome_editado.strip(), "categoria": categoria_editada,
                             "quantidade": quantidade_editada, "unidade": unidade_editada,
                             "local": local_editado.strip(), "validade": validade_editada.strip(),
                             "status": status_editado, "observacoes": observacoes_editadas.strip()}
                    try:
                        atualizar_reagente(item["id"], dados, responsavel_atual)
                        st.success("Reagente atualizado. O histórico guarda os campos alterados.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe outro reagente com esse nome.")
            if excluir_clicado:
                excluir_reagente(item["id"], responsavel_atual)
                st.success("Reagente excluído; a operação permanece registrada no histórico.")
                st.rerun()

with aba_historico:
    st.subheader("Histórico completo de alterações")
    eventos = carregar_historico()
    if not eventos:
        st.info("Ainda não há operações registradas.")
    else:
        filtro = st.text_input("Filtrar histórico por reagente ou responsável", key="busca_historico")
        df_historico = pd.DataFrame(eventos)
        if filtro.strip():
            mascara = (df_historico["nome_reagente"].str.contains(filtro.strip(), case=False, na=False)
                       | df_historico["responsavel"].str.contains(filtro.strip(), case=False, na=False))
            df_historico = df_historico[mascara]
        df_historico = df_historico.rename(columns={"data_hora": "Data e hora", "responsavel": "Responsável",
                                                    "acao": "Operação", "nome_reagente": "Reagente",
                                                    "detalhes": "Detalhes da alteração"})
        st.dataframe(df_historico[["Data e hora", "Responsável", "Operação", "Reagente", "Detalhes da alteração"]],
                     use_container_width=True, hide_index=True)
