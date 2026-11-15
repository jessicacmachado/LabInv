def obter_responsavel():
    """Retorna o usuário autenticado ou a identificação da sessão."""
    usuarios = {}
    try:
        usuarios = st.secrets.get("usuarios", {})
    except Exception:
        usuarios = {}
        with st.sidebar:
            st.warning("Arquivo de autenticação inválido. Usando modo sem login. Corrija .streamlit/secrets.toml.")

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
