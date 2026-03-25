import streamlit as st
import os
from core.database import inicializar_banco

inicializar_banco()

import pages.home as home
import pages.backlog as backlog
import pages.backlog_historico as backlog_historico
import pages.produtividade as produtividade
import pages.devolucoes as devolucoes
import pages.importacao as importacao

# 🔥 BASE DIR (pra não dar erro de caminho)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===== CSS DARK =====
def load_css_dark():
    path = os.path.join(BASE_DIR, "assets", "style_dark.css")
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ===== CSS LIGHT =====
def load_css_light():
    path = os.path.join(BASE_DIR, "assets", "style_light.css")
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ===== CONFIG =====
st.set_page_config(page_title="Control Tower", layout="wide")

# 🔥 FONT AWESOME (ícones)
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)

# 🔥 DARK MODE (toggle)
tema = st.sidebar.toggle("🌙 Dark Mode", value=True)

if tema:
    load_css_dark()
else:
    load_css_light()

# ===== SIDEBAR =====
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navegação / 导航",
    [
        "🏠 Home / 首页",
        "📦 Backlog Atual / 当前积压",
        "📊 Backlog Histórico / 历史积压",
        "⚡ Produtividade / 生产效率",
        "🔁 Devoluções / 退货",
        "📥 Importação / 数据导入"
    ]
)

# ===== ROTEAMENTO =====
if menu == "🏠 Home / 首页":
    home.render()
elif menu == "📦 Backlog Atual / 当前积压":
    backlog.render()
elif menu == "📊 Backlog Histórico / 历史积压":
    backlog_historico.render()
elif menu == "⚡ Produtividade / 生产效率":
    produtividade.render()
elif menu == "🔁 Devoluções / 退货":
    devolucoes.render()
elif menu == "📥 Importação / 数据导入":
    importacao.render()