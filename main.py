import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import calendar
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIGURAÇÃO INICIAL ----------------
st.set_page_config(layout="wide", page_title="Caixa Express", page_icon="💸")

if 'meta_diaria' not in st.session_state:
    st.session_state['meta_diaria'] = 0.0
if 'meta_mensal' not in st.session_state:
    st.session_state['meta_mensal'] = 0.0

# ---------------- CONEXÃO COM O GOOGLE SHEETS (GSPREAD) ----------------
SPREADSHEET_ID = "1G1m7VmhX6-XkQLSMN3K6VumOdyiVovDsHjGHvG6aJqU"
SENHA_ADMIN = st.secrets["senha_admin"]

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = {
        "type": st.secrets["type"],
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": st.secrets["auth_uri"],
        "token_uri": st.secrets["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
        "universe_domain": st.secrets["universe_domain"]
    }
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

@st.cache_data(ttl=2)
def load_data(sheet_name):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(sheet_name)
        data = sheet.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=["data", "hora", "tipo", "pagamento", "descricao", "valor"])
            
        df = pd.DataFrame(data)
        df.columns = [str(c).strip().lower() for c in df.columns] 
        df = df.loc[:, ~df.columns.duplicated()].copy()
        return df
    except Exception as e:
        st.error(f"Erro detalhado ao carregar {sheet_name}: {e}")
        return pd.DataFrame()

def save_data(sheet_name, df_new):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(sheet_name)
        df_new = df_new.fillna("-")
        for _, row in df_new.iterrows():
            linha_valores = [str(val) if val is not None else "" for val in row.values]
            sheet.append_row(linha_valores)
        st.cache_data.clear()
        st.success("Salvo com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def update_sheet(sheet_name, df_completo):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(sheet_name)
        df_completo = df_completo.fillna("-")
        sheet.clear()
        cabecalho = df_completo.columns.tolist()
        linhas = df_completo.astype(str).values.tolist()
        sheet.update([cabecalho] + linhas)
        st.cache_data.clear()
        st.success("Registro atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")

# ---------------- CARREGANDO AS BASES ----------------
df_vendas = load_data("vendas")
df_compras = load_data("compras")

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
    menu = st.radio("Navegação", ["💰 Vendas", "💸 Despesas", "🛠️ Editar", "📊 Balanço"])
    st.divider()
    st.info("Selecione 'Balanço' para ver o relatório completo e filtrar por mês/ano.")
    st.markdown("### 📊 Balanço do Mês")
    senha_digitada = st.text_input("Senha de acesso:", type="password")
    if senha_digitada == SENHA_ADMIN: 
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
            venda_data = st.date_input("Data da Venda", hoje_dt, format="DD/MM/YYYY")
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
                    "data": venda_data.strftime("%d/%m/%Y"),
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
    
    # ---------------- SUBSTITUA DAQUI PARA BAIXO ----------------
    # Verifica de forma segura se o DataFrame tem dados e a coluna 'data'
    if not df_vendas.empty and 'data' in df_vendas.columns:
        df_v_hoje = df_vendas[df_vendas['data'] == data_hoje_str]
    else:
        df_v_hoje = pd.DataFrame() # Cria um dataframe vazio de segurança

    # Exibe a tabela de vendas de hoje ou o aviso de vazio
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
    # ---------------- ATÉ AQUI ----------------

# ---------------- PÁGINA: DESPESAS ----------------
elif menu == "💸 Despesas":
    st.title("💸 Gestão de Despesas")
    senha_compras = st.text_input("Digite a senha para acessar Despesas:", type="password", key="acesso_compras")
    if senha_compras == SENHA_ADMIN:
        st.success("Acesso Liberado!")
        st.divider()
        st.subheader("Registrar Nova Despesa")
        with st.form("form_compra", clear_on_submit=True):
            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            with col_c1:
                despesa_data = st.date_input("Data da Despesa", hoje_dt, format="DD/MM/YYYY")
            with col_c2:
                valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            with col_c3:
                tipo_despesa = st.selectbox("Tipo de Despesa", ["Roupas", "Salários Colaboradores", "Impostos", "Contador", "Aluguel", "Marketing", "Luz", "Água", "Internet", "Outras"])
            with col_c4:
                recorrente = st.selectbox("Recorrente?", ["Não", "Sim"], index=0, help="Ao marcar 'Sim', o valor será repetido mensalmente até o fim do ano.")
            
            descricao = st.text_input("Descrição (Opcional)")
            
            if st.form_submit_button("💸 Confirmar Despesa"):
                if valor > 0:
                    if recorrente == "Sim":
                        dados_recorrentes = []
                        mes_inicial = despesa_data.month
                        ano_atual = despesa_data.year
                        for m in range(mes_inicial, 13):
                            # Ajuste para não quebrar em meses com menos dias (ex: 31 de Jan para Fev)
                            ultimo_dia_mes = calendar.monthrange(ano_atual, m)[1]
                            dia_ajustado = min(despesa_data.day, ultimo_dia_mes)
                            data_gera = datetime(ano_atual, m, dia_ajustado)
                            
                            dados_recorrentes.append({
                                "data": data_gera.strftime("%d/%m/%Y"),
                                "hora": datetime.now(fuso_br).strftime("%H:%M:%S"), 
                                "tipo": tipo_despesa, 
                                "descricao": descricao if descricao else "-", 
                                "valor": valor
                            })
                        nova = pd.DataFrame(dados_recorrentes)
                    else:
                        nova = pd.DataFrame([{
                            "data": despesa_data.strftime("%d/%m/%Y"),
                            "hora": datetime.now(fuso_br).strftime("%H:%M:%S"), 
                            "tipo": tipo_despesa, 
                            "descricao": descricao if descricao else "-", 
                            "valor": valor
                        }])
                    
                    save_data("compras", nova)
                    st.rerun()
        st.divider()
        
        # --- ATUALIZADO: Mostrar Despesas do Mês ---
        st.subheader(f"📉 Despesas do Mês ({mes_atual_str})")
        st.markdown(f'<div class="card-red"><div class="title">Total Gasto no Mês</div><div class="value">R$ {c_mes:,.2f}</div></div>', unsafe_allow_html=True)
        
        # Filtro para mostrar todas as despesas do mês atual
        if not df_compras.empty and 'temp_data_dt' in df_compras.columns:
            df_c_mes = df_compras[df_compras['temp_data_dt'].dt.strftime('%m/%Y') == mes_atual_str].sort_values(by='temp_data_dt', ascending=False)
            
            if not df_c_mes.empty:
                st.dataframe(
                    df_c_mes[["data", "hora", "tipo", "descricao", "valor"]] if "tipo" in df_c_mes.columns else df_c_mes[["data", "hora", "descricao", "valor"]], 
                    use_container_width=True, hide_index=True,
                    column_config={"data": "Data", "hora": "Hora", "tipo": "Tipo", "descricao": "Descrição", "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")}
                )
            else:
                st.info("Nenhuma despesa registrada neste mês.")
        else:
            st.info("Inicie os registros para visualizar a tabela.")

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
        
        # Variáveis do dia atual
        hoje_ano = hoje_dt.strftime('%Y')
        hoje_mes = hoje_dt.strftime('%m')
        hoje_dia = hoje_dt.strftime('%d')
        
        col_d, col_m, col_a = st.columns(3)
        with col_a:
            lista_anos = sorted(df_base['Ano'].unique(), reverse=True)
            idx_ano = lista_anos.index(hoje_ano) if hoje_ano in lista_anos else 0
            ano_edit = st.selectbox("Ano", lista_anos, index=idx_ano)
        with col_m:
            meses_disp = sorted(df_base[df_base['Ano'] == ano_edit]['Mês'].unique())
            idx_mes = meses_disp.index(hoje_mes) if hoje_mes in meses_disp else 0
            mes_edit = st.selectbox("Mês", meses_disp, index=idx_mes)
        with col_d:
            dias_disp = sorted(df_base[(df_base['Ano'] == ano_edit) & (df_base['Mês'] == mes_edit)]['Dia'].unique())
            idx_dia = dias_disp.index(hoje_dia) if hoje_dia in dias_disp else 0
            dia_edit = st.selectbox("Dia", dias_disp, index=idx_dia)

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
                    # --- VENDAS (Sem opção de recorrência) ---
                    ce1, ce2 = st.columns(2)
                    with ce1: novo_canal = st.selectbox("Canal", ["Presencial", "Online"], index=0 if linha_atual.get('tipo') == "Presencial" else 1)
                    with ce2:
                        lista_pag = ["Pix", "Dinheiro", "Cartão"]
                        val_p = linha_atual.get('pagamento', 'Pix')
                        idx_p = lista_pag.index(val_p) if val_p in lista_pag else 0
                        novo_pag = st.selectbox("Pagamento", lista_pag, index=idx_p)
                else:
                    # --- DESPESAS (Com opção de recorrência) ---
                    ce1, ce2 = st.columns(2)
                    with ce1:
                        lista_cat = ["Roupas", "Salários Colaboradores", "Impostos", "Contador", "Aluguel", "Marketing", "Luz", "Água", "Internet", "Outras"]
                        cat_atual = linha_atual.get('tipo', 'Outras')
                        idx_c = lista_cat.index(cat_atual) if cat_atual in lista_cat else 0
                        novo_tipo_desp = st.selectbox("Tipo de Despesa", lista_cat, index=idx_c)
                    with ce2:
                        novo_recorrente = st.selectbox("Tornar Recorrente?", ["Não", "Sim"], index=0, help="Criará cópias desta despesa para os meses seguintes do ano.")

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
                        
                        # A lógica de criar os próximos meses SÓ RODA se for Despesa
                        if novo_recorrente == "Sim":
                            try:
                                dt_base = datetime.strptime(nova_data, "%d/%m/%Y")
                                mes_inicial = dt_base.month + 1 
                                ano_atual = dt_base.year
                                
                                novos_registros = []
                                for m in range(mes_inicial, 13):
                                    ultimo_dia_mes = calendar.monthrange(ano_atual, m)[1]
                                    dia_ajustado = min(dt_base.day, ultimo_dia_mes)
                                    data_gera = datetime(ano_atual, m, dia_ajustado)
                                    
                                    novos_registros.append({
                                        "data": data_gera.strftime("%d/%m/%Y"),
                                        "hora": nova_hora, 
                                        "tipo": novo_tipo_desp, 
                                        "descricao": nova_desc, 
                                        "valor": novo_valor
                                    })
                                
                                if novos_registros:
                                    df_novos = pd.DataFrame(novos_registros)
                                    df_base = pd.concat([df_base, df_novos], ignore_index=True)
                            except ValueError:
                                st.error("Formato de data inválido. Use DD/MM/AAAA para habilitar a recorrência.")
                                st.stop()
                    
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
    if senha_balanco == SENHA_ADMIN:
        st.success("Acesso Liberado!")
        
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
            
            # Variáveis do dia atual
            hoje_ano = hoje_dt.strftime('%Y')
            hoje_mes = hoje_dt.strftime('%m')
            hoje_dia = hoje_dt.strftime('%d')

            col1, col2, col3 = st.columns(3)
            with col1: 
                lista_meses = sorted(df_fluxo['Mês'].unique())
                idx_mes = lista_meses.index(hoje_mes) if hoje_mes in lista_meses else 0
                filtro_mes = st.selectbox("Mês", lista_meses, index=idx_mes)
            with col2: 
                lista_anos = sorted(df_fluxo['Ano'].unique(), reverse=True)
                idx_ano = lista_anos.index(hoje_ano) if hoje_ano in lista_anos else 0
                filtro_ano = st.selectbox("Ano", lista_anos, index=idx_ano)
            
            dias_disp = sorted(df_fluxo[(df_fluxo['Mês'] == filtro_mes) & (df_fluxo['Ano'] == filtro_ano)]['Dia'].unique())
            opcoes_dia = ["Todos"] + list(dias_disp)
            
            with col3: 
                # index=0 força o padrão a ser o primeiro item da lista ("Todos")
                filtro_dia = st.selectbox("Dia", opcoes_dia, index=0, key="bal_dia")          
                     
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
