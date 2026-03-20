import streamlit as st
import plotly.express as px
import plotly.io as pio
import pandas as pd

from core.service import tratar_backlog_periodo, tratar_backlog_atual

# =========================
# 🎨 CORES DA EMPRESA
# =========================
COR_VERDE = "#16A34A"
COR_VERMELHO = "#DC2626"
COR_CINZA = "#6B7280"

# =========================
# 🎨 TEMPLATE GLOBAL
# =========================
pio.templates["empresa"] = pio.templates["plotly"]
pio.templates["empresa"].layout.colorway = [
    COR_VERDE,
    COR_VERMELHO,
    COR_CINZA
]
pio.templates.default = "empresa"

# =========================
# ⚡ CACHE
# =========================
@st.cache_data(ttl=60)
def carregar_atual():
    return tratar_backlog_atual()

@st.cache_data(ttl=60)
def carregar_periodo(data_inicio, data_fim):
    return tratar_backlog_periodo(data_inicio, data_fim)


# =========================
# 🚀 DASHBOARD
# =========================
def render():

    st.title("📦 Control Tower - Backlog")

    # =========================
    # 🎛️ MODO
    # =========================
    modo = st.radio("Modo de análise", ["Atual", "Período"])

    if modo == "Atual":
        df = carregar_atual()
    else:
        col1, col2 = st.columns(2)
        data_inicio = col1.date_input("Data inicial")
        data_fim = col2.date_input("Data final")
        df = carregar_periodo(data_inicio, data_fim)

    if df.empty:
        st.warning("Sem dados disponíveis")
        return

    # =========================
    # 🔧 TRATAMENTO
    # =========================
    df = df.drop_duplicates(subset=["waybill"])

    df["horas_backlog_snapshot"] = pd.to_numeric(
        df["horas_backlog_snapshot"], errors="coerce"
    )

    df["cliente"] = df.get("cliente", "Não informado")
    df["cidade"] = df.get("cidade", "Não informado")
    df["pre_entrega"] = df.get("pre_entrega", "Não informado")

    # =========================
    # 📊 KPIs COMPLETOS
    # =========================
    total = len(df)

    backlog_24 = len(df[df["horas_backlog_snapshot"] > 24])
    backlog_48 = len(df[df["horas_backlog_snapshot"] > 48])
    backlog_72 = len(df[df["horas_backlog_snapshot"] > 72])

    perc = (backlog_72 / total * 100) if total else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("📦 Total", total)
    col2.metric("⚠️ >24h", backlog_24)
    col3.metric("⏳ >48h", backlog_48)
    col4.metric("🚨 >72h", backlog_72)
    col5.metric("📊 % Crítico", f"{perc:.1f}%")

    if perc > 25:
        st.error("🚨 Operação crítica")
    elif perc > 15:
        st.warning("⚠️ Atenção")
    else:
        st.success("✅ Operação controlada")

    st.divider()

    # =========================
    # 🚨 ALERTA AUTOMÁTICO
    # =========================
    st.subheader("🚨 Alerta Operacional")

    top_critico = (
        df[df["horas_backlog_snapshot"] > 72]
        .groupby("pre_entrega")
        .size()
        .sort_values(ascending=False)
        .head(1)
    )

    if not top_critico.empty:
        cd_critico = top_critico.index[0]
        qtd = top_critico.iloc[0]

        st.error(f"🚨 CD crítico: {cd_critico} com {qtd} pedidos >72h")
    else:
        st.success("✅ Nenhum CD crítico no momento")

    # =========================
    # 📈 TENDÊNCIA
    # =========================
    st.subheader("📈 Evolução do Backlog")

    if "data_referencia" in df.columns:
        tendencia = df.groupby("data_referencia").size().reset_index(name="qtd")

        fig_trend = px.line(
            tendencia,
            x="data_referencia",
            y="qtd",
            markers=True
        )

        st.plotly_chart(fig_trend, use_container_width=True)

    # =========================
    # 🔮 PREVISÃO DE BACKLOG
    # =========================
    st.subheader("🔮 Previsão de Backlog (Próximos Dias)")

    if "data_referencia" in df.columns:

        tendencia = (
            df.groupby("data_referencia")
            .size()
            .reset_index(name="qtd")
            .sort_values("data_referencia")
        )

        # média dos últimos 3 dias
        tendencia["media_movel"] = tendencia["qtd"].rolling(3).mean()

        # previsão = último valor da média
        if not tendencia["media_movel"].dropna().empty:
            previsao = tendencia["media_movel"].iloc[-1]

            st.metric("📊 Previsão Próximo Dia", int(previsao))

            if previsao > tendencia["qtd"].iloc[-1]:
                st.warning("📈 Tendência de aumento do backlog")
            else:
                st.success("📉 Tendência de queda do backlog")

    # =========================
    # ⏱️ AGING + CD
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏱️ Distribuição de Aging")

        df["faixa"] = pd.cut(
            df["horas_backlog_snapshot"],
            bins=[0, 24, 48, 72, 9999],
            labels=["0-24h", "24-48h", "48-72h", "72h+"]
        )

        faixa = df["faixa"].value_counts().reset_index()
        faixa.columns = ["faixa", "qtd"]

        fig_aging = px.bar(
            faixa,
            x="faixa",
            y="qtd",
            text="qtd",
            color="faixa"
        )

        st.plotly_chart(fig_aging, use_container_width=True)

    with col2:
        st.subheader("📍 Pré-Entrega")

        top_pre = (
            df.groupby("pre_entrega")
            .size()
            .sort_values(ascending=False)
            .head(10)
            .reset_index(name="qtd")
        )

        fig_cd = px.bar(
            top_pre,
            x="pre_entrega",
            y="qtd",
            text="qtd",
            color_discrete_sequence=[COR_VERMELHO]
        )

        st.plotly_chart(fig_cd, use_container_width=True)

    # =========================
    # 🗺️ ESTADO (COM FILTRO)
    # =========================
    st.subheader("🗺️ Backlog por Estado")

    estado_sel = st.multiselect(
        "Filtrar por estado",
        options=df["estado"].dropna().unique(),
        default=df["estado"].dropna().unique(),
        key="estado_multi"
    )

    df_estado = df[df["estado"].isin(estado_sel)]

    estado = (
        df.groupby("estado")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="qtd")
    )

    fig_estado = px.bar(
        estado,
        x="estado",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_VERDE]
    )

    st.plotly_chart(fig_estado, use_container_width=True)

    # =========================
    # 🏙️ CIDADE
    # =========================
    st.subheader("🏙️ Backlog por Cidade")

    cidade_sel = st.multiselect(
        "Filtrar cidades",
        options=df["cidade"].dropna().unique(),
        default=df["cidade"].dropna().unique(),
        key="cidade_multi"
    )

    df_cidade = df[df["cidade"].isin(cidade_sel)]

    cidade = (
        df.groupby("cidade")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="qtd")
    )

    fig_cidade = px.bar(
        cidade,
        x="cidade",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_CINZA]
    )

    st.plotly_chart(fig_cidade, use_container_width=True)

    # =========================
    # 👤 CLIENTE (COM FILTRO)
    # =========================
    st.subheader("👤 Clientes com Maior Backlog")

    cliente_sel = st.multiselect(
        "Filtrar clientes",
        options=df["cliente"].dropna().unique(),
        default=df["cliente"].dropna().unique(),
        key="cliente_multi"
    )

    df_cliente = df[df["cliente"].isin(cliente_sel)]

    cliente = (
        df.groupby("cliente")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="qtd")
    )

    fig_cliente = px.bar(
        cliente,
        x="cliente",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COR_VERMELHO]
    )

    st.plotly_chart(fig_cliente, use_container_width=True)

    # =========================
    # 🚨 SCORE DE RISCO
    # =========================
    st.subheader("🚨 Score de Risco")

    risco = (
        df.groupby(["cliente", "pre_entrega"])
        .agg(
            qtd=("waybill", "count"),
            critico=("horas_backlog_snapshot", lambda x: (x > 72).sum())
        )
        .reset_index()
    )

    risco["perc"] = (risco["critico"] / risco["qtd"]) * 100

    st.dataframe(
        risco.sort_values("perc", ascending=False).head(10),
        use_container_width=True
    )

    # =========================
    # 🔥 HEATMAP CRÍTICO + TOP
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔥 Heatmap - Backlog Crítico (>72h)")

        df_critico = df[df["horas_backlog_snapshot"] > 72]

        if not df_critico.empty:
            matriz = (
                df_critico.groupby(["cliente", "pre_entrega"])
                .size()
                .reset_index(name="qtd")
            )

            pivot = matriz.pivot(
                index="cliente",
                columns="pre_entrega",
                values="qtd"
            ).fillna(0)

            fig_heat = px.imshow(
                pivot,
                text_auto=True,
                color_continuous_scale="Reds"
            )

            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Sem backlog crítico")

    with col2:
        st.subheader("🚨 Top Problemas (Cliente x CD)")

        matriz = (
            df.groupby(["cliente", "pre_entrega"])
            .size()
            .reset_index(name="qtd")
            .sort_values("qtd", ascending=False)
        )

        st.dataframe(matriz.head(10), use_container_width=True)

    # =========================
    # 🔎 DETALHAMENTO FINAL
    # =========================
    st.subheader("🔎 Detalhamento Operacional")

    st.dataframe(
        df[[
            "waybill",
            "cliente",
            "estado",
            "cidade",
            "pre_entrega",
            "horas_backlog_snapshot"
        ]],
        use_container_width=True
    )