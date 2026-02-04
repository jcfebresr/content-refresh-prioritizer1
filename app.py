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
        return "Análisis no disponible"

def normalize_url(url):
    """Normaliza URLs para matching robusto"""
    if pd.isna(url):
        return ""
    
    url = str(url).strip()
    
    # Remover protocolo
    url = re.sub(r'^https?://', '', url)
    
    # Remover www
    url = re.sub(r'^www\.', '', url)
    
    # Lowercase
    url = url.lower()
    
    # Remover trailing slash
    if url.endswith('/'):
        url = url[:-1]
    
    # Remover query strings (opcional - comentar si necesitas query strings)
    # url = url.split('?')[0]
    
    return url

def clean_number(val):
    """Convierte strings con comas, porcentajes, etc a números"""
    if pd.isna(val):
        return 0
    
    if isinstance(val, (int, float)):
        return float(val)
    
    # Convertir a string y limpiar
    val = str(val).strip()
    
    # Remover %
    val = val.replace('%', '')
    
    # Remover comas
    val = val.replace(',', '')
    
    try:
        return float(val)
    except:
        return 0

def is_valid_url(url_str):
    """Verifica si una string parece una URL válida"""
    if pd.isna(url_str):
        return False
    
    url_str = str(url_str).strip()
    
    # Debe contener al menos un dominio o empezar con /
    if url_str.startswith('/'):
        return True
    
    # Debe tener punto y caracteres (dominio.com/path)
    if '.' in url_str and len(url_str) > 5:
        # No debe ser una fecha
        date_patterns = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', '202']
        if not any(pattern in url_str.lower() for pattern in date_patterns):
            return True
    
    return False

def clean_ga4_csv(ga4_df):
    """Limpia CSV de GA4 removiendo basura y dejando solo URLs válidas"""
    
    # Remover filas donde la primera columna NO es una URL
    mask = ga4_df.iloc[:, 0].apply(is_valid_url)
    ga4_df = ga4_df[mask]
    
    # Remover columna "Date Comparison" si existe
    if 'Date Comparison' in ga4_df.columns:
        ga4_df = ga4_df.drop('Date Comparison', axis=1)
    
    # Remover filas completamente vacías
    ga4_df = ga4_df.dropna(how='all')
    
    return ga4_df

def clean_gsc_csv(gsc_df):
    """Limpia CSV de GSC"""
    
    # Remover filas con totales
    first_col = gsc_df.iloc[:, 0].astype(str)
    mask = ~first_col.str.contains('Grand total|^total$', case=False, regex=True, na=False)
    gsc_df = gsc_df[mask]
    
    # Solo URLs válidas
    mask = gsc_df.iloc[:, 0].apply(is_valid_url)
    gsc_df = gsc_df[mask]
    
    return gsc_df

def detect_columns(df, col_type):
    """Detecta columnas por tipo (position, sessions, bounce, duration)"""
    cols = df.columns.tolist()
    
    if col_type == 'position':
        position_cols = [col for col in cols if 'position' in col.lower()]
        # Ordenar: primero "last/current", luego "previous"
        position_cols = sorted(position_cols, key=lambda x: 'previous' in x.lower())
        return position_cols[:2] if len(position_cols) >= 2 else []
    
    elif col_type == 'sessions':
        session_cols = [col for col in cols if 'session' in col.lower() and 'duration' not in col.lower()]
        # Ordenar: primero sin .1, luego con .1
        session_cols = sorted(session_cols, key=lambda x: '.1' in x)
        return session_cols[:2] if len(session_cols) >= 2 else []
    
    elif col_type == 'bounce':
        bounce_cols = [col for col in cols if 'bounce' in col.lower()]
        return bounce_cols[:2] if len(bounce_cols) >= 1 else []
    
    elif col_type == 'duration':
        duration_cols = [col for col in cols if 'duration' in col.lower()]
        return duration_cols[:2] if len(duration_cols) >= 1 else []
    
    return []

def process_data(gsc_df, ga4_df, show_debug=False):
    
    if show_debug:
        st.write("**🔍 Debug activado - Mostrando datos sin procesar:**")
        st.write("**Columnas GSC:**", gsc_df.columns.tolist())
        st.write("**Primeras 3 URLs GSC:**")
        st.dataframe(gsc_df.head(3))
        
        st.write("**Columnas GA4:**", ga4_df.columns.tolist())
        st.write("**Primeras 5 filas GA4:**")
        st.dataframe(ga4_df.head(5))
    
    # Limpiar datos
    gsc_df = clean_gsc_csv(gsc_df)
    ga4_df = clean_ga4_csv(ga4_df)
    
    if show_debug:
        st.write(f"**Después de limpiar:** GSC={len(gsc_df)} URLs, GA4={len(ga4_df)} URLs")
    
    if len(gsc_df) == 0:
        st.error("❌ No se encontraron URLs válidas en Google Search Console")
        return None
    
    if len(ga4_df) == 0:
        st.error("❌ No se encontraron URLs válidas en Google Analytics 4")
        st.info("💡 Asegúrate de exportar desde: Reports → Engagement → Landing page (no Pages and screens)")
        return None
    
    # Normalizar URLs
    gsc_df['url_clean'] = gsc_df.iloc[:, 0].apply(normalize_url)
    ga4_df['url_clean'] = ga4_df.iloc[:, 0].apply(normalize_url)
    
    # Detectar columnas
    pos_cols = detect_columns(gsc_df, 'position')
    session_cols = detect_columns(ga4_df, 'sessions')
    bounce_cols = detect_columns(ga4_df, 'bounce')
    duration_cols = detect_columns(ga4_df, 'duration')
    
    if show_debug:
        st.write(f"**Columnas detectadas:**")
        st.write(f"- Posición: {pos_cols}")
        st.write(f"- Sessions: {session_cols}")
        st.write(f"- Bounce: {bounce_cols}")
        st.write(f"- Duration: {duration_cols}")
    
    if len(pos_cols) < 2:
        st.error("❌ No encuentro 2 columnas de posición en GSC. Necesitas comparar 2 períodos al exportar.")
        return None
    
    if len(session_cols) < 2:
        st.error("❌ No encuentro 2 columnas de sessions en GA4. Necesitas comparar 2 períodos al exportar.")
        return None
    
    # Procesar columnas numéricas
    gsc_df['position_current'] = gsc_df[pos_cols[0]].apply(clean_number)
    gsc_df['position_previous'] = gsc_df[pos_cols[1]].apply(clean_number)
    
    ga4_df['sessions_current'] = ga4_df[session_cols[0]].apply(clean_number)
    ga4_df['sessions_previous'] = ga4_df[session_cols[1]].apply(clean_number)
    
    if bounce_cols:
        ga4_df['bounce_rate'] = ga4_df[bounce_cols[0]].apply(clean_number)
    else:
        ga4_df['bounce_rate'] = 0
        
    if duration_cols:
        ga4_df['avg_duration'] = ga4_df[duration_cols[0]].apply(clean_number)
    else:
        ga4_df['avg_duration'] = 0
    
    # Merge
    merged = gsc_df.merge(ga4_df, on='url_clean', how='inner')
    
    if show_debug:
        st.write(f"**URLs después de merge:** {len(merged)}")
        if len(merged) == 0:
            st.write("**URLs GSC (sample):**", gsc_df['url_clean'].head(5).tolist())
            st.write("**URLs GA4 (sample):**", ga4_df['url_clean'].head(5).tolist())
    
    if len(merged) == 0:
        st.error("❌ No hay URLs coincidentes entre GSC y GA4")
        st.info("💡 Verifica que ambos archivos sean del mismo sitio web")
        return None
    
    # Filtrar posiciones válidas (evitar ceros)
    merged = merged[merged['position_current'] > 0]
    
    # Filtrar rango 5-20
    before_filter = len(merged)
    merged = merged[(merged['position_current'] >= 5) & (merged['position_current'] <= 20)]
    
    if show_debug:
        st.write(f"**URLs en rango 5-20:** {len(merged)} (de {before_filter} totales)")
    
    if len(merged) == 0:
        st.warning("⚠️ No hay URLs en el rango de posición 5-20")
        st.info(f"💡 Tienes {before_filter} URLs totales. Prueba ampliando el rango.")
        return None
    
    # Filtrar sessions > 0
    merged = merged[merged['sessions_current'] > 0]
    
    if len(merged) < 3:
        st.warning(f"⚠️ Solo {len(merged)} URLs con datos suficientes")
    
    # Calcular promedio y filtrar tráfico bajo
    avg_sessions = merged['sessions_current'].mean()
    threshold = avg_sessions * 0.3  # Más permisivo: 30% en vez de 50%
    merged = merged[merged['sessions_current'] >= threshold]
    
    if len(merged) == 0:
        st.warning("⚠️ Todas las URLs tienen tráfico muy bajo")
        return None
    
    # Calcular tendencias
    merged['position_change'] = ((merged['position_previous'] - merged['position_current']) / merged['position_previous']) * 100
    merged['sessions_change'] = ((merged['sessions_current'] - merged['sessions_previous']) / merged['sessions_previous']) * 100
    
    # Normalizar métricas
    if merged['sessions_current'].max() > merged['sessions_current'].min():
        merged['normalized_traffic'] = (merged['sessions_current'] - merged['sessions_current'].min()) / (merged['sessions_current'].max() - merged['sessions_current'].min()) * 100
    else:
        merged['normalized_traffic'] = 50
    
    merged['normalized_position'] = (20 - merged['position_current']) / 15 * 100
    
    # Score final
    merged['score'] = merged['normalized_traffic'] * 0.6 + merged['normalized_position'] * 0.4
    
    # Ordenar
    merged['losing_traffic'] = merged['sessions_change'] < 0
    merged = merged.sort_values(['score', 'losing_traffic'], ascending=[False, False])
    
    return merged

# UI
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero para maximizar tu tráfico orgánico")

# Checkbox para debug
show_debug = st.checkbox("🔍 Mostrar información de debug", value=False)

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
                
                # Limpiar líneas con símbolos raros
                lines = [line for line in raw_content.split('\n') if line.strip() and not line.startswith('#') and not line.startswith('---')]
                clean_csv = '\n'.join(lines)
                
                # Detectar delimitador
                delimiter = ',' if clean_csv.count(',') > clean_csv.count(';') else ';'
                
                # Leer CSV limpio
                ga4_df = pd.read_csv(StringIO(clean_csv), delimiter=delimiter, on_bad_lines='skip')
                
                # Procesar
                results = process_data(gsc_df, ga4_df, show_debug=show_debug)
                
                if results is None or len(results) == 0:
                    if not show_debug:
                        st.info("💡 Activa el modo debug (checkbox arriba) para ver más detalles")
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
                            'bounce_rate': top_url['bounce_rate'],
                            'avg_duration': top_url['avg_duration']
                        }
                        insight = get_groq_insight(top_url['url_clean'], metrics)
                    
                    st.info(f"💡 **Insight IA:** {insight}")
                    
                    st.markdown("---")
                    st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias** con la versión Pro")
                    
            except Exception as e:
                st.error(f"❌ Error procesando archivos: {str(e)}")
                if show_debug:
                    import traceback
                    st.code(traceback.format_exc())
                
else:
    st.info("👆 Sube ambos archivos CSV para comenzar")
    
    with st.expander("📖 ¿Cómo exportar los datos correctamente?"):
        st.markdown("""
        **Google Search Console:**
        1. Ve a **Performance → Pages**
        2. Click en **Compare** (arriba derecha)
        3. Selecciona: Últimos 28 días vs 28 días anteriores
        4. Click **Export** → CSV
        
        **Google Analytics 4:**
        1. Ve a **Reports → Engagement → Landing page** (NO "Pages and screens")
        2. Click en **Compare** (arriba derecha)
        3. Selecciona: Últimos 28 días vs 28 días anteriores
        4. Añade métricas necesarias (Sessions, Users, Bounce rate, Duration)
        5. Click **Download** → CSV
        
        ⚠️ **Importante:** Ambos archivos deben tener comparación de 2 períodos activada
        """)
