import duckdb
import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# =========================
# 🧱 DUCKDB (LOCAL)
# =========================
BASE_DIR = os.path.abspath(os.getcwd())
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "logistica.db")


def conectar_duckdb():
    os.makedirs(DB_DIR, exist_ok=True)

    con = duckdb.connect(DB_PATH)
    con.execute("PRAGMA threads=4")
    con.execute("PRAGMA memory_limit='1GB'")

    return con


# =========================
# ☁️ POSTGRES (NEON)
# =========================
def conectar_postgres():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# =========================
# 🔄 CONEXÃO INTELIGENTE
# =========================
def conectar():
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise Exception("DATABASE_URL não configurada!")

    return conectar_postgres()


# =========================
# 🚀 EXECUTAR (INSERT/DELETE/UPDATE)
# =========================
def executar(query, params=None):
    conn = conectar()

    # Postgres
    if hasattr(conn, "cursor"):
        cur = conn.cursor()
        cur.execute(query, params or ())
        conn.commit()
        cur.close()
        conn.close()

    # DuckDB
    else:
        conn.execute(query, params or ())


# =========================
# 📊 CONSULTAR (SELECT)
# =========================
def consultar(query, params=None):
    conn = conectar()

    # Postgres
    if hasattr(conn, "cursor"):
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df

    # DuckDB
    else:
        return conn.execute(query, params or ()).df()


# =========================
# 🧱 CRIAR TABELAS
# =========================
def inicializar_banco():
    executar("""
        CREATE TABLE IF NOT EXISTS pedidos (
            waybill TEXT,
            cliente TEXT,
            estado TEXT,
            cidade TEXT,
            pre_entrega TEXT,
            entrada_hub1 TIMESTAMP,
            saida_hub1 TIMESTAMP,
            entrada_hub2 TIMESTAMP,
            saida_hub2 TIMESTAMP,
            entrada_hub3 TIMESTAMP,
            saida_hub3 TIMESTAMP,
            nome_arquivo TEXT,
            data_referencia DATE,
            data_importacao TIMESTAMP,
            horas_backlog_snapshot DOUBLE PRECISION,
            faixa_backlog_snapshot TEXT,
            status TEXT
        )
    """)

    executar("""
        CREATE TABLE IF NOT EXISTS backlog_atual (
            waybill TEXT PRIMARY KEY,
            cliente TEXT,
            estado TEXT,
            cidade TEXT,
            pre_entrega TEXT,
            entrada_hub1 TIMESTAMP,
            horas_backlog_snapshot DOUBLE PRECISION,
            faixa_backlog_snapshot TEXT,
            data_atualizacao TIMESTAMP
        )
    """)

    executar("""
        CREATE TABLE IF NOT EXISTS log_importacoes (
            id INTEGER,
            nome_arquivo TEXT,
            status TEXT,
            registros INTEGER,
            tempo_segundos DOUBLE PRECISION,
            data_importacao TIMESTAMP
        )
    """)