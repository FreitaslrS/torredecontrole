import streamlit as st
import plotly.express as px
from core.repository import (
    buscar_backlog_resumo,
    buscar_backlog_paginado,
    contar_backlog,
    buscar_backlog_por_estado,
    buscar_backlog_por_cliente,
    buscar_top10_pre_entrega
)

COR_VERDE = "#16A34A"
COR_CINZA = "#6B7280"


def render():

    st.markdown("""
    ## <i class='fas fa-box'></i> Backlog Atual / 当前积压
    <p style='opacity:0.7'>Monitoramento em tempo real da operação / 实时运营监控</p>
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

    def cor_kpi(valor, total):
        perc_local = valor / total if total else 0
        if perc_local > 0.3:
            return "🔴"
        elif perc_local > 0.15:
            return "🟡"
        else:
            return "🟢"

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total / 总计", total)
    col2.metric(">24h / 超过24小时", f"{cor_kpi(b24, total)} {b24}")
    col3.metric(">48h / 超过48小时", f"{cor_kpi(b48, total)} {b48}")
    col4.metric(">72h / 超过72小时", f"{cor_kpi(b72, total)} {b72}")
    col5.metric("% crítico / 关键比例", f"{perc:.1f}%")

    if perc > 30:
        st.error("🚨 Backlog crítico! / 积压严重！")
    elif perc > 15:
        st.warning("⚠️ Backlog em atenção / 积压需关注")
    else:
        st.success("✅ Operação controlada / 运营正常")

    st.divider()

    # =========================
    # 🎛️ FILTROS GLOBAIS
    # =========================
    st.subheader("🎛️ Filtros Globais / 全局筛选")

    "Estados / 州"
    "Clientes / 客户"

    col_f1, col_f2 = st.columns(2)

    estados = col_f1.multiselect(
        "Estados",
        options=sorted(df_resumo["estado"].unique())
    )

    clientes = col_f2.multiselect(
        "Clientes",
        options=sorted(df_resumo["cliente"].unique())
    )

    # =========================
    # 📊 DADOS
    # =========================
    df_estado = buscar_backlog_por_estado(clientes=clientes)
    df_cliente = buscar_backlog_por_cliente(estados=estados)
    df_pre = buscar_top10_pre_entrega()

    # =========================
    # 📊 CRIA OS GRÁFICOS PRIMEIRO
    # =========================
    fig_estado = px.bar(
        df_estado.sort_values("qtd", ascending=False),
        x="estado",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_VERDE]
    )

    fig_cliente = px.bar(
        df_cliente.sort_values("qtd", ascending=False),
        x="cliente",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_VERDE]
    )

    # =========================
    # 📊 EXIBE
    # =========================
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📊 Estado / 州")
        st.plotly_chart(fig_estado, use_container_width=True)

        estado_select = st.selectbox(
            "Ver detalhe por estado",
            options=df_estado["estado"]
        )

    with col_g2:
        st.subheader("📊 Cliente / 客户")
        st.plotly_chart(fig_cliente, use_container_width=True)

    # =========================
    # 📦 DETALHE FULL WIDTH
    # =========================
    st.divider()

    st.subheader(f"📦 Detalhamento / 详细数据 - {estado_select}")

    df_detalhe = buscar_backlog_paginado(estados=[estado_select])

    st.dataframe(df_detalhe, use_container_width=True)

    # =========================
    # 🚚 PRÉ ENTREGA
    # =========================
    st.subheader("📊 Top 10 Pré-entrega / 预交付前10")

    fig_pre = px.bar(
        df_pre,
        x="qtd",
        y="pre_entrega",
        orientation="h",
        text="qtd",
        color_discrete_sequence=[COR_CINZA]
    )

    fig_pre.update_layout(yaxis=dict(autorange="reversed"))

    st.plotly_chart(fig_pre, use_container_width=True)

    st.divider()

    # =========================
    # 📦 TABELA
    # =========================
    if st.button("📦 Carregar pedidos / 加载订单 (modo pesado)"):
        df = buscar_backlog_paginado(limit=100)
        st.dataframe(df, use_container_width=True)