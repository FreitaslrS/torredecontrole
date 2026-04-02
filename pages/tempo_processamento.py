import streamlit as st
import pandas as pd
import plotly.express as px

from core.repository import (
    buscar_tempo_processamento,
    buscar_tempo_processamento_geral,
    buscar_hiata_por_dia,
    buscar_consolidado_por_dia
)

cores = {
    "Até 24h": "#16A34A",
    "> 24h": "#DC2626",
    "Sem saída": "#6B7280"
}

traducao_status = {
    "Até 24h": "Até 24h / 24小时内",
    "> 24h": "> 24h / 超过24小时",
    "Sem saída": "Sem saída / 无出库"
}

def render():

    # =========================
    # 📅 FILTRO (CORRIGIDO)
    # =========================
    col1, col2 = st.columns(2)

    usar_filtro = st.checkbox("Filtrar por período")

    if usar_filtro:
        data_inicio = col1.date_input("Data início / 开始日期")
        data_fim = col2.date_input("Data fim / 结束日期")
    else:
        data_inicio = None
        data_fim = None

    st.markdown("""
    ## ⏱️ Tempo de Processamento / 处理时效
    <p style='opacity:0.7'>Tempo entre entrada e saída HUB 1 / HUB1入库到出库时间</p>
    """, unsafe_allow_html=True)

    modo = st.radio("Modo de análise", ["H01 (TFK)", "Geral"])

    if modo == "H01 (TFK)":
        df = buscar_tempo_processamento()
    else:
        df = buscar_tempo_processamento_geral()

    if df.empty:
        st.warning("Sem dados / 暂无数据")
        return

    # =========================
    # 🧠 TRATAMENTO
    # =========================
    df["entrada_hub1"] = pd.to_datetime(df["entrada_hub1"], errors="coerce")
    df["saida_hub1"] = pd.to_datetime(df["saida_hub1"], errors="coerce")

    # 🔥 remove lixo (melhoria)
    df = df.dropna(subset=["entrada_hub1"])

    # =========================
    # 📅 FILTRO APLICADO
    # =========================
    if usar_filtro and data_inicio and data_fim:
        df = df[
            (df["entrada_hub1"].dt.date >= data_inicio) &
            (df["entrada_hub1"].dt.date <= data_fim)
        ]

    if df.empty:
        st.warning("Sem dados no período / 当前时间段无数据")
        return

    # =========================
    # ⏱️ TEMPO
    # =========================
    df["tempo_horas"] = (
        (df["saida_hub1"] - df["entrada_hub1"])
        .dt.total_seconds() / 3600
    )

    # 🔥 FILTRO TFK + H01
    df_h01 = df.copy() if not df.empty else pd.DataFrame()

    # =========================
    # 📊 SLA
    # =========================
    total = len(df)
    dentro_sla = len(df[df["tempo_horas"] <= 24])

    perc_sla = (dentro_sla / total) * 100 if total else 0

    st.metric("📊 SLA 24h / 24小时达标率", f"{perc_sla:.1f}%")

    if perc_sla < 70:
        st.error("🚨 SLA crítico / SLA严重")
    elif perc_sla < 85:
        st.warning("⚠️ SLA em atenção / SLA需关注")
    else:
        st.success("✅ SLA saudável / SLA正常")

    # =========================
    # ⏱️ TEMPO MÉDIO
    # =========================
    df_valido = df[
        (df["tempo_horas"] >= 0) &
        (df["tempo_horas"] <= 240)
    ]

    tempo_medio = df["tempo_horas"].dropna().mean()
    tempo_medio_limpo = df_valido["tempo_horas"].mean()

    st.metric("⏱️ Tempo médio / 平均处理时间", f"{tempo_medio_limpo:.1f}h")

    if tempo_medio_limpo > 24:
        st.error("🚨 Tempo médio acima de 24h / 超过24小时")
    else:
        st.success("✅ Tempo médio dentro do SLA / 时效正常")

    # =========================
    # 🧩 CLASSIFICAÇÃO
    # =========================
    def classificar(row):
        if pd.isna(row["saida_hub1"]):
            return "Sem saída"
        elif row["tempo_horas"] <= 24:
            return "Até 24h"
        else:
            return "> 24h"

    df["status"] = df.apply(classificar, axis=1)
    df["status_label"] = df["status"].map(traducao_status)

    # =========================
    # 🥧 PIZZA
    # =========================
    df_pizza = df["status"].value_counts().reset_index()
    df_pizza.columns = ["status", "qtd"]
    df_pizza["status_label"] = df_pizza["status"].map(traducao_status)

    fig_pizza = px.pie(
        df_pizza,
        names="status_label",
        values="qtd",
        color="status",
        color_discrete_map=cores,
        title="Status de Expedição / 出库状态"
    )

    st.plotly_chart(fig_pizza, use_container_width=True)

    # =========================
    # 📊 TABELA
    # =========================
    def faixa(h):
        if pd.isna(h):
            return "Sem saída"
        elif h <= 24:
            return "0-24h"
        elif h <= 48:
            return "24-48h"
        elif h <= 72:
            return "48-72h"
        else:
            return ">72h"

    df["faixa"] = df["tempo_horas"].apply(faixa)

    tabela = (
        df.groupby(["estado", "faixa"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for col in ["0-24h", "24-48h", "48-72h", ">72h", "Sem saída"]:
        if col not in tabela.columns:
            tabela[col] = 0

    tabela["Total / 总计"] = tabela[
        ["0-24h", "24-48h", "48-72h", ">72h", "Sem saída"]
    ].sum(axis=1)

    # =========================
    # 🏆 RANKING
    # =========================
    st.subheader("🏆 Top 5 Estados com Maior Atraso / 延误最多的州")

    df_atraso = df[df["tempo_horas"] > 24]

    ranking = (
        df_atraso.groupby("estado")
        .size()
        .reset_index(name="qtd_atrasos")
        .sort_values("qtd_atrasos", ascending=False)
        .head(5)
    )

    fig_rank = px.bar(
        ranking,
        x="estado",
        y="qtd_atrasos",
        text="qtd_atrasos",
        color_discrete_sequence=["#DC2626"]
    )

    st.plotly_chart(fig_rank, use_container_width=True)

    # =========================
    # 📊 TOTAL
    # =========================
    total_geral = tabela[
        ["0-24h", "24-48h", "48-72h", ">72h", "Sem saída"]
    ].sum()

    total_linha = pd.DataFrame([{
        "estado": "TOTAL",
        "0-24h": total_geral["0-24h"],
        "24-48h": total_geral["24-48h"],
        "48-72h": total_geral["48-72h"],
        ">72h": total_geral[">72h"],
        "Sem saída": total_geral["Sem saída"],
        "Total / 总计": total_geral.sum()
    }])

    tabela = pd.concat([tabela, total_linha], ignore_index=True)

    # =========================
    # 📊 PRÉ-ENTREGA (ATRASO)
    # =========================
    st.subheader("📦 Top 10 Pontos de Entrada com Atraso / 入库点延误TOP10")

    df_atraso_pre = df[df["tempo_horas"] > 24]

    if not df_atraso_pre.empty:

        ranking_pre = (
            df_atraso_pre.groupby("ponto_entrada")
            .size()
            .reset_index(name="qtd_atrasos")
            .sort_values("qtd_atrasos", ascending=False)
            .head(10)
        )

        fig_pre = px.bar(
            ranking_pre,
            x="ponto_entrada",
            y="qtd_atrasos",
            text="qtd_atrasos",
            color_discrete_sequence=["#DC2626"]
        )

        st.plotly_chart(fig_pre, use_container_width=True)

    else:
        st.info("Sem atrasos nos pontos de entrada")

    # =========================
    # 📋 EXIBIÇÃO
    # =========================
    st.subheader("📊 Tempo por Estado / 各州时效")

    st.dataframe(tabela, use_container_width=True)

    # ======================================
    # 🥧 TABELA DESTINO DIRETO AOS ESTADOS
    # ======================================

    tabela_h01 = (
        df_h01.groupby("estado")
        .agg(
            total=("estado", "count"),
            dentro_sla=("tempo_horas", lambda x: (x <= 24).sum()),
            fora_sla=("tempo_horas", lambda x: (x > 24).sum())
        )
        .reset_index()
    )

    # ======================================
    # 🥧 TABELA DESTINOS H01 (ENVIO DIRETO)
    # ======================================

    st.subheader("📊 Volume de Hiatas H001 por Dia")

    df_hiata = buscar_hiata_por_dia(data_inicio, data_fim)

    if not df_hiata.empty:

        tabela_hiata = (
            df_hiata
            .pivot(index="data", columns="hiata", values="qtd")
            .fillna(0)
            .reset_index()
        )

        st.dataframe(tabela_hiata, use_container_width=True)

    else:
        st.warning("Sem dados de hiata")

    st.subheader("📊 Consolidação Operacional (Perus + TFK)")

    df_cons = buscar_consolidado_por_dia(data_inicio, data_fim)

    if not df_cons.empty:

        # 📊 MÉDIAS
        media_perus = df_cons["total_perus"].mean()
        media_tfk = df_cons["total_tfk"].mean()
        media_total = df_cons["total_geral"].mean()

        col1, col2, col3 = st.columns(3)

        col1.metric("📦 Perus", f"{media_perus:.0f}/dia")
        col2.metric("🚚 TFK Direto", f"{media_tfk:.0f}/dia")
        col3.metric("🔥 Total", f"{media_total:.0f}/dia")

        # 📋 TABELA
        st.dataframe(df_cons, use_container_width=True)

    else:
        st.warning("Sem dados para o período")