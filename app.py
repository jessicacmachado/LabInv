import json
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"
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
    conn = get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS reagentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, categoria TEXT,
        quantidade REAL NOT NULL DEFAULT 2, unidade TEXT DEFAULT 'unidade', local TEXT DEFAULT '',
        validade TEXT DEFAULT '', status TEXT DEFAULT 'Disponível', observacoes TEXT DEFAULT '',
        created_at TEXT, updated_at TEXT, updated_by TEXT)""")
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(reagentes)").fetchall()}
    for name, kind in {
        "categoria":"TEXT", "quantidade":"REAL NOT NULL DEFAULT 2", "unidade":"TEXT DEFAULT 'unidade'",
        "local":"TEXT DEFAULT ''", "validade":"TEXT DEFAULT ''", "status":"TEXT DEFAULT 'Disponível'",
        "observacoes":"TEXT DEFAULT ''", "created_at":"TEXT", "updated_at":"TEXT", "updated_by":"TEXT",
    }.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE reagentes ADD COLUMN {name} {kind}")
    conn.execute("""CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, reagente_id INTEGER, nome_reagente TEXT NOT NULL,
        acao TEXT NOT NULL, data_hora TEXT NOT NULL, responsavel TEXT NOT NULL, detalhes TEXT NOT NULL)""")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute("UPDATE reagentes SET created_at=COALESCE(created_at, ?), updated_at=COALESCE(updated_at, ?), updated_by=COALESCE(updated_by, 'Registro anterior')", (now, now))
    if conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0] == 0:
        conn.executemany("""INSERT OR IGNORE INTO reagentes
            (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
            VALUES (?,'Geral',2,'unidade','Estoque inicial','','Disponível','Reagente básico do programa original',?,?,'Sistema')""",
            [(name, now, now) for name in reagentes_basicos])
    conn.commit(); conn.close()


def listar_reagentes():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reagentes ORDER BY id").fetchall()]


def buscar_reagente(term):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reagentes WHERE nome LIKE ? ORDER BY id", (f"%{term}%",)).fetchall()]


def registrar_historico(conn, rid, name, action, person, details):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute("INSERT INTO historico (reagente_id,nome_reagente,acao,data_hora,responsavel,detalhes) VALUES (?,?,?,?,?,?)",
                 (rid, name, action, now, person, json.dumps(details, ensure_ascii=False)))


def cadastrar_reagente(nome, categoria, quantidade, unidade, local, validade, status, observacoes, responsavel):
    conn = get_connection(); now = datetime.now().astimezone().isoformat(timespec="seconds")
    cur = conn.execute("""INSERT INTO reagentes (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (nome,categoria,quantidade,unidade,local,validade,status,observacoes,now,now,responsavel))
    registrar_historico(conn, cur.lastrowid, nome, "Cadastro", responsavel, {"quantidade inicial":quantidade,"unidade":unidade})
    conn.commit(); conn.close()


def atualizar_reagente(rid, data, person, action="Edição"):
    conn = get_connection(); row = conn.execute("SELECT * FROM reagentes WHERE id=?", (rid,)).fetchone()
    if row is None:
        conn.close(); return False
    old = dict(row); now = datetime.now().astimezone().isoformat(timespec="seconds")
    fields = ["nome","categoria","quantidade","unidade","local","validade","status","observacoes"]
    conn.execute("""UPDATE reagentes SET nome=?,categoria=?,quantidade=?,unidade=?,local=?,validade=?,status=?,observacoes=?,updated_at=?,updated_by=? WHERE id=?""",
                 tuple(data[f] for f in fields)+(now,person,rid))
    diffs = {f:{"antes":old.get(f),"depois":data[f]} for f in fields if old.get(f)!=data[f]}
    if diffs: registrar_historico(conn,rid,data["nome"],action,person,diffs)
    conn.commit(); conn.close(); return True


def excluir_reagente(rid, person):
    conn = get_connection(); row = conn.execute("SELECT * FROM reagentes WHERE id=?", (rid,)).fetchone()
    if row is None:
        conn.close(); return False
    item=dict(row); registrar_historico(conn,rid,item["nome"],"Exclusão",person,{"reagente removido":item})
    conn.execute("DELETE FROM reagentes WHERE id=?",(rid,)); conn.commit(); conn.close(); return True


def carregar_historico():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM historico ORDER BY id DESC").fetchall()]


st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
init_db()
with st.sidebar:
    st.subheader("Identificação do responsável")
    responsavel_atual = st.text_input("Seu nome", value="", key="responsavel_sessao").strip() or "Usuário"
st.title("🧪 LabInv — Controle de Estoque de Reagentes Químicos")
st.caption("Inventário de laboratório | Herança, polimorfismo e SQLite")
registros = listar_reagentes()
c1,c2,c3=st.columns(3)
c1.metric("Reagentes cadastrados",len(registros))
c2.metric("Quantidade total",sum(float(i["quantidade"] or 0) for i in registros))
c3.metric("Reagentes básicos",sum(i["nome"] in reagentes_basicos for i in registros))
aba_lista,aba_retirada,aba_devolucao,aba_cadastro,aba_historico=st.tabs(["📋 Lista","📤 Retirar","📥 Devolver / repor","➕ Cadastrar","🕘 Histórico"])

with aba_lista:
    # O expander funciona como botão: clique para abrir ou ocultar a lista.
    with st.expander("📋 Mostrar / ocultar lista de reagentes", expanded=False):
        st.subheader("Lista de reagentes cadastrados")
        term=st.text_input("Buscar pelo nome ou parte do nome",key="busca_lista")
        results=buscar_reagente(term) if term.strip() else listar_reagentes()
        if results:
            table=[]
            for item in results:
                cls=ReagenteBasico if item["nome"] in reagentes_basicos else ReagentePersonalizado
                line=cls(item["nome"],item["quantidade"]).exibir_detalhes()
                line.update({"Categoria":item.get("categoria") or "Geral","Unidade":item.get("unidade") or "unidade",
                    "Local":item.get("local") or "","Validade":item.get("validade") or "","Status":item.get("status") or "Disponível",
                    "Atualizado em":item.get("updated_at") or "","Responsável":item.get("updated_by") or ""})
                table.append(line)
            st.dataframe(pd.DataFrame(table),use_container_width=True,hide_index=True)
            st.caption(f"Total de reagentes exibidos: {len(results)}")
        else: st.info("Nenhum reagente encontrado.")

with aba_retirada:
    st.subheader("Retirada de reagente")
    with st.form("form_retirada"):
        term=st.text_input("Nome ou parte do nome",key="termo_retirada"); candidates=buscar_reagente(term) if term.strip() else listar_reagentes()
        if candidates:
            name=st.selectbox("Reagente",[x["nome"] for x in candidates],key="nome_retirada")
            qty=st.number_input("Quantidade a retirar",min_value=0.1,value=1.0,step=0.5); submit=st.form_submit_button("Confirmar retirada")
            if submit:
                item=next(x for x in listar_reagentes() if x["nome"]==name); balance=float(item["quantidade"] or 0)
                if balance>=qty:
                    data={"nome":item["nome"],"categoria":item.get("categoria") or "Geral","quantidade":balance-qty,"unidade":item.get("unidade") or "unidade","local":item.get("local") or "","validade":item.get("validade") or "","status":item.get("status") or "Disponível","observacoes":item.get("observacoes") or ""}
                    atualizar_reagente(item["id"],data,responsavel_atual,"Retirada"); st.success(f"Retirada realizada. Saldo: {data['quantidade']:g} {data['unidade']}."); st.rerun()
                else: st.error(f"Estoque insuficiente. Disponível: {balance:g} {item.get('unidade') or 'unidade'}.")
        else: st.info("Nenhum reagente encontrado com esse nome."); st.form_submit_button("Confirmar retirada",disabled=True)

with aba_devolucao:
    st.subheader("Devolução ou reposição de reagente")
    with st.form("form_devolucao"):
        term=st.text_input("Nome ou parte do nome",key="termo_devolucao"); candidates=buscar_reagente(term) if term.strip() else listar_reagentes()
        if candidates:
            name=st.selectbox("Reagente",[x["nome"] for x in candidates],key="nome_devolucao")
            qty=st.number_input("Quantidade a devolver / repor",min_value=0.1,value=1.0,step=0.5); submit=st.form_submit_button("Confirmar devolução")
            if submit:
                item=next(x for x in listar_reagentes() if x["nome"]==name)
                data={"nome":item["nome"],"categoria":item.get("categoria") or "Geral","quantidade":float(item["quantidade"] or 0)+qty,"unidade":item.get("unidade") or "unidade","local":item.get("local") or "","validade":item.get("validade") or "","status":item.get("status") or "Disponível","observacoes":item.get("observacoes") or ""}
                atualizar_reagente(item["id"],data,responsavel_atual,"Devolução / reposição"); st.success(f"Devolução registrada. Novo saldo: {data['quantidade']:g} {data['unidade']}."); st.rerun()
        else: st.info("Nenhum reagente encontrado com esse nome."); st.form_submit_button("Confirmar devolução",disabled=True)

with aba_cadastro:
    st.subheader("Cadastrar reagente personalizado")
    with st.form("form_cadastro",clear_on_submit=True):
        name=st.text_input("Nome e fórmula do reagente"); category=st.selectbox("Categoria",["Solvente","Ácido","Base","Indicador","Sal","Outro"])
        qty=st.number_input("Quantidade inicial",min_value=0.0,value=2.0,step=0.5); unit=st.selectbox("Unidade",["mL","g","mg","L","kg","unidade"])
        location=st.text_input("Local de armazenamento"); expiry=st.date_input("Validade (opcional)",value=None); status=st.selectbox("Status",["Disponível","Baixo","Vencido","Em uso"]); notes=st.text_area("Observações")
        submit=st.form_submit_button("Cadastrar reagente")
        if submit:
            name=name.strip()
            if not name: st.error("O nome não pode ficar vazio.")
            elif any(x["nome"].casefold()==name.casefold() for x in listar_reagentes()): st.warning("Esse reagente já está cadastrado.")
            else:
                try:
                    cadastrar_reagente(name,category,qty,unit,location.strip(),expiry.isoformat() if expiry else "",status,notes.strip(),responsavel_atual); st.success("Reagente cadastrado com sucesso."); st.rerun()
                except sqlite3.IntegrityError: st.error("Não foi possível cadastrar: já existe um reagente com esse nome.")
    st.divider(); st.subheader("Editar ou excluir reagente"); current=listar_reagentes()
    if current:
        by_name={x["nome"]:x for x in current}; chosen=st.selectbox("Selecione um reagente",list(by_name),key="selecionar_edicao"); item=by_name[chosen]
        with st.form("form_edicao"):
            edit_name=st.text_input("Nome",value=item["nome"]); categories=["Solvente","Ácido","Base","Indicador","Sal","Outro","Geral"]
            current_category=item.get("categoria") or "Geral"
            if current_category not in categories: categories.append(current_category)
            edit_category=st.selectbox("Categoria",categories,index=categories.index(current_category)); edit_qty=st.number_input("Quantidade",min_value=0.0,value=float(item["quantidade"] or 0),step=0.5)
            units=["mL","g","mg","L","kg","unidade"]; current_unit=item.get("unidade") or "unidade"
            edit_unit=st.selectbox("Unidade",units,index=units.index(current_unit) if current_unit in units else units.index("unidade")); edit_location=st.text_input("Local",value=item.get("local") or "")
            edit_expiry=st.text_input("Validade (AAAA-MM-DD)",value=item.get("validade") or ""); statuses=["Disponível","Baixo","Vencido","Em uso"]; current_status=item.get("status") or "Disponível"
            edit_status=st.selectbox("Status",statuses,index=statuses.index(current_status) if current_status in statuses else 0); edit_notes=st.text_area("Observações",value=item.get("observacoes") or "")
            save_col,delete_col=st.columns(2); save=save_col.form_submit_button("Salvar alterações"); delete=delete_col.form_submit_button("Excluir reagente")
            if save:
                if not edit_name.strip(): st.error("O nome não pode ficar vazio.")
                else:
                    data={"nome":edit_name.strip(),"categoria":edit_category,"quantidade":edit_qty,"unidade":edit_unit,"local":edit_location.strip(),"validade":edit_expiry.strip(),"status":edit_status,"observacoes":edit_notes.strip()}
                    try: atualizar_reagente(item["id"],data,responsavel_atual); st.success("Reagente atualizado. O histórico guarda os campos alterados."); st.rerun()
                    except sqlite3.IntegrityError: st.error("Já existe outro reagente com esse nome.")
            if delete: excluir_reagente(item["id"],responsavel_atual); st.success("Reagente excluído; a operação permanece registrada no histórico."); st.rerun()

with aba_historico:
    st.subheader("Histórico completo de alterações"); events=carregar_historico()
    if not events: st.info("Ainda não há operações registradas.")
    else:
        term=st.text_input("Filtrar histórico por reagente ou responsável",key="busca_historico"); hist=pd.DataFrame(events)
        if term.strip(): hist=hist[hist["nome_reagente"].str.contains(term.strip(),case=False,na=False)|hist["responsavel"].str.contains(term.strip(),case=False,na=False)]
        hist=hist.rename(columns={"data_hora":"Data e hora","responsavel":"Responsável","acao":"Operação","nome_reagente":"Reagente","detalhes":"Detalhes da alteração"})
        st.dataframe(hist[["Data e hora","Responsável","Operação","Reagente","Detalhes da alteração"]],use_container_width=True,hide_index=True)
