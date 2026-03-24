import streamlit as st
from core.database import consultar

@st.cache_data(ttl=600)
def carregar():
    return consultar("SELECT COUNT(*) as total FROM backlog_atual")

def render():
    st.markdown("## <i class='fas fa-tachometer-alt'></i> Torre de Controle", unsafe_allow_html=True)

    df = carregar()

    total = int(df["total"].iloc[0]) if not df.empty else 0

    st.markdown(f"""
    <div class="card">
        <h3>Total de Pedidos</h3>
        <h1>{total}</h1>
    </div>
    """, unsafe_allow_html=True)