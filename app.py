# LabInv — Controle de Estoque de Reagentes Químicos
import json
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"

# Lista original completa de 30 reagentes do projeto.
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
        self.nome, self.quantidade = nome, quantidade

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
    conn.execute("""CREATE TABLE IF NOT EXISTS reagentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, categoria TEXT,
        quantidade REAL NOT NULL DEFAULT 2, unidade TEXT DEFAULT 'unidade', local TEXT DEFAULT '',
        validade TEXT DEFAULT '', status TEXT DEFAULT 'Disponível', observacoes TEXT DEFAULT '',
        created_at TEXT, updated_at TEXT, updated_by TEXT)""")
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(reagentes)").fetchall()}
    columns = {
        "categoria": "TEXT", "quantidade": "REAL NOT NULL DEFAULT 2", "unidade": "TEXT DEFAULT 'unidade'",
        "local": "TEXT DEFAULT ''", "validade": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'Disponível'",
        "observacoes": "TEXT DEFAULT ''", "created_at": "TEXT", "updated_at": "TEXT", "updated_by": "TEXT",
    }
    for name, kind in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE reagentes ADD COLUMN {name} {kind}")
    conn.execute("""CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, reagente_id INTEGER, nome_reagente TEXT NOT NULL,
        acao TEXT NOT NULL, data_hora TEXT NOT NULL, responsavel TEXT NOT NULL, detalhes TEXT NOT NULL)""")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute("""UPDATE reagentes SET created_at=COALESCE(created_at, ?),
        updated_at=COALESCE(updated_at, ?), updated_by=COALESCE(updated_by, 'Registro anterior')""", (now, now))
    # Adiciona os reagentes iniciais ausentes sem alterar dados existentes.
    conn.executemany("""INSERT OR IGNORE INTO reagentes
        (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
        VALUES (?,'Geral',2,'unidade','Estoque inicial','','Disponível',
        'Reagente básico do programa original',?,?,'Sistema')""", [(name, now, now) for name in reagentes_basicos])
    conn.commit()
    conn.close()


def listar_reagentes():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM reagentes ORDER BY id").fetchall()]


def buscar_reagente(termo):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM reagentes WHERE nome LIKE ? ORDER BY id", (f"%{termo}%",)
        ).fetchall()]


def registrar_historico(conn, reagente_id, nome, acao, responsavel, detalhes):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute("""INSERT INTO historico
        (reagente_id,nome_reagente,acao,data_hora,responsavel,detalhes) VALUES (?,?,?,?,?,?)""",
        (reagente_id, nome, acao, now, responsavel, json.dumps(detalhes, ensure_ascii=False)))


def cadastrar_reagente(nome, categoria, quantidade, unidade, local, validade, status, observacoes, responsavel):
    conn = get_connection()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    cursor = conn.execute("""INSERT INTO reagentes
        (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (nome,categoria,quantidade,unidade,local,validade,status,observacoes,now,now,responsavel))
    registrar_historico(conn, cursor.lastrowid, nome, "Cadastro", responsavel,
                        {"quantidade inicial": quantidade, "unidade": unidade})
    conn.commit()
    conn.close()


def atualizar_reagente(reagente_id, dados, responsavel, acao="Edição"):
    conn = get_connection()
    row = conn.execute("SELECT * FROM reagentes WHERE id=?", (reagente_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    old = dict(row)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    fields = ["nome", "categoria", "quantidade", "unidade", "local", "validade", "status", "observacoes"]
    conn.execute("""UPDATE reagentes SET nome=?,categoria=?,quantidade=?,unidade=?,local=?,validade=?,
        status=?,observacoes=?,updated_at=?,updated_by=? WHERE id=?""",
        tuple(dados[field] for field in fields) + (now, responsavel, reagente_id))
    changes = {field: {"antes": old.get(field), "depois": dados[field]}
               for field in fields if old.get(field) != dados[field]}
    if changes:
        registrar_historico(conn, reagente_id, dados["nome"], acao, responsavel, changes)
    conn.commit()
    conn.close()
    return True


def excluir_reagente(reagente_id, responsavel):
    conn = get_connection()
    row = conn.execute("SELECT * FROM reagentes WHERE id=?", (reagente_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    item = dict(row)
    registrar_historico(conn, reagente_id, item["nome"], "Exclusão", responsavel, {"reagente removido": item})
    conn.execute("DELETE FROM reagentes WHERE id=?", (reagente_id,))
    conn.commit()
    conn.close()
    return True


def carregar_historico():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM historico ORDER BY id DESC").fetchall()]


def dados_para_edicao(item, quantidade):
    return {"nome": item["nome"], "categoria": item.get("categoria") or "Geral", "quantidade": quantidade,
            "unidade": item.get("unidade") or "unidade", "local": item.get("local") or "",
            "validade": item.get("validade") or "", "status": item.get("status") or "Disponível",
            "observacoes": item.get("observacoes") or ""}


st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")

# Tema visual neutro com utensílios de laboratório em traço translúcido no fundo.
st.markdown("""
<style>
.stApp {
  background-color: #efeee9;
  background-image:
    linear-gradient(rgba(245, 244, 239, 0.88), rgba(245, 244, 239, 0.88)),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='320' viewBox='0 0 320 320'%3E%3Cg fill='none' stroke='%237b8982' stroke-opacity='.22' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M70 42h46M82 42v72L48 190a18 18 0 0016 27h58a18 18 0 0016-27l-34-76V42'/%3E%3Cpath d='M63 174h70M86 147h20M222 44v56l-34 74a17 17 0 0015 24h48a17 17 0 0015-24l-34-74V44M211 44h22M197 158h60'/%3E%3Cpath d='M57 202h71M202 183h54M255 52v62M244 52h22M239 114h32'/%3E%3Ccircle cx='265' cy='244' r='25'/%3E%3Cpath d='M265 207v-16m0 106v-16m37-37h-16m-42 0h-16m63-26l-11 11m-30 30l-11 11m0-52l11 11m30 30l11 11'/%3E%3C/g%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: auto, 320px 320px;
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: rgba(245, 244, 239, 0.72); }
[data-testid="stSidebar"] { background: rgba(226, 228, 221, 0.90); }
[data-testid="stMetric"] {
  background: rgba(255, 255, 252, 0.78);
  border: 1px solid rgba(113, 127, 118, 0.20);
  padding: 14px 16px;
  border-radius: 14px;
}
[data-testid="stTabs"] [role="tablist"] { gap: 8px; }
[data-testid="stTabs"] button[role="tab"] {
  background: rgba(255, 255, 252, 0.60);
  border-radius: 10px 10px 0 0;
}
[data-testid="stExpander"] {
  background: rgba(255, 255, 252, 0.78);
  border: 1px solid rgba(113, 127, 118, 0.24);
  border-radius: 14px;
}
[data-testid="stForm"] {
  background: rgba(255, 255, 252, 0.76);
  border: 1px solid rgba(113, 127, 118, 0.20);
  border-radius: 14px;
  padding: 18px;
}
</style>
""", unsafe_allow_html=True)

init_db()
with st.sidebar:
    st.subheader("Identificação do responsável")
    responsavel_atual = st.text_input("Seu nome", key="responsavel_sessao").strip() or "Usuário"

st.title("🧪 LabInv — Controle de Estoque de Reagentes Químicos")
st.caption("Inventário de laboratório")
registros = listar_reagentes()
c1, c2, c3 = st.columns(3)
c1.metric("Reagentes cadastrados", len(registros))
c2.metric("Quantidade total", sum(float(item["quantidade"] or 0) for item in registros))
c3.metric("Reagentes básicos", sum(item["nome"] in reagentes_basicos for item in registros))

aba_lista, aba_retirada, aba_devolucao, aba_cadastro, aba_historico = st.tabs(
    ["📋 Lista", "📤 Retirar", "📥 Devolver / repor", "➕ Cadastrar", "🕘 Histórico"])

with aba_lista:
    with st.expander("📋 Mostrar / ocultar lista de reagentes", expanded=False):
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
            nome = st.selectbox("Reagente", [item["nome"] for item in candidatos], key="nome_retirada")
            quantidade = st.number_input("Quantidade a retirar", min_value=0.1, value=1.0, step=0.5)
            confirmar = st.form_submit_button("Confirmar retirada")
            if confirmar:
                item = next(row for row in listar_reagentes() if row["nome"] == nome)
                saldo = float(item["quantidade"] or 0)
                if saldo >= quantidade:
                    dados = dados_para_edicao(item, saldo - quantidade)
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
            nome = st.selectbox("Reagente", [item["nome"] for item in candidatos], key="nome_devolucao")
            quantidade = st.number_input("Quantidade a devolver / repor", min_value=0.1, value=1.0, step=0.5)
            confirmar = st.form_submit_button("Confirmar devolução")
            if confirmar:
                item = next(row for row in listar_reagentes() if row["nome"] == nome)
                saldo = float(item["quantidade"] or 0) + quantidade
                atualizar_reagente(item["id"], dados_para_edicao(item, saldo), responsavel_atual, "Devolução / reposição")
                st.success(f"Devolução registrada. Novo saldo: {saldo:g} {item.get('unidade') or 'unidade'}.")
                st.rerun()
        else:
            st.info("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar devolução", disabled=True)

with aba_cadastro:
    st.subheader("Cadastrar reagente personalizado")
    with st.form("form_cadastro", clear_on_submit=True):
        nome_novo = st.text_input("Nome e fórmula do reagente")
        categoria_nova = st.selectbox("Categoria", ["Solvente", "Ácido", "Base", "Indicador", "Sal", "Outro"])
        quantidade_nova = st.number_input("Quantidade inicial", min_value=0.0, value=2.0, step=0.5)
        unidade_nova = st.selectbox("Unidade", ["mL", "g", "mg", "L", "kg", "unidade"])
        local_novo = st.text_input("Local de armazenamento")
        validade_nova = st.date_input("Validade (opcional)", value=None)
        status_novo = st.selectbox("Status", ["Disponível", "Baixo", "Vencido", "Em uso"])
        observacoes_novas = st.text_area("Observações")
        cadastrar = st.form_submit_button("Cadastrar reagente")
        if cadastrar:
            nome_novo = nome_novo.strip()
            if not nome_novo:
                st.error("O nome não pode ficar vazio.")
            elif any(row["nome"].casefold() == nome_novo.casefold() for row in listar_reagentes()):
                st.warning("Esse reagente já está cadastrado.")
            else:
                try:
                    cadastrar_reagente(nome_novo, categoria_nova, quantidade_nova, unidade_nova,
                        local_novo.strip(), validade_nova.isoformat() if validade_nova else "",
                        status_novo, observacoes_novas.strip(), responsavel_atual)
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
            unidade_editada = st.selectbox("Unidade", unidades, index=unidades.index(unidade_atual) if unidade_atual in unidades else unidades.index("unidade"))
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
        historico_df = pd.DataFrame(eventos)
        if filtro.strip():
            mascara = (historico_df["nome_reagente"].str.contains(filtro.strip(), case=False, na=False)
                       | historico_df["responsavel"].str.contains(filtro.strip(), case=False, na=False))
            historico_df = historico_df[mascara]
        historico_df = historico_df.rename(columns={"data_hora": "Data e hora", "responsavel": "Responsável",
            "acao": "Operação", "nome_reagente": "Reagente", "detalhes": "Detalhes da alteração"})
        st.dataframe(historico_df[["Data e hora", "Responsável", "Operação", "Reagente", "Detalhes da alteração"]],
                     use_container_width=True, hide_index=True)
