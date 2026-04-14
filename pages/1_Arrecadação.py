import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import unicodedata # Importar unicodedata para normalização de strings

# --- Configurações da Página ---
st.set_page_config(
    page_title="Dashboard de Arrecadação - Home",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Paleta de Cores e Estilos (Consistente com o Power BI) ---
PRIMARY_COLOR = "#C8102E"  # Vermelho institucional
NAVY = "#0B3D91"           # Azul marinho
KPI_BG = "#F5F7FA"         # Fundo cinza claro para KPIs
BG_HISTORICO = "#FBF8F3"   # Fundo bege/creme para o histórico
TEXT_COLOR = "#222222"     # Cor de texto padrão
PLOTLY_TEMPLATE = "plotly_white" # Template para os gráficos Plotly

# Paleta de cores distintas para cada ano (ajustada para mais anos se necessário)
COLOR_PALETTE = {
    2016: '#C8102E', 2017: '#0B3D91', 2018: '#FF7F0E', 2019: '#2CA02C',
    2020: '#D62728', 2021: '#9467BD', 2022: '#8C564B', 2023: '#E377C2',
    2024: '#7F7F7F', 2025: '#BCBD22', 2026: '#17BECF', 2027: '#A55194',
    2028: '#637939', 2029: '#BD9E39', 2030: '#AD494A'
}

# Mapeamento de meses para ordenação
MESES_ORDEM = {
    'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
}

# --- Função de Carregamento de Dados (Reutilizada da sua página de Análise Detalhada) ---
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
                parts = re.split(r'[-/\\\$|', s)
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
# Esta função precisa ser capaz de encontrar o arquivo na pasta 'data'
def find_data_file(data_dir: str = 'data') -> str | None:
    # Obtém o diretório atual do script (1_Home.py)
    current_script_dir = os.path.dirname(__file__)
    # Constrói o caminho para a pasta 'data' a partir da raiz do projeto
    # Assumindo que 'pages' e 'data' estão no mesmo nível da raiz do projeto
    project_root = os.path.abspath(os.path.join(current_script_dir, '..'))
    data_folder_path = os.path.join(project_root, data_dir)

    if not os.path.isdir(data_folder_path):
        st.warning(f"Diretório de dados '{data_folder_path}' não encontrado.")
        return None

    # Lista de nomes de arquivos que podem ser o seu Excel
    possible_names = ['ARRECADAO.xlsx', 'ARRECADAÇÃO.xlsx', 'ARRECADACAO.xls', 'ARRECADAÇÃO.xls']

    for f_name in possible_names:
        full_path = os.path.join(data_folder_path, f_name)
        if os.path.exists(full_path):
            return full_path

    # Fallback: se não encontrou pelos nomes exatos, tenta procurar por 'ARRECADA' no nome
    for f in os.listdir(data_folder_path):
        if f.lower().endswith(('.xls', '.xlsx', '.xlsm', '.xlsb')):
            name_norm = unicodedata.normalize('NFKD', f).encode('ASCII', 'ignore').decode('ASCII').upper()
            if 'ARRECADA' in name_norm:
                return os.path.join(data_folder_path, f)

    return None

# --- Carregamento dos Dados ---
# O caminho para a pasta 'data' é relativo à raiz do projeto, não ao script da página.
# A função find_data_file já foi ajustada para isso.
DATA_PATH = find_data_file('data')

if DATA_PATH is None:
    st.error("Não foi possível encontrar o arquivo de dados na pasta 'data'. Verifique se 'ARRECADAO.xlsx' (ou similar) está lá.")
    df = pd.DataFrame() # Cria um DataFrame vazio para evitar erros
else:
    df = load_data(DATA_PATH)

# --- Verificação se o DataFrame foi carregado com sucesso ---
if df.empty:
    st.error("Não foi possível carregar os dados para a página Home. Verifique o arquivo 'ARRECADAO.xlsx' e sua estrutura.")
else:
    # --- Título do Dashboard ---
    st.title("📊 Dashboard de Arrecadação")
    st.markdown("Visão Geral da Arrecadação por Período")

    # --- Sidebar para Filtros ---
    st.sidebar.header("Filtros")

    # Filtro de Ano
    all_years = sorted(df['ano'].unique(), reverse=True)
    selected_year = st.sidebar.selectbox(
        "Selecione o Ano",
        options=all_years,
        index=0 # Seleciona o ano mais recente por padrão
    )

    # Filtro de Mês (para o gráfico de barras mensais)
    all_months_sorted = sorted(MESES_ORDEM.keys(), key=lambda x: MESES_ORDEM[x])
    selected_month_for_bar = st.sidebar.selectbox(
        "Selecione o Mês para Detalhe (Gráfico de Barras)",
        options=['Todos'] + all_months_sorted,
        index=0 # 'Todos' por padrão
    )

    # Filtrar o DataFrame com base no ano selecionado
    df_filtered_year = df[df['ano'] == selected_year].copy()

    if df_filtered_year.empty:
        st.warning(f"Nenhum dado encontrado para o ano {selected_year}. Ajuste o filtro.")
    else:
        # --- KPIs na parte superior ---
        st.markdown(f"""
            <style>
            .kpi-card {{
                background-color: {KPI_BG};
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                height: 100%; /* Garante que todos os cards tenham a mesma altura */
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .kpi-value {{
                font-size: 2.5em;
                font-weight: bold;
                color: {PRIMARY_COLOR};
                margin-bottom: 5px;
            }}
            .kpi-label {{
                font-size: 1em;
                color: {TEXT_COLOR};
            }}
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        # KPI 1: Arrecadação Total do Ano Selecionado
        total_arrecadacao_ano = df_filtered_year['arrecadacao'].sum()
        with col1:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-value">R$ {total_arrecadacao_ano:,.2f}</div>
                    <div class="kpi-label">Arrecadação Total {selected_year}</div>
                </div>
            """, unsafe_allow_html=True)

        # KPI 2: Média Mensal do Ano Selecionado
        media_mensal_ano = df_filtered_year['arrecadacao'].mean()
        with col2:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-value">R$ {media_mensal_ano:,.2f}</div>
                    <div class="kpi-label">Média Mensal {selected_year}</div>
                </div>
            """, unsafe_allow_html=True)

        # KPI 3: Mês de Maior Arrecadação
        max_arrecadacao_mes = df_filtered_year.loc[df_filtered_year['arrecadacao'].idxmax()]
        with col3:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-value">R$ {max_arrecadacao_mes['arrecadacao']:,.2f}</div>
                    <div class="kpi-label">Maior Mês: {max_arrecadacao_mes['mes_str']}</div>
                </div>
            """, unsafe_allow_html=True)

        # KPI 4: Mês de Menor Arrecadação
        min_arrecadacao_mes = df_filtered_year.loc[df_filtered_year['arrecadacao'].idxmin()]
        with col4:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-value">R$ {min_arrecadacao_mes['arrecadacao']:,.2f}</div>
                    <div class="kpi-label">Menor Mês: {min_arrecadacao_mes['mes_str']}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # --- Gráfico de Barras: Arrecadação Mensal (Ano Selecionado) ---
        st.subheader(f"Arrecadação Mensal em {selected_year}")

        df_plot_monthly = df_filtered_year.copy()
        if selected_month_for_bar != 'Todos':
            df_plot_monthly = df_plot_monthly[df_plot_monthly['mes_str'] == selected_month_for_bar]

        # Ordenar os meses corretamente para o gráfico
        df_plot_monthly['mes_str'] = pd.Categorical(df_plot_monthly['mes_str'], categories=all_months_sorted, ordered=True)
        df_plot_monthly = df_plot_monthly.sort_values('mes_str')

        fig_monthly = px.bar(
            df_plot_monthly,
            x='mes_str',
            y='arrecadacao',
            text='arrecadacao', # Adiciona o valor sobre a barra
            title=f'Arrecadação Mensal para {selected_year}' + (f' - Mês: {selected_month_for_bar}' if selected_month_for_bar != 'Todos' else ''),
            labels={'mes_str': 'Mês', 'arrecadacao': 'Arrecadação (R$)'},
            color_discrete_sequence=[PRIMARY_COLOR]
        )
        fig_monthly.update_traces(
            texttemplate='R$ %{text:,.2f}',
            textposition='outside' # Posição do texto acima da barra
        )
        fig_monthly.update_layout(
            uniformtext_minsize=8, uniformtext_mode='hide',
            xaxis_title='Mês',
            yaxis_title='Arrecadação (R$)',
            plot_bgcolor=KPI_BG, # Fundo similar aos KPIs
            paper_bgcolor=KPI_BG,
            font_color=TEXT_COLOR,
            title_font_color=TEXT_COLOR,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#E0E0E0'),
            hovermode="x unified"
        )
        fig_monthly.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig_monthly, use_container_width=True)

        st.markdown("---")

        # --- Gráfico de Linha: Histórico de Arrecadação (Todos os Anos) ---
        st.subheader("Histórico de Arrecadação Mensal")

        # Agrupar por ano e mês para o gráfico de linha
        df_history = df.groupby(['ano', 'mes_num', 'mes_str'])['arrecadacao'].sum().reset_index()
        df_history = df_history.sort_values(by=['ano', 'mes_num'])
        df_history['data_plot'] = df_history['mes_str'] + '/' + df_history['ano'].astype(str)

        fig_history = px.line(
            df_history,
            x='data_plot',
            y='arrecadacao',
            color='ano', # Linhas separadas por ano
            title='Histórico de Arrecadação Mensal por Ano',
            labels={'data_plot': 'Mês/Ano', 'arrecadacao': 'Arrecadação (R$)', 'ano': 'Ano'},
            color_discrete_map=COLOR_PALETTE # Usar a paleta de cores definida
        )
        fig_history.update_traces(mode='lines+markers')
        fig_history.update_layout(
            hovermode="x unified",
            xaxis_title='Mês/Ano',
            yaxis_title='Arrecadação (R$)',
            plot_bgcolor=BG_HISTORICO, # Fundo bege/creme
            paper_bgcolor=BG_HISTORICO,
            font_color=TEXT_COLOR,
            title_font_color=TEXT_COLOR,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#E0E0E0')
        )
        fig_history.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig_history, use_container_width=True)

        st.markdown("---")

        # --- Seção de Projeção (Ajustada para dois valores e alinhamento) ---
        st.subheader("Projeção de Arrecadação")

        # Exemplo de dados de projeção (você pode substituir por sua lógica real)
        # Para fins de demonstração, vamos projetar o próximo mês com base na média dos últimos 3 meses
        if not df.empty:
            last_3_months_avg = df.tail(3)['arrecadacao'].mean()
            projected_next_month = last_3_months_avg * 1.05 # Exemplo: 5% de crescimento

            # Exemplo de projeção anual (soma do ano atual + projeção dos meses restantes)
            current_year = df['ano'].max()
            df_current_year = df[df['ano'] == current_year]

            # Se o ano atual for 2026 e já temos dados até ABR, projetamos de MAI a DEZ
            # Vamos simular uma projeção para o ano completo de 2026
            # Assumindo que o ano 2026 tem dados até ABR, vamos projetar os 8 meses restantes
            # Para simplificar, vamos usar a média mensal do ano atual para os meses restantes

            if current_year == 2026: # Exemplo específico para 2026
                months_with_data = df_current_year['mes_num'].nunique()
                if months_with_data < 12:
                    avg_monthly_current_year = df_current_year['arrecadacao'].mean()
                    projected_remaining_months_value = avg_monthly_current_year * (12 - months_with_data)
                    projected_annual_total = df_current_year['arrecadacao'].sum() + projected_remaining_months_value
                else: # Se já tem todos os meses, a projeção é a soma total
                    projected_annual_total = df_current_year['arrecadacao'].sum()
            else: # Para outros anos, a projeção é a arrecadação total do ano
                projected_annual_total = df_current_year['arrecadacao'].sum()


            col_proj1, col_proj2 = st.columns(2)

            with col_proj1:
                st.markdown(f"""
                    <div class="kpi-card" style="background-color: {KPI_BG};">
                        <div class="kpi-label">Projeção Próximo Mês</div>
                        <div class="kpi-value" style="color: {NAVY};">R$ {projected_next_month:,.2f}</div>
                    </div>
                """, unsafe_allow_html=True)

            with col_proj2:
                st.markdown(f"""
                    <div class="kpi-card" style="background-color: {KPI_BG};">
                        <div class="kpi-label">Projeção Anual {current_year}</div>
                        <div class="kpi-value" style="color: {NAVY};">R$ {projected_annual_total:,.2f}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Dados insuficientes para projeção.")

        st.markdown("---")

        # --- Gráfico de Barras com Projeção (0.57M) ---
        # Este gráfico é um pouco mais complexo para replicar o "0.57M"
        # Vamos criar um gráfico de barras simples para o ano atual e adicionar uma "projeção" visual
        st.subheader(f"Arrecadação Mensal e Projeção (Visual) para {selected_year}")

        # Dados para o gráfico de projeção
        df_proj_plot = df_filtered_year.copy()

        # Adicionar um mês de projeção (ex: o próximo mês após o último mês com dados)
        last_month_data = df_proj_plot.sort_values('data').iloc[-1]
        next_month_date = last_month_data['data'] + pd.DateOffset(months=1)

        # Simular um valor de projeção para o próximo mês
        # Usaremos a média dos últimos 3 meses como base para a projeção
        if len(df_proj_plot) >= 3:
            proj_value = df_proj_plot['arrecadacao'].tail(3).mean() * 1.05 # 5% de crescimento
        else:
            proj_value = df_proj_plot['arrecadacao'].mean() * 1.05 if not df_proj_plot.empty else 0

        # Criar uma linha para a projeção
        proj_data = {
            'mes_str': [next_month_date.strftime('%b').upper()],
            'ano': [selected_year],
            'arrecadacao': [proj_value],
            'data': [next_month_date],
            'tipo': ['Projeção']
        }
        df_proj_next_month = pd.DataFrame(proj_data)
        df_proj_next_month['mes_str'] = pd.Categorical(df_proj_next_month['mes_str'], categories=all_months_sorted, ordered=True)

        # Adicionar uma coluna 'tipo' para diferenciar dados reais de projeção
        df_proj_plot['tipo'] = 'Real'
        df_combined_proj = pd.concat([df_proj_plot, df_proj_next_month], ignore_index=True)

        # Ordenar para garantir que a projeção apareça no final
        df_combined_proj['mes_num'] = df_combined_proj['mes_str'].map(MESES_ORDEM)
        df_combined_proj = df_combined_proj.sort_values(by=['ano', 'mes_num']).reset_index(drop=True)

        # Remover a coluna 'mes_num' se não for mais necessária para evitar conflitos de tipo
        if 'mes_num' in df_combined_proj.columns:
            df_combined_proj = df_combined_proj.drop(columns=['mes_num'])

        fig_bar_proj = px.bar(
            df_combined_proj,
            x='mes_str',
            y='arrecadacao',
            color='tipo', # Diferenciar real de projeção
            color_discrete_map={'Real': PRIMARY_COLOR, 'Projeção': NAVY}, # Cores para real e projeção
            text='arrecadacao',
            title=f'Arrecadação Mensal e Projeção para {selected_year}',
            labels={'mes_str': 'Mês', 'arrecadacao': 'Arrecadação (R$)', 'tipo': 'Tipo de Dado'}
        )
        fig_bar_proj.update_traces(
            texttemplate='R$ %{text:,.2f}',
            textposition='outside'
        )
        fig_bar_proj.update_layout(
            uniformtext_minsize=8, uniformtext_mode='hide',
            xaxis_title='Mês',
            yaxis_title='Arrecadação (R$)',
            plot_bgcolor=KPI_BG,
            paper_bgcolor=KPI_BG,
            font_color=TEXT_COLOR,
            title_font_color=TEXT_COLOR,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#E0E0E0'),
            hovermode="x unified"
        )
        fig_bar_proj.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig_bar_proj, use_container_width=True)