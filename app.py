import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import unicodedata

# Paleta de cores padrão (ajustável para combinar com o modelo institucional)
PRIMARY_COLOR = "#C8102E"  # tom de vermelho institucional
NAVY = "#0B3D91"
KPI_BG = "#F5F7FA"
BG_HISTORICO = "#FBF8F3"  # fundo bege/creme
TEXT_COLOR = "#222222"
PLOTLY_TEMPLATE = "plotly_white"

# Paleta de cores distintas para cada ano
COLOR_PALETTE = {
    2016: '#0066CC',
    2017: '#0099FF',
    2018: '#FF9900',
    2019: '#333333',
    2020: '#9933FF',
    2021: '#0066FF',
    2022: '#FFCC00',
    2023: '#00CC66',
    2024: '#FF3333',
    2025: '#00CCCC',
    2026: '#FF6600',
}

# --- Configurações da Página ---
st.set_page_config(layout="wide", page_title="Painel de Arrecadação CBMAM")

# --- Carregamento e Preparação dos Dados ---
@st.cache_data
def load_data(file_path):
    df = pd.read_excel(file_path)
    # Mapear meses para números para facilitar a criação da data
    month_mapping = {
        'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
        'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
    }
    df['MES_NUM'] = df['MÊS'].map(month_mapping)
    df['DATA'] = pd.to_datetime(df['ANO'].astype(str) + '-' + df['MES_NUM'].astype(str).str.zfill(2) + '-01')
    df = df.sort_values(by='DATA')
    return df

def _normalize_str(s: str) -> str:
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII').upper()

def find_data_file(data_dir: str = 'data') -> str | None:
    # Try common filenames first
    candidates = ['ARRECADAO.xlsx', 'ARRECADAÇÃO.xlsx', 'ARRECADACAO.xlsx',
                  'ARRECADAO.xls', 'ARRECADAÇÃO.xls']
    for c in candidates:
        p = os.path.join(data_dir, c)
        if os.path.exists(p):
            return p
    # Scan the directory for an Excel file whose normalized name contains 'ARRECADA'
    if os.path.isdir(data_dir):
        for f in os.listdir(data_dir):
            if f.lower().endswith(('.xls', '.xlsx', '.xlsm', '.xlsb')):
                if 'ARRECADA' in _normalize_str(f):
                    return os.path.join(data_dir, f)
    return None

file_path = find_data_file('data')
if file_path is None:
    st.error("Arquivo de dados não encontrado em data/. Por favor coloque 'ARRECADAO.xlsx' ou 'ARRECADAÇÃO.xlsx' em data/.")
    df = pd.DataFrame(columns=['ANO','MÊS','VALOR'])
else:
    df = load_data(file_path)

# --- Título do Painel ---
st.markdown(f"""
    <div style='background-color:{PRIMARY_COLOR}; padding: 14px; border-radius: 6px; font-family: Arial, Helvetica, sans-serif;'>
        <h1 style='color:white; text-align:center; margin:4px 0;'>CORPO DE BOMBEIRO MILITAR DO AMAZONAS - CBMAM</h1>
        <h3 style='color:white; text-align:center; margin:2px 0; font-weight:600;'>PAINEL DE GERENCIAMENTO DE PROJETOS E MODERNIZAÇÃO DO CBMAM</h3>
        <h2 style='color:white; text-align:center; margin:6px 0 4px 0;'>ARRECADAÇÃO</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---") # Separador visual

# --- Layout do Painel (usando colunas para organizar) ---
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.markdown("<h3 style='text-align:center;'>PROJEÇÃO 2026</h3>", unsafe_allow_html=True)
    # Filtrar dados para 2026
    df_2026 = df[df['ANO'] == 2026]
    arrecadacao_2026_gauge = df_2026['VALOR'].sum()
    meta_2026 = 3000000.00 # Meta de 2026

    # Gráfico de velocímetro (Gauge Chart)
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = arrecadacao_2026_gauge,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Arrecadação 2026 vs Meta", 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, meta_2026 * 1.2], 'tickwidth': 1, 'tickcolor': NAVY},
            'bar': {'color': PRIMARY_COLOR, 'thickness': 0.15},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#DDDDDD",
            'steps': [
                {'range': [0, meta_2026 * 0.5], 'color': '#FFE5E5'},
                {'range': [meta_2026 * 0.5, meta_2026 * 0.8], 'color': '#FFE5CC'},
                {'range': [meta_2026 * 0.8, meta_2026 * 1.2], 'color': '#E5F5E5'}
            ],
            'threshold': {
                'line': {'color': PRIMARY_COLOR, 'width': 4},
                'thickness': 0.75,
                'value': meta_2026
            }
        }
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=10, r=10, t=60, b=10), font=dict(size=12))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col2:
    st.markdown("<h3 style='text-align:center;'>ARRECADAÇÃO POR ANO</h3>", unsafe_allow_html=True)
    # Agrupar por ano
    df_anual = df.groupby('ANO')['VALOR'].sum().reset_index()
    df_anual['COR'] = df_anual['ANO'].map(COLOR_PALETTE).fillna(PRIMARY_COLOR)

    # Gráfico de barras anual com cores distintas por ano
    fig_bar = go.Figure()
    for idx, row in df_anual.iterrows():
        fig_bar.add_trace(go.Bar(
            x=[row['ANO']],
            y=[row['VALOR']],
            marker_color=row['COR'],
            text=f"R$ {row['VALOR']:,.2f}",
            textposition='outside',
            hovertemplate=f"<b>{int(row['ANO'])}</b><br>R$ {row['VALOR']:,.2f}<extra></extra>",
            showlegend=False
        ))
    fig_bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', height=260,
                          xaxis=dict(tickmode='linear', title='Ano'),
                          yaxis=dict(title='Arrecadação (R$)', tickprefix='R$ ', separatethousands=True),
                          plot_bgcolor='white',
                          showlegend=False,
                          margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

with col3:
    st.markdown("<h3 style='text-align:center;'>KPIs</h3>", unsafe_allow_html=True)
    
    meta_2026 = 3000000.00
    arrecadacao_2026 = df[df['ANO'] == 2026]['VALOR'].sum() if 'ANO' in df.columns and 'VALOR' in df.columns else 0.0
    
    # Encontrar o ano com maior arrecadação
    if 'ANO' in df.columns and 'VALOR' in df.columns and len(df) > 0:
        df_anual_max = df.groupby('ANO')['VALOR'].sum().reset_index()
        ano_maior = int(df_anual_max.loc[df_anual_max['VALOR'].idxmax(), 'ANO'])
        arrecadacao_maior = df_anual_max['VALOR'].max()
    else:
        ano_maior = 2022
        arrecadacao_maior = 0.0

    kpi_style = f"background-color:{KPI_BG}; padding:14px; border-radius:8px; margin-bottom:12px; border-left:4px solid {PRIMARY_COLOR};"
    label_red = f"font-size:13px; color:{PRIMARY_COLOR}; margin:0; font-weight:700; text-transform:uppercase;"
    label_normal = f"font-size:13px; color:{NAVY}; margin:0; font-weight:700; text-transform:uppercase;"
    value_style = f"font-size:24px; font-weight:bold; margin:4px 0 0 0; color:{NAVY};"

    st.markdown(f"""
        <div style='{kpi_style}'>
            <p style='{label_red}'>Arrecadação 2026</p>
            <p style='{value_style}'>R$ {max(arrecadacao_2026, 0):,.2f}</p>
        </div>
        <div style='{kpi_style}'>
            <p style='{label_normal}'>Meta Arrecadação 2026</p>
            <p style='{value_style}'>R$ {meta_2026:,.2f}</p>
        </div>
        <div style='{kpi_style}'>
            <p style='{label_red}'>Arrecadação {ano_maior}</p>
            <p style='{value_style}'>R$ {arrecadacao_maior:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---") # Separador visual

# Seção de Histórico com fundo bege
st.markdown(f"""
    <div style='background-color:{BG_HISTORICO}; padding:16px; border-radius:8px; margin-bottom:16px;'>
        <h3 style='text-align:center; color:{PRIMARY_COLOR}; margin-top:0;'>HISTÓRICO DE ARRECADAÇÃO</h3>
    </div>
    """, unsafe_allow_html=True)

# Filtro de anos para o gráfico de histórico
selected_years = st.multiselect(
    "Selecione os Anos para o Histórico:",
    options=sorted(df['ANO'].unique()),
    default=sorted(df['ANO'].unique()),
    key="year_filter"
)

df_filtered_history = df[df['ANO'].isin(selected_years)]

# Gráfico de área histórico com cores distintas por ano
years_history = sorted(df_filtered_history['ANO'].unique())
color_map = {int(y): COLOR_PALETTE.get(int(y), PRIMARY_COLOR) for y in years_history}

fig_history = px.area(df_filtered_history,
                      x='MÊS',
                      y='VALOR',
                      color='ANO',
                      line_group='ANO',
                      labels={'VALOR': 'Arrecadação (R$)', 'MÊS': 'Mês', 'ANO': 'Ano'},
                      hover_data={'DATA': False, 'MES_NUM': False},
                      color_discrete_map=color_map,
                      template=PLOTLY_TEMPLATE)

fig_history.update_traces(opacity=0.7, hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>')
fig_history.update_layout(hovermode="x unified", height=550,
                          xaxis=dict(categoryorder='array', categoryarray=[
                              'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN',
                              'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'
                          ], title='Mês'),
                          yaxis=dict(title='Arrecadação (R$)', tickprefix='R$ '),
                          plot_bgcolor='white',
                          paper_bgcolor=BG_HISTORICO)
st.plotly_chart(fig_history, use_container_width=True)
