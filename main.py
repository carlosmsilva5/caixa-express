import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# ---------------- CONFIGURAÇÃO INICIAL ----------------
st.set_page_config(layout="wide", page_title="Caixa Express", page_icon="💸")

# Inicialização das variáveis de meta na sessão (para não precisar de nova planilha)
if 'meta_diaria' not in st.session_state:
    st.session_state['meta_diaria'] = 0.0
if 'meta_mensal' not in st.session_state:
    st.session_state['meta_mensal'] = 0.0

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
        df.columns = [str(c).strip().lower() for c in df.columns] 
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

def update_sheet(sheet, df_completo):
    try:
        conn.update(worksheet=sheet, data=df_completo)
        st.cache_data.clear()
        st.success("Registro atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")

# ---------------- CARREGANDO AS BASES ----------------
df_vendas = load_data("vendas")
df_compras = load_data("compras") # Mantido nome interno para conexão

# ---------------- LÓGICA DE DATAS E CÁLCULOS ----------------
fuso_br = pytz.timezone('America/Sao_Paulo')
hoje_dt = datetime.now(fuso_br)
data_hoje_str = hoje_dt.strftime("%d/%m/%Y")
mes_atual_str = hoje_dt.strftime("%m/%Y")

def processar_financeiro(df):
    if df.empty: return df, 0.0, 0.0
    if 'valor' in df.columns:
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    if 'data' in df.columns:
        df['data'] = df['data'].astype(str).str.strip()
        try:
            df['temp_data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
            mask_mes = df['temp_data_dt'].dt.strftime('%m/%Y') == mes_atual_str
            total_mes = df.loc[mask_mes, 'valor'].sum()
        except:
            total_mes = 0.0
        total_hoje = df[df['data'] == data_hoje_str]['valor'].sum()
    else:
        total_mes = 0.0
        total_hoje = 0.0
    return df, total_hoje, total_mes

df_vendas, v_hoje, v_mes = processar_financeiro(df_vendas)
df_compras, c_hoje, c_mes = processar_financeiro(df_compras)
saldo_mes = v_mes - c_mes

# ---------------- MENU LATERAL ----------------
with st.sidebar:
    st.title("💸 Pegue Jeans")
    # Trocado de "Compras" para "Despesas"
    menu = st.radio("Navegação", ["💰 Vendas", "💸 Despesas", "🛠️ Editar", "📊 Balanço"])
    st.divider()
    st.info("Selecione 'Balanço' para ver o relatório completo e filtrar por mês/ano.")
    st.markdown("### 📊 Balanço do Mês")
    senha_digitada = st.text_input("Senha de acesso:", type="password")
    if senha_digitada == "jana@2018": 
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
    st.title("Registrar Venda")
    with st.form("form_venda", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            venda_data = st.date_input("Data da Venda", hoje_dt, format="DD/MM/YYYY") # Novo Campo de Data
        with col2: 
            tipo_venda = st.selectbox("Canal", ["Presencial", "Online"])
        with col3: 
            forma_pagamento = st.selectbox("Pagamento", ["Cartão", "Pix", "Dinheiro"])
        with col4: 
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", step=10.0)
            
        col_desc, col_vazia = st.columns([2, 1]) 
        with col_desc:
            descricao = st.text_area("Descrição Opcional", placeholder="Digite os detalhes da venda aqui...", height=100)
        
        if st.form_submit_button("💰 Confirmar Venda"):
            if valor > 0:
                nova = pd.DataFrame([{
                    "data": venda_data.strftime("%d/%m/%Y"), # Usa a data selecionada
                    "hora": datetime.now(fuso_br).strftime("%H:%M:%S"), 
                    "tipo": tipo_venda, 
                    "pagamento": forma_pagamento,
                    "descricao": descricao if descricao else "-", 
                    "valor": valor
                }])
                save_data("vendas", nova)
                st.rerun()

    st.divider()
    st.subheader(f"📉 Fechamento do Dia ({data_hoje_str})")
    
    # --- NOVO: Lógica para exibir as metas se configuradas ---
    m_diaria = st.session_state['meta_diaria']
    m_mensal = st.session_state['meta_mensal']
    
    if m_diaria > 0 or m_mensal > 0:
        qtd_colunas = 1 + (1 if m_diaria > 0 else 0) + (1 if m_mensal > 0 else 0)
        colunas_metricas = st.columns(qtd_colunas)
        
        with colunas_metricas[0]:
            st.markdown(f'<div class="card"><div class="title">Total Vendido Hoje</div><div class="value">R$ {v_hoje:,.2f}</div></div>', unsafe_allow_html=True)
        
        idx = 1
        if m_diaria > 0:
            with colunas_metricas[idx]:
                st.markdown(f'<div class="card"><div class="title">Meta Diária</div><div class="value">R$ {m_diaria:,.2f}</div></div>', unsafe_allow_html=True)
            idx += 1
            
        if m_mensal > 0:
            with colunas_metricas[idx]:
                st.markdown(f'<div class="card"><div class="title">Meta Mensal</div><div class="value">R$ {m_mensal:,.2f}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="card"><div class="title">Total Vendido Hoje</div><div class="value">R$ {v_hoje:,.2f}</div></div>', unsafe_allow_html=True)
    # ---------------------------------------------------------
    
    df_v_hoje = df_vendas[df_vendas['data'] == data_hoje_str]
    if not df_v_hoje.empty:
        colunas_exibir = ["data", "hora", "tipo", "pagamento", "descricao", "valor"]
        exibir_df = df_v_hoje[[c for c in colunas_exibir if c in df_v_hoje.columns]]
        st.dataframe(exibir_df, use_container_width=True, hide_index=True,
            column_config={
                "data": "Data", "hora": "Hora", "tipo": "Canal", 
                "pagamento": "Pagamento", "descricao": "Descrição",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
            })
    else:
        st.info("Nenhuma venda hoje.")

# ---------------- PÁGINA: DESPESAS (ANTIGA COMPRAS) ----------------
elif menu == "💸 Despesas":
    st.title("💸 Gestão de Despesas")
    senha_compras = st.text_input("Digite a senha para acessar Despesas:", type="password", key="acesso_compras")
    if senha_compras == "jana@2018":
        st.success("Acesso Liberado!")
        st.divider()
        st.subheader("Registrar Nova Despesa")
        with st.form("form_compra", clear_on_submit=True):
            col_c1, col_c2, col_c3 = st.columns(3) # Dividi em 3 colunas
            with col_c1:
                # NOVO: Campo de data para despesas
                despesa_data = st.date_input("Data da Despesa", hoje_dt, format="DD/MM/YYYY")
            with col_c2:
                valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            with col_c3:
                tipo_despesa = st.selectbox("Tipo de Despesa", ["Roupas", "Salários Colaboradores", "Impostos", "Contador", "Aluguel", "Marketing", "Luz", "Água", "Internet", "Outras"])
            
            descricao = st.text_input("Descrição (Opcional)")
            
            if st.form_submit_button("💸 Confirmar Despesa"):
                if valor > 0:
                    nova = pd.DataFrame([{
                        "data": despesa_data.strftime("%d/%m/%Y"), # Salva a data selecionada
                        "hora": datetime.now(fuso_br).strftime("%H:%M:%S"), 
                        "tipo": tipo_despesa, 
                        "descricao": descricao if descricao else "-", 
                        "valor": valor
                    }])
                    save_data("compras", nova)
                    st.rerun()
        st.divider()
        st.subheader(f"📉 Despesas do Dia ({data_hoje_str})")
        st.markdown(f'<div class="card-red"><div class="title">Total Gasto Hoje</div><div class="value">R$ {c_hoje:,.2f}</div></div>', unsafe_allow_html=True)
        df_c_hoje = df_compras[df_compras['data'] == data_hoje_str]
        if not df_c_hoje.empty:
            st.dataframe(
                df_c_hoje[["data", "hora", "tipo", "descricao", "valor"]] if "tipo" in df_c_hoje.columns else df_c_hoje[["data", "hora", "descricao", "valor"]], 
                use_container_width=True, hide_index=True,
                column_config={"data": "Data", "hora": "Hora", "tipo": "Tipo", "descricao": "Descrição", "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")}
            )
        else:
            st.info("Nenhuma despesa registrada hoje.")
    elif senha_compras != "":
        st.error("Senha incorreta.")
    else:
        st.info("Aba protegida. Insira a senha de administrador.")

# ---------------- PÁGINA: EDITAR ----------------
elif menu == "🛠️ Editar":
    st.title("🛠️ Editar Registros")
    categoria = st.selectbox("Selecione a categoria", ["Vendas", "Despesas"])
    df_base = df_vendas if categoria == "Vendas" else df_compras
    nome_aba = "vendas" if categoria == "Vendas" else "compras"

    if not df_base.empty:
        st.subheader("🔍 Filtrar por Período")
        df_base['Data_DT'] = pd.to_datetime(df_base['data'], format='%d/%m/%Y', errors='coerce')
        df_base = df_base.dropna(subset=['Data_DT'])
        df_base['Dia'] = df_base['Data_DT'].dt.strftime('%d')
        df_base['Mês'] = df_base['Data_DT'].dt.strftime('%m')
        df_base['Ano'] = df_base['Data_DT'].dt.strftime('%Y')
        
        col_d, col_m, col_a = st.columns(3)
        with col_a:
            lista_anos = sorted(df_base['Ano'].unique(), reverse=True)
            ano_edit = st.selectbox("Ano", lista_anos, index=0)
        with col_m:
            meses_disp = sorted(df_base[df_base['Ano'] == ano_edit]['Mês'].unique())
            mes_edit = st.selectbox("Mês", meses_disp, index=0)
        with col_d:
            dias_disp = sorted(df_base[(df_base['Ano'] == ano_edit) & (df_base['Mês'] == mes_edit)]['Dia'].unique())
            dia_edit = st.selectbox("Dia", dias_disp, index=0)

        df_filtrado_edit = df_base[(df_base['Dia'] == dia_edit) & (df_base['Mês'] == mes_edit) & (df_base['Ano'] == ano_edit)].copy()

        if not df_filtrado_edit.empty:
            st.divider()
            opcoes = [f"ID {i} | {row['hora']} | R$ {row['valor']:.2f} | {row['descricao'][:30]}..." for i, row in df_filtrado_edit.iterrows()]
            selecao = st.selectbox("Escolha o registro para alterar", opcoes)
            index_selecionado = int(selecao.split("ID ")[1].split(" |")[0])
            linha_atual = df_filtrado_edit.loc[index_selecionado]

            with st.form("form_edicao"):
                st.subheader(f"Editando Registro ID {index_selecionado}")
                c1, c2 = st.columns(2)
                with c1: nova_data = st.text_input("Data (dd/mm/aaaa)", value=linha_atual['data'])
                with c2: nova_hora = st.text_input("Hora", value=linha_atual['hora'])
                novo_valor = st.number_input("Valor (R$)", value=float(linha_atual['valor']), format="%.2f", step=10.0)
                nova_desc = st.text_area("Descrição", value=linha_atual['descricao'], height=100)
                
                if categoria == "Vendas":
                    ce1, ce2 = st.columns(2)
                    with ce1: novo_canal = st.selectbox("Canal", ["Presencial", "Online"], index=0 if linha_atual.get('tipo') == "Presencial" else 1)
                    with ce2:
                        lista_pag = ["Pix", "Dinheiro", "Cartão"]
                        val_p = linha_atual.get('pagamento', 'Pix')
                        idx_p = lista_pag.index(val_p) if val_p in lista_pag else 0
                        novo_pag = st.selectbox("Pagamento", lista_pag, index=idx_p)
                else:
                    lista_cat = ["Roupas", "Salários Colaboradores", "Impostos", "Contador", "Aluguel", "Marketing", "Luz", "Água", "Internet", "Outras"]
                    cat_atual = linha_atual.get('tipo', 'Outras')
                    idx_c = lista_cat.index(cat_atual) if cat_atual in lista_cat else 0
                    novo_tipo_desp = st.selectbox("Tipo de Despesa", lista_cat, index=idx_c)

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1: btn_salvar = st.form_submit_button("💾 Salvar Alterações")
                with col_btn2: btn_excluir = st.form_submit_button("🗑️ Excluir Registro")

                if btn_salvar:
                    df_base.at[index_selecionado, 'data'] = nova_data
                    df_base.at[index_selecionado, 'hora'] = nova_hora
                    df_base.at[index_selecionado, 'valor'] = novo_valor
                    df_base.at[index_selecionado, 'descricao'] = nova_desc
                    if categoria == "Vendas":
                        df_base.at[index_selecionado, 'tipo'] = novo_canal
                        df_base.at[index_selecionado, 'pagamento'] = novo_pag
                    else:
                        df_base.at[index_selecionado, 'tipo'] = novo_tipo_desp
                    
                    col_limpas = [c for c in df_base.columns if c not in ['Data_DT', 'Dia', 'Mês', 'Ano', 'temp_data_dt']]
                    update_sheet(nome_aba, df_base[col_limpas])
                    st.rerun()

                if btn_excluir:
                    df_base = df_base.drop(index_selecionado)
                    col_limpas = [c for c in df_base.columns if c not in ['Data_DT', 'Dia', 'Mês', 'Ano', 'temp_data_dt']]
                    update_sheet(nome_aba, df_base[col_limpas])
                    st.rerun()
        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info(f"A base de {categoria} está vazia.")

# ---------------- PÁGINA: BALANÇO ----------------
elif menu == "📊 Balanço":
    st.title("📊 Balanço Financeiro")
    senha_balanco = st.text_input("Senha gerencial:", type="password", key="senha_bal_final")
    if senha_balanco == "jana@2018":
        st.success("Acesso Liberado!")
        
        # --- NOVO: Configuração das Metas pela Gerência ---
        st.subheader("🎯 Configuração de Metas")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            nova_meta_diaria = st.number_input("Meta Diária (R$)", min_value=0.0, value=float(st.session_state['meta_diaria']), step=50.0)
        with col_m2:
            nova_meta_mensal = st.number_input("Meta Mensal (R$)", min_value=0.0, value=float(st.session_state['meta_mensal']), step=500.0)
            
        if st.button("Salvar Metas"):
            st.session_state['meta_diaria'] = nova_meta_diaria
            st.session_state['meta_mensal'] = nova_meta_mensal
            st.success("Metas atualizadas e salvas para a sessão!")
        
        st.divider()
        # ---------------------------------------------------

        df_v = df_vendas.copy()
        df_c = df_compras.copy()
        if not df_v.empty: df_v['Movimento'] = '🟢 Venda'
        if not df_c.empty: df_c['Movimento'] = '🔴 Despesa'
        df_fluxo = pd.concat([df_v, df_c], ignore_index=True)
        if not df_fluxo.empty and 'data' in df_fluxo.columns:
            df_fluxo['Data_DT'] = pd.to_datetime(df_fluxo['data'], format='%d/%m/%Y', errors='coerce')
            df_fluxo = df_fluxo.dropna(subset=['Data_DT'])
            df_fluxo['Dia'] = df_fluxo['Data_DT'].dt.strftime('%d')
            df_fluxo['Mês'] = df_fluxo['Data_DT'].dt.strftime('%m')
            df_fluxo['Ano'] = df_fluxo['Data_DT'].dt.strftime('%Y')
            
            col1, col2, col3 = st.columns(3)
            with col1: filtro_mes = st.selectbox("Mês", sorted(df_fluxo['Mês'].unique()), index=0)
            with col2: filtro_ano = st.selectbox("Ano", sorted(df_fluxo['Ano'].unique(), reverse=True), index=0)
            
            dias_disp = sorted(df_fluxo[(df_fluxo['Mês'] == filtro_mes) & (df_fluxo['Ano'] == filtro_ano)]['Dia'].unique())
            opcoes_dia = ["Todos"] + list(dias_disp)
            with col3: filtro_dia = st.selectbox("Dia", opcoes_dia, index=0)
            
            mask = (df_fluxo['Mês'] == filtro_mes) & (df_fluxo['Ano'] == filtro_ano)
            if filtro_dia != "Todos":
                mask &= (df_fluxo['Dia'] == filtro_dia)
            
            df_filtrado = df_fluxo[mask].copy()
            
            tv = df_filtrado[df_filtrado['Movimento'] == '🟢 Venda']['valor'].sum()
            tc = df_filtrado[df_filtrado['Movimento'] == '🔴 Despesa']['valor'].sum()
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", f"R$ {tv:,.2f}")
            c2.metric("Saídas", f"R$ {tc:,.2f}")
            c3.metric("Saldo", f"R$ {tv-tc:,.2f}")
            st.dataframe(df_filtrado.drop(columns=['Data_DT', 'Dia', 'Mês', 'Ano', 'temp_data_dt'], errors='ignore'), use_container_width=True, hide_index=True,
                         column_config={"valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")})
