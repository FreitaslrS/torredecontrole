import streamlit as st
from core.repository import buscar_pedidos


@st.cache_data(ttl=300)
def carregar():
    return buscar_pedidos()


def render():
    st.title("🚀 Torre de Controle Logística")

    df = carregar()

    if df.empty:
        st.warning("Sem dados carregados.")
        return

    total = len(df)

    col1 = st.columns(1)[0]
    col1.metric("📦 Total Pedidos", total)