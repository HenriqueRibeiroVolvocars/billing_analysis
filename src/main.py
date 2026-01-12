# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Análise Financeira", layout="wide")
st.title("📊 Análise de Recebimentos e Pagamentos (corrigido)")

uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx ou .xls)", type=["xlsx", "xls"])
if not uploaded_file:
    st.info("Faça upload do arquivo Excel para visualizar os dados.")
    st.stop()

# ---------- leitura ----------
df = pd.read_excel(uploaded_file, dtype=str)  # lê tudo como string para evitar surpresas
st.write(f"Linhas lidas: {len(df):,}")

# ---------- limpeza básica ----------
# remover linhas com Reference nulo
df["Reference"] = df["Reference"].astype(str).str.strip()
df = df[~df["Reference"].isna() & (df["Reference"].str.strip() != "")].copy()
st.write(f"Linhas após remover Reference nulo: {len(df):,}")

# normalizar nomes de colunas (remove espaços estranhos)
df.columns = [c.strip() for c in df.columns]

# ---------- converter coluna de valores (pt-BR -> float) ----------
amt_col = "Amount in local currency"
if amt_col not in df.columns:
    st.error(f"Coluna '{amt_col}' não encontrada no arquivo. Verifique os nomes das colunas.")
    st.stop()

# função de conversão robusta
def br_to_float(x):
    if pd.isna(x): 
        return 0.0
    s = str(x).strip()
    # remover possíveis espaços e 'BRL' etc
    # keep digits, dots, commas, minus
    # tratar casos com ponto de milhares e vírgula decimal: '8.698,71'
    # ou já com ponto decimal: '8698.71'
    s = s.replace(" ", "")
    # remover moeda se existir
    s = s.replace("BRL", "").replace("brl", "")
    # se tiver vírgula e ponto, assumimos ponto = milhares, vírgula = decimal
    if s.count(",") >= 1 and s.count(".") >= 1:
        s = s.replace(".", "")
        s = s.replace(",", ".")
    else:
        # se só tiver vírgula -> vírgula decimal
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        # se tiver só pontos e mais de 1 ponto, pode ser milhares -> remover todos os pontos e manter inteiro
        # se tiver só um ponto, deixa como está (decimal)
    # remover quaisquer caracteres que não sejam dígitos, '.' ou '-' 
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
    try:
        return float(cleaned) if cleaned not in ("", ".", "-") else 0.0
    except:
        return 0.0

df["Amount_float"] = df[amt_col].apply(br_to_float)

# ---------- converter datas (opcional) ----------
date_cols = ["Document Date", "Net due date", "Entry Date"]
for c in date_cols:
    if c in df.columns:
        df[c + "_parsed"] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")

# ---------- mapeamento (tabela que você passou) ----------
map_data_v1 = {
    "Conta": [301301, 301303, 301373, 342901, 302301, 302303, 301379, 301381,
              301382, 301383, 301384, 362501, 399903, 391101],
    "Descrição": [
        "Sale new cars, ngc", "RecBrVenVeíML-Cancel", "Sale basic car, ngc",
        "Rebates, aftermarket, incurred", "Sales aftermrkt ngc", "Canc Sale afterm ngc",
        "Sales other, ngc", "Rec Bruta Serviços Outras", "Receita Volvo On Call",
        "Receita Software", "Receita Webshop", "Comissão",
        "Outras Receitas Eletrificação", "Receita Bruta de Serviços - Aluguel a Executivo"
    ],
    "Classificação": [
        "Cars", "Cars", "Cars", "Cars", "P&A", "P&A", "P&A", "Comissão",
        "Comissão", "Others", "Others", "Comissão", "Eletrificação", "Locação"
    ]
}
# ---------- mapeamento (nova tabela fornecida) ----------
map_data = {
    "Document Type": ["MA", "42", "RV", "WO", "96", "50", "71"],
    "Descrição": [
        "peças",
        "Frota",
        "veículos e notas de software",
        "veículos em que a NF foi cancelada",
        "veículos",
        "veículos, locação, recarga eletrificação e comissão",
        "eletrificação"
    ]
}

map_df = pd.DataFrame(map_data)
map_df["Document Type"] = map_df["Document Type"].astype(str).str.strip()

# garantir que a coluna 'Document Type' no df também é string
df["Document Type_clean"] = df["Document Type"].astype(str).str.strip()

# faz o merge direto por Document Type (agora ambos são strings)
df = df.merge(map_df, left_on="Document Type_clean", right_on="Document Type", how="left")

# renomeia para manter consistência
df.rename(columns={"Descrição": "Classificação"}, inplace=True)

# marca registros não classificados como "Unknown"
df["Classificação"] = df["Classificação"].fillna("Unknown")

# cria coluna Recebido/Pago
df["Tipo Valor"] = df["Amount_float"].apply(lambda x: "Recebido (+)" if x > 0 else "Pago (-)")

# debug opcional
st.write(f"Registros sem classificação (Unknown): {(df['Classificação'] == 'Unknown').sum():,} / {len(df):,}")

# ---------- filtros ----------
col1, col2 = st.columns(2)
customers = ["Todos"] + sorted(df["Customer"].dropna().unique().tolist())
classes = ["Todas"] + sorted(df["Classificação"].dropna().unique().tolist())

with col1:
    selected_customer = st.selectbox("Filtrar por Customer:", customers)
with col2:
    selected_class = st.selectbox("Filtrar por Classificação:", classes)

filtered = df.copy()
if selected_customer != "Todos":
    filtered = filtered[filtered["Customer"] == selected_customer]
if selected_class != "Todas":
    filtered = filtered[filtered["Classificação"] == selected_class]

# ---------- gráficos ----------
st.subheader("📈 Valores por Classificação")
chart_data = filtered.groupby(["Classificação","Tipo Valor"])["Amount_float"].sum().reset_index()
fig1 = px.bar(chart_data, x="Classificação", y="Amount_float", color="Tipo Valor", barmode="group", title="Recebido (+) vs Pago (-) por Classificação", text_auto=".2s")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("👥 Valores por Customer")
chart_cust = filtered.groupby(["Customer","Tipo Valor"])["Amount_float"].sum().reset_index()
fig2 = px.bar(chart_cust, x="Customer", y="Amount_float", color="Tipo Valor", barmode="group", title="Recebido (+) vs Pago (-) por Customer", text_auto=".2s")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("📄 Tabela")
st.dataframe(filtered.drop(columns=["Document Type_clean","dt_lower","Document Type_numstr"] , errors="ignore"))

# ---------- totais rápidos ----------
st.subheader("💡 Totais Rápidos")
colA, colB, colC = st.columns(3)
with colA:
    st.metric("Total Recebido (+)", f"{df[df['Amount_float']>0]['Amount_float'].sum():,.2f}")
with colB:
    st.metric("Total Pago (-)", f"{df[df['Amount_float']<0]['Amount_float'].sum():,.2f}")
with colC:
    st.metric("Saldo Líquido", f"{df['Amount_float'].sum():,.2f}")

# ---------- export opcional ----------
buffer = BytesIO()
filtered.to_excel(buffer, index=False)
st.download_button("📥 Baixar dados filtrados (Excel)", data=buffer.getvalue(), file_name="dados_filtrados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
