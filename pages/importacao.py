import streamlit as st
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.database import executar_backlog
from core.repository import salvar_log_importacao
from core.processar_arquivo import importar_excel, importar_produtividade, limpar_base
from core.database import conectar_backlog
from core.database import (
    consultar_historico,
    consultar_operacional,
    executar_historico,
    executar_operacional
)
from core.processar_arquivo import importar_tempo_processamento
from core.database import consultar_processamento

@st.cache_resource

def get_conexao():
    return conectar_backlog()

# =========================
# 🔐 LOGIN
# =========================
def obter_senha():
    return "Ss.sist@05060711*"


def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    st.title("🔐 Área Restrita / 受限区域")

    senha = st.text_input("Digite a senha / 输入密码", type="password")

    if st.button("Entrar / 登录"):
        if senha == obter_senha():
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta")

    return False


# =========================
# 🚀 PROCESSAMENTO PARALELO
# =========================
def processar_arquivo_individual(arquivo, data_ref, tipo_importacao):
    inicio = time.time()

    try:
        if tipo_importacao == "Backlog":
            qtd = importar_excel(arquivo, data_ref)

        elif tipo_importacao == "Produtividade":
            qtd = importar_produtividade(arquivo)

        elif tipo_importacao == "Tempo de Processamento":
            qtd = importar_tempo_processamento(arquivo)

        else:
            raise Exception("Tipo de importação inválido")

        status = "Sucesso"

    except Exception as e:
        qtd = 0
        status = str(e)

    tempo = time.time() - inicio

    return {
        "arquivo": arquivo.name,
        "status": status,
        "registros": qtd,
        "tempo": tempo
    }

# =========================
# 🎯 TELA
# =========================
def render():

    if not verificar_senha():
        return

    st.markdown("## <i class='fas fa-upload'></i> Importação de Dados / 数据导入", unsafe_allow_html=True)

    data_ref = st.date_input("Data de referência / 参考日期")

    arquivos = st.file_uploader(
        "Selecione arquivos Excel / 选择Excel文件",
        type=["xlsx", "xls"],
        accept_multiple_files=True
    )

    if "resultado_importacao" not in st.session_state:
        st.session_state.resultado_importacao = None
        st.session_state.total_importado = 0

    tipo_importacao = st.selectbox(
        "Tipo de Importação / 导入类型",
        ["Backlog", "Produtividade", "Tempo de Processamento"]
    )

    # ========================
    # 🚀 IMPORTAR
    # ========================
    if st.button("Importar / 导入"):

        if tipo_importacao == "Backlog" and not data_ref:
            st.warning("Selecione a data de referência")
            return

        if not arquivos:
            st.warning("Selecione arquivos")
            return

        progress = st.progress(0)
        status_text = st.empty()

        resultados = []
        logs = []
        total_registros = 0

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(processar_arquivo_individual, arq, data_ref, tipo_importacao)
                for arq in arquivos
            ]

            for i, future in enumerate(as_completed(futures)):
                r = future.result()

                registros = r["registros"] or 0
                total_registros += registros

                resultados.append({
                    "arquivo": r["arquivo"],
                    "status": r["status"],
                    "registros": registros
                })

                logs.append({
                    "id": i,
                    "nome_arquivo": r["arquivo"],
                    "status": r["status"],
                    "registros": r["registros"],
                    "tempo_segundos": r["tempo"],
                    "data_importacao": pd.Timestamp.now()
                })

                progress.progress((i + 1) / len(arquivos))
                status_text.text(f"Finalizado: {r['arquivo']}")

        df_logs = pd.DataFrame(logs)
        salvar_log_importacao(df_logs)

        st.session_state.resultado_importacao = resultados
        st.session_state.total_importado = total_registros

        st.cache_data.clear()
        st.rerun()

    # ========================
    # 📊 RESULTADO
    # ========================
    if st.session_state.resultado_importacao is not None:

        st.success(f"{st.session_state.total_importado} registros importados")

        for r in st.session_state.resultado_importacao:
            if r["status"] != "Sucesso":
                st.error(f"{r['arquivo']} → {r['status']}")
            else:
                st.success(f"{r['arquivo']} → {r['registros']} registros")

    st.divider()

    # ========================
    # 📜 HISTÓRICO
    # ========================
    st.subheader("📊 Histórico de Importações / 导入历史")

    from core.database import consultar_backlog as consultar

    df_hist_backlog = consultar_historico("""
        SELECT 
            nome_arquivo,
            COUNT(*) as registros,
            MAX(data_importacao) as data_importacao,
            MAX(data_referencia) as data_referencia,
            'Backlog' as tipo
        FROM pedidos
        GROUP BY nome_arquivo
    """)

    df_hist_prod = consultar_operacional("""
        SELECT 
            nome_arquivo,
            COUNT(*) as registros,
            MAX(data_importacao) as data_importacao,
            MAX(data) as data_referencia,
            'Produtividade' as tipo
        FROM produtividade
        GROUP BY nome_arquivo
    """)

    df_hist_proc = consultar_processamento("""
        SELECT 
            nome_arquivo,
            COUNT(*) as registros,
            MAX(data_importacao) as data_importacao,
            MAX(DATE(entrada_hub1)) as data_referencia,
            'Tempo Processamento' as tipo
        FROM tempo_processamento
        GROUP BY nome_arquivo
    """)

    df_hist = pd.concat(
        [df_hist_backlog, df_hist_prod, df_hist_proc],
        ignore_index=True
    )

    df_hist = df_hist.sort_values("data_importacao", ascending=False)

    if df_hist.empty:
        st.info("Nenhum arquivo importado ainda / 暂无导入记录")
    else:
        for _, row in df_hist.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([4,2,2,3,3,1])

            col1.write(row["nome_arquivo"])
            col2.write(row["registros"])
            col3.write(row["tipo"])  # 🔥 novo
            col4.write(f"📅: {row['data_referencia']}")
            col5.write(f"⏱️ {row['data_importacao']}")

            if col6.button("🗑️", key=f"{row['nome_arquivo']}_{row['data_importacao']}"):
                excluir_arquivo(row["nome_arquivo"])
                st.success(f"{row['nome_arquivo']} excluído")
                st.rerun()

    # ========================
    # ⚠️ ZONA DE PERIGO
    # ========================
    st.divider()
    st.subheader("⚠️ Zona de Perigo")

    confirmar = st.checkbox("Tenho certeza que quero fazer isso (modo destruição)")

    col1, col2, col3 = st.columns(3)

    if confirmar:

        with col1:
            if st.button("🔥 Resetar Backlog Atual"):
                executar_backlog("DELETE FROM backlog_atual")
                st.success("Backlog atual zerado!")
                st.cache_data.clear()
                st.rerun()

        with col2:
            data_delete = st.date_input("Excluir por data de referência")

            if st.button("🗑️ Excluir por Data"):
                executar_historico(
                    "DELETE FROM pedidos WHERE data_referencia = %s",
                    [data_delete]
                )
                st.success(f"Dados da data {data_delete} excluídos!")
                st.cache_data.clear()
                st.rerun()

        with col3:
            if st.button("🧹 Limpar histórico > 30 dias"):
                limpar_base()
                st.success("Histórico antigo removido!")
                st.cache_data.clear()
                st.rerun()


# ========================
# 🗑️ DELETE
# ========================
def excluir_arquivo(nome_arquivo):

    executar_historico(
        "DELETE FROM pedidos WHERE nome_arquivo = %s",
        [nome_arquivo]
    )

    executar_operacional(
        "DELETE FROM produtividade WHERE nome_arquivo = %s",
        [nome_arquivo]
    )

    # 🔥 ADICIONA ISSO AQUI
    from core.database import executar_processamento

    executar_processamento(
        "DELETE FROM tempo_processamento WHERE nome_arquivo = %s",
        [nome_arquivo]
    )

    st.cache_data.clear()