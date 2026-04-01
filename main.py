import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------- CONFIGURAÇÃO INICIAL ----------------
st.set_page_config(layout="wide", page_title="Caixa Express", page_icon="💸")

# ---------------- CSS PREMIUM (MODO ESCURO) ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background-color: #000000; }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; text-align: center; border-left: 5px solid #3ec6a8; margin-bottom: 20px;}
    .card-red { background: #3a3b3c; padding: 18px; border-radius: 10px; text-align: center; border-left: 5px solid #e74c3c; margin-bottom: 20px;}
    .title { font-size: 14px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 28px; font-weight: bold; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO COM O GOOGLE SHEETS ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        # Limpa nomes de colunas: remove espaços e coloca em minúsculo
        df.columns = [str(c).strip().lower() for c in df.columns] 
        # Remove colunas duplicadas
        df = df.loc[:, ~df.columns.duplicated()].copy()
        return df
    except:
        return pd.DataFrame()

def save_data(sheet, df_new):
    try:
        df_atual = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        df_novo = pd.concat([df_atual, df_new], ignore_index=True)
        conn.update(worksheet=sheet, data=df_novo)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# ---------------- CARREGANDO AS BASES ----------------
df_vendas = load_data("vendas")
df_compras = load_data("compras")

# ---------------- LÓGICA DE DATAS E CÁLCULOS ----------------
hoje_dt = datetime.now()
data_hoje_str = hoje_dt.strftime("%d/%m/%Y")
mes_atual_str = hoje_dt.strftime("%m/%Y")

def processar_financeiro(df):
    """Garante que datas e valores estejam no formato correto para calculo"""
    if df.empty: return df, 0.0, 0.0
    
    # Garante que 'valor' seja número
    if 'valor' in df.columns:
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    
    # Garante que 'data' seja string limpa
    if 'data' in df.columns:
        df['data'] = df['data'].astype(str).str.strip()
        
    # Soma do Mês
    try:
        df['temp_data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        mask_mes = df['temp_data_dt'].dt.strftime('%m/%Y') == mes_atual_str
        total_mes = df.loc[mask_mes, 'valor'].sum()
    except:
        total_mes = 0.0
        
    # Soma de Hoje
    total_hoje = df[df['data'] == data_hoje_str]['valor'].sum()
    
    return df, total_hoje, total_mes

# Processando os dados
df_vendas, v_hoje, v_mes = processar_financeiro(df_vendas)
df_compras, c_hoje, c_mes = processar_financeiro(df_compras)
saldo_mes = v_mes - c_mes

# ---------------- MENU LATERAL ----------------
with st.sidebar:
    st.title("💸 Caixa Express")
    menu = st.radio("Navegação", ["💰 Vendas", "🛒 Compras"])
    st.divider()
    
    st.markdown("### 📊 Balanço do Mês")
    senha_digitada = st.text_input("Senha de acesso:", type="password")
    
    if senha_digitada == "admin123": 
        st.write(f"Mês: {mes_atual_str}")
        st.markdown(f"🟢 **Entradas:** R$ {v_mes:,.2f}")
        st.markdown(f"🔴 **Saídas:** R$ {c_mes:,.2f}")
        cor_saldo = "#3ec6a8" if saldo_mes >= 0 else "#e74c3c"
        st.markdown(f"### Saldo: <span style='color:{cor_saldo}'>R$ {saldo_mes:,.2f}</span>", unsafe_allow_html=True)
    elif senha_digitada != "":
        st.error("Senha incorreta.")
    else:
        st.info("Área restrita à gerência.")

# ---------------- PÁGINA: VENDAS ----------------
if menu == "💰 Vendas":
    st.title("Registrar Nova Venda")
    with st.form("form_venda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: tipo_venda = st.radio("Tipo", ["Presencial", "Online"], horizontal=True)
        with col2: valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        descricao = st.text_input("Descrição (Opcional)")
        
        if st.form_submit_button("💰 Confirmar Venda"):
            if valor > 0:
                nova = pd.DataFrame([{"data": data_hoje_str, "hora": datetime.now().strftime("%H:%M:%S"), "tipo": tipo_venda, "descricao": descricao if descricao else "-", "valor": valor}])
                save_data("vendas", nova)
                st.rerun()

    st.divider()
    st.subheader(f"📉 Fechamento do Dia ({data_hoje_str})")
    st.markdown(f'<div class="card"><div class="title">Total Vendido Hoje</div><div class="value">R$ {v_hoje:,.2f}</div></div>', unsafe_allow_html=True)
    
    df_v_hoje = df_vendas[df_vendas['data'] == data_hoje_str]
    if not df_v_hoje.empty:
        # --- AQUI ESTÁ A CORREÇÃO DA TABELA DE VENDAS ---
        st.dataframe(
            df_v_hoje[["data", "hora", "tipo", "descricao", "valor"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "data": "Data",
                "hora": "Hora",
                "tipo": "Tipo",
                "descricao": "Descrição",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f") # Força o formato de moeda
            }
        )
    else:
        st.info("Nenhuma venda hoje.")

# ---------------- PÁGINA: COMPRAS ----------------
elif menu == "🛒 Compras":
    st.title("Registrar Despesa")
    with st.form("form_compra", clear_on_submit=True):
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        descricao = st.text_input("Descrição (Opcional)")
        
        if st.form_submit_button("🛒 Confirmar Despesa"):
            if valor > 0:
                nova = pd.DataFrame([{"data": data_hoje_str, "hora": datetime.now().strftime("%H:%M:%S"), "descricao": descricao if descricao else "-", "valor": valor}])
                save_data("compras", nova)
                st.rerun()

    st.divider()
    st.subheader(f"📉 Despesas do Dia ({data_hoje_str})")
    st.markdown(f'<div class="card-red"><div class="title">Total Gasto Hoje</div><div class="value">R$ {c_hoje:,.2f}</div></div>', unsafe_allow_html=True)
