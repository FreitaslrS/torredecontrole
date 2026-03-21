import streamlit as st

from pages import home, backlog, devolucoes, importacao, produtividade

from core.database import inicializar_banco

inicializar_banco()

st.set_page_config(
    page_title="Control Tower Logística",
    layout="wide"
)

menu = st.sidebar.radio(
    "📊 Menu",
    ["Home", "Backlog", "Produtividade", "Devoluções", "Importação"]
)

if menu == "Home":
    home.render()

elif menu == "Backlog":
    backlog.render()

elif menu == "Produtividade":
    produtividade.render()

elif menu == "Devoluções":
    devolucoes.render()

elif menu == "Importação":
    importacao.render()