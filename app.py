import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
from io import StringIO

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
    if len(df) > 0:
        first_col = df.iloc[:, 0].astype(str)
        
        # Eliminar filas que NO son URLs válidas (fechas, totales, etc)
        # Una URL válida contiene http o al menos un punto y barra
        mask = (
            ~first_col.str.contains('Grand total|^total$|^%|jan |feb |mar |apr |may |jun |jul |aug |sep |oct |nov |dec ', case=False, regex=True, na=False) &
            (first_col.str.contains('http|/', case=False, na=False) | first_col.str.startswith('/'))
        )
        df = df[mask]
        
        df = df.dropna(how='all')
        df = df[df.iloc[:, 0].notna()]
        df = df[df.iloc[:, 0].astype(str).str.strip() != '']
    return df

def normalize_url(url):
    """Normaliza URLs para hacer match entre GSC y GA4"""
    url = str(url).lower().strip()
    if url.endswith('/'):
        url = url[:-1]
    return url

def process_data(gsc_df, ga4_df):
    # Debug info
    st.write("**Debug - Columnas GSC:**", gsc_df.columns.tolist())
    st.write("**Debug - Primeras 3 filas GSC:**")
    st.dataframe(gsc_df.head(3))
    
    st.write("**Debug - Columnas GA4:**", ga4_df.columns.tolist())
    st.write("**Debug - Primeras 3 filas GA4:**")
    st.dataframe(ga4_df.head(3))
    
    # Limpiar datos
    gsc_df = clean_dataframe(gsc_df)
    ga4_df = clean_dataframe(ga4_df)
    
    st.write(f"**Filas después de limpiar:** GSC={len(gsc_df)}, GA4={len(ga4_df)}")
    
    # Renombrar columnas para facilitar
    gsc_df.columns = gsc_df.columns.str.strip()
    ga4_df.columns = ga4_df.columns.str.strip()
    
    # Normalizar URLs
    gsc_df['url_clean'] = gsc_df.iloc[:, 0].apply(normalize_url)
    ga4_df['url_clean'] = ga4_df.iloc[:, 0].apply(normalize_url)
    
    # Detectar columnas de posición
    pos_cols = [col for col in gsc_df.columns if 'position' in col.lower()]
    st.write(f"**Columnas posición:** {pos_cols}")
    
    # Detectar columnas de sessions
    session_cols = [col for col in ga4_df.columns if 'session' in col.lower() and 'duration' not in col.lower()]
    st.write(f"**Columnas sessions:** {session_cols}")
    
    # Si no encuentra columnas, mostrar error
    if len(pos_cols) < 2:
        st.error("❌ No encuentro columnas de posición en GSC")
        return None
    
    if len(session_cols) < 2:
        st.error("❌ No encuentro columnas de sessions en GA4")
        return None
    
    # Convertir a numérico
    gsc_df['position_current'] = pd.to_numeric(gsc_df[pos_cols[0]], errors='coerce')
    gsc_df['position_previous'] = pd.to_numeric(gsc_df[pos_cols[1]], errors='coerce')
    
    ga4_df['sessions_current'] = pd.to_numeric(ga4_df[session_cols[0]], errors='coerce')
    ga4_df['sessions_previous'] = pd.to_numeric(ga4_df[session_cols[1]], errors='coerce')
    
    # Buscar bounce rate y duration
    bounce_col = [col for col in ga4_df.columns if 'bounce' in col.lower()]
    duration_col = [col for col in ga4_df.columns if 'duration' in col.lower()]
    
    if bounce_col:
        ga4_df['bounce_rate'] = pd.to_numeric(ga4_df[bounce_col[0]], errors='coerce')
    else:
        ga4_df['bounce_rate'] = 0
        
    if duration_col:
        ga4_df['avg_duration'] = pd.to_numeric(ga4_df[duration_col[0]], errors='coerce')
    else:
        ga4_df['avg_duration'] = 0
    
    # Merge
    merged = gsc_df.merge(ga4_df, on='url_clean', how='inner')
    st.write(f"**URLs después de merge:** {len(merged)}")
    
    if len(merged) == 0:
        st.warning("❌ No hay URLs que coincidan entre GSC y GA4. Verifica que ambos archivos sean del mismo sitio.")
        st.write("**Ejemplo URLs GSC:**", gsc_df['url_clean'].head(3).tolist())
        st.write("**Ejemplo URLs GA4:**", ga4_df['url_clean'].head(3).tolist())
        return None
    
    # Filtrar posiciones 5-20
    before_filter = len(merged)
    merged = merged[(merged['position_current'] >= 5) & (merged['position_current'] <= 20)]
    st.write(f"**URLs en posición 5-20:** {len(merged)} (antes: {before_filter})")
    
    if len(merged) == 0:
        st.warning("No hay URLs en el rango 5-20")
        return None
    
    # Calcular promedio de sessions
    avg_sessions = merged['sessions_current'].mean()
    st.write(f"**Promedio sessions:** {avg_sessions:.2f}")
    
    # Filtrar URLs con poco tráfico
    threshold = avg_sessions * 0.5
    before_traffic = len(merged)
    merged = merged[merged['sessions_current'] >= threshold]
    st.write(f"**URLs con tráfico > {threshold:.2f}:** {len(merged)} (antes: {before_traffic})")
    
    if len(merged) == 0:
        st.warning("Todas las URLs tienen poco tráfico")
        return None
    
    # Calcular tendencias
    merged['position_change'] = ((merged['position_previous'] - merged['position_current']) / merged['position_previous']) * 100
    merged['sessions_change'] = ((merged['sessions_current'] - merged['sessions_previous']) / merged['sessions_previous']) * 100
    
    # Normalizar métricas
    merged['normalized_traffic'] = (merged['sessions_current'] - merged['sessions_current'].min()) / (merged['sessions_current'].max() - merged['sessions_current'].min()) * 100
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

col1, col2 = st.columns(2)

with col1:
    gsc_file = st.file_uploader("📊 Google Search Console CSV", type=['csv'])
    
with col2:
    ga4_file = st.file_uploader("📈 Google Analytics 4 CSV", type=['csv'])

if gsc_file and ga4_file:
    if st.button("🚀 Analizar", type="primary"):
        with st.spinner("Analizando datos..."):
            try:
                # Leer GSC normal
                gsc_df = pd.read_csv(gsc_file, encoding='utf-8')
                
                # Leer GA4 saltando basura
                ga4_file.seek(0)
                lines = ga4_file.read().decode('utf-8').split('\n')
                
                # Encontrar primera línea con datos reales
                start_line = 0
                for i, line in enumerate(lines):
                    if line and not line.startswith('#') and not line.startswith('-') and ('landing' in line.lower() or 'page' in line.lower() or 'session' in line.lower()):
                        start_line = i
                        break
                
                # Crear CSV limpio
                clean_lines = lines[start_line:]
                clean_csv = '\n'.join(clean_lines)
                
                # Detectar delimitador
                delimiter = ',' if clean_csv.count(',') > clean_csv.count(';') else ';'
                
                # Leer con pandas
                ga4_df = pd.read_csv(StringIO(clean_csv), delimiter=delimiter, on_bad_lines='skip')
                
                results = process_data(gsc_df, ga4_df)
                
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
                            'bounce_rate': top_url['bounce_rate'],
                            'avg_duration': top_url['avg_duration']
                        }
                        insight = get_groq_insight(top_url['url_clean'], metrics)
                    
                    st.info(f"💡 **Insight IA:** {insight}")
                    
                    st.markdown("---")
                    st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias** con la versión Pro")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                
else:
    st.info("👆 Sube ambos archivos CSV para comenzar")
