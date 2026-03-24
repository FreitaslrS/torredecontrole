import streamlit as st
from core.database import consultar, executar
from psycopg2.extras import execute_values


# =========================
# 🗑️ DELETE
# =========================
def deletar_arquivo(nome_arquivo):
    executar(
        "DELETE FROM pedidos WHERE nome_arquivo = %s",
        [nome_arquivo]
    )


# =========================
# 📂 LISTAR ARQUIVOS
# =========================
@st.cache_data(ttl=300)
def listar_arquivos():
    return consultar("""
        SELECT 
            nome_arquivo, 
            COUNT(*) as registros
        FROM pedidos
        GROUP BY nome_arquivo
        ORDER BY nome_arquivo DESC
    """)


# =========================
# 📊 BACKLOG RESUMO (RÁPIDO)
# =========================
@st.cache_data(ttl=300)
def buscar_backlog_resumo():
    return consultar("""
        SELECT 
            estado,
            pre_entrega,
            cliente,
            COUNT(*) as qtd,
            SUM(CASE WHEN horas_backlog_snapshot > 24 THEN 1 ELSE 0 END) as b24,
            SUM(CASE WHEN horas_backlog_snapshot > 48 THEN 1 ELSE 0 END) as b48,
            SUM(CASE WHEN horas_backlog_snapshot > 72 THEN 1 ELSE 0 END) as b72
        FROM backlog_atual
        GROUP BY estado, pre_entrega, cliente
    """)


# =========================
# 📊 BACKLOG DETALHADO (PAGINADO + FILTRO)
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
            horas_backlog_snapshot,
            faixa_backlog_snapshot,
            data_atualizacao
        FROM backlog_atual
        WHERE 1=1
    """

    params = []

    # 🔥 FILTRO ESTADO
    if estados:
        query += " AND estado = ANY(%s)"
        params.append(estados)

    # 🔥 FILTRO CLIENTE
    if clientes:
        query += " AND cliente = ANY(%s)"
        params.append(clientes)

    # 🔥 FILTRO FAIXA
    if faixa == "24h+":
        query += " AND horas_backlog_snapshot > 24"
    elif faixa == "48h+":
        query += " AND horas_backlog_snapshot > 48"
    elif faixa == "72h+":
        query += " AND horas_backlog_snapshot > 72"

    query += " ORDER BY data_atualizacao DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return consultar(query, params)


# =========================
# 🔢 CONTAGEM (COM FILTRO)
# =========================
@st.cache_data(ttl=120)
def contar_backlog(estados=None, clientes=None, faixa=None):

    query = "SELECT COUNT(*) as total FROM backlog_atual WHERE 1=1"
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

    return consultar(query, params)


# =========================
# 📊 BACKLOG HISTÓRICO
# =========================
@st.cache_data(ttl=600)
def buscar_backlog_historico(data_inicio, data_fim):
    return consultar("""
        SELECT 
            data_referencia,
            estado,
            pre_entrega,
            COUNT(*) as qtd
        FROM pedidos
        WHERE status = 'backlog'
        AND data_referencia BETWEEN %s AND %s
        GROUP BY data_referencia, estado, pre_entrega
    """, [data_inicio, data_fim])


# =========================
# 📊 PRODUTIVIDADE
# =========================
@st.cache_data(ttl=300)
def buscar_produtividade():
    return consultar("""
        SELECT 
            operador,
            hub,
            data,
            volumes,
            tempo_medio
        FROM produtividade
    """)


# =========================
# 📦 PEDIDOS (DEVOLUÇÕES)
# =========================
@st.cache_data(ttl=120)
def buscar_pedidos(limit=1000):
    return consultar(f"""
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
        LIMIT {limit}
    """)


# =========================
# 💾 LOG IMPORTAÇÃO
# =========================
def salvar_log_importacao(logs_df):
    if logs_df.empty:
        return

    from core.database import conectar
    conn = conectar()
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