import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta
import os

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Calculadora de Troca de Ativos")

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

# --- Sidebar: Premissas ---
st.sidebar.header("Premissas de Mercado (Projeção)")
cdi_proj = st.sidebar.number_input("CDI Anual Projetado (%)", value=11.0, step=0.1)
ipca_proj = st.sidebar.number_input("IPCA Anual Projetado (%)", value=4.5, step=0.1)

# --- Título com Logo (Com proteção contra erro) ---
col_logo, col_titulo = st.columns([0.2, 0.8])

# Nome do arquivo de imagem (Certifique-se de fazer o upload como logo.png)
nome_arquivo_imagem = "logo.png" 

with col_logo:
    # Verifica se o arquivo existe antes de tentar abrir para não travar o app
    if os.path.exists(nome_arquivo_imagem):
        st.image(nome_arquivo_imagem, use_column_width=True)
    else:
        # Se não achar a imagem, mostra um emoji no lugar
        st.warning("⚠️ Faça upload do arquivo 'logo.png'")
        
with col_titulo:
    st.title("Calculadora de Estratégia: Troca de Ativos")
    
st.markdown("---")

# --- Inputs ---
col1, col_gap, col2 = st.columns([1, 0.1, 1])

with col1:
    st.subheader("📉 Ativo 1 (Atual/Sair)")
    nome_ativo_1 = st.text_input("Nome do Ativo 1", "Ativo Atual")
    idx_1 = st.selectbox("Indexador (Ativo 1)", ["%CDI", "IPCA", "CDI+", "Prefixado"], key="idx1")
    vencimento_1 = st.date_input("Data de Vencimento (Ativo 1)", date.today() + relativedelta(years=2))
    duration_1 = st.number_input("Duration (anos)", value=1.5, key="dur1")
    isento_1 = st.radio("Isento de IR?", ["Sim", "Não"], horizontal=True, key="isento1")
    val_aplicado_1 = st.number_input("Valor Original Aplicado (R$)", value=100000.0, step=1000.0)
    financeiro_atual_1 = st.number_input("Financeiro Atual (Bruto/Curva) (R$)", value=110000.0, step=1000.0)
    
    st.markdown("---")
    st.markdown("**Dados de Saída**")
    taxa_liq_1 = st.number_input("Taxa Líquida (Atual) % a.a.", value=10.0, step=0.1)
    taxa_bruta_1 = st.number_input("Taxa Bruta (Atual) % a.a.", value=12.0, step=0.1)
    taxa_venda = st.number_input("Taxa de Venda (Mercado) % a.a.", value=13.0, step=0.1)
    financeiro_venda = st.number_input("Financeiro de Venda (R$)", value=105000.0, step=1000.0)

with col2:
    st.subheader("📈 Ativo 2 (Novo/Entrar)")
    nome_ativo_2 = st.text_input("Nome do Ativo 2", "Nova Oportunidade")
    idx_2 = st.selectbox("Indexador (Ativo 2)", ["%CDI", "IPCA", "CDI+", "Prefixado"], key="idx2")
    vencimento_2 = st.date_input("Data de Vencimento (Ativo 2)", date.today() + relativedelta(years=3))
    duration_2 = st.number_input("Duration (anos)", value=2.5, key="dur2")
    isento_2 = st.radio("Isento de IR?", ["Sim", "Não"], horizontal=True, key="isento2")
    val_aplicado_2 = st.number_input("Valor a ser Aplicado (R$)", value=financeiro_venda, step=1000.0)
    
    st.markdown("---")
    st.markdown("**Taxas da Nova Aplicação**")
    taxa_liq_2 = st.number_input("Taxa Líquida (Novo) % a.a.", value=14.0, step=0.1)
    taxa_bruta_2 = st.number_input("Taxa Bruta (Novo) % a.a.", value=14.0, step=0.1)

st.markdown("---")
btn_calcular = st.button("🔄 Calcular Troca de Ativos", type="primary")

if btn_calcular:
    diferenca_venda_curva = financeiro_venda - financeiro_atual_1
    pct_impacto = (diferenca_venda_curva / financeiro_atual_1) * 100

    st.header("Resultados da Simulação")

    m1, m2, m3 = st.columns(3)
    m1.metric("Valor Disponível para Troca", format_currency(financeiro_venda))
    m2.metric("Impacto Imediato", format_currency(diferenca_venda_curva), delta=f"{pct_impacto:.2f}%")

    # --- Projeção ---
    data_hoje = date.today()
    max_date = max(vencimento_1, vencimento_2)
    days_diff = (max_date - data_hoje).days
    eixo_x_datas = [data_hoje + relativedelta(days=i) for i in range(0, days_diff + 1, 30)]

    rate_1_aa = calc_taxa_equivalente_anual(taxa_liq_1, idx_1, cdi_proj, ipca_proj)
    rate_2_aa = calc_taxa_equivalente_anual(taxa_liq_2, idx_2, cdi_proj, ipca_proj)

    days_array = np.array([(d - data_hoje).days for d in eixo_x_datas])
    y1 = financeiro_atual_1 * ((1 + rate_1_aa) ** (days_array/365))
    y2 = val_aplicado_2 * ((1 + rate_2_aa) ** (days_array/365))

    # Crossover
    idx_cross = np.where(y2 > y1)[0]
    encontrou_crossover = False
    crossover_date = None
    crossover_value = 0

    if len(idx_cross) > 0:
        idx_c = idx_cross[0]
        crossover_date = eixo_x_datas[idx_c]
        crossover_value = y2[idx_c]
        encontrou_crossover = True
        meses_recuperacao = (crossover_date - data_hoje).days / 30
        m3.metric("Breakeven (Recuperação)", f"{meses_recuperacao:.1f} meses", delta="Vantajoso", delta_color="normal")
        st.success(f"✅ **A troca vale a pena!** A partir de **{crossover_date.strftime('%d/%m/%Y')}**, o {nome_ativo_2} supera o {nome_ativo_1}.")
    else:
        m3.metric("Breakeven", "Não alcançado", delta="Manter Ativo 1", delta_color="inverse")
        st.error(f"❌ **A troca não compensa.** O novo ativo não recupera o deságio da venda no prazo analisado.")

    # --- Gráfico ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eixo_x_datas, y=y1, mode='lines', name=f"Manter {nome_ativo_1}", line=dict(color='gray', dash='dash')))
    fig.add_trace(go.Scatter(x=eixo_x_datas, y=y2, mode='lines', name=f"Trocar por {nome_ativo_2}", line=dict(color='green', width=3)))

    if encontrou_crossover:
        fig.add_annotation(
            x=crossover_date, y=crossover_value,
            text="Ponto de Virada 🚀", showarrow=True, arrowhead=1, yshift=10,
            bgcolor="yellow", bordercolor="black",
            font=dict(color="black") # COR DA FONTE AJUSTADA PARA PRETO
        )
        fig.add_shape(type="line", x0=crossover_date, y0=min(y2[0], y1[0]), x1=crossover_date, y1=max(y2[-1], y1[-1]), line=dict(color="red", width=1, dash="dot"))

    fig.update_layout(title="Evolução Patrimonial", xaxis_title="Tempo", yaxis_title="R$", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # Resumo Final
    col_res1, col_res2 = st.columns(2)
    valor_final_1 = y1[-1]
    valor_final_2 = y2[-1]
    diff = valor_final_2 - valor_final_1
    col_res1.info(f"Final {nome_ativo_1}: {format_currency(valor_final_1)}")
    if diff > 0:
        col_res2.success(f"Final {nome_ativo_2}: {format_currency(valor_final_2)} (+ {format_currency(diff)})")
    else:
        col_res2.error(f"Final {nome_ativo_2}: {format_currency(valor_final_2)} ({format_currency(diff)})")
