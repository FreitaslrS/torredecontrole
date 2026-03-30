import streamlit as st
from core.repository import buscar_pedidos


def render():
    st.markdown("## <i class='fas fa-undo'></i> Devoluções / 退货", unsafe_allow_html=True)

    from core.repository import buscar_devolucoes

    df = buscar_devolucoes(2000)

    if df.empty:
        st.warning("Sem dados carregados.")
        return

    st.dataframe(df)