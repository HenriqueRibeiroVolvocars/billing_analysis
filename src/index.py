import streamlit as st
import pandas as pd
import numpy as np

# =====================
# Configuração da página
# =====================
st.set_page_config(
    page_title="Análise Financeira de Pedidos",
    layout="wide"
)

st.title("📊 Análise Financeira de Pedidos")

# =====================
# Upload do arquivo
# =====================
uploaded_file = st.file_uploader(
    "Faça upload do arquivo Excel",
    type=["xlsx"]
)

# =====================
# Colunas financeiras
# =====================
COLUNAS_FINANCEIRAS = [
    "Valor de Nota Fiscal",
    "Valor Esperado Sinal",
    "Valor Pago Sinal",
    "Valor Esperado à Vista ",
    "Valor Pago à Vista",
    "Valor Esperado Usado",
    "Valor Pago Usado",
    "Valor Esperado Financiado",
    "Valor Pago Financiado",
    "Valor Esperado Leasing",
    "Valor Pago Leasing"
]

# =====================
# Funções utilitárias
# =====================
def tratar_valor_monetario(col):
    """
    Converte qualquer lixo de Excel em float seguro
    """
    col = (
        col.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(col, errors="coerce")

def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =====================
# Processamento
# =====================
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # =====================
    # Tratamento financeiro (FORÇADO)
    # =====================
    for col in COLUNAS_FINANCEIRAS:
        if col in df.columns:
            df[col] = tratar_valor_monetario(df[col])

    # Segurança extra: garantir dtype float
    df[COLUNAS_FINANCEIRAS] = df[COLUNAS_FINANCEIRAS].astype(float)

    # =====================
    # Filtros
    # =====================
    st.sidebar.header("🔎 Filtros")

    pedidos = sorted(df["Número do Pedido"].dropna().unique())
    pedido_selecionado = st.sidebar.multiselect(
        "Número do Pedido",
        pedidos
    )

    if pedido_selecionado:
        df_filtrado = df[df["Número do Pedido"].isin(pedido_selecionado)].copy()
    else:
        df_filtrado = df.copy()

    # 🔒 REFORÇO CRÍTICO (após o filtro!)
    df_filtrado[COLUNAS_FINANCEIRAS] = df_filtrado[COLUNAS_FINANCEIRAS].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0)

    # =====================
    # KPIs
    # =====================
    st.subheader("💰 Totais Financeiros")

    # Valor NF (linha única)
    valor_nf = df_filtrado["Valor de Nota Fiscal"].sum(numeric_only=True)
    st.metric(
        label="Valor de Nota Fiscal",
        value=formatar_real(valor_nf)
    )

    st.markdown("---")

    # Pares Esperado x Pago
    pares_valores = [
        ("Valor Esperado Sinal", "Valor Pago Sinal"),
        ("Valor Esperado à Vista ", "Valor Pago à Vista"),
        ("Valor Esperado Usado", "Valor Pago Usado"),
        ("Valor Esperado Financiado", "Valor Pago Financiado"),
        ("Valor Esperado Leasing", "Valor Pago Leasing"),
    ]

    for esperado, pago in pares_valores:
        col1, col2 = st.columns(2)

        total_esperado = df_filtrado[esperado].sum(numeric_only=True)
        total_pago = df_filtrado[pago].sum(numeric_only=True)

        col1.metric(
            label=esperado,
            value=formatar_real(total_esperado)
        )

        col2.metric(
            label=pago,
            value=formatar_real(total_pago)
        )

    # =====================
    # Organização da tabela
    # =====================
    outras_colunas = [c for c in df_filtrado.columns if c not in COLUNAS_FINANCEIRAS]
    df_filtrado = df_filtrado[outras_colunas + COLUNAS_FINANCEIRAS]

    st.subheader("📄 Dados Detalhados")
    st.dataframe(df_filtrado, use_container_width=True)

else:
    st.info("👆 Faça upload do arquivo Excel para iniciar.")
