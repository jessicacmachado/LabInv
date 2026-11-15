# LabInv — Controle de Estoque de Reagentes Químicos
import io
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


# BLOCO 1 - CLASSES
# A classe Reagente representa os dados gerais do item.
# As classes filhas mostram detalhes específicos para reagente básico e personalizado.
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


# BLOCO 2 - CONEXÃO COM O BANCO
# sqlite3.connect abre ou cria o arquivo `labinv.db`.
# row_factory transforma cada linha em um dicionário para facilitar leitura.
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# BLOCO 3 - CRIAÇÃO DO BANCO E TABELAS
# init_db cria a tabela `reagentes` e `historico` se elas ainda não existirem.
def init_db():
    conn = get_connection()
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
        [(name, now, now) for name in reagentes_basicos])
    conn.commit(); conn.close()


# BLOCO 4 - LEITURA E BUSCA DOS DADOS
# listar_reagentes busca todos os itens cadastrados no banco.
# buscar_reagente usa LIKE para procurar parte do nome.
def listar_reagentes():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reagentes ORDER BY id").fetchall()]


def buscar_reagente(termo):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM reagentes WHERE nome LIKE ? ORDER BY id", (f"%{termo}%",)).fetchall()]


# BLOCO 5 - HISTÓRICO DE OPERAÇÕES
# registrar_historico grava cada retirada, devolução, edição e exclusão.
def registrar_historico(conn, rid, nome, acao, responsavel, detalhes):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute("INSERT INTO historico (reagente_id,nome_reagente,acao,data_hora,responsavel,detalhes) VALUES (?,?,?,?,?,?)",
        (rid, nome, acao, now, responsavel, json.dumps(detalhes, ensure_ascii=False)))


def carregar_historico():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM historico ORDER BY id DESC").fetchall()]


# BLOCO 6 - CADASTRO, ALTERAÇÃO E EXCLUSÃO
# O `local` foi removido da interface de cadastro porque ele não é uma opção de armazenamento.
# Ele permanece no banco apenas para manutenção de dados antigos.
def cadastrar_reagente(nome, categoria, quantidade, unidade, local, validade, status, observacoes, responsavel):
    conn = get_connection(); now = datetime.now().astimezone().isoformat(timespec="seconds")
    cur = conn.execute("""INSERT INTO reagentes (nome,categoria,quantidade,unidade,local,validade,status,observacoes,created_at,updated_at,updated_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (nome,categoria,quantidade,unidade,local,validade,status,observacoes,now,now,responsavel))
    registrar_historico(conn, cur.lastrowid, nome, "Cadastro", responsavel, {"quantidade inicial":quantidade,"unidade":unidade})
    conn.commit(); conn.close()


def atualizar_reagente(rid, dados, responsavel, acao="Edição"):
    conn = get_connection(); row = conn.execute("SELECT * FROM reagentes WHERE id=?", (rid,)).fetchone()
    if row is None:
        conn.close(); return False
    old = dict(row); now = datetime.now().astimezone().isoformat(timespec="seconds")
    fields = ["nome","categoria","quantidade","unidade","local","validade","status","observacoes"]
    conn.execute("""UPDATE reagentes SET nome=?,categoria=?,quantidade=?,unidade=?,local=?,validade=?,status=?,observacoes=?,updated_at=?,updated_by=? WHERE id=?""",
        tuple(dados[f] for f in fields)+(now,responsavel,rid))
    changes = {f:{"antes":old.get(f),"depois":dados[f]} for f in fields if old.get(f)!=dados[f]}
    if changes: registrar_historico(conn,rid,dados["nome"],acao,responsavel,changes)
    conn.commit(); conn.close(); return True


def excluir_reagente(rid, responsavel):
    conn = get_connection(); row = conn.execute("SELECT * FROM reagentes WHERE id=?",(rid,)).fetchone()
    if row is None:
        conn.close(); return False
    item=dict(row); registrar_historico(conn,rid,item["nome"],"Exclusão",responsavel,{"reagente removido":item})
    conn.execute("DELETE FROM reagentes WHERE id=?",(rid,)); conn.commit(); conn.close(); return True


def dados_para_edicao(item, quantidade):
    return {"nome":item["nome"],"categoria":item.get("categoria") or "Geral","quantidade":quantidade,
        "unidade":item.get("unidade") or "unidade","local":item.get("local") or "","validade":item.get("validade") or "",
        "status":item.get("status") or "Disponível","observacoes":item.get("observacoes") or ""}


# BLOCO 7 - EXPORTAÇÃO DO HISTÓRICO PARA EXCEL
# `pd.ExcelWriter` cria a planilha e `st.download_button` envia o arquivo ao navegador.
def exportar_historico_excel(eventos):
    df = pd.DataFrame(eventos)
    if df.empty:
        df = pd.DataFrame(columns=["id","reagente_id","nome_reagente","acao","data_hora","responsavel","detalhes"])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Historico")
    buffer.seek(0)
    return buffer.getvalue()


# BLOCO 8 - CÁLCULOS DOS MÉTRICOS DA TELA INICIAL
# Os indicadores da tela devem refletir o estado real do banco, sem duplicar itens e sem somar valores inválidos.
def somar_total_unidades(registros):
    total = 0.0
    for item in registros:
        try:
            valor = float(item.get("quantidade") or 0)
            if valor >= 0:
                total += valor
        except (TypeError, ValueError):
            continue
    return total


def contar_reagentes_basicos(registros):
    nomes = {item.get("nome") for item in registros if item.get("nome")}
    return sum(1 for nome in nomes if nome in reagentes_basicos)


# BLOCO 9 - CONFIGURAÇÃO DA PÁGINA STREAMLIT
st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
st.markdown("""
<style>
.stApp {background-color:#efeee9;background-image:linear-gradient(rgba(245,244,239,.88),rgba(245,244,239,.88)),url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='320' viewBox='0 0 320 320'%3E%3Cg fill='%23dfe5d9'%3E%3Ccircle cx='40' cy='40' r='2'/%3E%3Ccircle cx='100' cy='80' r='2'/%3E%3Ccircle cx='220' cy='60' r='2'/%3E%3Ccircle cx='280' cy='140' r='2'/%3E%3Ccircle cx='50' cy='200' r='2'/%3E%3Ccircle cx='180' cy='180' r='2'/%3E%3Ccircle cx='260' cy='240' r='2'/%3E%3Ccircle cx='110' cy='260' r='2'/%3E%3C/g%3E%3C/svg%3E");}
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

# BLOCO 10 - SIDEBAR COM RESPONSÁVEL
with st.sidebar:
    st.subheader("🧑‍🔬 Identificação do responsável")
    responsavel_atual = st.text_input("Seu nome", key="responsavel_sessao").strip() or "Usuário"

    # Aviso importante para o usuário.
    st.warning("⚠️ Não use a pasta temporária do sistema como destino de backup. Salve os arquivos em pendrive, disco local ou pasta na nuvem.")

st.title("🧪 LabInv — Controle de Estoque de Reagentes Químicos")
st.caption("Inventário de laboratório")
registros = listar_reagentes()
quantidade_total = somar_total_unidades(registros)
reagentes_basicos_cadastrados = contar_reagentes_basicos(registros)

c1,c2,c3 = st.columns(3)
c1.metric("🧫 Reagentes cadastrados",len(registros))
c2.metric("⚖️ Unidades totais em estoque",round(quantidade_total, 2))
c3.metric("🧪 Reagentes básicos cadastrados",reagentes_basicos_cadastrados)

aba_lista,aba_retirada,aba_devolucao,aba_cadastro,aba_historico = st.tabs(["📋 Lista","📤 Retirar","📥 Devolver / repor","➕ Cadastrar","🕘 Histórico"])

with aba_lista:
    with st.expander("🧪 Mostrar / ocultar lista de reagentes", expanded=False):
        termo=st.text_input("🔎 Buscar pelo nome ou parte do nome",key="busca_lista")
        resultados=buscar_reagente(termo) if termo.strip() else listar_reagentes()
        if resultados:
            tabela=[]
            for item in resultados:
                cls=ReagenteBasico if item["nome"] in reagentes_basicos else ReagentePersonalizado
                linha=cls(item["nome"],item["quantidade"]).exibir_detalhes()
                linha.update({"Categoria":item.get("categoria") or "Geral","Unidade":item.get("unidade") or "unidade","Local":item.get("local") or "","Validade":item.get("validade") or "","Status":item.get("status") or "Disponível","Observações":item.get("observacoes") or "","Criado em":item.get("created_at") or "","Atualizado em":item.get("updated_at") or "","Atualizado por":item.get("updated_by") or ""})
                tabela.append(linha)
            st.dataframe(pd.DataFrame(tabela),use_container_width=True,hide_index=True)
            st.caption(f"✅ Total de reagentes exibidos: {len(resultados)}")
        else: st.info("🔎 Nenhum reagente encontrado.")

with aba_retirada:
    st.subheader("📤 Retirada de reagente")
    with st.form("form_retirada"):
        term=st.text_input("🔎 Nome ou parte do nome",key="termo_retirada"); candidatos=buscar_reagente(term) if term.strip() else listar_reagentes()
        if candidatos:
            nome=st.selectbox("🧪 Reagente",[x["nome"] for x in candidatos],key="nome_retirada"); quantidade=st.number_input("📏 Quantidade a retirar",min_value=0.1,value=1.0,step=0.5); confirmar=st.form_submit_button("📤 Confirmar retirada")
            if confirmar:
                item=next(x for x in listar_reagentes() if x["nome"]==nome); saldo=float(item["quantidade"] or 0)
                if saldo>=quantidade:
                    dados=dados_para_edicao(item,saldo-quantidade); atualizar_reagente(item["id"],dados,responsavel_atual,"Retirada"); st.success(f"✅ Retirada realizada. Saldo: {dados['quantidade']:.2f} {item.get('unidade') or 'unidade'}.")
                else: st.error(f"⚠️ Estoque insuficiente. Disponível: {saldo:g} {item.get('unidade') or 'unidade'}.")
        else: st.info("🔎 Nenhum reagente encontrado."); st.form_submit_button("📤 Confirmar retirada",disabled=True)

with aba_devolucao:
    st.subheader("📥 Devolução ou reposição de reagente")
    with st.form("form_devolucao"):
        term=st.text_input("🔎 Nome ou parte do nome",key="termo_devolucao"); candidatos=buscar_reagente(term) if term.strip() else listar_reagentes()
        if candidatos:
            nome=st.selectbox("🧪 Reagente",[x["nome"] for x in candidatos],key="nome_devolucao"); quantidade=st.number_input("📏 Quantidade a devolver / repor",min_value=0.1,value=1.0,step=0.5); confirmar=st.form_submit_button("📥 Confirmar devolução")
            if confirmar:
                item=next(x for x in listar_reagentes() if x["nome"]==nome); saldo=float(item["quantidade"] or 0)+quantidade; dados=dados_para_edicao(item,saldo); atualizar_reagente(item["id"],dados,responsavel_atual,"Devolução / reposição"); st.success(f"✅ Devolução registrada. Novo saldo: {saldo:g} {item.get('unidade') or 'unidade'}.")
        else: st.info("🔎 Nenhum reagente encontrado."); st.form_submit_button("📥 Confirmar devolução",disabled=True)

with aba_cadastro:
    st.subheader("➕ Cadastrar reagente personalizado")
    with st.form("form_cadastro",clear_on_submit=True):
        nome_novo=st.text_input("🧪 Nome e fórmula do reagente")
        categoria=st.selectbox("🏷️ Categoria",["Solvente","Ácido","Base","Indicador","Sal","Outro"])
        quantidade_nova=st.number_input("📏 Quantidade inicial",min_value=0.0,value=2.0,step=0.5)
        unidade=st.text_input("📏 Unidade",value="unidade")
        validade=st.date_input("📅 Validade",value=None)
        status=st.selectbox("📌 Status",["Disponível","Reservado","Baixo estoque","Em manutenção"])
        observacoes=st.text_area("📝 Observações",value="")
        cadastrar=st.form_submit_button("✅ Cadastrar")
        if cadastrar:
            nome_novo=nome_novo.strip()
            if not nome_novo: st.error("⚠️ O nome não pode ficar vazio.")
            elif any(x["nome"].casefold()==nome_novo.casefold() for x in listar_reagentes()): st.warning("⚠️ Esse reagente já está cadastrado.")
            else:
                try:
                    validade_text = validade.isoformat() if validade is not None else ""
                    cadastrar_reagente(nome_novo,categoria,quantidade_nova,unidade,"",validade_text,status,observacoes.strip(),responsavel_atual)
                    st.success(f"✅ Reagente cadastrado com sucesso: {nome_novo}")
                except sqlite3.IntegrityError: st.error("⚠️ Não foi possível cadastrar: já existe um reagente com esse nome.")

    st.divider(); st.subheader("✏️ Editar ou excluir reagente")
    atual=listar_reagentes()
    if atual:
        por_nome={x["nome"]:x for x in atual}; selecionado=st.selectbox("🧪 Selecione um reagente",list(por_nome),key="selecionar_edicao"); item=por_nome[selecionado]
        with st.form("form_edicao"):
            nome_editado=st.text_input("Nome",value=item["nome"])
            categorias=["Solvente","Ácido","Base","Indicador","Sal","Outro","Geral"]
            cat_atual=item.get("categoria") or "Geral"
            if cat_atual not in categorias: categorias.append(cat_atual)
            categoria_editada=st.selectbox("🏷️ Categoria",categorias,index=categorias.index(cat_atual))
            quantidade_editada=st.number_input("📏 Quantidade",min_value=0.0,value=float(item["quantidade"] or 0.0),step=0.5)
            unidade_editada=st.text_input("📏 Unidade",value=item.get("unidade") or "unidade")
            validade_editada=st.date_input("📅 Validade",value=datetime.strptime(item.get("validade") or "2000-01-01","%Y-%m-%d").date() if item.get("validade") else None)
            status_editado=st.selectbox("📌 Status",["Disponível","Reservado","Baixo estoque","Em manutenção"],index=["Disponível","Reservado","Baixo estoque","Em manutenção"].index(item.get("status") or "Disponível"))
            observacoes_editadas=st.text_area("📝 Observações",value=item.get("observacoes") or "")
            salvar=st.form_submit_button("💾 Salvar alterações")
            if salvar:
                if not nome_editado.strip(): st.error("⚠️ O nome não pode ficar vazio.")
                else:
                    dados={"nome":nome_editado.strip(),"categoria":categoria_editada,"quantidade":quantidade_editada,"unidade":unidade_editada,"local":item.get("local") or "","validade":validade_editada.isoformat() if validade_editada is not None else "","status":status_editado,"observacoes":observacoes_editadas.strip()}
                    try: atualizar_reagente(item["id"],dados,responsavel_atual); st.success("✅ Reagente atualizado."); st.rerun()
                    except sqlite3.IntegrityError: st.error("⚠️ Já existe outro reagente com esse nome.")
            excluir=st.form_submit_button("🗑️ Excluir reagente")
            if excluir: excluir_reagente(item["id"],responsavel_atual); st.success("🗑️ Reagente excluído e registrado no histórico."); st.rerun()

with aba_historico:
    st.subheader("🕘 Histórico completo de alterações")
    eventos=carregar_historico()
    if not eventos: st.info("📭 Ainda não há operações registradas.")
    else:
        st.info("💾 Este botão exporta o histórico para Excel. Salve o arquivo em pendrive, disco local ou pasta na nuvem. Não use a pasta temporária do sistema.")
        filtro=st.text_input("🔎 Filtrar histórico por reagente ou responsável",key="busca_historico")
        hist=pd.DataFrame(eventos)
        if filtro.strip(): hist=hist[hist["nome_reagente"].str.contains(filtro.strip(),case=False,na=False)|hist["responsavel"].str.contains(filtro.strip(),case=False,na=False)]
        hist=hist.rename(columns={"data_hora":"Data e hora","responsavel":"Responsável","acao":"Operação","nome_reagente":"Reagente","detalhes":"Detalhes da alteração"})
        st.dataframe(hist[["Data e hora","Responsável","Operação","Reagente","Detalhes da alteração"]],use_container_width=True,hide_index=True)
        st.download_button(
            label="📊 Exportar histórico para Excel",
            data=exportar_historico_excel(eventos),
            file_name=f"labinv_historico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Baixa o histórico completo em Excel. É melhor salvar em pendrive ou em uma pasta na nuvem."
        )

# Fim do programa
# Reagentes e histórico continuam sendo armazenados no banco SQLite `labinv.db`.
# O usuário pode baixar backups e relatórios externos, mas deve salvar fora da pasta temporária.
