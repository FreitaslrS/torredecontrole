import streamlit as st
import pandas as pd
import plotly.express as px
from core.repository import buscar_backlog_atual

COR_VERDE = "#16A34A"
COR_VERMELHO = "#DC2626"
COR_CINZA = "#6B7280"


def render():

    st.markdown("""
    ## <i class='fas fa-box'></i> Backlog Atual
    <p style='opacity:0.7'>Monitoramento em tempo real da operação</p>
    """, unsafe_allow_html=True)

    df = buscar_backlog_atual()

    if df.empty:
        st.warning("Sem dados")
        return

    # =========================
    # 🎛️ FILTRO EXCEL STYLE
    # =========================
    col1, col2 = st.columns(2)

    estados = sorted(df["estado"].dropna().unique())
    remover_estados = col1.multiselect("❌ Remover Estados", estados)

    clientes = sorted(df["cliente"].dropna().unique())
    remover_clientes = col2.multiselect("❌ Remover Clientes", clientes)

    if remover_estados:
        df = df[~df["estado"].isin(remover_estados)]

    if remover_clientes:
        df = df[~df["cliente"].isin(remover_clientes)]

    # =========================
    # ⏱️ FAIXA
    # =========================
    faixa = st.radio("Faixa", ["Todos", "24h+", "48h+", "72h+"], horizontal=True)

    if faixa == "24h+":
        df = df[df["horas_backlog_snapshot"] > 24]
    elif faixa == "48h+":
        df = df[df["horas_backlog_snapshot"] > 48]
    elif faixa == "72h+":
        df = df[df["horas_backlog_snapshot"] > 72]

    # =========================
    # 📊 KPIs
    # =========================
    total = len(df)
    b24 = len(df[df["horas_backlog_snapshot"] > 24])
    b48 = len(df[df["horas_backlog_snapshot"] > 48])
    b72 = len(df[df["horas_backlog_snapshot"] > 72])

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
    st.subheader("🗺️ Backlog por Estado")

    df_estado = df.groupby("estado").size().reset_index(name="qtd")

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
    st.subheader("🚚 Backlog por Pré-Entrega")

    df_pre = df.groupby("pre_entrega").size().reset_index(name="qtd")

    fig_pre = px.bar(
        df_pre.sort_values("qtd", ascending=False).head(10),
        x="pre_entrega",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_CINZA]
    )

    st.plotly_chart(fig_pre, use_container_width=True)

    # =========================
    # 👤 CLIENTES
    # =========================
    st.subheader("👤 Backlog por Cliente")

    df_cliente = df.groupby("cliente").size().reset_index(name="qtd")

    fig_cliente = px.bar(
        df_cliente.sort_values("qtd", ascending=False),
        x="cliente",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_VERDE]
    )

    st.plotly_chart(fig_cliente, use_container_width=True)

    st.divider()
    st.dataframe(df, use_container_width=True)