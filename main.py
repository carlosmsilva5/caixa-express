import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz  # Adicione esta linha

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

def update_sheet(sheet, df_completo):
    try:
        conn.update(worksheet=sheet, data=df_completo)
        st.cache_data.clear()
        st.success("Registro atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")

# ---------------- CARREGANDO AS BASES ----------------
df_vendas = load_data("vendas")
df_compras = load_data("compras")

# ---------------- LÓGICA DE DATAS E CÁLCULOS ----------------
# --- AJUSTE DE FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
hoje_dt = datetime.now(fuso_br) # Pega a hora exata de Brasília
data_hoje_str = hoje_dt.strftime("%d/%m/%Y")
mes_atual_str = hoje_dt.strftime("%m/%Y")

def processar_financeiro(df):
    """Garante que datas e valores estejam no formato correto para calculo"""
    if df.empty: return df, 0.0, 0.0
    
    # Garante que 'valor' seja número
    if 'valor' in df.columns:
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    
    # Garante que 'data' seja string limpa e faz as somas
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
    else:
        total_mes = 0.0
        total_hoje = 0.0
        
    return df, total_hoje, total_mes

# Processando os dados
df_vendas, v_hoje, v_mes = processar_financeiro(df_vendas)
df_compras, c_hoje, c_mes = processar_financeiro(df_compras)
saldo_mes = v_mes - c_mes

# ---------------- MENU LATERAL ----------------
# ---------------- MENU LATERAL ----------------
with st.sidebar:
    st.title("💸 Pegue Jeans")
    # Adicionamos a opção Balanço no menu
    menu = st.radio("Navegação", ["💰 Vendas", "🛒 Compras", "🛠️ Editar", "📊 Balanço"])
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
        col1, col2 = st.columns(2)
        with col1: tipo_venda = st.selectbox("Tipo", ["Presencial", "Online"])
        with col2: valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        descricao = st.text_input("Descrição (Opcional)")
        
        if st.form_submit_button("💰 Confirmar Venda"):
            if valor > 0:
                nova = pd.DataFrame([{"data": data_hoje_str, "hora": datetime.now(fuso_br).strftime("%H:%M:%S"), "tipo": tipo_venda, "descricao": descricao if descricao else "-", "valor": valor}])
                save_data("vendas", nova)
                st.rerun()

    st.divider()
    st.subheader(f"📉 Fechamento do Dia ({data_hoje_str})")
    st.markdown(f'<div class="card"><div class="title">Total Vendido Hoje</div><div class="value">R$ {v_hoje:,.2f}</div></div>', unsafe_allow_html=True)
    
    df_v_hoje = df_vendas[df_vendas['data'] == data_hoje_str]
    if not df_v_hoje.empty:
        st.dataframe(
            df_v_hoje[["data", "hora", "tipo", "descricao", "valor"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "data": "Data",
                "hora": "Hora",
                "tipo": "Tipo",
                "descricao": "Descrição",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma venda hoje.")

# ---------------- PÁGINA: COMPRAS ----------------
# ---------------- PÁGINA: COMPRAS ----------------
elif menu == "🛒 Compras":
    st.title("🛒 Gestão de Compras")
    
    # --- TRAVA DE ACESSO ---
    senha_compras = st.text_input("Digite a senha para acessar Compras:", type="password", key="acesso_compras")
    
    if senha_compras == "jana@2018":
        st.success("Acesso Liberado!")
        st.divider()
        
        # FORMULÁRIO DE REGISTRO
        st.subheader("Registrar Nova Despesa")
        with st.form("form_compra", clear_on_submit=True):
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            descricao = st.text_input("Descrição (Opcional)")
            
            if st.form_submit_button("🛒 Confirmar Despesa"):
                if valor > 0:
                    nova = pd.DataFrame([{"data": data_hoje_str, "hora": datetime.now(fuso_br).strftime("%H:%M:%S"), "descricao": descricao if descricao else "-", "valor": valor}])
                    save_data("compras", nova)
                    st.rerun()

        st.divider()
        
        # VISUALIZAÇÃO DO DIA
        st.subheader(f"📉 Despesas do Dia ({data_hoje_str})")
        st.markdown(f'<div class="card-red"><div class="title">Total Gasto Hoje</div><div class="value">R$ {c_hoje:,.2f}</div></div>', unsafe_allow_html=True)
        
        df_c_hoje = df_compras[df_compras['data'] == data_hoje_str]
        if not df_c_hoje.empty:
            st.dataframe(
                df_c_hoje[["data", "hora", "descricao", "valor"]], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "data": "Data",
                    "hora": "Hora",
                    "descricao": "Descrição",
                    "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
                }
            )
        else:
            st.info("Nenhuma despesa registrada hoje.")
            
    elif senha_compras != "":
        st.error("Senha incorreta. Acesso negado.")
    else:
        st.info("Aba protegida. Insira a senha de administrador para continuar.")

# ---------------- PÁGINA: EDITAR ----------------
elif menu == "🛠️ Editar":
    st.title("🛠️ Editar Registros")
    
    # 1. Seleção de Categoria
    categoria = st.selectbox("Selecione a categoria", ["Vendas", "Compras"])
    df_base = df_vendas if categoria == "Vendas" else df_compras
    nome_aba = "vendas" if categoria == "Vendas" else "compras"

    if not df_base.empty:
        # --- NOVO: FILTRO DE MÊS E ANO PARA EDIÇÃO ---
        st.subheader("🔍 Filtrar por Período")
        
        # Garante que a coluna data está em formato datetime para filtrar
        df_base['Data_DT'] = pd.to_datetime(df_base['data'], format='%d/%m/%Y', errors='coerce')
        df_base = df_base.dropna(subset=['Data_DT'])
        
        df_base['Mês'] = df_base['Data_DT'].dt.strftime('%m')
        df_base['Ano'] = df_base['Data_DT'].dt.strftime('%Y')
        
        col_m, col_a = st.columns(2)
        with col_m:
            mes_edit = st.selectbox("Mês do registro", sorted(df_base['Mês'].unique()), 
                                    index=sorted(df_base['Mês'].unique()).index(hoje_dt.strftime("%m")) if hoje_dt.strftime("%m") in df_base['Mês'].unique() else 0)
        with col_a:
            ano_edit = st.selectbox("Ano do registro", sorted(df_base['Ano'].unique(), reverse=True),
                                    index=0)

        # Filtra o DataFrame com base na escolha do usuário
        df_filtrado_edit = df_base[(df_base['Mês'] == mes_edit) & (df_base['Ano'] == ano_edit)].copy()

        if not df_filtrado_edit.empty:
            st.divider()
            st.write(f"Selecione o registro de **{categoria}** de {mes_edit}/{ano_edit}:")
            
            # 2. Seleção do Registro Específico (apenas os filtrados)
            opcoes = [f"ID {i} | {row['data']} {row['hora']} | R$ {row['valor']:.2f} | {row['descricao']}" 
                      for i, row in df_filtrado_edit.iterrows()]
            
            selecao = st.selectbox("Escolha o registro para alterar", opcoes)
            index_selecionado = int(selecao.split("ID ")[1].split(" |")[0])
            
            linha_atual = df_filtrado_edit.loc[index_selecionado]

            # 3. Formulário de Edição
            with st.form("form_edicao"):
                st.subheader(f"Editando Registro ID {index_selecionado}")
                
                c1, c2 = st.columns(2)
                with c1: nova_data = st.text_input("Data", value=linha_atual['data'])
                with c2: nova_hora = st.text_input("Hora", value=linha_atual['hora'])
                
                novo_valor = st.number_input("Valor (R$)", value=float(linha_atual['valor']), format="%.2f")
                nova_desc = st.text_input("Descrição", value=linha_atual['descricao'])
                
                if categoria == "Vendas":
                    novo_tipo = st.selectbox("Tipo", ["Presencial", "Online"], 
                                             index=0 if linha_atual['tipo'] == "Presencial" else 1)

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_salvar = st.form_submit_button("💾 Salvar Alterações")
                with col_btn2:
                    btn_excluir = st.form_submit_button("🗑️ Excluir Registro")

                if btn_salvar:
                    # Aplicamos a mudança no DataFrame ORIGINAL (df_base) usando o índice real
                    df_base.at[index_selecionado, 'data'] = nova_data
                    df_base.at[index_selecionado, 'hora'] = nova_hora
                    df_base.at[index_selecionado, 'valor'] = novo_valor
                    df_base.at[index_selecionado, 'descricao'] = nova_desc
                    if categoria == "Vendas":
                        df_base.at[index_selecionado, 'tipo'] = novo_tipo
                    
                    # Limpa colunas temporárias antes de salvar no Google Sheets
                    colunas_limpas = [c for c in df_base.columns if c not in ['Data_DT', 'Mês', 'Ano', 'temp_data_dt']]
                    update_sheet(nome_aba, df_base[colunas_limpas])
                    st.rerun()

                if btn_excluir:
                    df_base = df_base.drop(index_selecionado)
                    colunas_limpas = [c for c in df_base.columns if c not in ['Data_DT', 'Mês', 'Ano', 'temp_data_dt']]
                    update_sheet(nome_aba, df_base[colunas_limpas])
                    st.rerun()
        else:
            st.warning(f"Nenhum registro de {categoria} encontrado em {mes_edit}/{ano_edit}.")
            
        st.divider()
        st.write("Visualização da tabela filtrada:")
        st.dataframe(
            df_filtrado_edit[[c for c in df_filtrado_edit.columns if c not in ['Data_DT', 'Mês', 'Ano', 'temp_data_dt']]], 
            use_container_width=True,
            column_config={"valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")}
        )
    else:
        st.info(f"A base de {categoria} está totalmente vazia.")

    # --- ZONA DE PERIGO (APAGAR TUDO) ---
    st.divider()
    with st.expander("🚨 Zona de Perigo: Apagar Todos os Registros"):
        st.error(f"CUIDADO: Isso apagará TODOS os registros de {categoria} da história, não apenas do mês filtrado!")
        senha_limpeza = st.text_input(f"Senha para APAGAR TUDO de {categoria}:", type="password", key="senha_limpeza_total")
        
        if st.button(f"💥 Confirmar Exclusão TOTAL de {categoria}"):
            if senha_limpeza == "jana@2018":
                colunas_vazio = [c for c in df_base.columns if c not in ['Data_DT', 'Mês', 'Ano', 'temp_data_dt']]
                df_vazio = pd.DataFrame(columns=colunas_vazio)
                update_sheet(nome_aba, df_vazio)
                st.success("Limpeza concluída!")
                st.rerun()
            elif senha_limpeza != "":
                st.error("Senha incorreta!")

# ---------------- PÁGINA: BALANÇO MENSAL ----------------
elif menu == "📊 Balanço":
    st.title("📊 Balanço Financeiro Geral")
    
    senha_digitada = st.text_input("Senha de acesso gerencial:", type="password")
    
    if senha_digitada == "jana@2018":
        st.success("Acesso Liberado!")
        st.divider()
        
        # Cria cópias para não alterar os dados originais
        df_v = df_vendas.copy()
        df_c = df_compras.copy()
        
        # Cria uma coluna para identificar o que é venda e o que é despesa
        if not df_v.empty: df_v['Movimento'] = '🟢 Venda'
        if not df_c.empty: df_c['Movimento'] = '🔴 Despesa'
        
        # Junta as duas tabelas
        df_fluxo = pd.concat([df_v, df_c], ignore_index=True)
        
        if not df_fluxo.empty and 'data' in df_fluxo.columns:
            # Transforma a data em formato de tempo do pandas para extrair mês e ano
            df_fluxo['Data_DT'] = pd.to_datetime(df_fluxo['data'], format='%d/%m/%Y', errors='coerce')
            df_fluxo = df_fluxo.dropna(subset=['Data_DT']) # Remove erros
            
            # Cria colunas separadas de Mês e Ano para os filtros
            df_fluxo['Mês'] = df_fluxo['Data_DT'].dt.strftime('%m')
            df_fluxo['Ano'] = df_fluxo['Data_DT'].dt.strftime('%Y')
            
            st.subheader("Filtros")
            col1, col2 = st.columns(2)
            
            # Pega todos os meses e anos que existem registrados no sistema
            meses_disponiveis = sorted(df_fluxo['Mês'].unique())
            anos_disponiveis = sorted(df_fluxo['Ano'].unique(), reverse=True)
            
            # Tenta definir o mês e ano atuais como padrão
            mes_padrao = hoje_dt.strftime("%m")
            ano_padrao = hoje_dt.strftime("%Y")
            
            idx_mes = meses_disponiveis.index(mes_padrao) if mes_padrao in meses_disponiveis else 0
            idx_ano = anos_disponiveis.index(ano_padrao) if ano_padrao in anos_disponiveis else 0
            
            with col1:
                filtro_mes = st.selectbox("Selecione o Mês", meses_disponiveis, index=idx_mes)
            with col2:
                filtro_ano = st.selectbox("Selecione o Ano", anos_disponiveis, index=idx_ano)
                
            # Filtra a tabela final com base no que você selecionou nas caixas
            df_filtrado = df_fluxo[(df_fluxo['Mês'] == filtro_mes) & (df_fluxo['Ano'] == filtro_ano)].copy()
            
            # Calcula os totais do período selecionado
            tot_vendas = df_filtrado[df_filtrado['Movimento'] == '🟢 Venda']['valor'].sum()
            tot_compras = df_filtrado[df_filtrado['Movimento'] == '🔴 Despesa']['valor'].sum()
            saldo = tot_vendas - tot_compras
            
            # Exibe os cards financeiros
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("🟢 Total de Entradas", f"R$ {tot_vendas:,.2f}")
            c2.metric("🔴 Total de Saídas", f"R$ {tot_compras:,.2f}")
            c3.metric("💰 Saldo do Período", f"R$ {saldo:,.2f}")
            
            # Exibe a planilha
            st.divider()
            st.subheader(f"Registros de {filtro_mes}/{filtro_ano}")
            
            # Seleciona só as colunas que importam para mostrar na tela
            colunas_mostrar = ['data', 'hora', 'Movimento', 'tipo', 'descricao', 'valor']
            # Garante que não vai dar erro se faltar alguma coluna ("tipo" não existe nas compras)
            colunas_mostrar = [c for c in colunas_mostrar if c in df_filtrado.columns]
            
            # Mostra a tabela organizada por data e hora (mais recentes primeiro)
            st.dataframe(
                df_filtrado[colunas_mostrar].sort_values(by=['data', 'hora'], ascending=[False, False]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "data": "Data",
                    "hora": "Hora",
                    "tipo": "Tipo",
                    "descricao": "Descrição",
                    "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
                }
            )
        else:
            st.info("Nenhum registro encontrado no sistema ainda.")
            
    elif senha_digitada != "":
        st.error("Senha incorreta.")
