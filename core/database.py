import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# =========================
# 🔗 CONEXÕES
# =========================
def conectar_backlog():
    return psycopg2.connect(
        os.getenv("DATABASE_URL_BACKLOG"),
        sslmode="require"
    )

def conectar_operacional():
    return psycopg2.connect(
        os.getenv("DATABASE_URL_OPERACIONAL"),
        sslmode="require"
    )

def conectar_historico():
    return psycopg2.connect(
        os.getenv("DATABASE_URL_HISTORICO"),
        sslmode="require"
    )

def executar_historico(query, params=None):
    conn = conectar_historico()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def consultar_historico(query, params=None):
    conn = conectar_historico()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# =========================
# 🚀 EXECUTAR
# =========================
def executar_backlog(query, params=None):
    conn = conectar_backlog()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def executar_operacional(query, params=None):
    conn = conectar_operacional()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

# =========================
# 📊 CONSULTAR
# =========================
def consultar_backlog(query, params=None):
    conn = conectar_backlog()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def consultar_operacional(query, params=None):
    conn = conectar_operacional()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# =========================
# 🧱 CRIAR TABELAS
# =========================
def inicializar_banco():
    executar_backlog("""
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
            data_inbound_ponto TIMESTAMP,
            data_entrega TIMESTAMP,
            status_etapa TEXT,
            nome_arquivo TEXT,
            data_referencia DATE,
            data_importacao TIMESTAMP,
            horas_backlog_snapshot DOUBLE PRECISION,
            faixa_backlog_snapshot TEXT,
            status TEXT
        )
    """)

    executar_backlog("""
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

    executar_operacional("""
        CREATE TABLE IF NOT EXISTS produtividade (
            operador TEXT,
            hub TEXT,
            data DATE,
            volumes INTEGER,
            tempo_medio DOUBLE PRECISION,
            nome_arquivo TEXT,
            data_importacao TIMESTAMP
        )
    """)

    executar_operacional("""
        CREATE TABLE IF NOT EXISTS log_importacoes (
            id INTEGER,
            nome_arquivo TEXT,
            status TEXT,
            registros INTEGER,
            tempo_segundos DOUBLE PRECISION,
            data_importacao TIMESTAMP
        )
    """)

    executar_processamento("""
    CREATE TABLE IF NOT EXISTS tempo_processamento (
        estado TEXT,
        ponto_entrada TEXT,
        entrada_hub1 TIMESTAMP,
        saida_hub1 TIMESTAMP,
        nome_arquivo TEXT,
        data_importacao TIMESTAMP
        )
    """)

def conectar_devolucoes():
    return psycopg2.connect(
        os.getenv("DATABASE_URL_DEVOLUCOES"),
        sslmode="require"
    )

def consultar_devolucoes(query, params=None):
    conn = conectar_devolucoes()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def executar_devolucoes(query, params=None):
    conn = conectar_devolucoes()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def conectar_processamento():
    return psycopg2.connect(
        os.getenv("DATABASE_URL_PROCESSAMENTO"),
        sslmode="require"
    )

def executar_processamento(query, params=None):
    conn = conectar_processamento()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def consultar_processamento(query, params=None):
    conn = conectar_processamento()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df
