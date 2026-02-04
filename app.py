import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
from io import StringIO
import re

st.set_page_config(page_title="Content Refresh Prioritizer", page_icon="🎯", layout="wide")

def get_groq_insight(url, metrics):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        prompt = f"""Eres un experto SEO. Analiza esta URL y genera un insight accionable en español (máximo 2 frases):

URL: {url}
Posición actual: {metrics['position']}
Cambio posición: {metrics['position_change']}
Sessions: {metrics['sessions']}
Cambio sessions: {metrics['sessions_change']}%
Bounce rate: {metrics['bounce_rate']:.1f}%

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

def normalize_url(url):
    if pd.isna(url):
        return ""
    url = str(url).strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    url = url.lower()
    if url.endswith('/'):
        url = url[:-1]
    return url

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

def clean_ga4_csv(raw_content):
    """Procesa CSV de GA4 con doble header y formato pivotado"""
    
    lines = [line for line in raw_content.split('\n') if not line.startswith('#') and line.strip()]
    
    # Encontrar línea con "Landing page"
    header_idx = None
    for i, line in enumerate(lines):
        if 'landing page' in line.lower():
            header_idx = i
            break
    
    if header_idx is None:
        raise ValueError("No encuentro header 'Landing page'")
    
    # Usar esa línea como header (skiprows = todas las anteriores)
    # Reconstruir CSV limpio
    clean_lines = lines[header_idx:]
    clean_csv = '\n'.join(clean_lines)
    
    # Leer CSV
    df = pd.read_csv(StringIO(clean_csv), on_bad_lines='skip')
    
    # Extraer URLs y datos
    # Formato: cada 3 filas = URL (col0 tiene URL), datos actuales (col0 vacía), datos anteriores (col0 vacía)
    
    url_data = []
    i = 0
    while i < len(df):
        first_col = str(df.iloc[i, 0]).strip()
        
        # Si col 0 tiene contenido y NO es fecha/% change
        if (first_col and 
            first_col not in ['', 'nan', 'NaN'] and
            '/' in first_col and  # Las URLs tienen /
            not any(month in first_col.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])):
            
            url = first_col
            
            # Siguiente fila (i+1): datos actuales
            # Siguiente fila (i+2): datos anteriores
            if i + 2 < len(df):
                # Sessions está en columna "Sessions" (index 3)
                # Bounce rate está en "Bounce rate" (index 5)
                
                sessions_current = clean_number(df.iloc[i+1, 3])
                sessions_previous = clean_number(df.iloc[i+2, 3])
                bounce_current = clean_number(df.iloc[i+1, 5]) * 100  # Convertir a %
                
                url_data.append({
                    'url': url,
                    'sessions_current': sessions_current,
                    'sessions_previous': sessions_previous,
                    'bounce_rate': bounce_current
                })
                
                i += 3
                continue
        
        i += 1
    
    return pd.DataFrame(url_data)

def process_data(gsc_df, ga4_df):
    
    # Limpiar GSC
    gsc_df = gsc_df[~gsc_df.iloc[:, 0].astype(str).str.contains('Grand total|^total$', case=False, regex=True, na=False)]
    gsc_df = gsc_df[gsc_df.iloc[:, 0].notna()]
    
    if len(gsc_df) == 0 or len(ga4_df) == 0:
        st.error("❌ Sin datos después de limpiar")
        return None
    
    # Normalizar URLs
    gsc_df['url_clean'] = gsc_df.iloc[:, 0].apply(normalize_url)
    ga4_df['url_clean'] = ga4_df['url'].apply(normalize_url)
    
    # Detectar columnas GSC
    pos_cols = [col for col in gsc_df.columns if 'position' in col.lower()]
    pos_cols = sorted(pos_cols, key=lambda x: 'previous' in x.lower())
    
    if len(pos_cols) < 2:
        st.error("❌ Faltan columnas de posición en GSC")
        return None
    
    # Procesar métricas
    gsc_df['position_current'] = gsc_df[pos_cols[0]].apply(clean_number)
    gsc_df['position_previous'] = gsc_df[pos_cols[1]].apply(clean_number)
    
    # Merge
    merged = gsc_df.merge(ga4_df, on='url_clean', how='inner')
    
    if len(merged) == 0:
        st.error("❌ No hay URLs coincidentes entre GSC y GA4")
        return None
    
    # Filtrar
    merged = merged[merged['position_current'] > 0]
    merged = merged[(merged['position_current'] >= 5) & (merged['position_current'] <= 20)]
    
    if len(merged) == 0:
        st.warning("⚠️ No hay URLs en rango 5-20")
        return None
    
    merged = merged[merged['sessions_current'] > 0]
    avg_sessions = merged['sessions_current'].mean()
    merged = merged[merged['sessions_current'] >= (avg_sessions * 0.3)]
    
    if len(merged) == 0:
        st.warning("⚠️ No hay URLs con suficiente tráfico")
        return None
    
    # Calcular
    merged['position_change'] = ((merged['position_previous'] - merged['position_current']) / merged['position_previous']) * 100
    merged['sessions_change'] = ((merged['sessions_current'] - merged['sessions_previous']) / merged['sessions_previous']) * 100
    
    if merged['sessions_current'].max() > merged['sessions_current'].min():
        merged['normalized_traffic'] = (merged['sessions_current'] - merged['sessions_current'].min()) / (merged['sessions_current'].max() - merged['sessions_current'].min()) * 100
    else:
        merged['normalized_traffic'] = 50
    
    merged['normalized_position'] = (20 - merged['position_current']) / 15 * 100
    merged['score'] = merged['normalized_traffic'] * 0.6 + merged['normalized_position'] * 0.4
    merged['losing_traffic'] = merged['sessions_change'] < 0
    merged = merged.sort_values(['score', 'losing_traffic'], ascending=[False, False])
    
    return merged

# UI
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero para maximizar tu tráfico orgánico")

show_debug = st.checkbox("🔍 Modo debug", value=False)

col1, col2 = st.columns(2)

with col1:
    gsc_file = st.file_uploader("📊 Google Search Console CSV", type=['csv'])
    
with col2:
    ga4_file = st.file_uploader("📈 Google Analytics 4 CSV", type=['csv'])

if gsc_file and ga4_file:
    if st.button("🚀 Analizar", type="primary"):
        with st.spinner("Analizando datos..."):
            try:
                gsc_df = pd.read_csv(gsc_file, encoding='utf-8', on_bad_lines='skip')
                
                ga4_file.seek(0)
                raw_content = ga4_file.read().decode('utf-8')
                ga4_df = clean_ga4_csv(raw_content)
                
                if show_debug:
                    st.write("**DEBUG GA4:**")
                    st.write(f"URLs extraídas: {len(ga4_df)}")
                    if len(ga4_df) > 0:
                        st.dataframe(ga4_df.head(5))
                
                if len(ga4_df) == 0:
                    st.error("❌ No se pudieron extraer URLs del CSV de GA4")
                    st.stop()
                
                results = process_data(gsc_df, ga4_df)
                
                if show_debug and results is not None:
                    st.write("**DEBUG RESULTS:**")
                    st.write(f"Oportunidades: {len(results)}")
                    st.dataframe(results.head(3))
                
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
                        st.metric("Sessions", 
                                 f"{int(top_url['sessions_current'])}", 
                                 f"{top_url['sessions_change']:+.1f}%")
                    
                    with col4:
                        st.metric("Bounce Rate", f"{top_url['bounce_rate']:.1f}%")
                    
                    st.markdown(f"**URL:** `{top_url['url_clean']}`")
                    
                    with st.spinner("Generando análisis con IA..."):
                        metrics = {
                            'position': int(top_url['position_current']),
                            'position_change': f"{top_url['position_change']:+.1f}%",
                            'sessions': int(top_url['sessions_current']),
                            'sessions_change': top_url['sessions_change'],
                            'bounce_rate': top_url['bounce_rate']
                        }
                        insight = get_groq_insight(top_url['url_clean'], metrics)
                    
                    st.info(f"💡 **Insight IA:** {insight}")
                    
                    st.markdown("---")
                    st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias con la versión Pro**")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
else:
    st.info("👆 Sube ambos archivos CSV para comenzar")
