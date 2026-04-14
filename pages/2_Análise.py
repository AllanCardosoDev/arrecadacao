import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import unicodedata
import re

# --- Configurações da Página ---
st.set_page_config(
    page_title="Dashboard de Arrecadação - Análise Detalhada",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constantes e Paleta de Cores (Manter consistência) ---
COLOR_PRIMARY = '#1F77B4' # Azul escuro
COLOR_SECONDARY = '#AEC7E8' # Azul claro
COLOR_TEXT = '#333333'
COLOR_BACKGROUND = '#FFFFFF'
COLOR_CARD_BG = '#F0F2F6' # Um cinza claro para os cartões
COLOR_ACCENT = '#FF7F0E' # Laranja para destaque, se necessário

# Mapeamento de meses para ordenação
MESES_ORDEM = {
    'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
}

# --- Função de Carregamento de Dados ---
@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)
        # Normalizar nomes das colunas: remover acentos, espaços, converter para minúsculas
        df.columns = [unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8').lower().replace(' ', '_') for col in df.columns]

        # Renomear colunas para padronização
        df = df.rename(columns={'mes': 'mes_str', 'valor': 'arrecadacao'})

        # Validar colunas essenciais
        if 'mes_str' not in df.columns:
            st.error("Coluna 'mes' não encontrada no arquivo de dados. Verifique se a coluna de mês existe e está nomeada corretamente.")
            return pd.DataFrame()
        if 'ano' not in df.columns:
            st.error("Coluna 'ano' não encontrada no arquivo de dados. Verifique se a coluna de ano existe e está nomeada corretamente.")
            return pd.DataFrame()
        if 'arrecadacao' not in df.columns:
            st.error("Coluna 'valor' (arrecadacao) não encontrada no arquivo de dados. Verifique se a coluna de valor existe e está nomeada corretamente.")
            return pd.DataFrame()

        # Normalizar valores da coluna de mês (remover acentos e padronizar)
        df['mes_str'] = df['mes_str'].astype(str)
        df['mes_norm'] = df['mes_str'].apply(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('ASCII').upper())

        # Extrair código textual do mês (ex.: 'AGO' de 'AGO-2016')
        def _extract_month_code(s: str) -> str:
            m = re.search(r'([A-Z]+)', s)
            return m.group(1) if m else s

        df['mes_code'] = df['mes_norm'].apply(_extract_month_code)

        # Mapear para número do mês usando MESES_ORDEM
        df['mes_num'] = df['mes_code'].map(MESES_ORDEM)

        # Se houver linhas sem mes_num, tentar extrair mês/ano do texto (ex.: '08-2016' ou 'AGO-2016')
        mask_missing = df['mes_num'].isna()
        if mask_missing.any():
            def _parse_from_norm(s: str):
                # Tenta parsear formatos como 'MM-AAAA', 'MMM-AAAA', 'AAAA-MM', 'AAAA-MMM'
                parts = re.split(r'[-/\\\$|', s)
                if len(parts) == 2:
                    p1 = parts[0].strip()
                    p2 = parts[1].strip()

                    # Caso MM-AAAA ou MMM-AAAA
                    if p1.isdigit() and len(p1) <= 2: # MM-AAAA
                        return int(p1), p2
                    elif not p1.isdigit() and len(p1) <= 3: # MMM-AAAA
                        code = _extract_month_code(p1)
                        return MESES_ORDEM.get(code), p2
                    # Caso AAAA-MM ou AAAA-MMM
                    elif p2.isdigit() and len(p2) <= 2: # AAAA-MM
                        return int(p2), p1
                    elif not p2.isdigit() and len(p2) <= 3: # AAAA-MMM
                        code = _extract_month_code(p2)
                        return MESES_ORDEM.get(code), p1
                return None, None

            parsed_results = df.loc[mask_missing, 'mes_norm'].apply(_parse_from_norm)

            # Atualiza mes_num
            df.loc[mask_missing, 'mes_num'] = parsed_results.apply(lambda t: t[0])

            # Tenta preencher ano se estiver embutido em mes_norm e a coluna 'ano' estiver vazia
            for idx, (month_val, year_val) in parsed_results.items():
                if pd.isna(df.loc[idx, 'ano']) and year_val is not None:
                    try:
                        df.loc[idx, 'ano'] = int(year_val)
                    except ValueError:
                        pass # Não conseguiu converter para int, mantém como está

        # Converter ano e arrecadacao para tipos numéricos
        df['ano'] = pd.to_numeric(df['ano'], errors='coerce').astype('Int64')
        df['arrecadacao'] = pd.to_numeric(df['arrecadacao'], errors='coerce').fillna(0.0)

        # Remover linhas onde 'ano' ou 'mes_num' são nulos após todas as tentativas de parsing
        df.dropna(subset=['ano', 'mes_num'], inplace=True)

        # Criar coluna de data a partir de ano e mes_num (primeiro dia do mês)
        df['mes_num'] = pd.to_numeric(df['mes_num'], errors='coerce').astype('Int64')
        df['data'] = pd.to_datetime(df['ano'].astype(str) + '-' + df['mes_num'].astype(str).str.zfill(2) + '-01', errors='coerce')

        # Remover linhas com datas inválidas
        df.dropna(subset=['data'], inplace=True)

        # Ordenar
        df = df.sort_values(by=['ano', 'mes_num']).reset_index(drop=True)
        return df
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{file_path}' não foi encontrado. Certifique-se de que ele está na pasta 'data' e que o nome do arquivo está correto.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}. Verifique o formato do arquivo e as colunas 'mes', 'ano' e 'valor'.")
        return pd.DataFrame()

# Função para localizar arquivo de dados (suporta acentos e variações no nome)
def find_data_file(data_dir: str = 'data') -> str | None:
    if not os.path.isdir(data_dir):
        st.warning(f"A pasta '{data_dir}' não foi encontrada. Certifique-se de que a pasta 'data' existe no mesmo diretório do script.")
        return None

    # Lista de nomes de arquivo potenciais (normalizados)
    potential_names_norm = [
        'ARRECADAO.XLSX', 'ARRECADACAO.XLSX', 'ARRECADAO.XLS', 'ARRECADACAO.XLS',
        'ARRECADAO.XLSM', 'ARRECADACAO.XLSM', 'ARRECADAO.XLSB', 'ARRECADACAO.XLSB'
    ]

    for f in os.listdir(data_dir):
        # Normaliza o nome do arquivo encontrado para comparação
        f_norm = unicodedata.normalize('NFKD', f).encode('ASCII', 'ignore').decode('ASCII').upper()

        # Verifica se o nome normalizado do arquivo corresponde a algum dos potenciais
        if f_norm in potential_names_norm:
            return os.path.join(data_dir, f) # Retorna o caminho com o nome original do arquivo

    st.warning(f"Nenhum arquivo de arrecadação (ex: ARRECADAO.xlsx) foi encontrado na pasta '{data_dir}'.")
    return None

# Caminho do arquivo de dados
DATA_DIR = 'data'
found_file_path = find_data_file(DATA_DIR)

if found_file_path:
    df = load_data(found_file_path)
else:
    df = pd.DataFrame() # Cria um DataFrame vazio se o arquivo não for encontrado

if not df.empty:
    # --- Título da Página ---
    st.title("🔍 Análise Detalhada da Arrecadação")
    st.markdown("Explore a arrecadação com filtros de ano e mês.")

    # --- Sidebar para Filtros ---
    st.sidebar.header("Filtros de Análise")

    # Filtro de Ano
    all_years = sorted(df['ano'].unique(), reverse=True)
    selected_years = st.sidebar.multiselect(
        "Selecione o(s) Ano(s)",
        options=all_years,
        default=all_years # Seleciona todos por padrão
    )

    # Filtro de Mês
    # Garante que a ordem dos meses no filtro seja a correta
    available_months_in_data = df['mes_str'].unique()
    sorted_available_months = sorted(available_months_in_data, key=lambda x: MESES_ORDEM.get(unicodedata.normalize('NFKD', x).encode('ASCII', 'ignore').decode('ASCII').upper(), 99))

    selected_months_str = st.sidebar.multiselect(
        "Selecione o(s) Mês(es)",
        options=sorted_available_months,
        default=sorted_available_months # Seleciona todos por padrão
    )

    # Aplicar filtros
    df_filtered = df[df['ano'].isin(selected_years) & df['mes_str'].isin(selected_months_str)]

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados. Ajuste os filtros.")
    else:
        # --- Layout com Colunas para KPIs ---
        st.markdown("---")
        st.subheader("Indicadores Chave de Performance (KPIs)")
        col1, col2, col3 = st.columns(3)

        # KPI 1: Arrecadação Total
        total_arrecadacao = df_filtered['arrecadacao'].sum()
        col1.metric(
            label="Arrecadação Total",
            value=f"R$ {total_arrecadacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        # KPI 2: Média Mensal
        # Calcula a média com base no número de meses únicos no filtro
        num_meses_unicos = df_filtered[['ano', 'mes_num']].drop_duplicates().shape[0]
        media_mensal = total_arrecadacao / num_meses_unicos if num_meses_unicos > 0 else 0
        col2.metric(
            label="Média Mensal",
            value=f"R$ {media_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        # KPI 3: Arrecadação do Último Mês (se houver)
        if not df_filtered.empty:
            # Garante que o último mês seja o mais recente em termos de data
            latest_data_row = df_filtered.sort_values(by='data', ascending=False).iloc[0]
            ultimo_mes_arrecadacao = latest_data_row['arrecadacao']
            ultimo_mes_label = f"{latest_data_row['mes_str']}/{latest_data_row['ano']}"
            col3.metric(
                label=f"Arrecadação Último Mês ({ultimo_mes_label})",
                value=f"R$ {ultimo_mes_arrecadacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        else:
            col3.metric(label="Arrecadação Último Mês", value="N/A")

        st.markdown("---")

        # --- Gráfico de Barras: Arrecadação por Mês (Comparativo Anual) ---
        st.subheader("Arrecadação por Mês (Comparativo Anual)")

        # Agrupar por mês e ano para o gráfico de barras empilhadas ou agrupadas
        df_plot_monthly_comparison = df_filtered.groupby(['mes_num', 'mes_str', 'ano'])['arrecadacao'].sum().reset_index()
        df_plot_monthly_comparison = df_plot_monthly_comparison.sort_values(by='mes_num')

        fig_monthly_comparison = px.bar(
            df_plot_monthly_comparison,
            x='mes_str',
            y='arrecadacao',
            color='ano', # Diferenciar as barras por ano
            barmode='group', # Barras agrupadas para comparação
            title='Comparativo de Arrecadação Mensal por Ano',
            labels={'mes_str': 'Mês', 'arrecadacao': 'Arrecadação (R$)', 'ano': 'Ano'},
            color_discrete_sequence=px.colors.qualitative.Pastel # Uma paleta de cores diferente para os anos
        )
        fig_monthly_comparison.update_layout(
            xaxis_title='Mês',
            yaxis_title='Arrecadação (R$)',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font_color=COLOR_TEXT,
            title_font_color=COLOR_TEXT,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#E0E0E0')
        )
        fig_monthly_comparison.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig_monthly_comparison, use_container_width=True)

        st.markdown("---")

        # --- Gráfico de Linha: Tendência Anual da Arrecadação Média Mensal ---
        st.subheader("Tendência Anual da Arrecadação Média Mensal")
        df_plot_avg_annual = df_filtered.groupby('ano')['arrecadacao'].mean().reset_index()
        fig_avg_annual = px.line(
            df_plot_avg_annual,
            x='ano',
            y='arrecadacao',
            title='Média Mensal de Arrecadação por Ano',
            labels={'ano': 'Ano', 'arrecadacao': 'Média Mensal (R$)'},
            color_discrete_sequence=[COLOR_PRIMARY]
        )
        fig_avg_annual.update_traces(mode='lines+markers')
        fig_avg_annual.update_layout(
            hovermode="x unified",
            xaxis_title='Ano',
            yaxis_title='Média Mensal (R$)',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font_color=COLOR_TEXT,
            title_font_color=COLOR_TEXT,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#E0E0E0')
        )
        fig_avg_annual.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig_avg_annual, use_container_width=True)

        st.markdown("---")

        # --- Tabela de Dados (Opcional, para detalhe) ---
        st.subheader("Dados Detalhados (Amostra)")
        st.dataframe(df_filtered.head(10), use_container_width=True)

else:
    st.error("Não foi possível carregar os dados para a página de Análise Detalhada. Verifique a pasta 'data' e o arquivo de arrecadação.")
