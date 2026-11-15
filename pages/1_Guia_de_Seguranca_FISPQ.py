from pathlib import Path

import streamlit as st


st.set_page_config(page_title="Guia de segurança | LabInv", page_icon="📄", layout="wide")

st.title("📄 Guia básico de segurança química")
st.write(
    "Acesse o guia básico de segurança química disponibilizado com o LabInv. "
    "Use o botão abaixo para baixar o PDF."
)

pdf_path = Path(__file__).resolve().parents[1] / "pdfGuia_Basico_Seguranca_Quimica_30_Reagentes.pdf"

if pdf_path.is_file():
    pdf_bytes = pdf_path.read_bytes()
    st.download_button(
        label="📥 Baixar guia básico de segurança / FISPQ",
        data=pdf_bytes,
        file_name=pdf_path.name,
        mime="application/pdf",
        use_container_width=True,
    )
else:
    st.error("O PDF do guia não foi encontrado na pasta principal do projeto.")

st.info(
    "Este guia é material de orientação geral. Consulte também a FISPQ específica "
    "e atualizada do fabricante para cada reagente e siga os procedimentos do laboratório."
)
