import streamlit as st
import plotly.express as px
from core.repository import (
    buscar_backlog_resumo,
    buscar_backlog_paginado,
    contar_backlog
)

COR_VERDE = "#16A34A"
COR_CINZA = "#6B7280"


def render():

    st.markdown("""
    ## <i class='fas fa-box'></i> Backlog Atual
    <p style='opacity:0.7'>Monitoramento em tempo real da operação</p>
    """, unsafe_allow_html=True)

    df_resumo = buscar_backlog_resumo()

    if df_resumo.empty:
        st.warning("Sem dados")
        return

    # =========================
    # 📊 KPIs
    # =========================
    total = df_resumo["qtd"].sum()
    b24 = df_resumo["b24"].sum()
    b48 = df_resumo["b48"].sum()
    b72 = df_resumo["b72"].sum()

    perc = (b72 / total * 100) if total else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total", total)
    col2.metric(">24h", b24)
    col3.metric(">48h", b48)
    col4.metric(">72h", b72)
    col5.metric("% crítico", f"{perc:.1f}%")

    st.divider()

    # =========================
    # 🗺️ ESTADO
    # =========================
    df_estado = df_resumo.groupby("estado")["qtd"].sum().reset_index()

    fig_estado = px.bar(
        df_estado.sort_values("qtd", ascending=False),
        x="estado",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_VERDE]
    )

    st.plotly_chart(fig_estado, use_container_width=True)

    # =========================
    # 🚚 PRÉ ENTREGA
    # =========================
    df_pre = df_resumo.groupby("pre_entrega")["qtd"].sum().reset_index()

    fig_pre = px.bar(
        df_pre.sort_values("qtd", ascending=False),
        x="pre_entrega",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_CINZA]
    )

    st.plotly_chart(fig_pre, use_container_width=True)

    st.divider()

    # =========================
    # 🚀 LAZY LOADING + PAGINAÇÃO
    # =========================
    if "carregar_detalhes" not in st.session_state:
        st.session_state.carregar_detalhes = False

    if st.button("📦 Carregar pedidos (modo pesado)"):
        st.session_state.carregar_detalhes = True

    if st.session_state.carregar_detalhes:

        total_reg = contar_backlog()["total"].iloc[0]

        page_size = 100
        total_paginas = (total_reg // page_size) + 1

        pagina = st.number_input("Página", 1, total_paginas, 1)

        offset = (pagina - 1) * page_size

        df = buscar_backlog_paginado(page_size, offset)

        st.dataframe(df, use_container_width=True)

        st.caption(f"Página {pagina} de {total_paginas} | Total: {total_reg}")

        if st.button("📥 Exportar CSV (página atual)"):
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "backlog.csv", "text/csv")