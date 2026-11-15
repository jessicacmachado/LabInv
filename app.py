# ==============================================================
# PROGRAMA: CONTROLE DE ESTOQUE DE REAGENTES QUÍMICOS
# Baseado no programa original do LabInv:
# herança, polimorfismo e banco de dados SQLite.
#
# ADAPTAÇÃO PARA STREAMLIT:
# O Streamlit substitui print()/input() por componentes visuais
# (st.write, st.text_input, st.form, st.tabs etc.). As funções
# originais de estoque e a lista de 30 reagentes são preservadas.
# ==============================================================

# ==============================================================
# BLOCO 0: IMPORTAÇÕES E CONFIGURAÇÕES
# ==============================================================

import json
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"

# ==============================================================
# BLOCO 1: CLASSES — HERANÇA E POLIMORFISMO
# Estas classes mantêm a estrutura conceitual do programa original.
# Na interface web, exibir_detalhes() devolve dados para a tabela,
# em vez de usar print() no terminal.
# ==============================================================

class Reagente:
    """Classe principal que representa um reagente."""

    def __init__(self, nome, quantidade):
        self.nome = nome
        self.quantidade = quantidade

    def exibir_detalhes(self):
        return {"Nome": self.nome, "Quantidade disponível": self.quantidade}


class ReagenteBasico(Reagente):
    """Reagente que pertence à lista inicial do projeto."""

    def exibir_detalhes(self):
        return {
            "Nome": self.nome,
            "Tipo": "Reagente básico",
            "Quantidade disponível": self.quantidade,
        }


class ReagentePersonalizado(Reagente):
    """Reagente cadastrado por uma pessoa usuária."""

    def exibir_detalhes(self):
        return {
            "Nome": self.nome,
            "Tipo": "Reagente personalizado",
            "Quantidade disponível": self.quantidade,
        }


# ==============================================================
# BLOCO 2: DADOS INICIAIS — LISTA ORIGINAL DOS 30 REAGENTES
# A lista e os nomes permanecem iguais aos do programa fornecido.
# ==============================================================

reagentes_basicos = [
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

# ==============================================================
# BLOCO 3: BANCO DE DADOS — CONEXÃO, MIGRAÇÃO E INICIALIZAÇÃO
# A migração acrescenta campos/tabela sem apagar os dados existentes.
# O histórico registra cada cadastro, edição, movimentação e exclusão.
# ==============================================================

def get_connection():
    """Abre uma conexão SQLite e permite acessar colunas pelo nome."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria tabelas e acrescenta campos ausentes sem recriar a base."""
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

    # Compatibilidade: adiciona apenas as colunas que não existirem
    # em bancos SQLite criados por versões anteriores do aplicativo.
    colunas_existentes = {
        linha["name"] for linha in conn.execute("PRAGMA table_info(reagentes)").fetchall()
    }
    colunas_novas = {
        "categoria": "TEXT",
        "quantidade": "REAL NOT NULL DEFAULT 2",
        "unidade": "TEXT DEFAULT 'unidade'",
        "local": "TEXT DEFAULT ''",
        "validade": "TEXT DEFAULT ''",
        "status": "TEXT DEFAULT 'Disponível'",
        "observacoes": "TEXT DEFAULT ''",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "updated_by": "TEXT",
    }
    for nome_coluna, tipo_coluna in colunas_novas.items():
        if nome_coluna not in colunas_existentes:
            conn.execute(f"ALTER TABLE reagentes ADD COLUMN {nome_coluna} {tipo_coluna}")

    # Tabela append-only: cada operação cria um registro, sem substituir
    # os eventos anteriores de auditoria.
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

    # Preenche metadados para registros antigos, sem alterar quantidade ou nome.
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute(
        """UPDATE reagentes
           SET created_at = COALESCE(created_at, ?),
               updated_at = COALESCE(updated_at, ?),
               updated_by = COALESCE(updated_by, 'Registro anterior')""",
        (agora, agora),
    )

    # Insere a lista original somente se a tabela estiver vazia.
    total = conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0]
    if total == 0:
        conn.executemany(
            """INSERT OR IGNORE INTO reagentes
               (nome, categoria, quantidade, unidade, local, validade, status,
                observacoes, created_at, updated_at, updated_by)
               VALUES (?, 'Geral', 2, 'unidade', 'Estoque inicial', '',
                       'Disponível', 'Reagente básico do programa original', ?, ?, 'Sistema')""",
            [(nome, agora, agora) for nome in reagentes_basicos],
        )

    conn.commit()
    conn.close()


# ==============================================================
# BLOCO 4: FUNÇÕES DE BANCO — LISTAR, BUSCAR, CADASTRAR E ALTERAR
# ==============================================================

def listar_reagentes():
    """Retorna todos os reagentes na ordem em que foram cadastrados."""
    conn = get_connection()
    resultados = conn.execute("SELECT * FROM reagentes ORDER BY id").fetchall()
    conn.close()
    return [dict(linha) for linha in resultados]


def buscar_reagente(parte_nome):
    """Busca reagentes por nome completo ou parcial."""
    conn = get_connection()
    resultados = conn.execute(
        "SELECT * FROM reagentes WHERE nome LIKE ? ORDER BY id",
        (f"%{parte_nome}%",),
    ).fetchall()
    conn.close()
    return [dict(linha) for linha in resultados]


def registrar_historico(conn, reagente_id, nome, acao, responsavel, detalhes):
    """Registra uma operação na tabela de auditoria dentro da mesma transação."""
    data_hora = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO historico
           (reagente_id, nome_reagente, acao, data_hora, responsavel, detalhes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (reagente_id, nome, acao, data_hora, responsavel, json.dumps(detalhes, ensure_ascii=False)),
    )
    return data_hora


def cadastrar_reagente(nome, categoria, quantidade, unidade, local, validade, status, observacoes, responsavel):
    """Cadastra reagente e registra o evento no histórico completo."""
    conn = get_connection()
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    cursor = conn.execute(
        """INSERT INTO reagentes
           (nome, categoria, quantidade, unidade, local, validade, status,
            observacoes, created_at, updated_at, updated_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nome, categoria, quantidade, unidade, local, validade, status,
         observacoes, agora, agora, responsavel),
    )
    registrar_historico(
        conn, cursor.lastrowid, nome, "Cadastro", responsavel,
        {"quantidade inicial": quantidade, "unidade": unidade},
    )
    conn.commit()
    conn.close()


def atualizar_reagente(reagente_id, dados_novos, responsavel, acao="Edição"):
    """Atualiza os campos do reagente e registra valores anteriores/novos."""
    conn = get_connection()
    anterior = conn.execute("SELECT * FROM reagentes WHERE id = ?", (reagente_id,)).fetchone()
    if anterior is None:
        conn.close()
        return False

    anterior = dict(anterior)
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.execute(
        """UPDATE reagentes
           SET nome=?, categoria=?, quantidade=?, unidade=?, local=?, validade=?,
               status=?, observacoes=?, updated_at=?, updated_by=?
           WHERE id=?""",
        (dados_novos["nome"], dados_novos["categoria"], dados_novos["quantidade"],
         dados_novos["unidade"], dados_novos["local"], dados_novos["validade"],
         dados_novos["status"], dados_novos["observacoes"], agora, responsavel, reagente_id),
    )
    campos = ["nome", "categoria", "quantidade", "unidade", "local", "validade", "status", "observacoes"]
    diferencas = {
        campo: {"antes": anterior.get(campo), "depois": dados_novos[campo]}
        for campo in campos
        if anterior.get(campo) != dados_novos[campo]
    }
    if diferencas:
        registrar_historico(conn, reagente_id, dados_novos["nome"], acao, responsavel, diferencas)
    conn.commit()
    conn.close()
    return True


def excluir_reagente(reagente_id, responsavel):
    """Registra a exclusão no histórico antes de remover o item do estoque."""
    conn = get_connection()
    item = conn.execute("SELECT * FROM reagentes WHERE id = ?", (reagente_id,)).fetchone()
    if item is None:
        conn.close()
        return False
    item = dict(item)
    registrar_historico(
        conn, reagente_id, item["nome"], "Exclusão", responsavel,
        {"reagente removido": item},
    )
    conn.execute("DELETE FROM reagentes WHERE id = ?", (reagente_id,))
    conn.commit()
    conn.close()
    return True


def carregar_historico():
    """Carrega eventos de auditoria do mais recente para o mais antigo."""
    conn = get_connection()
    linhas = conn.execute("SELECT * FROM historico ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(linha) for linha in linhas]


# ==============================================================
# BLOCO 5: ADAPTAÇÃO DO MENU DE TERMINAL PARA LOGIN STREAMLIT
#
# Se Streamlit Secrets contiver [usuarios], o formulário valida
# usuário e senha. Sem essa configuração, o campo de responsável é
# apenas uma identificação informada pela pessoa, NÃO autenticação.
# ==============================================================

def obter_responsavel():
    """Retorna o usuário autenticado ou a identificação da sessão."""
    usuarios = st.secrets.get("usuarios", {})
    if usuarios:
        if st.session_state.get("usuario_autenticado"):
            with st.sidebar:
                st.success(f"Conectado: {st.session_state['usuario_autenticado']}")
                if st.button("Sair", key="logout"):
                    del st.session_state["usuario_autenticado"]
                    st.rerun()
            return st.session_state["usuario_autenticado"]

        st.title("LabInv — Entrar")
        st.caption("Acesso ao sistema de inventário")
        with st.form("login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")
        if entrar:
            senha_correta = usuarios.get(usuario)
            if senha_correta is not None and senha == senha_correta:
                st.session_state["usuario_autenticado"] = usuario
                st.rerun()
            st.error("Usuário ou senha incorretos.")
        st.info("Configure as credenciais em Streamlit → App settings → Secrets, na seção [usuarios].")
        st.stop()

    # Modo de identificação sem autenticação, para manter o app utilizável
    # antes de configurar credenciais privadas no painel do Streamlit.
    with st.sidebar:
        st.subheader("Identificação do responsável")
        st.warning("Sem login configurado: o nome informado não é verificado.")
        responsavel = st.text_input("Seu nome", value="Usuário", key="responsavel_sessao")
    return responsavel.strip() or "Usuário"


# ==============================================================
# BLOCO 6: ADAPTAÇÃO DA TELA DE BOAS-VINDAS E MENU PARA STREAMLIT
# print()/input() do terminal são substituídos por título, abas,
# formulários, tabelas e mensagens do Streamlit.
# ==============================================================

st.set_page_config(page_title="LabInv", page_icon="🧪", layout="wide")
init_db()
responsavel_atual = obter_responsavel()
st.title("🧪 LabInv — Controle de Estoque de Reagentes Químicos")
st.caption("Inventário de laboratório | Herança, polimorfismo e SQLite")

# Recarrega a lista a cada execução Streamlit para mostrar as alterações recentes.
registros = listar_reagentes()
linhas_tabela = []
for item in registros:
    classe = ReagenteBasico if item["nome"] in reagentes_basicos else ReagentePersonalizado
    reagente = classe(item["nome"], item["quantidade"])
    linha = reagente.exibir_detalhes()
    linha.update({
        "Categoria": item.get("categoria") or "Geral",
        "Unidade": item.get("unidade") or "unidade",
        "Local": item.get("local") or "",
        "Validade": item.get("validade") or "",
        "Status": item.get("status") or "Disponível",
        "Atualizado em": item.get("updated_at") or "",
        "Responsável": item.get("updated_by") or "",
    })
    linhas_tabela.append(linha)
df = pd.DataFrame(linhas_tabela)

# Indicadores correspondem ao resumo da versão de terminal, agora exibidos na web.
col1, col2, col3 = st.columns(3)
col1.metric("Reagentes cadastrados", len(registros))
col2.metric("Quantidade total", sum(float(item["quantidade"] or 0) for item in registros))
col3.metric("Reagentes básicos", sum(item["nome"] in reagentes_basicos for item in registros))

# Abas Streamlit substituem as opções numeradas do menu original.
aba_lista, aba_retirada, aba_devolucao, aba_cadastro, aba_historico = st.tabs(
    ["📋 Lista", "📤 Retirar", "📥 Devolver / repor", "➕ Cadastrar", "🕘 Histórico"]
)

# ==============================================================
# BLOCO 7: OPÇÃO 1 DO MENU ORIGINAL — MOSTRAR E BUSCAR REAGENTES
# ==============================================================

with aba_lista:
    st.subheader("Lista de reagentes cadastrados")
    termo = st.text_input("Buscar pelo nome ou parte do nome", key="busca_lista")
    resultados = buscar_reagente(termo) if termo.strip() else listar_reagentes()
    if resultados:
        tabela = []
        for item in resultados:
            classe = ReagenteBasico if item["nome"] in reagentes_basicos else ReagentePersonalizado
            linha = classe(item["nome"], item["quantidade"]).exibir_detalhes()
            linha.update({
                "Categoria": item.get("categoria") or "Geral",
                "Unidade": item.get("unidade") or "unidade",
                "Local": item.get("local") or "",
                "Validade": item.get("validade") or "",
                "Status": item.get("status") or "Disponível",
                "Atualizado em": item.get("updated_at") or "",
                "Responsável": item.get("updated_by") or "",
            })
            tabela.append(linha)
        st.dataframe(pd.DataFrame(tabela), use_container_width=True, hide_index=True)
        st.caption(f"Total de reagentes exibidos: {len(resultados)}")
    else:
        st.info("Nenhum reagente encontrado.")

# ==============================================================
# BLOCO 8: OPÇÕES 2 E 3 DO MENU ORIGINAL — RETIRAR E DEVOLVER
# A alteração de quantidade é registrada como evento no histórico.
# ==============================================================

with aba_retirada:
    st.subheader("Retirada de reagente")
    with st.form("form_retirada"):
        termo_retirada = st.text_input("Nome ou parte do nome", key="termo_retirada")
        candidatos = buscar_reagente(termo_retirada) if termo_retirada.strip() else listar_reagentes()
        if candidatos:
            nomes = [item["nome"] for item in candidatos]
            nome_escolhido = st.selectbox("Reagente", nomes, key="nome_retirada")
            quantidade = st.number_input("Quantidade a retirar", min_value=0.1, value=1.0, step=0.5)
            confirmar = st.form_submit_button("Confirmar retirada")
            if confirmar:
                item = next(row for row in listar_reagentes() if row["nome"] == nome_escolhido)
                if float(item["quantidade"]) >= quantidade:
                    novos_dados = {
                        "nome": item["nome"], "categoria": item.get("categoria") or "Geral",
                        "quantidade": float(item["quantidade"]) - quantidade,
                        "unidade": item.get("unidade") or "unidade", "local": item.get("local") or "",
                        "validade": item.get("validade") or "", "status": item.get("status") or "Disponível",
                        "observacoes": item.get("observacoes") or "",
                    }
                    atualizar_reagente(item["id"], novos_dados, responsavel_atual, "Retirada")
                    st.success(f"Retirada realizada. Saldo: {novos_dados['quantidade']:g} {novos_dados['unidade']}.")
                    st.rerun()
                else:
                    st.error(f"Estoque insuficiente. Disponível: {item['quantidade']} {item.get('unidade') or 'unidade'}.")
        else:
            st.info("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar retirada", disabled=True)

with aba_devolucao:
    st.subheader("Devolução ou reposição de reagente")
    with st.form("form_devolucao"):
        termo_devolucao = st.text_input("Nome ou parte do nome", key="termo_devolucao")
        candidatos = buscar_reagente(termo_devolucao) if termo_devolucao.strip() else listar_reagentes()
        if candidatos:
            nomes = [item["nome"] for item in candidatos]
            nome_escolhido = st.selectbox("Reagente", nomes, key="nome_devolucao")
            quantidade = st.number_input("Quantidade a devolver / repor", min_value=0.1, value=1.0, step=0.5)
            confirmar = st.form_submit_button("Confirmar devolução")
            if confirmar:
                item = next(row for row in listar_reagentes() if row["nome"] == nome_escolhido)
                novos_dados = {
                    "nome": item["nome"], "categoria": item.get("categoria") or "Geral",
                    "quantidade": float(item["quantidade"]) + quantidade,
                    "unidade": item.get("unidade") or "unidade", "local": item.get("local") or "",
                    "validade": item.get("validade") or "", "status": item.get("status") or "Disponível",
                    "observacoes": item.get("observacoes") or "",
                }
                atualizar_reagente(item["id"], novos_dados, responsavel_atual, "Devolução / reposição")
                st.success(f"Devolução registrada. Novo saldo: {novos_dados['quantidade']:g} {novos_dados['unidade']}.")
                st.rerun()
        else:
            st.info("Nenhum reagente encontrado com esse nome.")
            st.form_submit_button("Confirmar devolução", disabled=True)

# ==============================================================
# BLOCO 9: OPÇÃO 4 DO MENU ORIGINAL — CADASTRO E EDIÇÃO
# Formulários Streamlit substituem os inputs de texto do terminal.
# ==============================================================

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
            elif any(item["nome"].casefold() == nome_novo.casefold() for item in listar_reagentes()):
                st.warning("Esse reagente já está cadastrado.")
            else:
                try:
                    cadastrar_reagente(
                        nome_novo, categoria_nova, quantidade_nova, unidade_nova,
                        local_novo.strip(), validade_nova.isoformat() if validade_nova else "",
                        status_novo, observacoes_novas.strip(), responsavel_atual,
                    )
                    st.success("Reagente cadastrado com sucesso.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Não foi possível cadastrar: já existe um reagente com esse nome.")

    st.divider()
    st.subheader("Editar ou excluir reagente")
    lista_atual = listar_reagentes()
    if lista_atual:
        ids_por_nome = {item["nome"]: item for item in lista_atual}
        nome_editar = st.selectbox("Selecione um reagente", list(ids_por_nome), key="selecionar_edicao")
        item = ids_por_nome[nome_editar]
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
            validade_atual = item.get("validade") or ""
            validade_editada = st.text_input("Validade (AAAA-MM-DD)", value=validade_atual)
            status_opcoes = ["Disponível", "Baixo", "Vencido", "Em uso"]
            status_atual = item.get("status") or "Disponível"
            status_editado = st.selectbox("Status", status_opcoes, index=status_opcoes.index(status_atual) if status_atual in status_opcoes else 0)
            observacoes_editadas = st.text_area("Observações", value=item.get("observacoes") or "")
            salvar, excluir = st.columns(2)
            salvar_clicado = salvar.form_submit_button("Salvar alterações")
            excluir_clicado = excluir.form_submit_button("Excluir reagente")

            if salvar_clicado:
                if not nome_editado.strip():
                    st.error("O nome não pode ficar vazio.")
                else:
                    dados = {
                        "nome": nome_editado.strip(), "categoria": categoria_editada,
                        "quantidade": quantidade_editada, "unidade": unidade_editada,
                        "local": local_editado.strip(), "validade": validade_editada.strip(),
                        "status": status_editado, "observacoes": observacoes_editadas.strip(),
                    }
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

# ==============================================================
# BLOCO 10: HISTÓRICO COMPLETO — DATA/HORA, RESPONSÁVEL E ALTERAÇÕES
# Ao contrário de mostrar somente a última modificação, esta aba
# preserva uma linha para cada operação realizada no aplicativo.
# ==============================================================

with aba_historico:
    st.subheader("Histórico completo de alterações")
    eventos = carregar_historico()
    if not eventos:
        st.info("Ainda não há operações registradas.")
    else:
        busca_historico = st.text_input("Filtrar histórico por reagente ou responsável", key="busca_historico")
        historico_df = pd.DataFrame(eventos)
        if busca_historico.strip():
            termo_busca = busca_historico.strip()
            mascara = (
                historico_df["nome_reagente"].str.contains(termo_busca, case=False, na=False)
                | historico_df["responsavel"].str.contains(termo_busca, case=False, na=False)
            )
            historico_df = historico_df[mascara]
        historico_df = historico_df.rename(columns={
            "data_hora": "Data e hora",
            "responsavel": "Responsável",
            "acao": "Operação",
            "nome_reagente": "Reagente",
            "detalhes": "Detalhes da alteração",
        })
        st.dataframe(
            historico_df[["Data e hora", "Responsável", "Operação", "Reagente", "Detalhes da alteração"]],
            use_container_width=True,
            hide_index=True,
        )

# ==============================================================
# FIM DO PROGRAMA
# ==============================================================
