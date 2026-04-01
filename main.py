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
hoje_dt = datetime.now()
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
                nova = pd.DataFrame([{"data": data_hoje_str, "hora": datetime.now().strftime("%H:%M:%S"), "tipo": tipo_venda, "descricao": descricao if descricao else "-", "valor": valor}])
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
    
    # --- BLOCO FINAL QUE ESTAVA FALTANDO ---
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

# ---------------- PÁGINA: EDITAR ----------------
elif menu == "🛠️ Editar":
    st.title("🛠️ Editar ou Excluir Registros")
    
    categoria = st.selectbox("Selecione a categoria", ["Vendas", "Compras"])
    df_selecionado = df_vendas if categoria == "Vendas" else df_compras
    nome_aba = "vendas" if categoria == "Vendas" else "compras"

    if not df_selecionado.empty:
        st.write(f"Selecione o registro de {categoria} que deseja alterar:")
        
        # Criamos uma lista de opções para o selectbox mostrando Data, Hora e Valor
        opcoes = [f"ID {i} | {row['data']} {row['hora']} | R$ {row['valor']:.2f}" 
                  for i, row in df_selecionado.iterrows()]
        
        selecao = st.selectbox("Registro", opcoes)
        index_selecionado = int(selecao.split("ID ")[1].split(" |")[0])
        
        # Carrega os dados atuais da linha selecionada
        linha_atual = df_selecionado.loc[index_selecionado]

        with st.form("form_edicao"):
            st.subheader(f"Editando Registro ID {index_selecionado}")
            
            nova_data = st.text_input("Data", value=linha_atual['data'])
            nova_hora = st.text_input("Hora", value=linha_atual['hora'])
            novo_valor = st.number_input("Valor (R$)", value=float(linha_atual['valor']), format="%.2f")
            nova_desc = st.text_input("Descrição", value=linha_atual['descricao'])
            
            if categoria == "Vendas":
                novo_tipo = st.selectbox("Tipo", ["Presencial", "Online"], 
                                         index=0 if linha_atual['tipo'] == "Presencial" else 1)

            col1, col2 = st.columns(2)
            with col1:
                btn_salvar = st.form_submit_button("💾 Salvar Alterações")
            with col2:
                btn_excluir = st.form_submit_button("🗑️ Excluir Registro")

            if btn_salvar:
                # Atualiza o DataFrame local
                df_selecionado.at[index_selecionado, 'data'] = nova_data
                df_selecionado.at[index_selecionado, 'hora'] = nova_hora
                df_selecionado.at[index_selecionado, 'valor'] = novo_valor
                df_selecionado.at[index_selecionado, 'descricao'] = nova_desc
                if categoria == "Vendas":
                    df_selecionado.at[index_selecionado, 'tipo'] = novo_tipo
                
                # Remove colunas temporárias de cálculo antes de salvar
                if 'temp_data_dt' in df_selecionado.columns:
                    df_selecionado = df_selecionado.drop(columns=['temp_data_dt'])
                
                update_sheet(nome_aba, df_selecionado)
                st.rerun()

            if btn_excluir:
                df_selecionado = df_selecionado.drop(index_selecionado)
                if 'temp_data_dt' in df_selecionado.columns:
                    df_selecionado = df_selecionado.drop(columns=['temp_data_dt'])
                
                update_sheet(nome_aba, df_selecionado)
                st.rerun()
                
        st.divider()
        st.write("Tabela Completa para conferência:")
        st.dataframe(
            df_selecionado, 
            use_container_width=True,
            column_config={
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
            }
        )
    else:
        st.info(f"Não há registros em {categoria} para editar.")

    # --- NOVO BLOCO: APAGAR TUDO (Posicionado corretamente) ---
    st.divider()
    with st.expander("🚨 Zona de Perigo: Apagar Todos os Registros"):
        st.warning(f"Atenção! Esta ação é irreversível e apagará todos os dados de {categoria} na planilha do Google Sheets.")
        
        senha_limpeza = st.text_input(f"Digite a senha de administrador para APAGAR TUDO de {categoria}:", 
                                      type="password", 
                                      key="senha_limpeza_total")
        
        if st.button(f"💥 Confirmar Exclusão de Todas as {categoria}"):
            if senha_limpeza == "jana@2018":
                # Pega apenas as colunas originais (ignora as de cálculo)
                colunas_originais = [c for c in df_selecionado.columns if c != 'temp_data_dt']
                df_vazio = pd.DataFrame(columns=colunas_originais)
                
                # Envia o arquivo vazio para limpar a aba no Sheets
                update_sheet(nome_aba, df_vazio)
                
                st.success(f"Todos os registros de {categoria} foram apagados com sucesso!")
                st.rerun()
            elif senha_limpeza == "":
                st.info("Insira a senha para habilitar a exclusão.")
            else:
                st.error("Senha incorreta! Operação cancelada.")

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
