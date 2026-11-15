import json
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_NAME = "labinv.db"

REAGENTES_BASICOS = [
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


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria ou atualiza as tabelas sem apagar registros existentes."""
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
    existentes = {row["name"] for row in conn.execute("PRAGMA table_info(reagentes)")}
    colunas = {
        "categoria": "TEXT", "quantidade": "REAL NOT NULL DEFAULT 2",
        "unidade": "TEXT DEFAULT 'unidade'", "local": "TEXT DEFAULT ''",
        "validade": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'Disponível'",
        "observacoes": "TEXT DEFAULT ''", "created_at": "TEXT",
        "updated_at": "TEXT", "updated_by": "TEXT",
    }
    for nome, tipo in colunas.items():
        if nome not in existentes:
            conn.execute(f"ALTER TABLE reagentes ADD COLUMN {nome} {tipo}")

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
    total = conn.execute("SELECT COUNT(*) FROM reagentes").fetchone()[0]
    if total == 0:
        conn.executemany(
            """INSERT OR IGNORE INTO reagentes
               (nome, categoria, quantidade, unidade, local, validade, status,
                observacoes, created_at, updated_at, updated_by)
               VALUES (?, 'Geral', 2, 'unidade', 'Estoque inicial', '',
                       'Disponível', 'Reagente básico do programa original', ?, ?, 'Sistema')""",
            [(nome, agora, agora) for nome in REAGENTES_BASICOS],
        )
    conn.commit()
    conn.close()


def listar_reagentes():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM reagentes ORDER BY nome")]


def registrar_uso(reagente, quantidade, responsavel):
    """Baixa o estoque e registra quem utilizou o reagente."""
    conn = get_connection()
    try:
        item = conn.execute(
            "SELECT * FROM reagentes WHERE id = ?", (reagente["id"],)
        ).fetchone()
        if item is None:
            return False, "Reagente não encontrado. Atualize a página e tente novamente."
        saldo = float(item["quantidade"] or 0)
        if quantidade <= 0:
            return False, "A quantidade precisa ser maior que zero."
        if quantidade > saldo:
            return False, f"Estoque insuficiente. Disponível: {saldo:g} {item['unidade'] or 'unidade'}."

        novo_saldo = saldo - quantidade
        agora = datetime.now().astimezone().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE reagentes SET quantidade = ?, updated_at = ?, updated_by = ? WHERE id = ?",
            (novo_saldo, agora, responsavel, item["id"]),
        )
        detalhes = {
            "quantidade utilizada": quantidade,
            "unidade": item["unidade"] or "unidade",
            "saldo anterior": saldo,
            "saldo atualizado": novo_saldo,
        }
        conn.execute(
            """INSERT INTO historico
               (reagente_id, nome_reagente, acao, data_hora, responsavel, detalhes)
               VALUES (?, ?, 'Uso', ?, ?, ?)""",
            (item["id"], item["nome"], agora, responsavel, json.dumps(detalhes, ensure_ascii=False)),
        )
        conn.commit()
        return True, f"Uso registrado. Saldo atualizado: {novo_saldo:g} {item['unidade'] or 'unidade'}."
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def carregar_historico():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT data_hora, nome_reagente, responsavel, detalhes FROM historico ORDER BY id DESC LIMIT 100"
        )]


st.set_page_config(page_title="LabInv — Registro de uso", page_icon="🧪", layout="wide")
init_db()
st.title("🧪 LabInv — Registro de uso de reagentes")
st.caption("Registre o reagente utilizado, a quantidade e o nome de quem fez o uso.")

registros = listar_reagentes()
if not registros:
    st.warning("Não há reagentes cadastrados no estoque.")
    st.stop()

with st.form("form_registro_uso"):
    opcoes = {f"{item['nome']} — saldo: {float(item['quantidade'] or 0):g} {item.get('unidade') or 'unidade'}": item
              for item in registros}
    reagente_label = st.selectbox("Reagente utilizado", list(opcoes))
    responsavel = st.text_input("Nome de quem usou o reagente")
    item_selecionado = opcoes[reagente_label]
    saldo_atual = float(item_selecionado["quantidade"] or 0)
    quantidade = st.number_input(
        f"Quantidade utilizada ({item_selecionado.get('unidade') or 'unidade'})",
        min_value=0.1, max_value=max(saldo_atual, 0.1), value=min(1.0, max(saldo_atual, 0.1)), step=0.1,
    )
    enviar = st.form_submit_button("Registrar uso")

if enviar:
    if not responsavel.strip():
        st.error("Informe o nome de quem utilizou o reagente.")
    elif saldo_atual <= 0:
        st.error("Este reagente está sem estoque disponível.")
    else:
        sucesso, mensagem = registrar_uso(item_selecionado, quantidade, responsavel.strip())
        if sucesso:
            st.success(mensagem)
            st.rerun()
        else:
            st.error(mensagem)

st.divider()
st.subheader("Estoque atual")
st.dataframe(
    pd.DataFrame([
        {"Reagente": item["nome"], "Quantidade": item["quantidade"],
         "Unidade": item.get("unidade") or "unidade", "Última atualização": item.get("updated_at") or ""}
        for item in listar_reagentes()
    ]),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Últimos registros de uso")
historico = [evento for evento in carregar_historico() if evento["responsavel"]]
if historico:
    tabela_historico = []
    for evento in historico:
        try:
            detalhes = json.loads(evento["detalhes"])
        except (TypeError, json.JSONDecodeError):
            detalhes = {}
        tabela_historico.append({
            "Data e hora": evento["data_hora"],
            "Reagente": evento["nome_reagente"],
            "Quem usou": evento["responsavel"],
            "Quantidade utilizada": f"{detalhes.get('quantidade utilizada', '')} {detalhes.get('unidade', '')}".strip(),
        })
    st.dataframe(pd.DataFrame(tabela_historico), use_container_width=True, hide_index=True)
else:
    st.info("Ainda não há registros de uso.")
