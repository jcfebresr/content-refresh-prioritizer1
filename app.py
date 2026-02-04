import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq

st.set_page_config(page_title="Content Refresh Prioritizer", page_icon="🎯", layout="wide")

def get_groq_insight(url, metrics):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        prompt = f"""Eres un experto SEO. Analiza esta URL y genera un insight accionable en español (máximo 2 frases):

URL: {url}
Posición actual: {metrics['position']}
Cambio posición: {metrics['position_change']}
Clicks: {metrics['clicks']}
Cambio clicks: {metrics['clicks_change']}%
Impressions: {metrics['impressions']}
CTR: {metrics['ctr']:.1f}%

Genera un insight que diga QUÉ hacer específicamente para mejorar."""

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except:
        return "Análisis no disponible"

def clean_number(val):
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip().replace('%', '').replace(',', '')
    try:
        return float(val)
    except:
        return 0

def process_gsc_data(df):
    
    # Limpiar
    df = df[~df.iloc[:, 0].astype(str).str.contains('Grand total|^total$', case=False, regex=True, na=False)]
    df = df[df.iloc[:, 0].notna()]
    
    if len(df) == 0:
        st.error("❌ Sin datos después de limpiar")
        return None
    
    # Detectar columnas
    pos_cols = [col for col in df.columns if 'position' in col.lower()]
    click_cols = [col for col in df.columns if 'click' in col.lower()]
    imp_cols = [col for col in df.columns if 'impression' in col.lower()]
    ctr_cols = [col for col in df.columns if 'ctr' in col.lower()]
    
    pos_cols = sorted(pos_cols, key=lambda x: 'previous' in x.lower())
    click_cols = sorted(click_cols, key=lambda x: 'previous' in x.lower())
    imp_cols = sorted(imp_cols, key=lambda x: 'previous' in x.lower())
    ctr_cols = sorted(ctr_cols, key=lambda x: 'previous' in x.lower())
    
    if len(pos_cols) < 2 or len(click_cols) < 2:
        st.error("❌ Faltan columnas necesarias en GSC")
        return None
    
    # Procesar
    df['url'] = df.iloc[:, 0]
    df['position_current'] = df[pos_cols[0]].apply(clean_number)
    df['position_previous'] = df[pos_cols[1]].apply(clean_number)
    df['clicks_current'] = df[click_cols[0]].apply(clean_number)
    df['clicks_previous'] = df[click_cols[1]].apply(clean_number)
    df['impressions_current'] = df[imp_cols[0]].apply(clean_number) if imp_cols else 0
    df['ctr_current'] = df[ctr_cols[0]].apply(clean_number) if ctr_cols else 0
    
    # Filtrar rango 5-20
    df = df[df['position_current'] > 0]
    df = df[(df['position_current'] >= 5) & (df['position_current'] <= 20)]
    
    if len(df) == 0:
        st.warning("⚠️ No hay URLs en rango 5-20")
        return None
    
    # Filtrar tráfico mínimo
    df = df[df['clicks_current'] > 0]
    avg_clicks = df['clicks_current'].mean()
    df = df[df['clicks_current'] >= (avg_clicks * 0.3)]
    
    if len(df) == 0:
        st.warning("⚠️ No hay URLs con suficiente tráfico")
        return None
    
    # Calcular tendencias
    df['position_change'] = ((df['position_previous'] - df['position_current']) / df['position_previous']) * 100
    df['clicks_change'] = ((df['clicks_current'] - df['clicks_previous']) / df['clicks_previous']) * 100
    
    # Normalizar y calcular score
    if df['clicks_current'].max() > df['clicks_current'].min():
        df['normalized_traffic'] = (df['clicks_current'] - df['clicks_current'].min()) / (df['clicks_current'].max() - df['clicks_current'].min()) * 100
    else:
        df['normalized_traffic'] = 50
    
    df['normalized_position'] = (20 - df['position_current']) / 15 * 100
    df['score'] = df['normalized_traffic'] * 0.6 + df['normalized_position'] * 0.4
    
    # Ordenar: priorizar pérdida de clicks
    df['losing_traffic'] = df['clicks_change'] < 0
    df = df.sort_values(['score', 'losing_traffic'], ascending=[False, False])
    
    return df

# UI
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero basándote en Google Search Console")

gsc_file = st.file_uploader("📊 Google Search Console CSV", type=['csv'])

if gsc_file:
    if st.button("🚀 Analizar", type="primary"):
        with st.spinner("Analizando datos..."):
            try:
                gsc_df = pd.read_csv(gsc_file, encoding='utf-8', on_bad_lines='skip')
                results = process_gsc_data(gsc_df)
                
                if results is None or len(results) == 0:
                    st.error("❌ No se encontraron oportunidades")
                else:
                    st.success(f"✅ {len(results)} oportunidades encontradas")
                    
                    top_url = results.iloc[0]
                    
                    st.markdown("---")
                    st.subheader("🏆 TOP Oportunidad")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Score", f"{top_url['score']:.1f}/100")
                    
                    with col2:
                        st.metric("Posición", 
                                 f"{int(top_url['position_current'])}", 
                                 f"{top_url['position_change']:+.1f}%")
                    
                    with col3:
                        st.metric("Clicks", 
                                 f"{int(top_url['clicks_current'])}", 
                                 f"{top_url['clicks_change']:+.1f}%")
                    
                    with col4:
                        st.metric("CTR", f"{top_url['ctr_current']:.1f}%")
                    
                    st.markdown(f"**URL:** `{top_url['url']}`")
                    
                    with st.spinner("Generando análisis con IA..."):
                        metrics = {
                            'position': int(top_url['position_current']),
                            'position_change': f"{top_url['position_change']:+.1f}%",
                            'clicks': int(top_url['clicks_current']),
                            'clicks_change': top_url['clicks_change'],
                            'impressions': int(top_url['impressions_current']),
                            'ctr': top_url['ctr_current']
                        }
                        insight = get_groq_insight(top_url['url'], metrics)
                    
                    st.info(f"💡 **Insight IA:** {insight}")
                    
                    st.markdown("---")
                    st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias con la versión Pro**")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
else:
    st.info("👆 Sube tu archivo CSV de Google Search Console para comenzar")
    
    with st.expander("📖 ¿Cómo exportar desde GSC?"):
        st.markdown("""
        1. Ve a **Performance → Pages**
        2. Click en **Compare** (arriba derecha)
        3. Selecciona: Últimos 28 días vs 28 días anteriores
        4. Click **Export** → CSV
        """)
