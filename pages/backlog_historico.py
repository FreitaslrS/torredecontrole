import streamlit as st
import plotly.express as px
from core.repository import buscar_backlog_historico


# =========================
# 🎨 CORES DA EMPRESA
# =========================
COR_PRINCIPAL = "#16A34A"
COR_SECUNDARIA = "#22C55E"
COR_DESTAQUE = "#15803D"
COR_CINZA = "#6B7280"


def render():

    st.markdown("""
    ## <i class='fas fa-chart-line'></i> Backlog Histórico / 历史积压
    <p style='opacity:0.7'>Evolução do backlog ao longo do tempo / 积压趋势变化</p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    data_inicio = col1.date_input("Data início / 开始日期")
    data_fim = col2.date_input("Data fim / 结束日期")

    if not data_inicio or not data_fim:
        return

    df = buscar_backlog_historico(data_inicio, data_fim)

    if df.empty:
        st.warning("Sem dados")
        return

    # =========================
    # 🎛️ FILTROS
    # =========================
    st.subheader("🎛️ Filtros / 筛选")

    col_f1, col_f2 = st.columns(2)

    estados = col_f1.multiselect(
        "Estados / 州",
        options=sorted(df["estado"].unique())
    )

    clientes = col_f2.multiselect(
        "Clientes / 客户",
        options=sorted(df["cliente"].unique())
    )

    if estados:
        df = df[df["estado"].isin(estados)]

    if clientes:
        df = df[df["cliente"].isin(clientes)]

    # =========================
    # 🧠 KPI POR FAIXA DE DIAS
    # =========================
    st.subheader("📊 Faixa de Backlog (dias) / 积压区间（天）")

    if "horas_backlog_snapshot" in df.columns:
        df["dias"] = df["horas_backlog_snapshot"] / 24
    else:
        st.warning("Coluna horas_backlog_snapshot não encontrada")
        df["dias"] = 0

    d1 = df[df["dias"] <= 1].shape[0]
    d1_5 = df[(df["dias"] > 1) & (df["dias"] <= 5)].shape[0]
    d5_10 = df[(df["dias"] > 5) & (df["dias"] <= 10)].shape[0]
    d10_20 = df[(df["dias"] > 10) & (df["dias"] <= 20)].shape[0]
    d30 = df[df["dias"] > 30].shape[0]

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("1 dia / 1天", d1)
    col2.metric("1-5 dias / 1-5天", d1_5)
    col3.metric("5-10 dias / 5-10天", d5_10)
    col4.metric("10-20 dias / 10-20天", d10_20)
    col5.metric("30+ dias / 30+天", d30)

    st.divider()

    # =========================
    # 📈 EVOLUÇÃO
    # =========================
    df_tempo = df.groupby("data_referencia").size().reset_index(name="qtd")

    fig_linha = px.line(
        df_tempo,
        x="data_referencia",
        y="qtd",
        markers=True
    )

    fig_linha.update_traces(line_color=COR_PRINCIPAL)

    st.plotly_chart(fig_linha, use_container_width=True)

    st.divider()

    # =========================
    # 📊 AGRUPAMENTOS
    # =========================
    df_estado = df.groupby("estado").size().reset_index(name="qtd")
    df_cliente = df.groupby("cliente").size().reset_index(name="qtd")
    df_pre = df.groupby("pre_entrega").size().reset_index(name="qtd").sort_values("qtd", ascending=False).head(10)

    # =========================
    # 📊 GRÁFICOS LADO A LADO
    # =========================
    col_g1, col_g2 = st.columns(2)

    fig_estado = px.bar(
        df_estado.sort_values("qtd", ascending=False),
        x="estado",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_PRINCIPAL]
    )

    fig_cliente = px.bar(
        df_cliente.sort_values("qtd", ascending=False),
        x="cliente",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_SECUNDARIA]
    )

    with col_g1:
        st.subheader("📊 Estado / 州")
        st.plotly_chart(fig_estado, use_container_width=True)

    with col_g2:
        st.subheader("📊 Cliente / 客户")
        st.plotly_chart(fig_cliente, use_container_width=True)

    # =========================
    # 🚚 PRÉ ENTREGA
    # =========================
    st.subheader("📊 Top 10 Pré-entrega / 前10预交付")

    fig_pre = px.bar(
        df_pre,
        x="qtd",
        y="pre_entrega",
        orientation="h",
        text="qtd",
        color_discrete_sequence=[COR_DESTAQUE]
    )

    fig_pre.update_layout(yaxis=dict(autorange="reversed"))

    st.plotly_chart(fig_pre, use_container_width=True)