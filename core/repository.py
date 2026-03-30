import streamlit as st
from psycopg2.extras import execute_values

from core.database import (
    consultar_backlog,
    consultar_operacional,
    executar_backlog,
    executar_operacional,
    conectar_operacional,
    consultar_historico,
    consultar_devolucoes
)

# =========================
# 🗑️ DELETE
# =========================
def deletar_arquivo(nome_arquivo):
    executar_backlog(
        "DELETE FROM pedidos WHERE nome_arquivo = %s",
        [nome_arquivo]
    )


# =========================
# 📂 LISTAR ARQUIVOS
# =========================
@st.cache_data(ttl=300)
def listar_arquivos():
    return consultar_backlog("""
        SELECT 
            nome_arquivo,
            COUNT(*) as registros
        FROM pedidos
        GROUP BY nome_arquivo
        ORDER BY nome_arquivo DESC
    """)


# =========================
# 📊 BACKLOG RESUMO
# =========================
@st.cache_data(ttl=300)
def buscar_backlog_resumo():
    return consultar_backlog("""
        SELECT 
            estado,
            pre_entrega,
            cliente,
            qtd,
            b24,
            b48,
            b72
        FROM mv_backlog_resumo
    """)


# =========================
# 📊 GRÁFICO POR ESTADO
# =========================
@st.cache_data(ttl=120)
def buscar_backlog_por_estado(remover_estados=None, remover_clientes=None, faixa=None):

    query = """
        SELECT estado, SUM(qtd) as qtd
        FROM mv_backlog_resumo
        WHERE 1=1
    """

    params = []

    if remover_estados:
        query += " AND estado != ALL(%s)"
        params.append(remover_estados)

    if remover_clientes:
        query += " AND cliente != ALL(%s)"
        params.append(remover_clientes)

    # ⚠️ NÃO USA faixa aqui (view não tem horas)

    query += " GROUP BY estado ORDER BY qtd DESC"

    return consultar_backlog(query, params)


# =========================
# 📊 GRÁFICO POR CLIENTE
# =========================
@st.cache_data(ttl=120)
def buscar_backlog_por_cliente(remover_clientes=None, remover_estados=None, faixa=None):

    query = """
        SELECT cliente, SUM(qtd) as qtd
        FROM mv_backlog_resumo
        WHERE 1=1
    """

    params = []

    if remover_clientes:
        query += " AND cliente != ALL(%s)"
        params.append(remover_clientes)

    if remover_estados:
        query += " AND estado != ALL(%s)"
        params.append(remover_estados)

    # ⚠️ NÃO USA faixa aqui (view não tem horas)

    query += " GROUP BY cliente ORDER BY qtd DESC"

    return consultar_backlog(query, params)


# =========================
# 📊 PRÓXIMO PONTO
# =========================
@st.cache_data(ttl=120)
def buscar_backlog_por_proximo_ponto(faixa=None):

    query = """
        SELECT 
            CASE 
                WHEN proximo_ponto IS NULL OR proximo_ponto = '' 
                THEN 'Sem informação / 无信息'
                ELSE proximo_ponto
            END as proximo_ponto,
            COUNT(*) as qtd
        FROM backlog_atual
        WHERE 1=1
    """

    if faixa == "24h+":
        query += " AND horas_backlog_snapshot > 24"
    elif faixa == "48h+":
        query += " AND horas_backlog_snapshot > 48"
    elif faixa == "72h+":
        query += " AND horas_backlog_snapshot > 72"

    query += """
        GROUP BY 
            CASE 
                WHEN proximo_ponto IS NULL OR proximo_ponto = '' 
                THEN 'Sem informação / 无信息'
                ELSE proximo_ponto
            END
        ORDER BY qtd DESC
    """

    return consultar_backlog(query)


# =========================
# 🏆 TOP 10 PRÉ-ENTREGA
# =========================
@st.cache_data(ttl=120)
def buscar_top10_pre_entrega(faixa=None):

    query = """
        SELECT pre_entrega, SUM(qtd) as qtd
        FROM mv_backlog_resumo
        WHERE 1=1
    """

    # ⚠️ NÃO usa faixa aqui (view não tem horas)

    query += " GROUP BY pre_entrega ORDER BY qtd DESC LIMIT 10"

    return consultar_backlog(query)


# =========================
# 📊 BACKLOG DETALHADO
# =========================
@st.cache_data(ttl=120)
def buscar_backlog_paginado(limit=100, offset=0, estados=None, clientes=None, faixa=None):

    query = """
        SELECT 
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            proximo_ponto,
            horas_backlog_snapshot,
            faixa_backlog_snapshot,
            data_atualizacao
        FROM backlog_atual
        WHERE 1=1
    """

    params = []

    if estados:
        query += " AND estado = ANY(%s)"
        params.append(estados)

    if clientes:
        query += " AND cliente = ANY(%s)"
        params.append(clientes)

    if faixa == "24h+":
        query += " AND horas_backlog_snapshot > 24"
    elif faixa == "48h+":
        query += " AND horas_backlog_snapshot > 48"
    elif faixa == "72h+":
        query += " AND horas_backlog_snapshot > 72"

    query += " ORDER BY data_atualizacao DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return consultar_backlog(query, params)


# =========================
# 🔢 CONTAGEM BACKLOG
# =========================
@st.cache_data(ttl=120)
def contar_backlog(estados=None, clientes=None, faixa=None):

    query = "SELECT SUM(qtd) as total FROM mv_backlog_resumo WHERE 1=1"
    params = []

    if estados:
        query += " AND estado = ANY(%s)"
        params.append(estados)

    if clientes:
        query += " AND cliente = ANY(%s)"
        params.append(clientes)

    # ❌ NÃO usa faixa aqui (view não tem horas)

    return consultar_backlog(query, params)


# =========================
# 📊 BACKLOG HISTÓRICO
# =========================
def buscar_backlog_historico(data_inicio, data_fim):
    return consultar_historico("""
        SELECT 
            data_referencia,
            estado,
            pre_entrega,
            cliente,
            horas_backlog_snapshot
        FROM pedidos
        WHERE status = 'backlog'
        AND data_referencia BETWEEN %s AND %s
    """, [data_inicio, data_fim])


# =========================
# 📊 PRODUTIVIDADE (AGORA NO RAILWAY)
# =========================
@st.cache_data(ttl=300)
def buscar_produtividade():
    return consultar_operacional("""
        SELECT 
            cliente,
            estado,
            hub,
            operador,
            data,
            hora,
            turno,
            dispositivo,
            volumes
        FROM produtividade
    """)


# =========================
# 📦 PEDIDOS
# =========================
@st.cache_data(ttl=120)
def buscar_pedidos(limit=1000):
    return consultar_historico("""
        SELECT 
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            horas_backlog_snapshot,
            data_referencia
        FROM pedidos
        ORDER BY data_referencia DESC
        LIMIT %s
    """, [limit])


# =========================
# 💾 LOG IMPORTAÇÃO (RAILWAY)
# =========================
def salvar_log_importacao(logs_df):

    if logs_df.empty:
        return

    conn = conectar_operacional()
    cur = conn.cursor()

    logs_df = logs_df.fillna(0)

    values = [
        (
            int(row["id"] or 0),
            row["nome_arquivo"],
            row["status"],
            int(row["registros"] or 0),
            float(row["tempo_segundos"] or 0),
            row["data_importacao"]
        )
        for _, row in logs_df.iterrows()
    ]

    execute_values(
        cur,
        """
        INSERT INTO log_importacoes (
            id,
            nome_arquivo,
            status,
            registros,
            tempo_segundos,
            data_importacao
        ) VALUES %s
        """,
        values
    )

    conn.commit()
    cur.close()
    conn.close()


# =========================
# 🔍 DRILL
# =========================
def buscar_waybills_por_faixa_dias(data_inicio, data_fim, faixa):

    query = """
        SELECT waybill, estado, cliente, pre_entrega, horas_backlog_snapshot
        FROM pedidos
        WHERE status = 'backlog'
        AND data_referencia BETWEEN %s AND %s
    """

    params = [data_inicio, data_fim]

    if faixa == "1 dia":
        query += " AND horas_backlog_snapshot <= 24"
    elif faixa == "1-5 dias":
        query += " AND horas_backlog_snapshot > 24 AND horas_backlog_snapshot <= 120"
    elif faixa == "5-10 dias":
        query += " AND horas_backlog_snapshot > 120 AND horas_backlog_snapshot <= 240"
    elif faixa == "10-20 dias":
        query += " AND horas_backlog_snapshot > 240 AND horas_backlog_snapshot <= 480"
    elif faixa == "30+ dias":
        query += " AND horas_backlog_snapshot > 720"

    return consultar_historico(query, params)


# =========================
# ⏱️ TEMPO PROCESSAMENTO
# =========================
@st.cache_data(ttl=300)
def buscar_tempo_processamento():

    query = """
        SELECT 
            estado,
            entrada_hub1,
            saida_hub1
        FROM pedidos
        WHERE entrada_hub1 IS NOT NULL
    """

    return consultar_historico(query)   # 🔥 TEM QUE SER ISSO

def buscar_devolucoes(limit=1000):
    return consultar_devolucoes("""
        SELECT *
        FROM devolucoes
        ORDER BY data_devolucao DESC
        LIMIT %s
    """, [limit])