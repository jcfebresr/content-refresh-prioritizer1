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
Bounce rate: {metrics['bounce_rate']}%

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
    """Normaliza URLs"""
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
    """Convierte a número limpiando formato"""
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip().replace('%', '').replace(',', '')
    try:
        return float(val)
    except:
        return 0

def is_url_row(first_cell):
    """Verifica si la fila es una URL válida"""
    if pd.isna(first_cell):
        return False
    cell_str = str(first_cell).strip()
    
    # Detectar fechas (formato: "Jan 5 - Feb 3, 2026")
    date_patterns = ['jan ', 'feb ', 'mar ', 'apr ', 'may ', 'jun ', 'jul ', 'aug ', 'sep ', 'oct ', 'nov ', 'dec ', '202']
    if any(pattern in cell_str.lower() for pattern in date_patterns):
        return False
    
    # Detectar % change
    if '% change' in cell_str.lower():
        return False
    
    # Una URL válida tiene / o es dominio.com/path
    if '/' in cell_str or cell_str.startswith('http'):
        return True
    
    return False

def clean_ga4_csv(raw_content):
    """Limpia CSV de GA4 con doble header"""
    
    lines = raw_content.split('\n')
    
    # Encontrar la línea que contiene "Landing page + query string"
    header_line_idx = None
    for i, line in enumerate(lines):
        if 'landing page' in line.lower():
            header_line_idx = i
            break
    
    if header_line_idx is None:
        raise ValueError("No encuentro header 'Landing page + query string'")
    
    # Tomar desde esa línea en adelante
    clean_lines = lines[header_line_idx:]
    clean_csv = '\n'.join(clean_lines)
    
    # Leer CSV
    df = pd.read_csv(StringIO(clean_csv), on_bad_lines='skip')
    
    # Filtrar solo URLs válidas
    df = df[df.iloc[:, 0].apply(is_url_row)]
    
    return df

def process_data(gsc_df, ga4_df, show_debug=False):
    
    if show_debug:
        st.write("**🔍 Columnas GSC:**", gsc_df.columns.tolist())
        st.write("**Primeras 3 URLs GSC:**")
        st.dataframe(gsc_df.head(3))
        
        st.write("**Columnas GA4 originales:**", ga4_df.columns.tolist())
        st.write("**Primeras 5 filas GA4:**")
        st.dataframe(ga4_df.head(5))
    
    # Limpiar GSC
    gsc_df = gsc_df[~gsc_df.iloc[:, 0].astype(str).str.contains('Grand total|^total$', case=False, regex=True, na=False)]
    gsc_df = gsc_df[gsc_df.iloc[:, 0].notna()]
    
    if len(gsc_df) == 0 or len(ga4_df) == 0:
        st.error("❌ Sin datos válidos después de limpiar")
        return None
    
    # Normalizar URLs
    gsc_df['url_clean'] = gsc_df.iloc[:, 0].apply(normalize_url)
    ga4_df['url_clean'] = ga4_df.iloc[:, 0].apply(normalize_url)
    
    # GSC: Detectar columnas de posición
    pos_cols = [col for col in gsc_df.columns if 'position' in col.lower()]
    pos_cols = sorted(pos_cols, key=lambda x: 'previous' in x.lower())
    
    if len(pos_cols) < 2:
        st.error("❌ No encuentro columnas de posición en GSC")
        return None
    
    # GA4: Buscar columnas de sessions
    # El CSV tiene columnas duplicadas, usamos las primeras
    session_cols = [col for col in ga4_df.columns if col == 'Sessions']
    bounce_cols = [col for col in ga4_df.columns if 'bounce' in col.lower()]
    
    if show_debug:
        st.write(f"**Posición:** {pos_cols}")
        st.write(f"**Sessions encontradas:** {session_cols}")
        st.write(f"**Bounce encontradas:** {bounce_cols}")
    
    if len(session_cols) < 2:
        st.error("❌ No encuentro 2 columnas 'Sessions' en GA4")
        st.info("Las columnas disponibles son: " + str(ga4_df.columns.tolist()))
        return None
    
    # Procesar métricas
    gsc_df['position_current'] = gsc_df[pos_cols[0]].apply(clean_number)
    gsc_df['position_previous'] = gsc_df[pos_cols[1]].apply(clean_number)
    
    # GA4: usar la primera aparición de cada columna
    ga4_df['sessions_current'] = ga4_df[session_cols[0]].apply(clean_number)
    # La segunda aparición de Sessions está más adelante
    if len(session_cols) > 1:
        # En realidad están duplicadas, buscar la columna con índice mayor
        all_sessions_indices = [i for i, col in enumerate(ga4_df.columns) if col == 'Sessions']
        if len(all_sessions_indices) >= 2:
            ga4_df['sessions_previous'] = ga4_df.iloc[:, all_sessions_indices[1]].apply(clean_number)
        else:
            ga4_df['sessions_previous'] = 0
    else:
        ga4_df['sessions_previous'] = 0
    
    if bounce_cols:
        ga4_df['bounce_rate'] = ga4_df[bounce_cols[0]].apply(lambda x: clean_number(x) * 100)
    else:
        ga4_df['bounce_rate'] = 0
    
    # Merge
    merged = gsc_df.merge(ga4_df, on='url_clean', how='inner')
    
    if show_debug:
        st.write(f"**URLs después de merge:** {len(merged)}")
    
    if len(merged) == 0:
        st.error("❌ No hay URLs coincidentes")
        st.write("**Ejemplo URLs GSC:**", gsc_df['url_clean'].head(3).tolist())
        st.write("**Ejemplo URLs GA4:**", ga4_df['url_clean'].head(3).tolist())
        return None
    
    # Filtrar posiciones válidas
    merged = merged[merged['position_current'] > 0]
    merged = merged[(merged['position_current'] >= 5) & (merged['position_current'] <= 20)]
    
    if show_debug:
        st.write(f"**URLs en rango 5-20:** {len(merged)}")
    
    if len(merged) == 0:
        st.warning("⚠️ No hay URLs en rango 5-20")
        return None
    
    # Filtrar tráfico mínimo
    merged = merged[merged['sessions_current'] > 0]
    avg_sessions = merged['sessions_current'].mean()
    threshold = avg_sessions * 0.3
    merged = merged[merged['sessions_current'] >= threshold]
    
    if len(merged) == 0:
        st.warning("⚠️ No hay URLs con suficiente tráfico")
        return None
    
    # Calcular tendencias
    merged['position_change'] = ((merged['position_previous'] - merged['position_current']) / merged['position_previous']) * 100
    merged['sessions_change'] = ((merged['sessions_current'] - merged['sessions_previous']) / merged['sessions_previous']) * 100
    
    # Normalizar y calcular score
    if merged['sessions_current'].max() > merged['sessions_current'].min():
        merged['normalized_traffic'] = (merged['sessions_current'] - merged['sessions_current'].min()) / (merged['sessions_current'].max() - merged['sessions_current'].min()) * 100
    else:
        merged['normalized_traffic'] = 50
    
    merged['normalized_position'] = (20 - merged['position_current']) / 15 * 100
    merged['score'] = merged['normalized_traffic'] * 0.6 + merged['normalized_position'] * 0.4
    
    # Ordenar
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
                # Leer GSC
                gsc_df = pd.read_csv(gsc_file, encoding='utf-8', on_bad_lines='skip')
                
                # Leer GA4 de forma robusta
                ga4_file.seek(0)
                raw_content = ga4_file.read().decode('utf-8')
                ga4_df = clean_ga4_csv(raw_content)
                
                # Procesar
                results = process_data(gsc_df, ga4_df, show_debug=show_debug)
                
                if results is None or len(results) == 0:
                    st.info("💡 Activa modo debug para más detalles")
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
                    
                    # Insight IA
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
                if show_debug:
                    import traceback
                    st.code(traceback.format_exc())
                
else:
    st.info("👆 Sube ambos archivos CSV para comenzar")
