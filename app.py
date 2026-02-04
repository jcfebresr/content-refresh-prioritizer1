import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
import os

st.set_page_config(page_title="Content Refresh Prioritizer", page_icon="🎯", layout="wide")

# Inicializar Groq
def get_groq_insight(url, metrics):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
        prompt = f"""Eres un experto SEO. Analiza esta URL y genera un insight accionable en español (máximo 2 frases):

URL: {url}
Posición actual: {metrics['position']}
Cambio posición: {metrics['position_change']}
Sessions: {metrics['sessions']}
Cambio sessions: {metrics['sessions_change']}%
Bounce rate: {metrics['bounce_rate']}%
Duración sesión: {metrics['avg_duration']}s

Genera un insight que diga QUÉ hacer específicamente para mejorar."""

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except:
        return "No disponible (configura tu API key de Groq)"

def clean_dataframe(df):
    """Limpia filas con % change, Grand total, etc."""
    df = df[~df.iloc[:, 0].astype(str).str.contains('%|Grand total|total', case=False, na=False)]
    return df.dropna()

def normalize_url(url):
    """Normaliza URLs para hacer match entre GSC y GA4"""
    url = str(url).lower().strip()
    if url.endswith('/'):
        url = url[:-1]
    return url

def process_data(gsc_df, ga4_df):
    # Limpiar datos
    gsc_df = clean_dataframe(gsc_df)
    ga4_df = clean_dataframe(ga4_df)
    
    # Renombrar columnas para facilitar
    gsc_df.columns = gsc_df.columns.str.strip()
    ga4_df.columns = ga4_df.columns.str.strip()
    
    # Normalizar URLs
    gsc_df['url_clean'] = gsc_df.iloc[:, 0].apply(normalize_url)
    ga4_df['url_clean'] = ga4_df.iloc[:, 0].apply(normalize_url)
    
    # Convertir a numérico
    gsc_df['position_current'] = pd.to_numeric(gsc_df.iloc[:, 1], errors='coerce')
    gsc_df['position_previous'] = pd.to_numeric(gsc_df.iloc[:, 2], errors='coerce')
    gsc_df['clicks_current'] = pd.to_numeric(gsc_df.iloc[:, 3], errors='coerce')
    
    ga4_df['sessions_current'] = pd.to_numeric(ga4_df.iloc[:, 1], errors='coerce')
    ga4_df['sessions_previous'] = pd.to_numeric(ga4_df.iloc[:, 2], errors='coerce')
    ga4_df['users_current'] = pd.to_numeric(ga4_df.iloc[:, 3], errors='coerce')
    ga4_df['bounce_rate'] = pd.to_numeric(ga4_df.iloc[:, 4], errors='coerce')
    ga4_df['avg_duration'] = pd.to_numeric(ga4_df.iloc[:, 5], errors='coerce')
    
    # Merge
    merged = gsc_df.merge(ga4_df, on='url_clean', how='inner')
    
    # Filtrar posiciones 5-20
    merged = merged[(merged['position_current'] >= 5) & (merged['position_current'] <= 20)]
    
    if len(merged) == 0:
        return None
    
    # Calcular promedio de sessions
    avg_sessions = merged['sessions_current'].mean()
    
    # Filtrar URLs con poco tráfico
    merged = merged[merged['sessions_current'] >= (avg_sessions * 0.5)]
    
    if len(merged) == 0:
        return None
    
    # Calcular tendencias
    merged['position_change'] = ((merged['position_previous'] - merged['position_current']) / merged['position_previous']) * 100
    merged['sessions_change'] = ((merged['sessions_current'] - merged['sessions_previous']) / merged['sessions_previous']) * 100
    
    # Normalizar métricas
    merged['normalized_traffic'] = (merged['sessions_current'] - merged['sessions_current'].min()) / (merged['sessions_current'].max() - merged['sessions_current'].min()) * 100
    merged['normalized_position'] = (20 - merged['position_current']) / 15 * 100
    
    # Score final
    merged['score'] = merged['normalized_traffic'] * 0.6 + merged['normalized_position'] * 0.4
    
    # Ordenar: score descendente, luego priorizar pérdida de tráfico
    merged['losing_traffic'] = merged['sessions_change'] < 0
    merged = merged.sort_values(['score', 'losing_traffic'], ascending=[False, False])
    
    return merged

# UI
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero para maximizar tu tráfico orgánico")

col1, col2 = st.columns(2)

with col1:
    gsc_file = st.file_uploader("📊 Google Search Console CSV", type=['csv'])
    
with col2:
    ga4_file = st.file_uploader("📈 Google Analytics 4 CSV", type=['csv'])

if gsc_file and ga4_file:
    if st.button("🚀 Analizar", type="primary"):
        with st.spinner("Analizando datos..."):
            try:
                # Leer GSC con manejo de errores
                gsc_df = pd.read_csv(gsc_file, encoding='utf-8')
                
                # Leer GA4 detectando delimitador automáticamente
                ga4_file.seek(0)  # Reset file pointer
                sample = ga4_file.read(1024).decode('utf-8')
                ga4_file.seek(0)
                
                # Detectar delimitador (coma, punto y coma, tab)
                delimiter = ',' if sample.count(',') > sample.count(';') else ';'
                
                ga4_df = pd.read_csv(ga4_file, encoding='utf-8', delimiter=delimiter, on_bad_lines='skip')
                
            except Exception as e:
                st.error(f"❌ Error leyendo archivos: {str(e)}")
                st.info("Asegúrate de exportar los CSVs en formato UTF-8 desde Google")
                st.stop()
            else:
                st.success(f"✅ {len(results)} oportunidades encontradas")
                
                # TOP 1 URL
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
                
                # URL
                st.markdown(f"**URL:** `{top_url['url_clean']}`")
                
                # Insight de Groq
                with st.spinner("Generando análisis con IA..."):
                    metrics = {
                        'position': int(top_url['position_current']),
                        'position_change': f"{top_url['position_change']:+.1f}%",
                        'sessions': int(top_url['sessions_current']),
                        'sessions_change': top_url['sessions_change'],
                        'bounce_rate': top_url['bounce_rate'],
                        'avg_duration': top_url['avg_duration']
                    }
                    insight = get_groq_insight(top_url['url_clean'], metrics)
                
                st.info(f"💡 **Insight IA:** {insight}")
                
                # Mensaje upgrade
                st.markdown("---")
                st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias** con la versión Pro")

else:
    st.info("👆 Sube ambos archivos CSV para comenzar")
    
    with st.expander("📖 ¿Cómo exportar los datos?"):
        st.markdown("""
        **Google Search Console:**
        1. Ve a Performance → Pages
        2. Compara últimos 28 días vs 28 días anteriores
        3. Exporta CSV
        
        **Google Analytics 4:**
        1. Ve a Reports → Engagement → Landing page
        2. Compara últimos 28 días vs 28 días anteriores
        3. Añade métricas: Sessions, Users, Bounce rate, Avg session duration
        4. Exporta CSV
        """)
