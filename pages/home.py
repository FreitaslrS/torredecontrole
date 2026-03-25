import streamlit as st
from core.database import consultar

@st.cache_data(ttl=600)
def carregar():
    return consultar("SELECT COUNT(*) as total FROM backlog_atual")

def render():
    st.markdown("## <i class='fas fa-tachometer-alt'></i> Torre de Controle / 控制塔", unsafe_allow_html=True)

    df = carregar()

    total = int(df["total"].iloc[0]) if not df.empty else 0
