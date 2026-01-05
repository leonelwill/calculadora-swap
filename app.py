import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta
import os
from fpdf import FPDF
import tempfile

# --- Configuração da Página e CSS Personalizado ---
st.set_page_config(layout="wide", page_title="Calculadora Swap | Ethimos")

# CSS para alinhar logo e título e dar estilo 'clean'
st.markdown("""
    <style>
        .title-container {
            display: flex;
            align-items: center;
            justify_content: flex-start;
            padding-bottom: 20px;
        }
        .title-text {
            font-size: 40px;
            font-weight: bold;
            margin-left: 20px;
            color: #333;
        }
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            height: 50px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- Funções Auxiliares ---
def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calc_taxa_equivalente_anual(taxa_input, indexador, cdi_proj, ipca_proj):
    if indexador == "Prefixado":
        return taxa_input / 100
    elif indexador == "%CDI":
        return (taxa_input / 100) * (cdi_proj / 100)
    elif indexador == "CDI+":
        return ((cdi_proj / 100) + (taxa_input / 100))
    elif indexador == "IPCA":
        return ((1 + ipca_proj/100) * (1 + taxa_input/100)) - 1
    return 0.0

# --- Classe para o Relatório PDF ---
class PDF(FPDF):
    def header(self):
        # Logo
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 40)
        
        self.set_font('Arial', 'B', 15)
        self.cell(80) # Move to right
        self.cell(110, 10, 'Relatório de Estratégia: Troca de Ativos', 0, 0, 'R')
        self.ln(20)
        self.line(10, 30, 200, 30) # Linha horizontal
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} - Gerado por Ethimos Investimentos', 0, 0, 'C')

def criar_pdf(dados_entrada, resultados):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Seção 1: Resumo Executivo
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Resultado da Análise", 0, 1)
    pdf.set_font("Arial", size=12)
    
    if resultados['vantajoso']:
        pdf.set_text_color(0, 100, 0) # Verde
        pdf.multi_cell(0, 10, f"A TROCA É VANTAJOSA. O novo ativo supera o anterior a partir de {resultados['data_break']}.")
    else:
        pdf.set_text_color(150, 0, 0) # Vermelho
        pdf.multi_cell(0, 10, "A TROCA NÃO É RECOMENDADA no cenário base atual.")
    
    pdf.set_text_color(0, 0, 0) # Volta preto
    pdf.ln(5)
    
    # Tabela de Comparação Financeira
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 10, "Patrimônio Final (Manter)", 1, 0, 'C', 1)
    pdf.cell(95, 10, "Patrimônio Final (Trocar)", 1, 1, 'C', 1)
    
    pdf.cell(95, 10, resultados['final_v1'], 1, 0, 'C')
    pdf.cell(95, 10, resultados['final_v2'], 1, 1, 'C')
    
    diferenca = resultados['diff_val']
    txt_diff = f"Diferença Financeira: {format_currency(diferenca)}"
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt_diff, 1, 1, 'C')
    
    pdf.ln(10)
    
    # Seção 2: Detalhes dos Ativos
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "2. Parâmetros da Simulação", 0, 1)
    pdf.set_font("Arial", size=10)
    
    # Tabela Inputs
    col_w = 47.5
    pdf.cell(col_w, 8, "Parâmetro", 1, 0, 'C', 1)
    pdf.cell(col_w*1.5, 8, dados_entrada['nome1'], 1, 0, 'C', 1)
    pdf.cell(col_w*1.5, 8, dados_entrada['nome2'], 1, 1, 'C', 1)
    
    def row(label, v1, v2):
        pdf.cell(col_w, 8, label, 1)
        pdf.cell(col_w*1.5, 8, str(v1), 1)
        pdf.cell(col_w*1.5, 8, str(v2), 1, 1)

    row("Indexador", dados_entrada['idx1'], dados_entrada['idx2'])
    row("Taxa Líquida (% a.a.)", f"{dados_entrada['taxa1']}%", f"{dados_entrada['taxa2']}%")
    row("Vencimento", str(dados_entrada['venc1']), str(dados_entrada['venc2']))
    row("Aplicação Inicial", dados_entrada['fin_atual'], dados_entrada['val_aplicado2'])
    
    pdf.ln(5)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, "*Nota: O cálculo considera a venda do ativo 1 a mercado (com deságio/ágio) e reaplicação no ativo 2. As projeções assumem as premissas de CDI e IPCA informadas.")
    
    return pdf.output(dest='S').encode('latin-1')

# --- Header Visual ---
# Usando colunas nativas com alinhamento vertical (Streamlit mais recente) ou truque visual
col_h1, col_h2 = st.columns([0.15, 0.85])

with col_h1:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_column_width=True)
    else:
        st.warning("Sem logo")

with col_h2:
    # Usando HTML para garantir o alinhamento vertical centralizado com a imagem
    st.markdown("""
        <div style='display: flex; height: 100%; align-items: center;'>
            <h1 style='margin-top: 0px; margin-bottom: 0px;'>Calculadora de Estratégia: Troca de Ativos</h1>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- Sidebar ---
st.sidebar.header("Premissas Macro")
cdi_proj = st.sidebar.number_input("CDI Projetado (% a.a.)", 11.0, step=0.1)
ipca_proj = st.sidebar.number_input("IPCA Projetado (% a.a.)", 4.5, step=0.1)

# --- Inputs ---
c1, c2 = st.columns(2)

with c1:
    st.success("📉 **Ativo 1: SAÍDA (Venda)**")
    nome_ativo_1 = st.text_input("Nome Ativo 1", "LCI Banco X")
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        idx_1 = st.selectbox("Indexador", ["%CDI", "IPCA", "CDI+", "Prefixado"], key="i1")
        taxa_liq_1 = st.number_input("Taxa Líquida (% a.a.)", value=10.0, key="t1")
    with col_i2:
        vencimento_1 = st.date_input("Vencimento", date.today() + relativedelta(years=2), key="d1")
        duration_1 = st.number_input("Duration", 1.5, key="dur1")
    
    financeiro_atual_1 = st.number_input("Financeiro Atual (Curva) R$", 110000.0)
    financeiro_venda = st.number_input("Valor de VENDA (Mercado) R$", 105000.0, help="Quanto cai na conta hoje")
    
    # Cálculo do Haircut
    haircut = financeiro_venda - financeiro_atual_1
    pct_haircut = (haircut/financeiro_atual_1)*100
    st.caption(f"Impacto de Saída: {format_currency(haircut)} ({pct_haircut:.2f}%)")

with c2:
    st.info("📈 **Ativo 2: ENTRADA (Compra)**")
    nome_ativo_2 = st.text_input("Nome Ativo 2", "CRA Empresa Y")
    col_i3, col_i4 = st.columns(2)
    with col_i3:
        idx_2 = st.selectbox("Indexador", ["%CDI", "IPCA", "CDI+", "Prefixado"], key="i2")
        taxa_liq_2 = st.number_input("Taxa Líquida (% a.a.)", value=14.0, key="t2")
    with col_i4:
        vencimento_2 = st.date_input("Vencimento", date.today() + relativedelta(years=3), key="d2")
        duration_2 = st.number_input("Duration", 2.5, key="dur2")
        
    val_aplicado_2 = st.number_input("Valor a Aplicar R$", value=financeiro_venda)

st.markdown("---")
btn_calcular = st.button("🚀 CALCULAR ESTRATÉGIA")

if btn_calcular:
    # 1. Preparar Dados
    data_hoje = date.today()
    max_date = max(vencimento_1, vencimento_2)
    days_total = (max_date - data_hoje).days
    dates = [data_hoje + relativedelta(days=i) for i in range(0, days_total + 1, 15)] # De 15 em 15 dias para suavizar
    days_arr = np.array([(d - data_hoje).days for d in dates])
    
    # 2. Calcular Taxas Equivalentes
    r1 = calc_taxa_equivalente_anual(taxa_liq_1, idx_1, cdi_proj, ipca_proj)
    r2 = calc_taxa_equivalente_anual(taxa_liq_2, idx_2, cdi_proj, ipca_proj)
    
    # 3. Evolução
    # Ativo 1 parte do Financeiro ATUAL (Curva) se mantiver
    y1 = financeiro_atual_1 * ((1 + r1) ** (days_arr/365))
    # Ativo 2 parte do Valor de APLICAÇÃO (que veio da venda)
    y2 = val_aplicado_2 * ((1 + r2) ** (days_arr/365))
    
    # 4. Análise
    final_v1 = y1[-1]
    final_v2 = y2[-1]
    diff = final_v2 - final_v1
    
    cross_idx = np.where(y2 > y1)[0]
    has_cross = len(cross_idx) > 0
    cross_date = dates[cross_idx[0]] if has_cross else None
    cross_val = y2[cross_idx[0]] if has_cross else 0
    
    # --- RESULTADOS VISUAIS ---
    
    # Container para números grandes
    st.markdown("### 📊 Resultado da Simulação")
    kpi1, kpi2, kpi3 = st.columns(3)
    
    kpi1.metric("Patrimônio Final (Manter)", format_currency(final_v1))
    kpi2.metric("Patrimônio Final (Trocar)", format_currency(final_v2), delta=format_currency(diff))
    
    if has_cross:
        meses = (cross_date - data_hoje).days / 30
        kpi3.metric("Tempo de Recuperação", f"{meses:.1f} meses", f"Virada em {cross_date.strftime('%d/%m/%Y')}")
    else:
        kpi3.metric("Tempo de Recuperação", "Nunca", delta="Não compensa", delta_color="inverse")

    # --- GRÁFICO PREMIUN ---
    fig = go.Figure()
    
    # Cores Ethimos/Institucionais
    color_v1 = "#7f8c8d" # Cinza concreto
    color_v2 = "#27ae60" # Verde sucesso (ou use preto/dourado se preferir)
    
    fig.add_trace(go.Scatter(x=dates, y=y1, mode='lines', name=f"Manter {nome_ativo_1}", line=dict(color=color_v1, width=2, dash='dot')))
    fig.add_trace(go.Scatter(x=dates, y=y2, mode='lines', name=f"Trocar por {nome_ativo_2}", line=dict(color=color_v2, width=4)))
    
    # ANOTAÇÕES DE INÍCIO E FIM (Evitando sobreposição)
    # Inicio
    fig.add_annotation(x=dates[0], y=y1[0], text=f"Início: {format_currency(y1[0])}", showarrow=False, yshift=15, font=dict(color=color_v1))
    fig.add_annotation(x=dates[0], y=y2[0], text=f"Início: {format_currency(y2[0])}", showarrow=False, yshift=-15, font=dict(color=color_v2))
    
    # Fim
    # Verifica quem é maior para posicionar texto
    shift_v1 = 15 if y1[-1] > y2[-1] else -15
    shift_v2 = 15 if y2[-1] > y1[-1] else -15
    
    fig.add_annotation(x=dates[-1], y=y1[-1], text=f"Final: {format_currency(y1[-1])}", showarrow=True, arrowhead=1, ax=-40, ay=shift_v1, font=dict(color=color_v1, size=12))
    fig.add_annotation(x=dates[-1], y=y2[-1], text=f"Final: {format_currency(y2[-1])}", showarrow=True, arrowhead=1, ax=-40, ay=shift_v2, font=dict(color=color_v2, size=14, family="Arial Black"))

    # Marcação do Ponto de Virada
    if has_cross:
        fig.add_annotation(
            x=cross_date, y=cross_val,
            text="VIRADA 🚀",
            showarrow=True, arrowhead=2,
            bgcolor="#f1c40f", bordercolor="#000", borderwidth=1,
            font=dict(size=12, color="black"),
            ay=-40
        )

    fig.update_layout(
        height=600, # Gráfico maior
        title="Curva de Evolução Patrimonial",
        xaxis_title="Linha do Tempo",
        yaxis_title="Patrimônio (R$)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # --- GERAÇÃO DE PDF ---
    st.markdown("### 📑 Exportar Relatório")
    
    # Dicionários de dados para passar pro PDF
    inputs_pdf = {
        'nome1': nome_ativo_1, 'idx1': idx_1, 'taxa1': taxa_liq_1, 'venc1': vencimento_1, 'fin_atual': format_currency(financeiro_atual_1),
        'nome2': nome_ativo_2, 'idx2': idx_2, 'taxa2': taxa_liq_2, 'venc2': vencimento_2, 'val_aplicado2': format_currency(val_aplicado_2)
    }
    results_pdf = {
        'final_v1': format_currency(final_v1),
        'final_v2': format_currency(final_v2),
        'diff_val': diff,
        'vantajoso': has_cross,
        'data_break': cross_date.strftime('%d/%m/%Y') if has_cross else "N/A"
    }
    
    pdf_bytes = criar_pdf(inputs_pdf, results_pdf)
    
    st.download_button(
        label="📄 Baixar Relatório em PDF (A4)",
        data=pdf_bytes,
        file_name="Relatorio_Troca_Ativos.pdf",
        mime="application/pdf",
        type="secondary"
    )
