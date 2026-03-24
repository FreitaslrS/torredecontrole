import streamlit as st
import plotly.express as px
from core.repository import buscar_backlog_historico


def render():

    st.markdown("""
    ## <i class='fas fa-chart-line'></i> Backlog Histórico
    <p style='opacity:0.7'>Evolução do backlog ao longo do tempo</p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    data_inicio = col1.date_input("Data início")
    data_fim = col2.date_input("Data fim")

    if not data_inicio or not data_fim:
        return

    df = buscar_backlog_historico(data_inicio, data_fim)

    if df.empty:
        st.warning("Sem dados")
        return

    # =========================
    # 📈 EVOLUÇÃO
    # =========================
    df_tempo = df.groupby("data_referencia")["qtd"].sum().reset_index()

    fig = px.line(df_tempo, x="data_referencia", y="qtd", markers=True)

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # 🗺️ ESTADO
    # =========================
    df_estado = df.groupby("estado")["qtd"].sum().reset_index()

    fig_estado = px.bar(
        df_estado.sort_values("qtd", ascending=False),
        x="estado",
        y="qtd"
    )

    st.plotly_chart(fig_estado, use_container_width=True)

    # =========================
    # 🚚 PRÉ ENTREGA
    # =========================
    df_pre = df.groupby("pre_entrega")["qtd"].sum().reset_index()

    fig_pre = px.bar(
        df_pre.sort_values("qtd", ascending=False).head(10),
        x="pre_entrega",
        y="qtd"
    )

    st.plotly_chart(fig_pre, use_container_width=True)