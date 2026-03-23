from core.database import consultar, executar, conectar_duckdb


# =========================
# 📦 INSERÇÃO VIA PARQUET (FUTURO)
# =========================
def inserir_pedidos_parquet(caminho_parquet):
    executar(f"""
        INSERT INTO pedidos
        SELECT *
        FROM read_parquet('{caminho_parquet}') t
        WHERE NOT EXISTS (
            SELECT 1 FROM pedidos p
            WHERE p.waybill = t.waybill
            AND p.data_referencia = t.data_referencia
        )
    """)


# =========================
# 🗑️ DELETAR ARQUIVO
# =========================
def deletar_arquivo(nome_arquivo):
    executar(
        "DELETE FROM pedidos WHERE nome_arquivo = %s",
        [nome_arquivo]
    )


# =========================
# 📄 LISTAR ARQUIVOS
# =========================
def listar_arquivos():
    return consultar("""
        SELECT nome_arquivo, COUNT(*) as registros
        FROM pedidos
        GROUP BY nome_arquivo
        ORDER BY nome_arquivo DESC
    """)


# =========================
# 📊 BUSCAR TODOS PEDIDOS
# =========================
def buscar_pedidos():
    return consultar("""
        SELECT *
        FROM pedidos
    """)


# =========================
# 🔥 BACKLOG ATUAL
# =========================
def buscar_backlog_atual():
    return consultar("""
        SELECT *
        FROM backlog_atual
    """)


# =========================
# 📈 BACKLOG POR PERÍODO
# =========================
def buscar_backlog_periodo(data_inicio, data_fim):
    return consultar("""
        SELECT *
        FROM pedidos
        WHERE data_referencia BETWEEN %s AND %s
        AND horas_backlog_snapshot IS NOT NULL
    """, [data_inicio, data_fim])


# =========================
# 🧾 LOG DE IMPORTAÇÃO
# =========================
def salvar_log_importacao(logs):
    # 🔥 mantém DuckDB só pra esse caso (rápido e compatível)
    con = conectar_duckdb()

    con.register("logs_temp", logs)

    con.execute("""
        INSERT INTO log_importacoes
        SELECT * FROM logs_temp
    """)