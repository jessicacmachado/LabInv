import sqlite3

import pandas as pd
import streamlit as st

DB_NAME = "estoque_reagentes.db"

REAGENTES_BASICOS = [
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


class Reagente:
    """Representa um reagente e sua quantidade disponível."""

    def __init__(self, nome, quantidade):
        self.nome = nome
        self.quantidade = quantidade

    def detalhes(self):
        return {"Nome": self.nome, "Quantidade disponível": self.quantidade}


class ReagenteBasico(Reagente):
    def detalhes(self):
        return {"Nome": self.nome, "Tipo": "Reagente básico", "Quantidade disponível": self.quantidade}


class ReagentePersonalizado(Reagente):
    def detalhes(self):
        return {"Nome": self.nome, "Tipo": "Reagente personalizado", "Quantidade disponível": self.quantidade}


class BancoEstoque:
    def __init__(self):
        self.conexao = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.execute(
            """CREATE TABLE IF NOT EXISTS reagentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                quantidade REAL NOT NULL,
                tipo TEXT NOT NULL
            )"""
        )
        self.conexao.commit()
        self.inicializar_estoque(REAGENTES_BASICOS)

    def inicializar_estoque(self, lista_reagentes):
        self.conexao.executemany(
            "INSERT OR IGNORE INTO reagentes (nome, quantidade, tipo) VALUES (?, ?, ?)",
            [(nome, 2, "basico") for nome in lista_reagentes],
        )
        self.conexao.commit()

    def listar_reagentes(self):
        return self.conexao.execute(
            "SELECT nome, quantidade, tipo FROM reagentes ORDER BY id"
        ).fetchall()

    def buscar_reagente(self, parte_nome):
        return self.conexao.execute(
            "SELECT nome FROM reagentes WHERE nome LIKE ? ORDER BY id",
            (f"%{parte_nome}%",),
        ).fetchall()

    def obter_reagente(self, nome):
        return self.conexao.execute(
            "SELECT nome, quantidade, tipo FROM reagentes WHERE nome = ?", (nome,)
        ).fetchone()

    def atualizar_quantidade(self, nome, quantidade):
        self.conexao.execute(
            "UPDATE reagentes SET quantidade = ? WHERE nome = ?", (quantidade, nome)
        )
        self.conexao.commit()

    def cadastrar_reagente(self, nome):
        self.conexao.execute(
            "INSERT INTO reagentes (nome, quantidade, tipo) VALUES (?, ?, ?)",
            (nome, 2, "personalizado"),
        )
        self.conexao.commit()

    def fechar(self):
        self.conexao.close()


st.set_page_config(page_title="LabInv — Controle de Reagentes", page_icon="🧪", layout="wide")
st.title("🧪 LabInv — Controle de Estoque de Reagentes")
st.caption("Inventário de reagentes químicos | Estoque inicial de 30 reagentes")

@st.cache_resource
def obter_banco():
    return BancoEstoque()

banco = obter_banco()
registros = banco.listar_reagentes()

# A classe correspondente a cada registro mantém a demonstração de herança e polimorfismo.
detalhes = []
for registro in registros:
    classe = ReagenteBasico if registro["tipo"] == "basico" else ReagentePersonalizado
    detalhes.append(classe(registro["nome"], registro["quantidade"]).detalhes())
df = pd.DataFrame(detalhes)

col1, col2, col3 = st.columns(3)
col1.metric("Reagentes cadastrados", len(registros))
col2.metric("Quantidade total em estoque", f"{sum(float(r['quantidade']) for r in registros):g}")
col3.metric("Reagentes básicos", sum(1 for r in registros if r["tipo"] == "basico"))

tab_lista, tab_retirada, tab_devolucao, tab_cadastro = st.tabs(
    ["📋 Lista de reagentes", "📤 Retirar", "📥 Devolver / repor", "➕ Cadastrar"]
)

with tab_lista:
    st.subheader("Reagentes cadastrados")
    pesquisa = st.text_input("Buscar por nome", key="busca_reagente")
    if pesquisa:
        encontrados = banco.buscar_reagente(pesquisa)
        nomes_encontrados = {r["nome"] for r in encontrados}
        df_exibicao = df[df["Nome"].isin(nomes_encontrados)]
    else:
        df_exibicao = df
    if df_exibicao.empty:
        st.info("Nenhum reagente encontrado.")
    else:
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    st.caption("Os 30 reagentes iniciais entram no estoque com quantidade 2, como no programa original.")

with tab_retirada:
    st.subheader("Retirada de reagente")
    with st.form("form_retirada"):
        termo = st.text_input("Digite o nome ou parte do nome", key="termo_retirada")
        candidatos = [r["nome"] for r in banco.buscar_reagente(termo)] if termo else [r["nome"] for r in registros]
        if candidatos:
            selecionado = st.selectbox("Reagente", candidatos, key="reagente_retirada")
            qtd = st.number_input("Quantidade a retirar", min_value=0.1, value=1.0, step=0.5, key="qtd_retirada")
            enviar_retirada = st.form_submit_button("Confirmar retirada")
            if enviar_retirada:
                reagente = banco.obter_reagente(selecionado)
                if reagente and reagente["quantidade"] >= qtd:
                    banco.atualizar_quantidade(selecionado, reagente["quantidade"] - qtd)
                    st.success(f"Retirada realizada. Saldo: {reagente['quantidade'] - qtd:g}")
                    st.rerun()
                else:
                    disponivel = reagente["quantidade"] if reagente else 0
                    st.error(f"Estoque insuficiente. Disponível: {disponivel:g}")
        else:
            st.warning("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar retirada", disabled=True)

with tab_devolucao:
    st.subheader("Devolução ou reposição de reagente")
    with st.form("form_devolucao"):
        termo = st.text_input("Digite o nome ou parte do nome", key="termo_devolucao")
        candidatos = [r["nome"] for r in banco.buscar_reagente(termo)] if termo else [r["nome"] for r in registros]
        if candidatos:
            selecionado = st.selectbox("Reagente", candidatos, key="reagente_devolucao")
            qtd = st.number_input("Quantidade a devolver / repor", min_value=0.1, value=1.0, step=0.5, key="qtd_devolucao")
            enviar_devolucao = st.form_submit_button("Confirmar devolução")
            if enviar_devolucao:
                reagente = banco.obter_reagente(selecionado)
                nova_quantidade = reagente["quantidade"] + qtd
                banco.atualizar_quantidade(selecionado, nova_quantidade)
                st.success(f"Devolução registrada. Novo saldo: {nova_quantidade:g}")
                st.rerun()
        else:
            st.warning("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar devolução", disabled=True)

with tab_cadastro:
    st.subheader("Cadastrar reagente personalizado")
    with st.form("form_cadastro"):
        nome_novo = st.text_input("Nome e fórmula do reagente")
        enviar_cadastro = st.form_submit_button("Cadastrar com quantidade inicial 2")
        if enviar_cadastro:
            nome_novo = nome_novo.strip()
            if not nome_novo:
                st.error("O nome não pode ficar vazio.")
            elif banco.obter_reagente(nome_novo):
                st.warning("Esse reagente já está cadastrado.")
            else:
                banco.cadastrar_reagente(nome_novo)
                st.success(f"Reagente cadastrado: {nome_novo} (quantidade inicial: 2)")
                st.rerun()
