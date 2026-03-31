import streamlit as st
import plotly.express as px
import pandas as pd

from core.repository import buscar_produtividade

# =========================
# 🎨 CORES
# =========================
COR_VERDE = "#16A34A"
COR_VERMELHO = "#DC2626"
COR_CINZA = "#6B7280"

cores_empresa = [COR_VERDE, COR_VERMELHO, COR_CINZA]

color_dispositivo = {
    "Sorter Oval": COR_VERDE,
    "Sorter Linear": COR_VERMELHO,
    "Cubometro": COR_CINZA
}

color_turno = {
    "T1": COR_VERDE,
    "T2": COR_VERMELHO,
    "T3": COR_CINZA
}

map_traducao = {
    "Sorter Oval": "Sorter Oval / 环形分拣机",
    "Sorter Linear": "Sorter Linear / 直线分拣机",
    "Cubometro": "Cubômetro / 体积测量设备"
}

# =========================
# ⚡ CACHE
# =========================
@st.cache_data(ttl=300)
def carregar_dados():
    df = buscar_produtividade()
    return df[["data", "hora", "dispositivo", "cliente", "volumes"]].copy()

@st.cache_data(ttl=300)
def preparar_dados(df):
    df["hora"] = df["hora"].astype("int8")
    df["data"] = pd.to_datetime(df["data"]).dt.date

    # turno otimizado (rápido)
    df["turno_real"] = "T3"
    df.loc[(df["hora"] >= 6) & (df["hora"] < 14), "turno_real"] = "T1"
    df.loc[(df["hora"] >= 14) & (df["hora"] < 21), "turno_real"] = "T2"

    return df

@st.cache_data(ttl=300)
def agrupar(df):
    df_turno = df.groupby("turno_real")["volumes"].sum().reset_index()
    df_bar = df.groupby(["hora", "dispositivo"])["volumes"].sum().reset_index()
    df_tabela = df.groupby(["hora", "dispositivo"])["volumes"].sum().unstack(fill_value=0)
    return df_turno, df_bar, df_tabela

@st.cache_data(ttl=300)
def agrupar_cliente(df):
    df_cliente = (
        df.groupby("cliente")["volumes"]
        .sum()
        .reset_index()
        .sort_values(by="volumes", ascending=False)
    )
    
    df_top10 = df_cliente.head(10)

    return df_cliente, df_top10

# =========================
# 🚀 RENDER
# =========================
def render():

    st.markdown("## ⚡ Produtividade / 生产效率")

    df = carregar_dados()

    if df.empty:
        st.warning("Sem dados / 暂无数据")
        return

    df = preparar_dados(df)

    # =========================
    # 🎛️ FILTROS
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        datas = df["data"].unique()
        data_inicio, data_fim = st.date_input(
            "📅 Período / 日期范围",
            value=(datas.min(), datas.max())
        )

    with col2:
        turno = st.selectbox(
            "🕒 Turno / 班次",
            ["Todos", "T1", "T2", "T3"]
        )

    df = df[(df["data"] >= data_inicio) & (df["data"] <= data_fim)]

    if turno != "Todos":
        df = df[df["turno_real"] == turno]

    if df.empty:
        st.warning("Sem dados após filtros / 筛选后无数据")
        return

    # =========================
    # KPI
    # =========================
    st.metric("📦 Total / 总量", int(df["volumes"].sum()))

    # =========================
    # ⚡ AGRUPAMENTO
    # =========================
    df_turno, df_bar, df_tabela = agrupar(df)

    # =========================
    # 🥧 PIZZA
    # =========================
    st.subheader("🥧 Produtividade por Turno / 按班次效率")

    fig_pizza = px.pie(
        df_turno,
        names="turno_real",
        values="volumes",
        color="turno_real",
        color_discrete_map=color_turno
    )

    st.plotly_chart(fig_pizza, use_container_width=True)

    # =========================
    # 📊 BARRA
    # =========================
    st.subheader("📊 Produtividade por Hora (Dispositivos) / 按小时设备效率")

    horas = pd.DataFrame({"hora": range(24)})
    dispositivos = ["Sorter Oval", "Sorter Linear", "Cubometro"]

    base = horas.assign(key=1).merge(
        pd.DataFrame({"dispositivo": dispositivos, "key": 1}),
        on="key"
    ).drop("key", axis=1)

    df_bar = base.merge(df_bar, on=["hora", "dispositivo"], how="left").fillna(0)

    fig_bar = px.bar(
        df_bar,
        x="hora",
        y="volumes",
        color="dispositivo",
        barmode="stack",
        color_discrete_map=color_dispositivo,
        labels={
            "hora": "Hora / 时间",
            "volumes": "Volumes / 数量",
            "dispositivo": "Dispositivo / 设备"
        }
    )

    fig_bar.for_each_trace(
        lambda t: t.update(name=map_traducao.get(t.name, t.name))
    )

    fig_bar.update_xaxes(dtick=1)

    st.plotly_chart(fig_bar, use_container_width=True)

    # =========================
    # 📋 TABELA
    # =========================
    st.subheader("📋 Resumo por Hora / 每小时汇总")

    df_tabela["Total"] = df_tabela.sum(axis=1)
    df_tabela.index = df_tabela.index.map(lambda x: f"{x:02d}:00")
    df_tabela.columns = df_tabela.columns.map(lambda x: map_traducao.get(x, x))

    st.dataframe(df_tabela, use_container_width=True)

    # =========================
    # 🧑‍💼 PRODUTIVIDADE POR CLIENTE
    # =========================
    st.subheader("🧑‍💼 Top 10 Clientes / 前10客户")

    df_cliente, df_top10 = agrupar_cliente(df)

    fig_cliente = px.bar(
        df_top10,
        x="volumes",
        y="cliente",
        orientation="h",
        text="volumes"
    )

    # 🔥 aplica cores da empresa (cíclico)
    fig_cliente.update_traces(
        marker_color=[cores_empresa[i % 3] for i in range(len(df_top10))]
    )

    fig_cliente.update_layout(
        xaxis_title="Volumes / 数量",
        yaxis_title="Cliente / 客户"
    )

    fig_cliente.update_traces(textposition="outside")

    st.plotly_chart(fig_cliente, use_container_width=True)

    # =========================
    # 📋 TABELA CLIENTES
    # =========================
    st.subheader("📋 Produção por Cliente (Completo) / 客户完整列表")

    df_cliente_formatado = df_cliente.copy()
    df_cliente_formatado.columns = ["Cliente / 客户", "Volumes / 数量"]

    st.dataframe(df_cliente_formatado, use_container_width=True)
    