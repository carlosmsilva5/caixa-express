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
        # ttl=0 garante que ele sempre puxe os dados mais frescos da planilha
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        df.columns = [str(c).strip().lower() for c in df.columns] 
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

# ---------------- LÓGICA DE DATAS E FECHAMENTO ----------------
hoje = datetime.now()
data_hoje_str = hoje.strftime("%d/%m/%Y")
mes_atual_str = hoje.strftime("%m/%Y")

def calcular_total_mes(df):
    """Soma todos os valores do mês atual para o painel lateral"""
    if df.empty or 'data' not in df.columns: return 0.0
    df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    mask = df['data_dt'].dt.strftime('%m/%Y') == mes_atual_str
    return pd.to_numeric(df.loc[mask, 'valor'], errors='coerce').sum()

def filtrar_hoje(df):
    """Filtra a base para mostrar apenas as movimentações de hoje"""
    if df.empty or 'data' not in df.columns: return pd.DataFrame(), 0.0
    df_hoje = df[df['data'] == data_hoje_str].copy()
    total_hoje = pd.to_numeric(df_hoje['valor'], errors='coerce').sum()
    return df_hoje, total_hoje

# Variáveis do mês para a barra lateral
vendas_mes = calcular_total_mes(df_vendas)
compras_mes = calcular_total_mes(df_compras)
saldo_mes = vendas_mes - compras_mes

# ---------------- MENU LATERAL ----------------
with st.sidebar:
    st.title("💸 Caixa Express")
    menu = st.radio("Navegação", ["💰 Vendas", "🛒 Compras"])
    
    st.divider()
    
    # --- BLOCO: BALANÇO DO MÊS COM SENHA ---
    st.markdown("### 📊 Balanço do Mês")
    
    # Cria o campo de senha (o type="password" esconde o que é digitado)
    senha_digitada = st.text_input("Senha de acesso:", type="password")
    
    # Verifica se a senha está correta (Você pode mudar "admin123" para a senha que quiser)
    if senha_digitada == "admin123": 
        st.markdown(f"<span style='color:#b0b3b8'>Mês de referência: {mes_atual_str}</span>", unsafe_allow_html=True)
        st.write("")
        st.markdown(f"🟢 **Entradas:** R$ {vendas_mes:,.2f}")
        st.markdown(f"🔴 **Saídas:** R$ {compras_mes:,.2f}")
        
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
        with col1:
            tipo_venda = st.radio("Tipo de Venda", ["Presencial", "Online"], horizontal=True)
        with col2:
            valor = st.number_input("Valor da Venda (R$)", min_value=0.0, format="%.2f", step=10.0)
            
        descricao = st.text_input("Descrição dos produtos (Opcional)", placeholder="Ex: 2 camisetas pretas, 1 boné")
        
        if st.form_submit_button("💰 Confirmar Venda", use_container_width=True):
            if valor > 0:
                nova_venda = pd.DataFrame([{
                    "data": data_hoje_str,
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "tipo": tipo_venda,
                    "descricao": descricao if descricao else "-",
                    "valor": valor
                }])
                save_data("vendas", nova_venda)
                st.success("✅ Venda registrada com sucesso!")
                st.rerun()
            else:
                st.error("⚠️ O valor da venda deve ser maior que zero.")
                
    st.divider()
    
    # --- FECHAMENTO DO DIA (VENDAS) ---
    st.subheader(f"📉 Fechamento do Dia ({data_hoje_str})")
    
    df_vendas_hoje, total_vendas_hoje = filtrar_hoje(df_vendas)
    
    # Card com a soma do dia
    st.markdown(f'<div class="card"><div class="title">Total Vendido Hoje</div><div class="value">R$ {total_vendas_hoje:,.2f}</div></div>', unsafe_allow_html=True)
    
    # Tabela filtrada só com o dia atual
    if not df_vendas_hoje.empty:
        st.dataframe(
            df_vendas_hoje[["hora", "tipo", "descricao", "valor"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "hora": "Hora",
                "tipo": "Tipo",
                "descricao": "Descrição",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma venda registrada hoje ainda. Bora vender! 🚀")

# ---------------- PÁGINA: COMPRAS ----------------
elif menu == "🛒 Compras":
    st.title("Registrar Despesa / Compra")
    
    with st.form("form_compra", clear_on_submit=True):
        valor = st.number_input("Valor da Compra (R$)", min_value=0.0, format="%.2f", step=10.0)
        descricao = st.text_input("Descrição da compra (Opcional)", placeholder="Ex: Fornecedor X, embalagens, etc.")
        
        if st.form_submit_button("🛒 Confirmar Despesa", use_container_width=True):
            if valor > 0:
                nova_compra = pd.DataFrame([{
                    "data": data_hoje_str,
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "descricao": descricao if descricao else "-",
                    "valor": valor
                }])
                save_data("compras", nova_compra)
                st.success("✅ Compra/Despesa registrada com sucesso!")
                st.rerun()
            else:
                st.error("⚠️ O valor da compra deve ser maior que zero.")
                
    st.divider()
    
    # --- FECHAMENTO DO DIA (COMPRAS) ---
    st.subheader(f"📉 Despesas do Dia ({data_hoje_str})")
    
    df_compras_hoje, total_compras_hoje = filtrar_hoje(df_compras)
    
    # Card vermelho com a soma de despesas do dia
    st.markdown(f'<div class="card-red"><div class="title">Total Gasto Hoje</div><div class="value">R$ {total_compras_hoje:,.2f}</div></div>', unsafe_allow_html=True)
    
    # Tabela filtrada só com o dia atual
    if not df_compras_hoje.empty:
        st.dataframe(
            df_compras_hoje[["hora", "descricao", "valor"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "hora": "Hora",
                "descricao": "Descrição",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma despesa registrada hoje. Seu bolso agradece! 💸")
