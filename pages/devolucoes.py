import streamlit as st
from core.repository import buscar_pedidos


def render():
    st.markdown("## <i class='fas fa-undo'></i> Devoluções", unsafe_allow_html=True)

    df = buscar_pedidos(2000)

    if df.empty:
        st.warning("Sem dados carregados.")
        return

    st.dataframe(df)