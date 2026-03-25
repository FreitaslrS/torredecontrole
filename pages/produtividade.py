import streamlit as st
from core.repository import buscar_produtividade

def render():
    st.markdown("## <i class='fas fa-bolt'></i> Produtividade / 生产效率", unsafe_allow_html=True)

    df = buscar_produtividade()

    if df.empty:
        st.warning("Sem dados")
        return

    total = df["volumes"].sum()

    st.metric("📦 Total processado / 处理总量", total)

    # PRODUTIVIDADE POR OPERADOR
    st.subheader("👤 Produtividade por Operador / 按操作员效率")

    df_op = df.groupby("operador")["volumes"].sum().reset_index()

    import plotly.express as px

    fig = px.bar(
        df_op.sort_values("volumes", ascending=False),
        x="operador",
        y="volumes",
        text="volumes"
    )

    st.plotly_chart(fig, use_container_width=True)

    # POR HUB
    st.subheader("🏭 Produtividade por HUB / 按分拨中心效率")

    df_hub = df.groupby("hub")["volumes"].sum().reset_index()

    fig2 = px.bar(
        df_hub.sort_values("volumes", ascending=False),
        x="hub",
        y="volumes",
        text="volumes"
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(df)