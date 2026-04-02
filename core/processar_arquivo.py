import pandas as pd
from datetime import datetime
from psycopg2.extras import execute_values
from core.database import (
    conectar_backlog,
    executar_backlog,
    consultar_backlog,
    conectar_operacional,
    executar_operacional,
    conectar_historico,
    executar_historico
)
from core.database import conectar_processamento

import requests
import os

def enviar_telegram(msg):
    TOKEN = 'SEU_TOKEN_AQUI'
    CHAT_ID = 'SEU_CHAT_ID_AQUI'

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={
        'chat_id': CHAT_ID,
        'text': msg
    })

    # ⚠️ BLOCO DESATIVADO (evita erro e loop infinito)
    """
    enviar_telegram(f"...")

    import tkinter as tk

    def executar():
        os.system("Automacao_Anjun.exe")

    janela = tk.Tk()
    janela.title("Automação Anjun")

    botao = tk.Button(janela, text="Executar", command=executar)
    botao.pack(padx=50, pady=30)

    janela.mainloop()
    """

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
    "saida_hub3": ["saída do centro nível 03"],
    "data_inbound_ponto": ["网点入库时间", "tempo de inbound"],
    "data_entrega": ["签收时间", "tempo de assinatura"]
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

def ajustar_data_operacional(data_hora):
    if pd.isna(data_hora):
        return None
    
    if data_hora.hour < 5 or (data_hora.hour == 5 and data_hora.minute < 30):
        return (data_hora - pd.Timedelta(days=1)).date()
    else:
        return data_hora.date()

def limpar_base():
    executar_historico("""
        DELETE FROM pedidos
        WHERE data_referencia < CURRENT_DATE - INTERVAL '30 days'
    """)

def calcular_base_tempo(row):
    return row["entrada_hub1"]


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
        "entrada_hub3","saida_hub3",
        "data_inbound_ponto",   # 🔥 NOVO
        "data_entrega"          # 🔥 NOVO
    ]:
        dados[col] = pd.to_datetime(dados[col], errors="coerce")

    dados["waybill"] = dados["waybill"].astype(str).str.strip()
    dados = dados[(dados["waybill"] != "") & (dados["waybill"].str.lower() != "nan")]

    agora = pd.to_datetime(data_referencia)

    # 🔥 BACKLOG REAL
    mask = (
        dados["entrada_hub1"].notna() &
        dados["entrada_hub2"].isna() &
        dados["entrada_hub3"].isna() &
        dados["saida_hub1"].isna() &
        dados["saida_hub2"].isna() &
        dados["saida_hub3"].isna() &
        dados["data_entrega"].isna()   # 🔥 NOVO
    )

    dados["status"] = "finalizado"
    dados.loc[mask, "status"] = "backlog"

    def classificar_status_avancado(row):

        if pd.notna(row["data_entrega"]):
            return "Entregue"

        if pd.notna(row["entrada_hub3"]):
            return "Hub 3"

        if pd.notna(row["entrada_hub2"]):
            return "Hub 2"

        if pd.notna(row["entrada_hub1"]):
            return "Hub 1"

        return "Sem entrada"

    dados["status_etapa"] = dados.apply(classificar_status_avancado, axis=1)

    # ⏱️ TEMPO
    dados["base_tempo"] = dados.apply(calcular_base_tempo, axis=1)

    # 🔥 CORREÇÃO
    dados = dados[dados["base_tempo"].notna()]

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

def validar_backlog(df):

    erros = []

    # ❌ HUB 2 sem HUB 1
    erro_hub2 = df[
        df["entrada_hub2"].notna() &
        df["entrada_hub1"].isna()
    ]
    if not erro_hub2.empty:
        erros.append(f"HUB2 sem HUB1: {len(erro_hub2)}")

    # ❌ HUB 3 sem HUB 2
    erro_hub3 = df[
        df["entrada_hub3"].notna() &
        df["entrada_hub2"].isna()
    ]
    if not erro_hub3.empty:
        erros.append(f"HUB3 sem HUB2: {len(erro_hub3)}")

    # ❌ saída sem entrada
    erro_saida = df[
        df["saida_hub1"].notna() &
        df["entrada_hub1"].isna()
    ]
    if not erro_saida.empty:
        erros.append(f"Saída sem entrada: {len(erro_saida)}")

    # ❌ horas negativas
    erro_tempo = df[df["horas_backlog_snapshot"] < 0]
    if not erro_tempo.empty:
        erros.append(f"Tempo negativo: {len(erro_tempo)}")

    erro_backlog = df[
        (df["status"] == "backlog") &
        (
            df["entrada_hub2"].notna() |
            df["entrada_hub3"].notna()
        )
    ]

    if not erro_backlog.empty:
        erros.append(f"Backlog inválido (já avançou): {len(erro_backlog)}")

    return erros

def inserir_em_massa(df):
    conn = conectar_historico()
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
        "data_inbound_ponto",
        "data_entrega",
        "status_etapa",
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

    # ✅ valida
    erros = validar_backlog(dados)

    if erros:
        print("🚨 ERROS ENCONTRADOS:")
        for e in erros:
            print(e)

    

    # ✅ filtra backlog
    dados = dados[dados["status"] == "backlog"]

    # ✅ remove duplicados
    dados = dados.drop_duplicates(subset=["waybill"])

    if dados.empty:
        return 0
    
    # 🔥 SALVA HISTÓRICO (ESSA É A LINHA QUE VOCÊ QUER)
    inserir_em_massa(dados)

    # 🔥 pega backlog atual do banco
    existentes = consultar_backlog("SELECT waybill FROM backlog_atual")

    existentes_set = set(existentes["waybill"]) if not existentes.empty else set()
    novos_set = set(dados["waybill"])

    # =========================
    # 🧠 1. REMOVER QUEM SUMIU
    # =========================
    removidos = existentes_set - novos_set

    if removidos:
        conn = conectar_backlog()
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
    conn = conectar_backlog()
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
    import pandas as pd
    from datetime import datetime

    # 🔥 LEITURA
    df = pd.read_excel(arquivo)

    if df.empty:
        return 0

    # 🔥 RENOMEAR
    df = df.rename(columns={
        "客户名称(Nome do Cliente)": "cliente",
        "操作时间(tempo de operação)": "data_hora",
        "收件人州(Estado do destinatário)": "estado",
        "预派送网点(Ponto de Pré-entrega)": "hub",
        "操作人(Operador)": "operador"
    })

    # 🔥 GARANTIR COLUNAS
    df["cliente"] = df.get("cliente", "Desconhecido")
    df["estado"] = df.get("estado", "Desconhecido")
    df["hub"] = df.get("hub", "Desconhecido")
    df["operador"] = df.get("operador", "Desconhecido")

    # 🔥 LIMPEZA
    df["operador"] = (
        df["operador"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    df["hora"] = df["data_hora"].dt.hour
    df["data"] = df["data_hora"].apply(ajustar_data_operacional)

    def definir_turno(data_hora):
        if pd.isna(data_hora):
            return None

        hora = data_hora.hour
        minuto = data_hora.minute

        if (hora == 5 and minuto >= 30) or (6 <= hora < 13) or (hora == 13 and minuto < 50):
            return "T1"
        elif (hora == 13 and minuto >= 50) or (14 <= hora < 22):
            return "T2"
        else:
            return "T3"

    df["turno"] = df["data_hora"].apply(definir_turno)

    # 🔥 CLASSIFICAÇÃO
    def classificar_dispositivo(op):
        if "PERUS01" in op:
            return "Sorter Oval"
        elif "PERUS02" in op:
            return "Sorter Linear"
        else:
            return "Cubometro"

    df["dispositivo"] = df["operador"].apply(classificar_dispositivo)

    # 🔥 VOLUME
    df["volumes"] = 1

    # 🔥 CONTROLE
    df["data_importacao"] = datetime.now()
    df["nome_arquivo"] = arquivo.name

    # 🔥 BANCO
    from psycopg2.extras import execute_values
    from core.database import conectar_operacional

    conn = conectar_operacional()
    cur = conn.cursor()

    cur.execute("DELETE FROM produtividade WHERE nome_arquivo = %s", [arquivo.name])

    colunas = [
        "cliente", "estado", "hub", "operador",
        "data", "hora", "turno", "dispositivo",
        "volumes", "nome_arquivo", "data_importacao"
    ]

    values = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df[colunas].itertuples(index=False, name=None)
    ]

    execute_values(
        cur,
        f"INSERT INTO produtividade ({','.join(colunas)}) VALUES %s",
        values
    )

    conn.commit()
    cur.close()
    conn.close()

    return len(df)
    
def importar_tempo_processamento(arquivo):

    import pandas as pd
    from datetime import datetime
    from psycopg2.extras import execute_values
    from core.database import conectar_processamento

    df = pd.read_excel(arquivo)

    if df.empty:
        return 0

    df.columns = df.columns.str.strip()

    df_tratado = pd.DataFrame()

    df_tratado["estado"] = df["收件人州(Estado do destinatário)"]
    df_tratado["ponto_entrada"] = df["实际入库网点(Ponto de entrada)"]

    df_tratado["entrada_hub1"] = pd.to_datetime(
        df["一级分拨到件时间(Entrada no centro nível 01)"], errors="coerce"
    )

    df_tratado["saida_hub1"] = pd.to_datetime(
        df["一级分拨发件时间(Saída do centro nível 01)"], errors="coerce"
    )

    # 🔥 NOVO (CORRIGIDO COM CHINÊS)
    df_tratado["cliente"] = df["客户名称(Nome do cliente)"]

    df_tratado["hiata"] = df["下一站(Próximo ponto)"] if "下一站(Próximo ponto)" in df.columns else None

    df_tratado["nome_arquivo"] = arquivo.name
    df_tratado["data_importacao"] = datetime.now()

    df_tratado["data_snapshot"] = datetime.now().date()

    # 🔥 remove linhas sem data válida
    df_tratado = df_tratado.dropna(subset=["entrada_hub1"])

    # 🔥 agora sim cria data
    df_tratado["data"] = df_tratado["entrada_hub1"].dt.date

    conn = conectar_processamento()
    cur = conn.cursor()

    colunas = [
        "estado",
        "ponto_entrada",
        "entrada_hub1",
        "saida_hub1",
        "cliente",
        "hiata",
        "data",
        "data_snapshot",
        "nome_arquivo",
        "data_importacao"
    ]

    values = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df_tratado[colunas].itertuples(index=False, name=None)
    ]

    execute_values(
        cur,
        f"INSERT INTO tempo_processamento ({','.join(colunas)}) VALUES %s",
        values
    )

    conn.commit()
    cur.close()
    conn.close()

    return len(df_tratado)