import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import unicodedata

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
        df.columns = [unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8').lower() for col in df.columns]
        df = df.rename(columns={'mes': 'mes_str', 'valor': 'arrecadacao'})

        # Validar colunas essenciais
        if 'mes_str' not in df.columns:
            st.error("Coluna 'mes' não encontrada no arquivo de dados.")
            return pd.DataFrame()
        if 'ano' not in df.columns:
            st.error("Coluna 'ano' não encontrada no arquivo de dados.")
            return pd.DataFrame()

        # Normalizar valores da coluna de mês (remover acentos e padronizar)
        df['mes_str'] = df['mes_str'].astype(str)
        df['mes_norm'] = df['mes_str'].apply(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('ASCII').upper())

        # Extrair código textual do mês (ex.: 'AGO' de 'AGO-2016')
        import re
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
                parts = re.split(r'[-/\\\\]', s)
                if len(parts) >= 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    if left.isdigit():
                        return int(left), right
                    else:
                        code = _extract_month_code(left)
                        return (MESES_ORDEM.get(code), right)
                return (None, None)

            parsed = df.loc[mask_missing, 'mes_norm'].apply(_parse_from_norm)
            df.loc[mask_missing, 'mes_num'] = parsed.apply(lambda t: t[0])
            # tentar preencher ano se estiver embutido em mes_norm
            try:
                df.loc[mask_missing, 'ano'] = df.loc[mask_missing].apply(lambda r: r['ano'] if pd.notna(r['ano']) else (parsed.loc[r.name][1] if parsed.loc[r.name] and parsed.loc[r.name][1] is not None else r['ano']), axis=1)
            except Exception:
                pass

        # Converter ano e arrecadacao para tipos numéricos
        df['ano'] = pd.to_numeric(df['ano'], errors='coerce').astype('Int64')
        df['arrecadacao'] = pd.to_numeric(df['arrecadacao'], errors='coerce').fillna(0.0)

        # Criar coluna de data a partir de ano e mes_num (primeiro dia do mês)
        df['mes_num'] = pd.to_numeric(df['mes_num'], errors='coerce').astype('Int64')
        df['data'] = pd.to_datetime(df['ano'].astype(str) + '-' + df['mes_num'].astype(str).str.zfill(2) + '-01', errors='coerce')

        # Ordenar
        df = df.sort_values(by=['ano', 'mes_num']).reset_index(drop=True)
        return df
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{file_path}' não foi encontrado. Certifique-se de que ele está na pasta 'data'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}")
        return pd.DataFrame()

# Função para localizar arquivo de dados (suporta acentos e variações no nome)
def find_data_file(data_dir: str = 'data') -> str | None:
    if not os.path.isdir(data_dir):
        return None
    for f in os.listdir(data_dir):
        if f.lower().endswith(('.xls', '.xlsx', '.xlsm', '.xlsb')):
            name_norm = unicodedata.normalize('NFKD', f).encode('ASCII', 'ignore').decode('ASCII').upper()
            if 'ARRECADA' in name_norm:
                return os.path.join(data_dir, f)
    candidates = ['ARRECADAO.xlsx', 'ARRECADAÇÃO.xlsx', 'ARRECADACAO.xlsx', 'ARRECADAO.xls', 'ARRECADAÇÃO.xls']
    for c in candidates:
        p = os.path.join(data_dir, c)
        if os.path.exists(p):
            return p
    return None

# Caminho do arquivo de dados
found = find_data_file('data')
if found is None:
    DATA_PATH = os.path.join('data', 'ARRECADACAO.xlsx')
else:
    DATA_PATH = found

df = load_data(DATA_PATH)

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
    all_months_str = list(MESES_ORDEM.keys())
    selected_months_str = st.sidebar.multiselect(
        "Selecione o(s) Mês(es)",
        options=all_months_str,
        default=all_months_str # Seleciona todos por padrão
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
        media_mensal = df_filtered['arrecadacao'].mean()
        col2.metric(
            label="Média Mensal",
            value=f"R$ {media_mensal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        # KPI 3: Arrecadação do Último Mês (se houver)
        if not df_filtered.empty:
            latest_data = df_filtered.sort_values(by='data', ascending=False).iloc[0]
            ultimo_mes_arrecadacao = latest_data['arrecadacao']
            ultimo_mes_label = f"{latest_data['mes_str']}/{latest_data['ano']}"
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
    st.error("Não foi possível carregar os dados para a página de Análise Detalhada. Verifique o arquivo 'ARRECADAO.xlsx'.")
