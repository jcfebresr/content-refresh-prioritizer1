import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
import requests
from bs4 import BeautifulSoup
import json
import time
import re

st.set_page_config(page_title="Content Refresh Prioritizer", page_icon="🎯", layout="wide")

def get_groq_insight(url, metrics, metadata):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
        prompt = f"""Eres un experto SEO. Analiza esta URL y genera 3 recomendaciones ESPECÍFICAS y ACCIONABLES en español:

URL: {url}

**Datos GSC:**
- Posición: {metrics['position']} (cambio: {metrics['position_change']})
- Clicks: {metrics['clicks']} (cambio: {metrics['clicks_change']}%)
- CTR: {metrics['ctr']:.1f}%

**Datos On-Page:**
- Title: "{metadata['title']}" ({metadata['title_length']} caracteres)
- Meta Description: ({metadata['description_length']} caracteres)
- Word Count: {metadata['word_count']} palabras
- H1: {metadata['h1_count']}, H2: {metadata['h2_count']}, H3: {metadata['h3_count']}
- Schemas: {metadata['schemas_count']}
- FAQs: {metadata['faqs_count']}
- Enlaces internos en contenido: {metadata['internal_links']}

Genera 3 recomendaciones concretas priorizadas por impacto. Cada una en 1 línea, formato:
1. [Acción específica con número/dato]
2. [Acción específica con número/dato]
3. [Acción específica con número/dato]"""

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=300
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error generando insight: {str(e)}"

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

def extract_domain(url):
    """Extrae el dominio de una URL"""
    if not url.startswith('http'):
        url = 'https://' + url
    
    match = re.search(r'https?://([^/]+)', url)
    if match:
        return match.group(1).replace('www.', '')
    return None

def scrape_url_metadata(url, target_domain=None):
    """Extrae metadata SEO de una URL"""
    
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ""
        
        # Headings
        h1_tags = [h.get_text().strip() for h in soup.find_all('h1')]
        h2_tags = [h.get_text().strip() for h in soup.find_all('h2')]
        h3_tags = [h.get_text().strip() for h in soup.find_all('h3')]
        
        # Schema markup
        schemas = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                schema_data = json.loads(script.string)
                schema_type = schema_data.get('@type', 'Unknown')
                if isinstance(schema_type, list):
                    schemas.extend(schema_type)
                else:
                    schemas.append(schema_type)
            except:
                pass
        
        # FAQs
        faqs = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                schema_data = json.loads(script.string)
                if schema_data.get('@type') == 'FAQPage':
                    for entity in schema_data.get('mainEntity', []):
                        question = entity.get('name', '')
                        faqs.append(question)
            except:
                pass
        
        # Word count
        text = soup.get_text()
        words = len(text.split())
        
        # Images
        images = soup.find_all('img')
        images_total = len(images)
        images_without_alt = len([img for img in images if not img.get('alt')])
        
        # Enlaces internos SOLO DEL CONTENIDO
        internal_links = 0
        if target_domain:
            # Intentar encontrar el contenido principal
            content_area = None
            
            # Buscar por orden de prioridad
            content_selectors = [
                soup.find('article'),
                soup.find('main'),
                soup.find('div', class_=re.compile(r'content|post|entry|article', re.I)),
                soup.find('div', id=re.compile(r'content|post|entry|article', re.I))
            ]
            
            for selector in content_selectors:
                if selector:
                    content_area = selector
                    break
            
            # Si no encontramos área específica, usar body pero excluir nav/footer/header/aside
            if not content_area:
                content_area = soup.find('body')
            
            if content_area:
                # Excluir elementos de navegación/footer
                for unwanted in content_area.find_all(['nav', 'footer', 'header', 'aside']):
                    unwanted.decompose()
                
                # Contar enlaces internos en el contenido limpio
                all_links = content_area.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    # Es interno si contiene el dominio o empieza con /
                    if target_domain in href or (href.startswith('/') and not href.startswith('//')):
                        internal_links += 1
        
        return {
            'success': True,
            'url': url,
            'title': title_text,
            'title_length': len(title_text),
            'description': description,
            'description_length': len(description),
            'h1_count': len(h1_tags),
            'h1_tags': h1_tags,
            'h2_count': len(h2_tags),
            'h2_tags': h2_tags,
            'h3_count': len(h3_tags),
            'h3_tags': h3_tags,
            'word_count': words,
            'images_total': images_total,
            'images_without_alt': images_without_alt,
            'schemas': schemas,
            'schemas_count': len(schemas),
            'faqs_count': len(faqs),
            'faqs': faqs,
            'internal_links': internal_links
        }
        
    except Exception as e:
        return {
            'success': False,
            'url': url,
            'error': str(e),
            'title': '',
            'title_length': 0,
            'description': '',
            'description_length': 0,
            'h1_count': 0,
            'h1_tags': [],
            'h2_count': 0,
            'h2_tags': [],
            'h3_count': 0,
            'h3_tags': [],
            'word_count': 0,
            'images_total': 0,
            'images_without_alt': 0,
            'schemas_count': 0,
            'faqs_count': 0,
            'internal_links': 0
        }

def recommend_internal_links(current_url, all_results_df, n=3):
    """Recomienda enlaces internos basados en otras URLs del GSC"""
    
    other_urls = all_results_df[all_results_df['url'] != current_url].copy()
    
    if len(other_urls) == 0:
        return []
    
    other_urls = other_urls.sort_values('score', ascending=False)
    
    recommendations = []
    for idx, row in other_urls.head(n).iterrows():
        recommendations.append({
            'url': row['url'],
            'position': int(row['position_current']),
            'clicks': int(row['clicks_current']),
            'score': round(row['score'], 1)
        })
    
    return recommendations

get_google_top_10

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
    
    # Ordenar
    df['losing_traffic'] = df['clicks_change'] < 0
    df = df.sort_values(['score', 'losing_traffic'], ascending=[False, False])
    
    return df

# UI
# UI
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero basándote en Google Search Console")

# Debug mode
debug_mode = st.sidebar.checkbox("🐛 Modo Debug", value=False)

# Inicializar session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'top_url_data' not in st.session_state:
    st.session_state.top_url_data = None
if 'current_metadata' not in st.session_state:
    st.session_state.current_metadata = None

gsc_file = st.file_uploader("📊 Google Search Console CSV", type=['csv'])

if gsc_file:
    # Solo analizar si no hay resultados en session_state
    if st.session_state.analysis_results is None:
        if st.button("🚀 Analizar", type="primary"):
            with st.spinner("Analizando datos..."):
                try:
                    gsc_df = pd.read_csv(gsc_file, encoding='utf-8', on_bad_lines='skip')
                    results = process_gsc_data(gsc_df)
                    
                    if results is None or len(results) == 0:
                        st.error("❌ No se encontraron oportunidades")
                    else:
                        # Guardar en session state
                        st.session_state.analysis_results = results
                        st.session_state.top_url_data = results.iloc[0]
                        
                        # Analizar metadata
                        top_url = st.session_state.top_url_data
                        target_domain = extract_domain(top_url['url'])
                        st.session_state.current_metadata = scrape_url_metadata(top_url['url'], target_domain)
                        
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Mostrar resultados si existen
    if st.session_state.analysis_results is not None:
        results = st.session_state.analysis_results
        top_url = st.session_state.top_url_data
        current_metadata = st.session_state.current_metadata
        
        st.success(f"✅ {len(results)} oportunidades encontradas")
        
        # Botón para reiniciar análisis
        if st.button("🔄 Nuevo análisis"):
            st.session_state.analysis_results = None
            st.session_state.top_url_data = None
            st.session_state.current_metadata = None
            st.rerun()
        
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
        
        # Análisis On-Page
        if current_metadata and current_metadata['success']:
            st.markdown("---")
            st.subheader("🔍 Análisis On-Page")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Word Count", current_metadata['word_count'])
                st.metric("H1", current_metadata['h1_count'])
                st.metric("H2", current_metadata['h2_count'])
            
            with col2:
                title_status = "✅" if 30 <= current_metadata['title_length'] <= 60 else "⚠️"
                st.metric("Title Length", f"{current_metadata['title_length']} {title_status}")
                
                desc_status = "✅" if 120 <= current_metadata['description_length'] <= 160 else "⚠️"
                st.metric("Meta Desc Length", f"{current_metadata['description_length']} {desc_status}")
                
                st.metric("Images sin ALT", current_metadata['images_without_alt'])
            
            with col3:
                st.metric("Schemas", current_metadata['schemas_count'])
                st.metric("FAQs", current_metadata['faqs_count'])
                st.metric("Enlaces Internos", current_metadata['internal_links'])
            
            # Insight IA
            st.markdown("---")
            st.subheader("💡 Recomendaciones IA")
            
            with st.spinner("Generando análisis personalizado..."):
                metrics = {
                    'position': int(top_url['position_current']),
                    'position_change': f"{top_url['position_change']:+.1f}%",
                    'clicks': int(top_url['clicks_current']),
                    'clicks_change': top_url['clicks_change'],
                    'impressions': int(top_url['impressions_current']),
                    'ctr': top_url['ctr_current']
                }
                insight = get_groq_insight(top_url['url'], metrics, current_metadata)
            
            st.info(insight)
            
            # Enlaces internos
            st.markdown("---")
            st.subheader("🔗 Recomendaciones de Enlaces Internos")
            
            internal_link_recs = recommend_internal_links(top_url['url'], results, n=3)
            
            if internal_link_recs:
                st.write(f"**Actual:** Tu página tiene {current_metadata['internal_links']} enlaces internos en el contenido.")
                st.write("**Sugerencia:** Añade enlaces a estas páginas de alto rendimiento:")
                
                for idx, rec in enumerate(internal_link_recs, 1):
                    st.write(f"{idx}. `{rec['url']}` (Posición: #{rec['position']}, Score: {rec['score']}/100)")
            
            # Comparativa con Top 10
            st.markdown("---")
            st.subheader("📊 Comparativa vs Top 10 de Google")
            
            # Input de keyword SIN auto-rerun
            keyword_input = st.text_input(
                "Ingresa la keyword principal de esta URL:",
                placeholder="Ej: tipos de colirios con y sin receta"
            )
            
           # Botón para iniciar comparativa
            if keyword_input:
                if st.button("🔍 Comparar con Top 10", type="primary"):
                    with st.spinner(f"Obteniendo top 10 para '{keyword_input}'..."):
                        top_10_urls = get_google_top_10(keyword_input, debug=debug_mode)
                    
                    if top_10_urls and len(top_10_urls) > 0:
                        st.info(f"Analizando {len(top_10_urls)} URLs del top 10...")
                        
                        comparison_data = []
                        competitors_metadata = []
                        
                        # Tu URL
                        comparison_data.append({
                            'Posición': f"#{int(top_url['position_current'])} (TU URL)",
                            'Title Length': current_metadata['title_length'],
                            'Desc Length': current_metadata['description_length'],
                            'Word Count': current_metadata['word_count'],
                            'H1': current_metadata['h1_count'],
                            'H2': current_metadata['h2_count'],
                            'H3': current_metadata['h3_count'],
                            'Schemas': current_metadata['schemas_count'],
                            'FAQs': current_metadata['faqs_count']
                        })
                        
                        # Top 10
                        progress_bar = st.progress(0)
                        for idx, url in enumerate(top_10_urls[:10], 1):
                            with st.spinner(f"Analizando posición #{idx}..."):
                                metadata = scrape_url_metadata(url)
                                competitors_metadata.append(metadata)
                                time.sleep(2)
                                
                                comparison_data.append({
                                    'Posición': f"#{idx}",
                                    'Title Length': metadata['title_length'],
                                    'Desc Length': metadata['description_length'],
                                    'Word Count': metadata['word_count'],
                                    'H1': metadata['h1_count'],
                                    'H2': metadata['h2_count'],
                                    'H3': metadata['h3_count'],
                                    'Schemas': metadata['schemas_count'],
                                    'FAQs': metadata['faqs_count']
                                })
                                
                                progress_bar.progress(idx / 10)
                        
                        progress_bar.empty()
                        
                        # Tabla de métricas
                        comparison_df = pd.DataFrame(comparison_data)
                        
                        # Calcular promedios
                        avg_row = {
                            'Posición': '📊 PROMEDIO TOP 10',
                            'Title Length': int(comparison_df.iloc[1:]['Title Length'].mean()),
                            'Desc Length': int(comparison_df.iloc[1:]['Desc Length'].mean()),
                            'Word Count': int(comparison_df.iloc[1:]['Word Count'].mean()),
                            'H1': round(comparison_df.iloc[1:]['H1'].mean(), 1),
                            'H2': round(comparison_df.iloc[1:]['H2'].mean(), 1),
                            'H3': round(comparison_df.iloc[1:]['H3'].mean(), 1),
                            'Schemas': round(comparison_df.iloc[1:]['Schemas'].mean(), 1),
                            'FAQs': round(comparison_df.iloc[1:]['FAQs'].mean(), 1)
                        }
                        
                        comparison_df = pd.concat([comparison_df, pd.DataFrame([avg_row])], ignore_index=True)
                        
                        st.dataframe(comparison_df, use_container_width=True)
                        
                        # Comparativa de Headings
                        st.markdown("---")
                        st.subheader("📑 Comparativa de Headings: Tu URL vs Competidores")
                        
                        tab1, tab2, tab3 = st.tabs(["H1", "H2", "H3"])
                        
                        with tab1:
                            st.write("**Tus H1:**")
                            if current_metadata['h1_tags']:
                                for h1 in current_metadata['h1_tags']:
                                    st.write(f"- {h1}")
                            else:
                                st.warning("⚠️ No tienes H1")
                            
                            st.write("**H1 de Competidores (Top 5):**")
                            for idx, meta in enumerate(competitors_metadata[:5], 1):
                                if meta['success'] and meta.get('h1_tags'):
                                    st.write(f"**Posición #{idx}:**")
                                    for h1 in meta['h1_tags'][:2]:
                                        st.write(f"- {h1}")
                        
                        with tab2:
                            st.write("**Tus H2 (primeros 10):**")
                            if current_metadata['h2_tags']:
                                for h2 in current_metadata['h2_tags'][:10]:
                                    st.write(f"- {h2}")
                            else:
                                st.warning("⚠️ No tienes H2")
                            
                            st.write("**H2 de Competidores (Top 3, primeros 5 H2 c/u):**")
                            for idx, meta in enumerate(competitors_metadata[:3], 1):
                                if meta['success'] and meta.get('h2_tags'):
                                    st.write(f"**Posición #{idx}:**")
                                    for h2 in meta['h2_tags'][:5]:
                                        st.write(f"- {h2}")
                        
                        with tab3:
                            st.write("**Tus H3 (primeros 10):**")
                            if current_metadata['h3_tags']:
                                for h3 in current_metadata['h3_tags'][:10]:
                                    st.write(f"- {h3}")
                            else:
                                st.info("No tienes H3")
                            
                            st.write("**Promedio H3 en competidores:**")
                            avg_h3 = sum([len(m.get('h3_tags', [])) for m in competitors_metadata]) / len(competitors_metadata)
                            st.metric("Promedio H3 en Top 10", f"{avg_h3:.1f}")
                        
                        # Recomendaciones
                        st.markdown("---")
                        st.subheader("💡 GAPs vs Competencia")
                        
                        recs = []
                        
                        avg_words = avg_row['Word Count']
                        if current_metadata['word_count'] < avg_words * 0.8:
                            recs.append(f"📝 **Contenido corto:** Tienes {current_metadata['word_count']} palabras vs {avg_words} promedio. Amplía +{int(avg_words - current_metadata['word_count'])} palabras.")
                        
                        avg_h2 = avg_row['H2']
                        if current_metadata['h2_count'] < avg_h2 * 0.7:
                            recs.append(f"📑 **H2 insuficientes:** {current_metadata['h2_count']} H2 vs {avg_h2:.0f} promedio. Añade {int(avg_h2 - current_metadata['h2_count'])} H2 más.")
                        
                        avg_h3 = avg_row['H3']
                        if current_metadata['h3_count'] < avg_h3 * 0.7:
                            recs.append(f"📑 **H3 insuficientes:** {current_metadata['h3_count']} H3 vs {avg_h3:.0f} promedio. Añade subsecciones.")
                        
                        avg_schemas = avg_row['Schemas']
                        if current_metadata['schemas_count'] < avg_schemas:
                            recs.append(f"🏷️ **Schema:** {current_metadata['schemas_count']} schemas vs {avg_schemas:.0f} promedio. Añade más markup.")
                        
                        avg_faqs = avg_row['FAQs']
                        if current_metadata['faqs_count'] == 0 and avg_faqs > 0:
                            recs.append(f"❓ **FAQs:** 0 FAQs vs {avg_faqs:.0f} promedio. Añade sección FAQ con schema.")
                        
                        if not recs:
                            st.success("✅ Tu página está bien optimizada")
                        else:
                            for rec in recs:
                                st.warning(rec)
                    
                    else:
                        st.error("❌ No se pudo obtener el top 10 de Google.")
                        st.info("💡 Intenta con otra keyword.")
            
            with st.expander("📄 Ver detalles completos de tu URL"):
                st.write("**Title:**", current_metadata['title'])
                st.write("**Meta Description:**", current_metadata['description'])
                
                if current_metadata['h1_tags']:
                    st.write("**H1:**")
                    for h1 in current_metadata['h1_tags']:
                        st.write(f"- {h1}")
                
                if current_metadata['h2_tags']:
                    st.write("**H2 (primeros 10):**")
                    for h2 in current_metadata['h2_tags'][:10]:
                        st.write(f"- {h2}")
                
                if current_metadata['schemas']:
                    st.write("**Schema Markup:**")
                    st.write(", ".join(current_metadata['schemas']))
                
                if current_metadata['faqs']:
                    st.write("**FAQs encontradas:**")
                    for faq in current_metadata['faqs']:
                        st.write(f"- {faq}")
        
        else:
            st.warning("⚠️ No se pudo analizar la página")
        
        st.markdown("---")
        st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias con la versión Pro**")
                
else:
    st.info("👆 Sube tu archivo CSV de Google Search Console para comenzar")
    
    with st.expander("📖 ¿Cómo exportar desde GSC?"):
        st.markdown("""
        1. Ve a **Performance → Pages**
        2. Click en **Compare** (arriba derecha)
        3. Selecciona: Últimos 28 días vs 28 días anteriores
        4. Click **Export** → CSV
        """)
