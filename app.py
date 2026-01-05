import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta
import os
from fpdf import FPDF
import tempfile

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Calculadora Swap | Ethimos")

# --- CSS Personalizado (Estética) ---
st.markdown("""
    <style>
        .main-title {
            text-align: center;
            font-size: 36px;
            font-weight: bold;
            color: #FFFFFF; /* Título Branco */
            margin-top: -20px;
        }
        .stButton>button {
            width: 100%;
            height: 50px;
            font-size: 18px;
            font-weight: 600;
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

# --- Classe PDF (Layout A4) ---
class PDF(FPDF):
    def header(self):
        # Logo Centralizado
        if os.path.exists("logo.png"):
            self.image("logo.png", x=75, y=10, w=60) 
        self.ln(25)
        
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Relatório de Estratégia: Troca de Ativos', 0, 1, 'C')
        self.line(10, 45, 200, 45)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Ethimos Investimentos - Página {self.page_no()}', 0, 0, 'C')

def criar_pdf_premium(dados_entrada, resultados, imagem_grafico_path):
    pdf = PDF()
    pdf.add_page()
    
    # 1. Dados
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. Parâmetros da Simulação", 0, 1)
    
    pdf.set_font("Arial", size=10)
    col_width = 95
    line_height = 7
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_width, line_height, f"ATIVO 1 (SAÍDA): {dados_entrada['nome1']}", 1, 0, 'L', 1)
    pdf.cell(col_width, line_height, f"ATIVO 2 (ENTRADA): {dados_entrada['nome2']}", 1, 1, 'L', 1)
    
    def double_row(label1, val1, label2, val2):
        pdf.cell(col_width, line_height, f"  {label1}: {val1}", 1, 0)
        pdf.cell(col_width, line_height, f"  {label2}: {val2}", 1, 1)

    double_row("Indexador", dados_entrada['idx1'], "Indexador", dados_entrada['idx2'])
    double_row("Taxa Líq.", f"{dados_entrada['taxa1']}%", "Taxa Líq.", f"{dados_entrada['taxa2']}%")
    double_row("Vencimento", str(dados_entrada['venc1']), "Vencimento", str(dados_entrada['venc2']))
    double_row("Fin. Atual", dados_entrada['fin_atual'], "Valor Aplicado", dados_entrada['val_aplicado2'])
    
    pdf.ln(5)
    
    # 2. Gráfico
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2. Evolução Patrimonial (Projeção)", 0, 1)
    
    if imagem_grafico_path and os.path.exists(imagem_grafico_path):
        pdf.image(imagem_grafico_path, x=10, w=190)
    else:
        pdf.cell(0, 10, "[Gráfico indisponível]", 0, 1)
        
    pdf.ln(5)

    # 3. Conclusão
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "3. Análise de Viabilidade", 0, 1)
    
    pdf.set_font("Arial", size=11)
    if resultados['vantajoso']:
        pdf.set_text_color(0, 100, 0) # Verde
        pdf.multi_cell(0, 8, f"RESULTADO: POSITIVO. A troca torna-se vantajosa a partir de {resultados['data_break']}. Ao final do período, projeta-se um ganho adicional de {format_currency(resultados['diff_val'])}.")
    else:
        pdf.set_text_color(150, 0, 0) # Vermelho
        pdf.multi_cell(0, 8, f"RESULTADO: NEGATIVO. No horizonte analisado, a troca não recupera o deságio inicial. Manter o ativo atual resulta em {format_currency(abs(resultados['diff_val']))} a mais.")
    
    return pdf.output(dest='S').encode('latin-1')


# --- LAYOUT UI ---

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_column_width=True)
    else:
        st.warning("⚠️ Adicione 'logo.png'")

st.markdown('<div class="main-title">Calculadora de Estratégia: Troca de Ativos</div>', unsafe_allow_html=True)
st.markdown("---")

st.sidebar.header("Premissas Macro")
cdi_proj = st.sidebar.number_input("CDI Projetado (% a.a.)", 11.0, step=0.1)
ipca_proj = st.sidebar.number_input("IPCA Projetado (% a.a.)", 4.5, step=0.1)

c1, c2 = st.columns(2)

with c1:
    st.subheader("📉 Ativo 1: SAÍDA")
    nome_ativo_1 = st.text_input("Nome Ativo 1", "LCI Banco X")
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        idx_1 = st.selectbox("Indexador", ["%CDI", "IPCA", "CDI+", "Prefixado"], key="i1")
        taxa_liq_1 = st.number_input("Taxa Líquida (% a.a.)", value=10.0, key="t1")
    with col_i2:
        vencimento_1 = st.date_input("Vencimento", date.today() + relativedelta(years=2), key="d1")
        duration_1 = st.number_input("Duration", 1.5, key="dur1")
    
    financeiro_atual_1 = st.number_input("Financeiro Atual (Curva) R$", 110000.0)
    financeiro_venda = st.number_input("Valor de VENDA (Mercado) R$", 105000.0, help="Valor líquido hoje")
    
    haircut = financeiro_venda - financeiro_atual_1
    st.caption(f"Impacto Imediato: {format_currency(haircut)}")

with c2:
    st.subheader("📈 Ativo 2: ENTRADA")
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
    # Cálculos
    data_hoje = date.today()
    max_date = max(vencimento_1, vencimento_2)
    days_total = (max_date - data_hoje).days
    dates = [data_hoje + relativedelta(days=i) for i in range(0, days_total + 1, 15)]
    days_arr = np.array([(d - data_hoje).days for d in dates])
    
    r1 = calc_taxa_equivalente_anual(taxa_liq_1, idx_1, cdi_proj, ipca_proj)
    r2 = calc_taxa_equivalente_anual(taxa_liq_2, idx_2, cdi_proj, ipca_proj)
    
    y1 = financeiro_atual_1 * ((1 + r1) ** (days_arr/365))
    y2 = val_aplicado_2 * ((1 + r2) ** (days_arr/365))
    
    final_v1 = y1[-1]
    final_v2 = y2[-1]
    diff = final_v2 - final_v1
    
    cross_idx = np.where(y2 > y1)[0]
    has_cross = len(cross_idx) > 0
    cross_date = dates[cross_idx[0]] if has_cross else None
    
    # --- KPIs ---
    st.markdown("### 📊 Resultado da Simulação")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Patrimônio Final (Manter)", format_currency(final_v1))
    kpi2.metric("Patrimônio Final (Trocar)", format_currency(final_v2), delta=format_currency(diff))
    
    if has_cross:
        meses = (cross_date - data_hoje).days / 30
        kpi3.metric("Recuperação (Breakeven)", f"{meses:.1f} meses", f"Virada em {cross_date.strftime('%d/%m/%Y')}")
    else:
        kpi3.metric("Recuperação", "Nunca", delta="Inviável", delta_color="inverse")

    # --- GRÁFICO ---
    fig = go.Figure()
    
    color_v1 = "#95a5a6"
    color_v2 = "#27ae60"
    
    fig.add_trace(go.Scatter(x=dates, y=y1, mode='lines', name=f"Manter {nome_ativo_1}", line=dict(color=color_v1, width=2, dash='dot')))
    fig.add_trace(go.Scatter(x=dates, y=y2, mode='lines', name=f"Trocar por {nome_ativo_2}", line=dict(color=color_v2, width=4)))
    
    # Anotações
    fig.add_annotation(x=dates[0], y=y1[0], text=f"Início: {format_currency(y1[0])}", showarrow=False, yshift=20, font=dict(color=color_v1), bgcolor="rgba(255,255,255,0.8)")
    fig.add_annotation(x=dates[0], y=y2[0], text=f"Início: {format_currency(y2[0])}", showarrow=False, yshift=-20, font=dict(color=color_v2), bgcolor="rgba(255,255,255,0.8)")
    
    distancia_final = abs(y1[-1] - y2[-1])
    offset_base = 20
    if distancia_final < (final_v1 * 0.05):
        offset_base = 40
        
    y_shift_1 = offset_base if y1[-1] > y2[-1] else -offset_base
    y_shift_2 = offset_base if y2[-1] > y1[-1] else -offset_base

    fig.add_annotation(
        x=dates[-1], y=y1[-1], 
        text=f"Final: {format_currency(y1[-1])}", 
        showarrow=True, arrowhead=1, ax=-50, ay=y_shift_1, 
        font=dict(color=color_v1), bgcolor="rgba(255,255,255,0.8)", bordercolor=color_v1
    )
    fig.add_annotation(
        x=dates[-1], y=y2[-1], 
        text=f"Final: {format_currency(y2[-1])}", 
        showarrow=True, arrowhead=1, ax=-50, ay=y_shift_2, 
        font=dict(color=color_v2, size=14, weight="bold"), bgcolor="rgba(255,255,255,0.9)", bordercolor=color_v2, borderwidth=2
    )

    if has_cross:
        fig.add_annotation(
            x=cross_date, y=y2[cross_idx[0]],
            text=f"VIRADA 🚀<br>{cross_date.strftime('%d/%m/%Y')}",
            showarrow=True, arrowhead=2,
            bgcolor="#f1c40f", bordercolor="#000", borderwidth=1,
            font=dict(size=11, color="black"),
            ay=-60
        )

    fig.update_layout(
        height=650, 
        title=dict(text="Curva de Evolução Patrimonial", x=0.5),
        xaxis_title="Linha do Tempo",
        yaxis_title="Patrimônio (R$)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # --- CONCLUSÃO NA TELA (NOVO) ---
    st.markdown("### 📝 Conclusão da Análise")
    if has_cross:
        st.success(f"**RESULTADO: POSITIVO.** ✅\n\nA troca torna-se vantajosa a partir de **{cross_date.strftime('%d/%m/%Y')}**. Ao final do período, projeta-se um ganho adicional de **{format_currency(diff)}**.")
    else:
        st.error(f"**RESULTADO: NEGATIVO.** ❌\n\nNo horizonte analisado, a troca não recupera o deságio inicial. Manter o ativo atual resulta em **{format_currency(abs(diff))}** a mais.")

    
    # --- PDF ---
    st.markdown("---")
    
    chart_path = None
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        try:
            fig.write_image(tmpfile.name, width=1200, height=600, scale=2)
            chart_path = tmpfile.name
        except Exception as e:
            st.error(f"Erro imagem: {e}. Verifique se instalou 'kaleido==0.2.1'")

    inputs_pdf = {
        'nome1': nome_ativo_1, 'idx1': idx_1, 'taxa1': taxa_liq_1, 'venc1': vencimento_1, 'fin_atual': format_currency(financeiro_atual_1),
        'nome2': nome_ativo_2, 'idx2': idx_2, 'taxa2': taxa_liq_2, 'venc2': vencimento_2, 'val_aplicado2': format_currency(val_aplicado_2)
    }
    results_pdf = {
        'diff_val': diff,
        'vantajoso': has_cross,
        'data_break': cross_date.strftime('%d/%m/%Y') if has_cross else "N/A"
    }
    
    pdf_bytes = criar_pdf_premium(inputs_pdf, results_pdf, chart_path)
    
    st.download_button(
        label="📄 CLIQUE AQUI PARA BAIXAR O RELATÓRIO PDF",
        data=pdf_bytes,
        file_name="Relatorio_Estrategia_Ethimos.pdf",
        mime="application/pdf",
        type="primary"
    )
