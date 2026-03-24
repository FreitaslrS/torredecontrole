import streamlit as st
from core.database import inicializar_banco

inicializar_banco()

import pages.home as home
import pages.backlog as backlog
import pages.backlog_historico as backlog_historico
import pages.produtividade as produtividade
import pages.devolucoes as devolucoes
import pages.importacao as importacao

def load_css_dark():
    with open("assets/style_dark.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def load_css_light():
    with open("assets/style_light.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="Control Tower", layout="wide")

# 🔥 toggle de tema
tema = st.sidebar.toggle("🌙 Dark Mode", value=True)

if tema:
    load_css_dark()
else:
    load_css_light()

st.sidebar.markdown("## 📊 Control Tower")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navegação",
    [
        "🏠 Home",
        "📦 Backlog Atual",
        "📊 Backlog Histórico",
        "⚡ Produtividade",
        "🔁 Devoluções",
        "📥 Importação"
    ]
)

if menu == "🏠 Home":
    home.render()
elif menu == "📦 Backlog Atual":
    backlog.render()
elif menu == "📊 Backlog Histórico":
    backlog_historico.render()
elif menu == "⚡ Produtividade":
    produtividade.render()
elif menu == "🔁 Devoluções":
    devolucoes.render()
elif menu == "📥 Importação":
    importacao.render()