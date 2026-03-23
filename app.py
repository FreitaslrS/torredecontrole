import streamlit as st

import os

import psycopg2

st.write("DATABASE_URL:", os.getenv("DATABASE_URL"))
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    st.success("✅ Conectou no Postgres")
    conn.close()
except Exception as e:
    st.error(f"❌ Erro conexão: {e}")

from pages import home, backlog, devolucoes, importacao, produtividade

from core.database import inicializar_banco

import streamlit as st
from core.database import consultar  # 👈 adiciona isso

df_teste = consultar("SELECT COUNT(*) as total FROM pedidos")
st.write("🧪 TESTE BANCO:", df_teste)

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

    from core.database import consultar
