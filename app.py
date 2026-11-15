# LabInv — Controle de Estoque de Reagentes Químicos
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"
LIMITE_REAGENTES = 300
LIMITE_HISTORICO = 300
PDF_GUIA = Path(__file__).resolve().parent / "pdfGuia_Basico_Seguranca_Quimica_30_Reagentes.pdf"
reagentes_basicos = [
    "1. Ácido Clorídrico (HCl)", "2. Ácido Sulfúrico (H2SO4)", "3. Ácido Nítrico (HNO3)",
    "4. Ácido Acético (CH3COOH)", "5. Hidróxido de Sódio (NaOH)", "6. Hidróxido de Amônio (NH4OH)",
    "7. Hidróxido de Cálcio (Ca(OH)2)", "8. Bicarbonato de Sódio (NaHCO3)", "9. Cloreto de Sódio (NaCl)",
    "10. Sulfato de Cobre II (CuSO4)", "11. Nitrato de Prata (AgNO3)", "12. Cloreto de Bário (BaCl2)",
    "13. Carbonato de Sódio (Na2CO3)", "14. Permanganato de Potássio (KMnO4)", "15. Iodeto de Potássio (KI)",
    "16. Cromato de Potássio (K2CrO4)", "17. Água Destilada/Deionizada (H2O)",
    "18. Álcool Etílico/Etanol (C2H5OH)", "19. Acetona (CH3COCH3)", "20. Hexano (C6H14)",
    "21. Fenolftaleína", "22. Metiloranje (Alaranjado de Metila)", "23. Azul de Bromotimol",
    "24. Solução de Amido", "25. Peróxido de Hidrogênio (H2O2)", "26. Glicerina/Glicerol",
    "27. Ácido Ascórbico", "28. Sulfato de Magnésio (MgSO4) Anidro", "29. Glicose (C6H12O6)",
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
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reagentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, categoria TEXT,
            quantidade REAL NOT NULL DEFAULT 2, unidade TEXT DEFAULT 'unidade', local TEXT DEFAULT '',
            validade TEXT DEFAULT '', status TEXT DEFAULT 'Disponível', observacoes TEXT DEFAULT '',
            created_at TEXT, updated_at TEXT, updated_by TEXT)""")
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(reagentes)").fetchall()}
        columns = {"categoria":"TEXT", "quantidade":"REAL NOT NULL DEFAULT 2", "unidade":"TEXT DEFAULT 'unidade'",
            "local":"TEXT DEFAULT ''", "validade":"TEXT DEFAULT ''", "status":"TEXT DEFAULT 'Disponível'",
            "observacoes":"TEXT DEFAULT ''", "created_at":"TEXT", "updated_at":"TEXT", "updated_by":"TEXT"}
        for name, kind in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE reagentes ADD COLUMN {name} {kind}")
        conn.execute("""CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT, reagente_id INTEGER, nome_reagente TEXT NOT NULL,
            acao TEXT NOT NULL, data_hora TEXT NOT NULL, responsavel TEXT NOT NULL, detalhes TEXT NOT NULL)""")
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        conn.execute("UPDATE reagentes SET created_at=COALESCE(created_at, ?), updated_at=COALESCE(updated_at, ?), updated_by=COALESCE(updated_by, 'Registro anterior')", (now, now))
        conn.executemany("""INSERT OR IGNORE INTO reagentes
            (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
            VALUES (?,'Geral',2,'unidade','Estoque inicial','','Disponível','Reagente básico do programa original',?,?,'Sistema')""",
            [(name, now, now) for name in reagentes_basicos[:LIMITE_REAGENTES]])


def listar_reagentes():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reagentes ORDER BY id LIMIT ?", (LIMITE_REAGENTES,)).fetchall()]


def buscar_reagente(termo):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reagentes WHERE nome LIKE ? ORDER BY id LIMIT ?", (f"%{termo}%", LIMITE_REAGENTES)).fetchall()]


def registrar_historico(conn, rid, nome, acao, responsavel, detalhes):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute("INSERT INTO historico (reagente_id,nome_reagente,acao,data_hora,responsavel,detalhes) VALUES (?,?,?,?,?,?)",
        (rid, nome, acao, now, responsavel, json.dumps(detalhes, ensure_ascii=False)))
    conn.execute("DELETE FROM historico WHERE id NOT IN (SELECT id FROM historico ORDER BY id DESC LIMIT ?)", (LIMITE_HISTORICO,))


def cadastrar_reagente(nome, categoria, quantidade, unidade, local, validade, status, observacoes, responsavel):
    conn = get_connection()
    try:
        if conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0] >= LIMITE_REAGENTES:
            return False
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        cur = conn.execute("""INSERT INTO reagentes (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (nome,categoria,quantidade,unidade,local,validade,status,observacoes,now,now,responsavel))
        registrar_historico(conn, cur.lastrowid, nome, "Cadastro", responsavel, {"quantidade inicial":quantidade,"unidade":unidade})
        conn.commit()
        return True
    finally:
        conn.close()


def atualizar_reagente(rid, dados, responsavel, acao="Edição"):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM reagentes WHERE id=?", (rid,)).fetchone()
        if row is None:
            return False
        old = dict(row); now = datetime.now().astimezone().isoformat(timespec="seconds")
        fields = ["nome","categoria","quantidade","unidade","local","validade","status","observacoes"]
        conn.execute("""UPDATE reagentes SET nome=?,categoria=?,quantidade=?,unidade=?,local=?,validade=?,status=?,observacoes=?,updated_at=?,updated_by=? WHERE id=?""",
            tuple(dados[f] for f in fields)+(now,responsavel,rid))
        changes = {f:{"antes":old.get(f),"depois":dados[f]} for f in fields if old.get(f)!=dados[f]}
        if changes:
            registrar_historico(conn,rid,dados["nome"],acao,responsavel,changes)
        conn.commit()
        return True
    finally:
        conn.close()


def excluir_reagente(rid, responsavel):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM reagentes WHERE id=?",(rid,)).fetchone()
        if row is None:
            return False
        item=dict(row); registrar_historico(conn,rid,item["nome"],"Exclusão",responsavel,{"reagente removido":item})
        conn.execute("DELETE FROM reagentes WHERE id=?",(rid,)); conn.commit()
        return True
    finally:
        conn.close()


def carregar_historico():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM historico ORDER BY id DESC LIMIT ?", (LIMITE_HISTORICO,)).fetchall()]


def dados_para_edicao(item, quantidade):
    return {"nome":item["nome"],"categoria":item.get("categoria") or "Geral","quantidade":quantidade,
        "unidade":item.get("unidade") or "unidade","local":item.get("local") or "","validade":item.get("validade") or "",
        "status":item.get("status") or "Disponível","observacoes":item.get("observacoes") or ""}


st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
st.markdown("""
<style>
.stApp {background-color:#efeee9;background-image:linear-gradient(rgba(245,244,239,.88),rgba(245,244,239,.88)),url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='320' viewBox='0 0 320 320'%3E%3Cpath fill='none' stroke='%237b8a82' stroke-opacity='.22' stroke-width='3' stroke-linecap='round' stroke-linejoin='round' d='M70 42h46M82 42v70L48 174a18 18 0 0 0 15 28h40l24 48M217 42h-46M168 42v70l34 62a18 18 0 0 1-15 28h-40l-27 44M210 42l18 80M150 122h56M142 84h76M243 132h38M222 174h60M115 224h60M124 182h-32M272 72l-16 18M195 192l-24 30M120 77l18-22M11 172h34M57 228h18'/%3E%3C/svg%3E");background-repeat:repeat;background-size:320px 320px}
[data-testid="stHeader"]{background:rgba(245,244,239,.72)}
[data-testid="stSidebar"]{background:rgba(226,228,221,.90)}
[data-testid="stMetric"],[data-testid="stExpander"],[data-testid="stForm"]{background:rgba(255,255,252,.82);border:1px solid rgba(113,127,118,.22);border-radius:14px}
[data-testid="stMetric"]{padding:14px 16px}[data-testid="stForm"]{padding:18px}
[data-testid="stFormSubmitButton"] button, [data-testid="stButton"] button {border-radius:10px;font-weight:600;transition:all .2s ease}
[data-testid="stFormSubmitButton"] button:hover, [data-testid="stButton"] button:hover {border-color:#5b9b8a;color:#276b5c;transform:translateY(-1px);box-shadow:0 4px 12px rgba(39,107,92,.16)}
</style>
""", unsafe_allow_html=True)
init_db()
st.markdown("<div style='text-align:center;padding:1rem;color:#48564f;font-size:1.12rem;font-style:italic'>🧪 “Na natureza nada se cria, nada se perde, tudo se transforma.” ⚗️</div>", unsafe_allow_html=True)
with st.sidebar:
    st.subheader("🧑‍🔬 Identificação do responsável")
    responsavel_atual = st.text_input("Seu nome", key="responsavel_sessao").strip() or "Usuário"
    st.divider()
    st.subheader("📄 Guia de segurança / FISPQ")
    if PDF_GUIA.is_file():
        st.download_button("📥 Baixar guia FISPQ", data=PDF_GUIA.read_bytes(), file_name=PDF_GUIA.name, mime="application/pdf", use_container_width=True)
    else:
        st.warning("PDF do guia não encontrado na pasta do projeto.")
st.title("🧪 LabInv — Controle de Estoque de Reagentes Químicos")
st.caption("Inventário de laboratório")
registros = listar_reagentes()
c1,c2,c3 = st.columns(3)
c1.metric("🧫 Reagentes cadastrados",len(registros))
c2.metric("⚖️ Quantidade total",sum(float(i["quantidade"] or 0) for i in registros))
c3.metric("🧪 Reagentes básicos",sum(i["nome"] in reagentes_basicos for i in registros))
st.caption(f"Limite do inventário: {len(registros)}/{LIMITE_REAGENTES} reagentes")

aba_lista,aba_retirada,aba_devolucao,aba_cadastro,aba_historico = st.tabs(["📋 Lista","📤 Retirar","📥 Devolver / repor","➕ Cadastrar","🕘 Histórico"])

with aba_lista:
    with st.expander("🧪 Mostrar / ocultar lista de reagentes", expanded=False):
        with st.form("form_busca_lista", clear_on_submit=False):
            termo = st.text_input("🔎 Buscar pelo nome ou parte do nome", key="busca_lista")
            buscar = st.form_submit_button("🔎 Buscar", use_container_width=True)
        resultados = buscar_reagente(termo.strip()) if buscar and termo.strip() else (listar_reagentes() if not termo.strip() else buscar_reagente(termo.strip()))
        if resultados:
            tabela=[]
            for item in resultados:
                cls=ReagenteBasico if item["nome"] in reagentes_basicos else ReagentePersonalizado
                linha=cls(item["nome"],item["quantidade"]).exibir_detalhes()
                linha.update({"Categoria":item.get("categoria") or "Geral","Unidade":item.get("unidade") or "unidade","Local":item.get("local") or "","Validade":item.get("validade") or "","Status":item.get("status") or "Disponível","Atualizado em":item.get("updated_at") or "","Responsável":item.get("updated_by") or ""})
                tabela.append(linha)
            st.dataframe(pd.DataFrame(tabela),use_container_width=True,hide_index=True)
            st.caption(f"✅ Total de reagentes exibidos: {len(resultados)}")
        else:
            st.info("🔎 Nenhum reagente encontrado.")

with aba_retirada:
    st.subheader("📤 Retirada de reagente")
    with st.form("form_retirada"):
        term=st.text_input("🔎 Nome ou parte do nome",key="termo_retirada"); candidatos=buscar_reagente(term) if term.strip() else listar_reagentes()
        if candidatos:
            nome=st.selectbox("🧪 Reagente",[x["nome"] for x in candidatos],key="nome_retirada"); quantidade=st.number_input("📏 Quantidade a retirar",min_value=0.1,value=1.0,step=0.5); confirmar=st.form_submit_button("📤 Confirmar retirada")
            if confirmar:
                item=next(x for x in listar_reagentes() if x["nome"]==nome); saldo=float(item["quantidade"] or 0)
                if saldo>=quantidade:
                    dados=dados_para_edicao(item,saldo-quantidade); atualizar_reagente(item["id"],dados,responsavel_atual,"Retirada"); st.success(f"✅ Retirada realizada. Saldo: {dados['quantidade']} {item.get('unidade') or 'unidade'}."); st.rerun()
                else: st.error(f"⚠️ Estoque insuficiente. Disponível: {saldo:g} {item.get('unidade') or 'unidade'}.")
        else: st.info("🔎 Nenhum reagente encontrado."); st.form_submit_button("📤 Confirmar retirada",disabled=True)

with aba_devolucao:
    st.subheader("📥 Devolução ou reposição de reagente")
    with st.form("form_devolucao"):
        term=st.text_input("🔎 Nome ou parte do nome",key="termo_devolucao"); candidatos=buscar_reagente(term) if term.strip() else listar_reagentes()
        if candidatos:
            nome=st.selectbox("🧪 Reagente",[x["nome"] for x in candidatos],key="nome_devolucao"); quantidade=st.number_input("📏 Quantidade a devolver / repor",min_value=0.1,value=1.0,step=0.5); confirmar=st.form_submit_button("📥 Confirmar devolução")
            if confirmar:
                item=next(x for x in listar_reagentes() if x["nome"]==nome); saldo=float(item["quantidade"] or 0)+quantidade
                atualizar_reagente(item["id"],dados_para_edicao(item,saldo),responsavel_atual,"Devolução / reposição"); st.success(f"✅ Devolução registrada. Novo saldo: {saldo:g} {item.get('unidade') or 'unidade'}."); st.rerun()
        else: st.info("🔎 Nenhum reagente encontrado."); st.form_submit_button("📥 Confirmar devolução",disabled=True)

with aba_cadastro:
    st.subheader("➕ Cadastrar reagente personalizado")
    if len(registros) >= LIMITE_REAGENTES:
        st.warning(f"Limite atingido: o inventário aceita até {LIMITE_REAGENTES} reagentes.")
    else:
        with st.form("form_cadastro",clear_on_submit=True):
            nome_novo=st.text_input("🧪 Nome e fórmula do reagente"); categoria=st.selectbox("🏷️ Categoria",["Solvente","Ácido","Base","Indicador","Sal","Outro"]); quantidade_nova=st.number_input("📏 Quantidade inicial",min_value=0.0,value=2.0,step=0.5); unidade=st.selectbox("📏 Unidade",["mL","g","mg","L","kg","unidade"]); local=st.text_input("📍 Local de armazenamento"); validade=st.date_input("📅 Validade (opcional)",value=None); status=st.selectbox("🧪 Status",["Disponível","Baixo","Vencido","Em uso"]); observacoes=st.text_area("📝 Observações"); cadastrar=st.form_submit_button("Cadastrar reagente")
            if cadastrar:
                nome_novo=nome_novo.strip()
                if not nome_novo: st.error("⚠️ O nome não pode ficar vazio.")
                elif len(listar_reagentes()) >= LIMITE_REAGENTES: st.error(f"⚠️ Limite de {LIMITE_REAGENTES} reagentes atingido.")
                elif any(x["nome"].casefold()==nome_novo.casefold() for x in listar_reagentes()): st.warning("⚠️ Esse reagente já está cadastrado.")
                else:
                    try:
                        if cadastrar_reagente(nome_novo,categoria,quantidade_nova,unidade,local.strip(),validade.isoformat() if validade else "",status,observacoes.strip(),responsavel_atual):
                            st.success("✅ Reagente cadastrado com sucesso."); st.rerun()
                        else: st.error(f"⚠️ Limite de {LIMITE_REAGENTES} reagentes atingido.")
                    except sqlite3.IntegrityError: st.error("⚠️ Não foi possível cadastrar: já existe um reagente com esse nome.")
    st.divider(); st.subheader("✏️ Editar ou excluir reagente"); atual=listar_reagentes()
    if atual:
        por_nome={x["nome"]:x for x in atual}; selecionado=st.selectbox("🧪 Selecione um reagente",list(por_nome),key="selecionar_edicao"); item=por_nome[selecionado]
        with st.form("form_edicao"):
            nome_editado=st.text_input("Nome",value=item["nome"]); categorias=["Solvente","Ácido","Base","Indicador","Sal","Outro","Geral"]; cat_atual=item.get("categoria") or "Geral"
            if cat_atual not in categorias: categorias.append(cat_atual)
            categoria_editada=st.selectbox("🏷️ Categoria",categorias,index=categorias.index(cat_atual)); quantidade_editada=st.number_input("📏 Quantidade",min_value=0.0,value=float(item["quantidade"] or 0),step=0.5); unidades=["mL","g","mg","L","kg","unidade"]; un_atual=item.get("unidade") or "unidade"; unidade_editada=st.selectbox("📏 Unidade",unidades,index=unidades.index(un_atual) if un_atual in unidades else 5); local_editado=st.text_input("📍 Local",value=item.get("local") or ""); validade_editada=st.text_input("📅 Validade",value=item.get("validade") or ""); statuses=["Disponível","Baixo","Vencido","Em uso"]; status_atual=item.get("status") or "Disponível"; status_ed=st.selectbox("🧪 Status",statuses,index=statuses.index(status_atual) if status_atual in statuses else 0); obs_editadas=st.text_area("📝 Observações",value=item.get("observacoes") or ""); salvar=st.form_submit_button("💾 Salvar alterações"); excluir=st.form_submit_button("🗑️ Excluir reagente")
            if salvar:
                if not nome_editado.strip(): st.error("⚠️ O nome não pode ficar vazio.")
                else:
                    dados={"nome":nome_editado.strip(),"categoria":categoria_editada,"quantidade":quantidade_editada,"unidade":unidade_editada,"local":local_editado.strip(),"validade":validade_editada.strip(),"status":status_ed,"observacoes":obs_editadas.strip()}
                    try: atualizar_reagente(item["id"],dados,responsavel_atual); st.success("✅ Reagente atualizado."); st.rerun()
                    except sqlite3.IntegrityError: st.error("⚠️ Já existe outro reagente com esse nome.")
            if excluir: excluir_reagente(item["id"],responsavel_atual); st.success("🗑️ Reagente excluído e registrado no histórico."); st.rerun()

with aba_historico:
    st.subheader(f"🕘 Histórico de alterações (últimos {LIMITE_HISTORICO} registros)"); eventos=carregar_historico()
    if not eventos: st.info("📭 Ainda não há operações registradas.")
    else:
        filtro=st.text_input("🔎 Filtrar histórico por reagente ou responsável",key="busca_historico"); hist=pd.DataFrame(eventos)
        if filtro.strip(): hist=hist[hist["nome_reagente"].str.contains(filtro.strip(),case=False,na=False)|hist["responsavel"].str.contains(filtro.strip(),case=False,na=False)]
        hist=hist.rename(columns={"data_hora":"Data e hora","responsavel":"Responsável","acao":"Operação","nome_reagente":"Reagente","detalhes":"Detalhes da alteração"})
        st.dataframe(hist[["Data e hora","Responsável","Operação","Reagente","Detalhes da alteração"]],use_container_width=True,hide_index=True)
