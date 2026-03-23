import pandas as pd
from datetime import datetime
from psycopg2.extras import execute_values
from core.database import conectar_postgres

COLUNAS_MAPEAMENTO = {
    "waybill": ["waybill", "awb", "pedido"],
    "cliente": ["cliente"],
    "estado": ["estado"],
    "cidade": ["cidade", "city", "城市", "destino"],
    "pre_entrega": ["预派送网点", "ponto de pré-entrega", "pre entrega"],
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


def tratar_valor(v):
    if pd.isna(v):
        return None
    return v


def preparar_dados(arquivo, data_referencia):
    df = pd.read_excel(arquivo, engine="openpyxl")
    df.columns = df.columns.str.strip()

    if df.empty:
        raise ValueError("Arquivo vazio")

    dados = pd.DataFrame()

    for coluna_padrao, aliases in COLUNAS_MAPEAMENTO.items():
        col = encontrar_coluna_mapeada(df, aliases)
        dados[coluna_padrao] = df[col] if col else None

    for col in ["entrada_hub1","saida_hub1","entrada_hub2","saida_hub2","entrada_hub3","saida_hub3"]:
        dados[col] = pd.to_datetime(dados[col], errors="coerce")

    dados["waybill"] = dados["waybill"].astype(str).str.strip()
    dados = dados[(dados["waybill"] != "") & (dados["waybill"].str.lower() != "nan")]

    agora = pd.to_datetime(data_referencia)

    mask = (dados["entrada_hub1"].notna() & dados["saida_hub1"].isna())

    dados["horas_backlog_snapshot"] = None

    dados.loc[mask, "horas_backlog_snapshot"] = (
        (agora - dados.loc[mask, "entrada_hub1"]).dt.total_seconds() / 3600
    )

    dados["faixa_backlog_snapshot"] = dados["horas_backlog_snapshot"].apply(classificar_faixa)

    dados["status"] = "finalizado"
    dados.loc[mask, "status"] = "backlog"

    dados["data_referencia"] = agora.date()
    dados["data_importacao"] = datetime.now()
    dados["nome_arquivo"] = arquivo.name

    return dados


def inserir_em_massa(df):
    conn = conectar_postgres()
    cur = conn.cursor()

    cols = [
        "waybill",
        "cliente",
        "estado",
        "cidade",
        "pre_entrega",
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

    df = df[cols]

    values = [
        tuple(tratar_valor(v) for v in row)
        for row in df.to_numpy()
    ]

    query = f"""
        INSERT INTO pedidos ({','.join(cols)})
        VALUES %s
    """

    execute_values(cur, query, values)

    conn.commit()
    cur.close()
    conn.close()


def importar_excel(arquivo, data_referencia):
    dados = preparar_dados(arquivo, data_referencia)

    if dados.empty:
        return 0

    conn = conectar_postgres()
    cur = conn.cursor()

    cur.execute("DELETE FROM pedidos WHERE nome_arquivo = %s", [arquivo.name])

    conn.commit()
    cur.close()
    conn.close()

    dados = dados.drop_duplicates(subset=["waybill", "data_referencia"])

    inserir_em_massa(dados)

    from core.database import executar

    executar("DELETE FROM backlog_atual")

    # ✅ CORREÇÃO AQUI (SEM SELECT *)
    executar("""
        INSERT INTO backlog_atual (
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            entrada_hub1,
            horas_backlog_snapshot,
            faixa_backlog_snapshot,
            data_atualizacao
        )
        SELECT
            waybill,
            cliente,
            estado,
            cidade,
            pre_entrega,
            entrada_hub1,
            horas_backlog_snapshot,
            faixa_backlog_snapshot,
            CURRENT_TIMESTAMP
        FROM (
            SELECT
                waybill,
                cliente,
                estado,
                cidade,
                pre_entrega,
                entrada_hub1,
                horas_backlog_snapshot,
                faixa_backlog_snapshot,
                ROW_NUMBER() OVER (
                    PARTITION BY waybill
                    ORDER BY data_referencia DESC
                ) as rn
            FROM pedidos
            WHERE status = 'backlog'
        ) t
        WHERE rn = 1
    """)

    return len(dados)