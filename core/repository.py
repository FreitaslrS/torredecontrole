from core.database import consultar, executar, conectar_duckdb


# =========================
# 📥 INSERÇÃO (PARQUET) - CORRIGIDO
# =========================
def inserir_pedidos_parquet(caminho_parquet):
    executar(f"""
        INSERT INTO pedidos (
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            entrada_hub1,
            saida_hub1,
            entrada_hub2,
            saida_hub2,
            entrada_hub3,
            saida_hub3,
            nome_arquivo,
            data_referencia,
            data_importacao,
            horas_backlog_snapshot,
            faixa_backlog_snapshot,
            status
        )
        SELECT
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            entrada_hub1,
            saida_hub1,
            entrada_hub2,
            saida_hub2,
            entrada_hub3,
            saida_hub3,
            nome_arquivo,
            data_referencia,
            data_importacao,
            horas_backlog_snapshot,
            faixa_backlog_snapshot,
            status
        FROM read_parquet('{caminho_parquet}') t
        WHERE NOT EXISTS (
            SELECT 1 FROM pedidos p
            WHERE p.waybill = t.waybill
            AND p.data_referencia = t.data_referencia
        )
    """)


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
# 📊 PEDIDOS GERAIS
# =========================
def buscar_pedidos():
    return consultar("""
        SELECT 
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            horas_backlog_snapshot,
            data_referencia
        FROM pedidos
    """)


# =========================
# 🔥 BACKLOG POR PERÍODO
# =========================
def buscar_backlog_periodo(data_inicio, data_fim):
    return consultar("""
        SELECT 
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            horas_backlog_snapshot,
            data_referencia
        FROM pedidos
        WHERE data_referencia BETWEEN %s AND %s
        AND horas_backlog_snapshot IS NOT NULL
    """, [data_inicio, data_fim])


# =========================
# ⚡ BACKLOG ATUAL
# =========================
def buscar_backlog_atual():
    return consultar("""
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
    """)


# =========================
# 📊 BACKLOG OTIMIZADO
# =========================
def buscar_backlog_fast(data_inicio, data_fim):
    return consultar("""
        SELECT *
        FROM mv_backlog
        WHERE data_referencia BETWEEN %s AND %s
    """, [data_inicio, data_fim])


# =========================
# 💾 LOG IMPORTAÇÃO
# =========================
def salvar_log_importacao(logs):
    con = conectar_duckdb()
    con.register("logs_temp", logs)

    con.execute("""
        INSERT INTO log_importacoes
        SELECT * FROM logs_temp
    """)