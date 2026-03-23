import streamlit as st
import plotly.express as px

from core.repository import buscar_backlog_periodo

@st.cache_data(ttl=120)
def carregar_backlog(data_inicio, data_fim):
    from core.repository import buscar_backlog_periodo
    return buscar_backlog_periodo(data_inicio, data_fim)

# =========================
# 🎨 CORES EMPRESA
# =========================
COR_VERDE = "#16A34A"
COR_VERMELHO = "#DC2626"
COR_CINZA = "#6B7280"
COR_AZUL = "#2563EB"

COLOR_MAP = {
    "estado": COR_VERDE,
    "cidade": COR_CINZA,
    "cliente": COR_VERMELHO,
    "tempo": COR_VERDE,
    "pre_entrega": COR_AZUL
}


def render():

    st.title("📦 Control Tower - Backlog")

    # =========================
    # 📅 FILTRO DATA
    # =========================
    col1, col2 = st.columns(2)

    data_inicio = col1.date_input("📅 Data inicial")
    data_fim = col2.date_input("📅 Data final")

    if not data_inicio or not data_fim:
        st.warning("Selecione o período")
        return

    from core.repository import buscar_backlog_fast

    df = buscar_backlog_fast(data_inicio, data_fim)

    if df.empty:
        st.warning("Sem dados")
        return

    # =========================
    # 🎛️ FILTROS DINÂMICOS
    # =========================
    col3, col4 = st.columns(2)

    estados = col3.multiselect(
        "🌎 Estado",
        sorted(df["estado"].dropna().unique())
    )

    clientes = col4.multiselect(
        "👤 Cliente",
        sorted(df["cliente"].dropna().unique())
    )

    if estados:
        df = df[df["estado"].isin(estados)]

    if clientes:
        df = df[df["cliente"].isin(clientes)]

    # =========================
    # ⏱️ FILTRO DE FAIXA
    # =========================
    faixa = st.radio(
        "⏱️ Faixa de backlog",
        ["Todos", "24h+", "48h+", "72h+"]
    )

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
    backlog_24 = len(df[df["horas_backlog_snapshot"] > 24])
    backlog_48 = len(df[df["horas_backlog_snapshot"] > 48])
    backlog_72 = len(df[df["horas_backlog_snapshot"] > 72])

    perc = (backlog_72 / total * 100) if total else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("📦 Total", total)
    col2.metric("⚠️ >24h", backlog_24)
    col3.metric("⏳ >48h", backlog_48)
    col4.metric("🚨 >72h", backlog_72)
    col5.metric("📊 % crítico", f"{perc:.1f}%")

    if perc > 25:
        st.error("🚨 Operação crítica")
    elif perc > 15:
        st.warning("⚠️ Atenção")
    else:
        st.success("✅ Operação controlada")

    st.divider()

    # =========================
    # 📈 EVOLUÇÃO
    # =========================
    st.subheader("📈 Evolução do Backlog")

    df_tempo = df.groupby("data_referencia").size().reset_index(name="qtd")

    fig_trend = px.line(
        df_tempo,
        x="data_referencia",
        y="qtd",
        markers=True,
        color_discrete_sequence=[COLOR_MAP["tempo"]]
    )

    st.plotly_chart(fig_trend, use_container_width=True)

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
        color_discrete_sequence=[COLOR_MAP["estado"]]
    )

    st.plotly_chart(fig_estado, use_container_width=True)

    # =========================
    # 🏙️ CIDADE
    # =========================
    st.subheader("🏙️ Backlog por Cidades")

    df_cidade = df.groupby("cidade").size().reset_index(name="qtd")

    fig_cidade = px.bar(
        df_cidade.sort_values("qtd", ascending=False).head(10),
        x="cidade",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COLOR_MAP["cidade"]]
    )

    st.plotly_chart(fig_cidade, use_container_width=True)

    # =========================
    # 👤 CLIENTE
    # =========================
    st.subheader("👤 Backlog porClientes")

    df_cliente = df.groupby("cliente").size().reset_index(name="qtd")

    fig_cliente = px.bar(
        df_cliente.sort_values("qtd", ascending=False).head(10),
        x="cliente",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COLOR_MAP["cliente"]]
    )

    st.plotly_chart(fig_cliente, use_container_width=True)

    # =========================
    # 🚚 PRÉ-ENTREGA
    # =========================
    st.subheader("🚚 Backlog por ponto de Pré-Entrega")

    df_pre = (
        df.groupby("pre_entrega")
        .size()
        .reset_index(name="qtd")
        .sort_values("qtd", ascending=False)
        .head(10)
    )

    fig_pre = px.bar(
        df_pre,
        x="pre_entrega",
        y="qtd",
        text="qtd",
        color_discrete_sequence=[COLOR_MAP["pre_entrega"]]
    )

    st.plotly_chart(fig_pre, use_container_width=True)

    # =========================
    # 📋 TABELA FINAL
    # =========================
    st.subheader("📋 Waybills em Backlog")

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Baixar CSV",
        csv,
        "backlog_filtrado.csv",
        "text/csv"
    )