import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import unicodedata

PRIMARY_COLOR = "#C8102E"
NAVY = "#0B3D91"
KPI_BG = "#F5F7FA"
BG_HISTORICO = "#FBF8F3"
PLOTLY_TEMPLATE = "plotly_white"

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

st.set_page_config(layout="wide", page_title="Painel de Arrecadação CBMAM")

def _normalize_str(s: str) -> str:
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII').upper()

@st.cache_data
def load_data(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        # Tenta ponto e vírgula primeiro (padrão Excel BR), depois vírgula
        try:
            df = pd.read_csv(file_path, sep=';', encoding='utf-8-sig')
            if df.shape[1] < 2:
                df = pd.read_csv(file_path, sep=',', encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8-sig')
    else:
        df = pd.read_excel(file_path, engine='openpyxl')

    # Normaliza nome das colunas (remove espaços extras)
    df.columns = df.columns.str.strip()

    month_mapping = {
        'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
        'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
    }

    # Suporte a coluna MÊS ou MES
    mes_col = 'MÊS' if 'MÊS' in df.columns else 'MES'
    df['MES_NUM'] = df[mes_col].str.strip().str.upper().map(month_mapping)
    df['MÊS'] = df[mes_col].str.strip().str.upper()

    df['DATA'] = pd.to_datetime(
        df['ANO'].astype(str) + '-' + df['MES_NUM'].astype(str).str.zfill(2) + '-01'
    )
    df['ANO'] = df['ANO'].astype(int)

    # Garante que VALOR é numérico (CSV pode vir com vírgula decimal)
    if df['VALOR'].dtype == object:
        df['VALOR'] = (
            df['VALOR'].astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float)
        )

    df = df.sort_values(by='DATA')
    return df

def find_data_file(data_dir: str = 'data') -> str | None:
    # Prioriza CSV
    candidates = [
        'ARRECADACAO.csv', 'ARRECADAÇÃO.csv',
        'ARRECADAO.csv',
        'ARRECADACAO.xlsx', 'ARRECADAÇÃO.xlsx', 'ARRECADAO.xlsx',
        'ARRECADACAO.xls', 'ARRECADAÇÃO.xls',
    ]
    for c in candidates:
        p = os.path.join(data_dir, c)
        if os.path.exists(p):
            return p
    if os.path.isdir(data_dir):
        for f in os.listdir(data_dir):
            if f.startswith('~$'):
                continue
            if f.lower().endswith(('.csv', '.xls', '.xlsx', '.xlsm', '.xlsb')):
                if 'ARRECADA' in _normalize_str(f):
                    return os.path.join(data_dir, f)
    return None

file_path = find_data_file('data')
if file_path is None:
    st.error(
        "Arquivo de dados não encontrado em data/. "
        "Coloque 'ARRECADACAO.csv' (recomendado) ou 'ARRECADACAO.xlsx' na pasta data/."
    )
    df = pd.DataFrame(columns=['ANO', 'MÊS', 'VALOR', 'MES_NUM', 'DATA'])
else:
    df = load_data(file_path)

# --- Título ---
st.markdown(f"""
    <div style='background-color:{PRIMARY_COLOR}; padding:14px; border-radius:6px;
                font-family:Arial,Helvetica,sans-serif;'>
        <h1 style='color:white; text-align:center; margin:4px 0;'>
            CORPO DE BOMBEIRO MILITAR DO AMAZONAS - CBMAM
        </h1>
        <h3 style='color:white; text-align:center; margin:2px 0; font-weight:600;'>
            PAINEL DE GERENCIAMENTO DE PROJETOS E MODERNIZAÇÃO DO CBMAM
        </h3>
        <h2 style='color:white; text-align:center; margin:6px 0 4px 0;'>ARRECADAÇÃO</h2>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

# --- Coluna 1: Gauge ---
with col1:
    st.markdown("<h3 style='text-align:center;'>PROJEÇÃO 2026</h3>", unsafe_allow_html=True)
    meta_2026 = 3_000_000.00
    arrecadacao_2026_gauge = df[df['ANO'] == 2026]['VALOR'].sum() if len(df) > 0 else 0.0

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=arrecadacao_2026_gauge,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Arrecadação 2026 vs Meta", 'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, meta_2026 * 1.2], 'tickwidth': 1, 'tickcolor': NAVY},
            'bar': {'color': PRIMARY_COLOR, 'thickness': 0.15},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#DDDDDD",
            'steps': [
                {'range': [0, meta_2026 * 0.5], 'color': '#FFE5E5'},
                {'range': [meta_2026 * 0.5, meta_2026 * 0.8], 'color': '#FFE5CC'},
                {'range': [meta_2026 * 0.8, meta_2026 * 1.2], 'color': '#E5F5E5'},
            ],
            'threshold': {
                'line': {'color': PRIMARY_COLOR, 'width': 4},
                'thickness': 0.75,
                'value': meta_2026,
            }
        }
    ))
    fig_gauge.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(size=12)
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

# --- Coluna 2: Barras anuais ---
with col2:
    st.markdown("<h3 style='text-align:center;'>ARRECADAÇÃO POR ANO</h3>", unsafe_allow_html=True)

    if len(df) > 0:
        df_anual = df.groupby('ANO')['VALOR'].sum().reset_index()
        df_anual['COR'] = df_anual['ANO'].map(COLOR_PALETTE).fillna(PRIMARY_COLOR)

        fig_bar = go.Figure()
        for _, row in df_anual.iterrows():
            fig_bar.add_trace(go.Bar(
                x=[row['ANO']],
                y=[row['VALOR']],
                marker_color=row['COR'],
                text=f"R$ {row['VALOR']:,.2f}",
                textposition='outside',
                hovertemplate=f"<b>{int(row['ANO'])}</b><br>R$ {row['VALOR']:,.2f}<extra></extra>",
                showlegend=False
            ))
        fig_bar.update_layout(
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            height=260,
            xaxis=dict(tickmode='linear', title='Ano'),
            yaxis=dict(title='Arrecadação (R$)', tickprefix='R$ ', separatethousands=True),
            plot_bgcolor='white',
            showlegend=False,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# --- Coluna 3: KPIs ---
with col3:
    st.markdown("<h3 style='text-align:center;'>KPIs</h3>", unsafe_allow_html=True)

    arrecadacao_2026 = df[df['ANO'] == 2026]['VALOR'].sum() if len(df) > 0 else 0.0

    if len(df) > 0:
        df_anual_kpi = df.groupby('ANO')['VALOR'].sum().reset_index()
        ano_maior = int(df_anual_kpi.loc[df_anual_kpi['VALOR'].idxmax(), 'ANO'])
        arrecadacao_maior = df_anual_kpi['VALOR'].max()
    else:
        ano_maior = 2022
        arrecadacao_maior = 0.0

    kpi_style = (
        f"background-color:{KPI_BG}; padding:14px; border-radius:8px; "
        f"margin-bottom:12px; border-left:4px solid {PRIMARY_COLOR};"
    )
    label_red    = f"font-size:13px; color:{PRIMARY_COLOR}; margin:0; font-weight:700; text-transform:uppercase;"
    label_normal = f"font-size:13px; color:{NAVY}; margin:0; font-weight:700; text-transform:uppercase;"
    value_style  = f"font-size:24px; font-weight:bold; margin:4px 0 0 0; color:{NAVY};"

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
            <p style='{label_red}'>Maior Arrecadação ({ano_maior})</p>
            <p style='{value_style}'>R$ {arrecadacao_maior:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- Histórico ---
st.markdown(f"""
    <div style='background-color:{BG_HISTORICO}; padding:16px; border-radius:8px; margin-bottom:16px;'>
        <h3 style='text-align:center; color:{PRIMARY_COLOR}; margin-top:0;'>
            HISTÓRICO DE ARRECADAÇÃO
        </h3>
    </div>
""", unsafe_allow_html=True)

if len(df) > 0:
    selected_years = st.multiselect(
        "Selecione os Anos para o Histórico:",
        options=sorted(df['ANO'].unique()),
        default=sorted(df['ANO'].unique()),
        key="year_filter"
    )

    df_filtered = df[df['ANO'].isin(selected_years)]
    color_map = {int(y): COLOR_PALETTE.get(int(y), PRIMARY_COLOR) for y in sorted(df_filtered['ANO'].unique())}

    fig_history = px.area(
        df_filtered,
        x='MÊS',
        y='VALOR',
        color='ANO',
        line_group='ANO',
        labels={'VALOR': 'Arrecadação (R$)', 'MÊS': 'Mês', 'ANO': 'Ano'},
        color_discrete_map=color_map,
        template=PLOTLY_TEMPLATE
    )
    fig_history.update_traces(
        opacity=0.7,
        hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>'
    )
    fig_history.update_layout(
        hovermode="x unified",
        height=550,
        xaxis=dict(
            categoryorder='array',
            categoryarray=['JAN','FEV','MAR','ABR','MAI','JUN',
                           'JUL','AGO','SET','OUT','NOV','DEZ'],
            title='Mês'
        ),
        yaxis=dict(title='Arrecadação (R$)', tickprefix='R$ '),
        plot_bgcolor='white',
        paper_bgcolor=BG_HISTORICO
    )
    st.plotly_chart(fig_history, use_container_width=True)
else:
    st.info("Nenhum dado disponível para exibir o histórico.")
