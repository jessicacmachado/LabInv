import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Buscar reagentes | LabInv", page_icon="🔎", layout="wide")
st.title("🔎 Buscar reagentes")
st.caption("Pesquise pelo nome completo ou por parte do nome do reagente.")

with st.form("form_busca_reagentes"):
    termo = st.text_input("Nome ou parte do nome", placeholder="Ex.: ácido, etanol, HCl")
    buscar = st.form_submit_button("🔎 Buscar", type="primary")

if buscar:
    db_path = Path(__file__).resolve().parents[1] / "labinv.db"
    if not db_path.is_file():
        st.info("O banco de dados ainda não foi criado. Abra primeiro a página principal do LabInv.")
    else:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            encontrados = conn.execute(
                "SELECT nome, categoria, quantidade, unidade, local, validade, status "
                "FROM reagentes WHERE nome LIKE ? ORDER BY id",
                (f"%{termo.strip()}%",),
            ).fetchall()

        if encontrados:
            st.success(f"Encontrados: {len(encontrados)}")
            st.dataframe(pd.DataFrame([dict(row) for row in encontrados]), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum reagente corresponde à busca.")
