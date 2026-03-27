import pandas as pd
from datetime import datetime
from psycopg2.extras import execute_values
from core.database import conectar_postgres, executar, consultar

import requests

def enviar_telegram(msg):
    TOKEN = 'SEU_TOKEN_AQUI'
    CHAT_ID = 'SEU_CHAT_ID_AQUI'

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={
        'chat_id': CHAT_ID,
        'text': msg
    })

    enviar_telegram(f"""
    🚀 Automação Anjun Executada

    📅 Data: {ontem}
    📦 Total: {vol_total}
    🟢 T1: {prod_turnos.get('T1', 0)}
    🟡 T2: {prod_turnos.get('T2', 0)}
    🔴 T3: {prod_turnos.get('T3', 0)}
    """)

    import tkinter as tk

    def executar():
        os.system("Automacao_Anjun.exe")

    janela = tk.Tk()
    janela.title("Automação Anjun")

    botao = tk.Button(janela, text="Executar", command=executar)
    botao.pack(padx=50, pady=30)

    janela.mainloop()

COLUNAS_MAPEAMENTO = {
    "waybill": ["waybill", "awb", "pedido"],
    "cliente": ["cliente"],
    "estado": ["estado", "uf", "estado destino", "destino uf", "州"],
    "cidade": ["cidade", "city", "城市", "destino"],
    "pre_entrega": ["预派送网点", "ponto de pré-entrega", "pre entrega"],
    "proximo_ponto": ["下一站", "proximo ponto", "próximo ponto", "next hub"],
    "entrada_hub1": ["entrada no centro nível 01"],
    "saida_hub1": ["saída do centro nível 01"],
    "entrada_hub2": ["entrada no centro nível 02"],
    "saida_hub2": ["saída do centro nível 02"],
    "entrada_hub3": ["entrada no centro nível 03"],
    "saida_hub3": ["saída do centro nível 03"]
}


def encontrar_coluna_mapeada(df, aliases):
    for col in df.columns:
        for alias in aliases:
            if alias.lower() in col.lower():
                return col
    return None


def classificar_faixa(h):
    if pd.isna(h):
        return None
    elif h <= 24:
        return "0-24h"
    elif h <= 48:
        return "24-48h"
    elif h <= 72:
        return "48-72h"
    else:
        return "72h+"


def limpar_base():
    executar("""
        DELETE FROM pedidos
        WHERE data_referencia < CURRENT_DATE - INTERVAL '30 days'
    """)


def calcular_base_tempo(row):
    if pd.notna(row["entrada_hub3"]) and pd.isna(row["saida_hub3"]):
        return row["entrada_hub3"]
    elif pd.notna(row["entrada_hub2"]) and pd.isna(row["saida_hub2"]):
        return row["entrada_hub2"]
    elif pd.notna(row["entrada_hub1"]) and pd.isna(row["saida_hub1"]):
        return row["entrada_hub1"]
    return None


def preparar_dados(arquivo, data_referencia):
    df = pd.read_excel(arquivo, engine="openpyxl")
    df.columns = df.columns.str.strip()

    dados = pd.DataFrame()

    for coluna_padrao, aliases in COLUNAS_MAPEAMENTO.items():
        col = encontrar_coluna_mapeada(df, aliases)
        dados[coluna_padrao] = df[col] if col else None

    for col in [
        "entrada_hub1","saida_hub1",
        "entrada_hub2","saida_hub2",
        "entrada_hub3","saida_hub3"
    ]:
        dados[col] = pd.to_datetime(dados[col], errors="coerce")

    dados["waybill"] = dados["waybill"].astype(str).str.strip()
    dados = dados[(dados["waybill"] != "") & (dados["waybill"].str.lower() != "nan")]

    agora = pd.to_datetime(data_referencia)

    # 🔥 BACKLOG REAL
    mask = (
        (dados["entrada_hub3"].notna() & dados["saida_hub3"].isna()) |
        (dados["entrada_hub2"].notna() & dados["saida_hub2"].isna()) |
        (dados["entrada_hub1"].notna() & dados["saida_hub1"].isna())
    )

    dados["status"] = "finalizado"
    dados.loc[mask, "status"] = "backlog"

    # ⏱️ TEMPO
    dados["base_tempo"] = dados.apply(calcular_base_tempo, axis=1)

    dados["horas_backlog_snapshot"] = (
        (agora - dados["base_tempo"]).dt.total_seconds() / 3600
    )

    dados["faixa_backlog_snapshot"] = dados["horas_backlog_snapshot"].apply(classificar_faixa)

    dados["data_referencia"] = agora.date()
    dados["data_importacao"] = datetime.now()
    dados["nome_arquivo"] = arquivo.name

    # 🔥 tratar próximo ponto
    dados["proximo_ponto"] = dados["proximo_ponto"].fillna("Sem informação / 无信息")

    return dados


def inserir_em_massa(df):
    conn = conectar_postgres()
    cur = conn.cursor()

    colunas = [
        "waybill",
        "cliente",
        "estado",
        "cidade",
        "pre_entrega",
        "proximo_ponto",
        "entrada_hub1",
        "saida_hub1",
        "entrada_hub2",
        "saida_hub2",
        "entrada_hub3",
        "saida_hub3",
        "nome_arquivo",
        "data_referencia",
        "data_importacao",
        "horas_backlog_snapshot",
        "faixa_backlog_snapshot",
        "status"
    ]

    df = df[colunas]

    def tratar_valor(v):
        if pd.isna(v):
            return None
        return v

    values = [
        tuple(tratar_valor(v) for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    execute_values(
        cur,
        f"INSERT INTO pedidos ({','.join(colunas)}) VALUES %s",
        values
    )

    conn.commit()
    cur.close()
    conn.close()


def importar_excel(arquivo, data_referencia):
    dados = preparar_dados(arquivo, data_referencia)

    if dados.empty:
        return 0

    # 🔥 só backlog
    dados = dados[dados["status"] == "backlog"]
    dados = dados.drop_duplicates(subset=["waybill"])

    if dados.empty:
        return 0
    
    # 🔥 SALVA HISTÓRICO (ESSA É A LINHA QUE VOCÊ QUER)
    inserir_em_massa(dados)

    # 🔥 pega backlog atual do banco
    existentes = consultar("SELECT waybill FROM backlog_atual")

    existentes_set = set(existentes["waybill"]) if not existentes.empty else set()
    novos_set = set(dados["waybill"])

    # =========================
    # 🧠 1. REMOVER QUEM SUMIU
    # =========================
    removidos = existentes_set - novos_set

    if removidos:
        conn = conectar_postgres()
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM backlog_atual WHERE waybill = ANY(%s)",
            (list(removidos),)
        )

        conn.commit()
        cur.close()
        conn.close()

    # =========================
    # 🚀 2. UPSERT (NOVOS + ATUALIZA)
    # =========================
    conn = conectar_postgres()
    cur = conn.cursor()

    values = [
        (
            row["waybill"],
            row["cliente"],
            row["estado"],
            row["cidade"],
            row["pre_entrega"],
            row["proximo_ponto"],
            row["entrada_hub1"],
            row["horas_backlog_snapshot"],
            row["faixa_backlog_snapshot"]
        )
        for _, row in dados.iterrows()
    ]

    execute_values(
        cur,
        """
        INSERT INTO backlog_atual (
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            proximo_ponto,
            entrada_hub1,
            horas_backlog_snapshot,
            faixa_backlog_snapshot
        ) VALUES %s
        ON CONFLICT (waybill)
        DO UPDATE SET
            horas_backlog_snapshot = EXCLUDED.horas_backlog_snapshot,
            faixa_backlog_snapshot = EXCLUDED.faixa_backlog_snapshot,
            proximo_ponto = EXCLUDED.proximo_ponto,
            data_atualizacao = NOW()
        """,
        values
    )

    conn.commit()
    cur.close()
    conn.close()

    return len(dados)


def importar_produtividade(arquivo):
    df = pd.read_excel(arquivo)

    if df.empty:
        return 0

    df.columns = df.columns.str.lower().str.strip()

    df["data_importacao"] = datetime.now()
    df["nome_arquivo"] = arquivo.name

    conn = conectar_postgres()
    cur = conn.cursor()

    cur.execute("DELETE FROM produtividade WHERE nome_arquivo = %s", [arquivo.name])

    cols = df.columns.tolist()

    values = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    execute_values(
        cur,
        f"INSERT INTO produtividade ({','.join(cols)}) VALUES %s",
        values
    )

    conn.commit()
    cur.close()
    conn.close()

    return len(df)

def log(msg):
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {msg}\n")

    log("Iniciando automação")
    log(f"Arquivo lido: {arquivo_recente}")
    log("Finalizado com sucesso")

def pausar(msg="Finalizando..."):
    print(msg)
    try:
        input("\nPressione ENTER para fechar...")
    except:
        import time
        time.sleep(3)