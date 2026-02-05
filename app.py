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
    """Extrae metadata SEO de una URL con error handling robusto"""
    
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        
        if not url or url == 'https://' or len(url) < 10:
            raise ValueError("URL inválida")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            raise ValueError(f"No es HTML: {content_type}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ""
        
        # Headings
        h1_tags = []
        h2_tags = []
        h3_tags = []
        
        try:
            h1_tags = [h.get_text().strip() for h in soup.find_all('h1') if h.get_text().strip()][:20]
            h2_tags = [h.get_text().strip() for h in soup.find_all('h2') if h.get_text().strip()][:30]
            h3_tags = [h.get_text().strip() for h in soup.find_all('h3') if h.get_text().strip()][:30]
        except:
            pass
        
        # Schema markup
        schemas = []
        try:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    schema_data = json.loads(script.string)
                    schema_type = schema_data.get('@type', 'Unknown')
                    if isinstance(schema_type, list):
                        schemas.extend(schema_type)
                    else:
                        schemas.append(schema_type)
                except:
                    continue
        except:
            pass
        
        # FAQs
        faqs = []
        try:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    schema_data = json.loads(script.string)
                    if schema_data.get('@type') == 'FAQPage':
                        for entity in schema_data.get('mainEntity', []):
                            question = entity.get('name', '')
                            if question:
                                faqs.append(question)
                except:
                    continue
        except:
            pass
        
        # Word count
        words = 0
        try:
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            text = soup.get_text()
            words = len(text.split())
        except:
            pass
        
        # Images
        images_total = 0
        images_without_alt = 0
        try:
            images = soup.find_all('img')
            images_total = len(images)
            images_without_alt = len([img for img in images if not img.get('alt')])
        except:
            pass
        
        # Enlaces internos SOLO DEL CONTENIDO
        internal_links = 0
        if target_domain:
            try:
                content_area = None
                
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
                
                if not content_area:
                    content_area = soup.find('body')
                
                if content_area:
                    for unwanted in content_area.find_all(['nav', 'footer', 'header', 'aside']):
                        unwanted.decompose()
                    
                    all_links = content_area.find_all('a', href=True)
                    for link in all_links:
                        href = link['href']
                        if target_domain in href or (href.startswith('/') and not href.startswith('//')):
                            internal_links += 1
            except:
                pass
        
        return {
            'success': True,
            'url': url,
            'title': title_text[:200],
            'title_length': len(title_text),
            'description': description[:500],
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
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'url': url,
            'error': 'Timeout (>10s)',
            'title': '', 'title_length': 0, 'description': '', 'description_length': 0,
            'h1_count': 0, 'h1_tags': [], 'h2_count': 0, 'h2_tags': [],
            'h3_count': 0, 'h3_tags': [], 'word_count': 0,
            'images_total': 0, 'images_without_alt': 0,
            'schemas_count': 0, 'faqs_count': 0, 'internal_links': 0
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'url': url,
            'error': f'Error de red: {str(e)[:50]}',
            'title': '', 'title_length': 0, 'description': '', 'description_length': 0,
            'h1_count': 0, 'h1_tags': [], 'h2_count': 0, 'h2_tags': [],
            'h3_count': 0, 'h3_tags': [], 'word_count': 0,
            'images_total': 0, 'images_without_alt': 0,
            'schemas_count': 0, 'faqs_count': 0, 'internal_links': 0
        }
    except Exception as e:
        return {
            'success': False,
            'url': url,
            'error': str(e)[:100],
            'title': '', 'title_length': 0, 'description': '', 'description_length': 0,
            'h1_count': 0, 'h1_tags': [], 'h2_count': 0, 'h2_tags': [],
            'h3_count': 0, 'h3_tags': [], 'word_count': 0,
            'images_total': 0, 'images_without_alt': 0,
            'schemas_count': 0, 'faqs_count': 0, 'internal_links': 0
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

def get_google_top_10(keyword, debug=False):
    """Scrape top 10 con múltiples métodos de fallback"""
    
    # MÉTODO 1: Google con headers mejorados
    try:
        if debug:
            st.write("**🔍 Método 1: Google Search**")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Referer': 'https://www.google.com/',
            'DNT': '1'
        }
        
        url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&num=20&hl=es"
        
        if debug:
            st.write(f"URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        if debug:
            st.write(f"Status: {response.status_code}")
            st.write(f"Encoding: {response.encoding}")
            st.write("Primeros 500 caracteres:")
            st.code(response.text[:500])
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        
        selectors = [
            ('div', {'class': 'g'}),
            ('div', {'class': 'yuRUbf'}),
            ('div', {'data-sokoban-container': True}),
            ('a', {'jsname': 'UWckNb'})
        ]
        
        for tag, attrs in selectors:
            elements = soup.find_all(tag, attrs)
            if debug:
                st.write(f"Selector {tag} {attrs}: {len(elements)} encontrados")
            
            for elem in elements:
                link = elem.find('a', href=True) if tag == 'div' else elem
                if link:
                    href = link.get('href', '')
                    if href.startswith('/url?q='):
                        href = href.split('/url?q=')[1].split('&')[0]
                    
                    if (href.startswith('http') and 
                        'google.com' not in href and 
                        'youtube.com' not in href and
                        'gstatic.com' not in href):
                        
                        if href not in results:
                            results.append(href)
                            if debug:
                                st.write(f"✅ Encontrada: {href[:80]}")
            
            if len(results) >= 10:
                break
        
        if len(results) >= 3:
            if debug:
                st.success(f"✅ Google: {len(results)} URLs")
            return results[:10]
        
        if debug:
            st.warning(f"Google solo devolvió {len(results)} URLs, probando método 2...")
            
    except Exception as e:
        if debug:
            st.error(f"Error en Método 1: {str(e)}")
    
    # MÉTODO 2: DuckDuckGo
    try:
        if debug:
            st.write("**🦆 Método 2: DuckDuckGo**")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://html.duckduckgo.com/html/?q={keyword.replace(' ', '+')}"
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        
        for result in soup.find_all('a', class_='result__url'):
            href = result.get('href', '')
            if href.startswith('http'):
                if href not in results:
                    results.append(href)
                    if debug:
                        st.write(f"✅ Encontrada: {href[:80]}")
                if len(results) >= 10:
                    break
        
        if len(results) >= 3:
            if debug:
                st.success(f"✅ DuckDuckGo: {len(results)} URLs")
            return results[:10]
        
        if debug:
            st.warning(f"DuckDuckGo solo devolvió {len(results)} URLs, probando método 3...")
            
    except Exception as e:
        if debug:
            st.error(f"Error en Método 2: {str(e)}")
    
    # MÉTODO 3: Fallback para demo
    if debug:
        st.write("**⚠️ Método 3: Fallback con sitios populares**")
        st.warning("No se pudo hacer scraping. Usando sitios genéricos para demostración.")
    
    demo_urls = [
        "https://www.mayoclinic.org/",
        "https://medlineplus.gov/spanish/",
        "https://www.cdc.gov/spanish/",
        "https://www.who.int/es",
        "https://www.healthline.com/",
        "https://www.webmd.com/",
        "https://www.nih.gov/",
        "https://www.health.harvard.edu/",
        "https://www.nhs.uk/",
        "https://www.clevelandclinic.org/"
    ]
    
    return demo_urls[:10]

def process_gsc_data(df):
    
    df = df[~df.iloc[:, 0].astype(str).str.contains('Grand total|^total$', case=False, regex=True, na=False)]
    df = df[df.iloc[:, 0].notna()]
    
    if len(df) == 0:
        st.error("❌ Sin datos después de limpiar")
        return None
    
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
    
    df['url'] = df.iloc[:, 0]
    df['position_current'] = df[pos_cols[0]].apply(clean_number)
    df['position_previous'] = df[pos_cols[1]].apply(clean_number)
    df['clicks_current'] = df[click_cols[0]].apply(clean_number)
    df['clicks_previous'] = df[click_cols[1]].apply(clean_number)
    df['impressions_current'] = df[imp_cols[0]].apply(clean_number) if imp_cols else 0
    df['ctr_current'] = df[ctr_cols[0]].apply(clean_number) if ctr_cols else 0
    
    df = df[df['position_current'] > 0]
    df = df[(df['position_current'] >= 5) & (df['position_current'] <= 20)]
    
    if len(df) == 0:
        st.warning("⚠️ No hay URLs en rango 5-20")
        return None
    
    df = df[df['clicks_current'] > 0]
    avg_clicks = df['clicks_current'].mean()
    df = df[df['clicks_current'] >= (avg_clicks * 0.3)]
    
    if len(df) == 0:
        st.warning("⚠️ No hay URLs con suficiente tráfico")
        return None
    
    # Calcular cambios
    df['position_change'] = df['position_current'] - df['position_previous']
    df['clicks_change'] = ((df['clicks_current'] - df['clicks_previous']) / df['clicks_previous']) * 100
    
    # NUEVA FÓRMULA PRIORIZADA
    
    # 1. SCORE DE POSICIÓN (50%)
    df['position_score'] = (20 - df['position_current']) / 15 * 100
    
    # 2. SCORE DE TRÁFICO (30%)
    if df['clicks_current'].max() > df['clicks_current'].min():
        df['traffic_score'] = (df['clicks_current'] - df['clicks_current'].min()) / (df['clicks_current'].max() - df['clicks_current'].min()) * 100
    else:
        df['traffic_score'] = 50
    
    # 3. SCORE DE TENDENCIA (20%)
    df['trend_score'] = 50
    
    df.loc[df['position_change'] > 0, 'trend_score'] -= df['position_change'] * 5
    df.loc[df['clicks_change'] < 0, 'trend_score'] += df['clicks_change'] * 0.3
    df.loc[df['position_change'] < 0, 'trend_score'] += abs(df['position_change']) * 3
    df.loc[df['clicks_change'] > 0, 'trend_score'] += df['clicks_change'] * 0.2
    
    df['trend_score'] = df['trend_score'].clip(0, 100)
    
    # SCORE FINAL
    df['score'] = (df['position_score'] * 0.5) + (df['traffic_score'] * 0.3) + (df['trend_score'] * 0.2)
    
    # BONIFICACIONES
    df['fell_from_page1'] = (df['position_previous'] <= 10) & (df['position_current'] > 10)
    df.loc[df['fell_from_page1'], 'score'] += 30
    df.loc[df['position_change'] > 3, 'score'] += 15
    df.loc[df['clicks_change'] < -20, 'score'] += 10
    
    df = df.sort_values('score', ascending=False)
    
    return df

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
    if st.session_state.analysis_results is None:
        if st.button("🚀 Analizar", type="primary"):
            with st.spinner("Analizando datos..."):
                try:
                    gsc_df = pd.read_csv(gsc_file, encoding='utf-8', on_bad_lines='skip')
                    results = process_gsc_data(gsc_df)
                    
                    if results is None or len(results) == 0:
                        st.error("❌ No se encontraron oportunidades")
                    else:
                        st.session_state.analysis_results = results
                        st.session_state.top_url_data = results.iloc[0]
                        
                        top_url = st.session_state.top_url_data
                        target_domain = extract_domain(top_url['url'])
                        st.session_state.current_metadata = scrape_url_metadata(top_url['url'], target_domain)
                        
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    if st.session_state.analysis_results is not None:
        results = st.session_state.analysis_results
        top_url = st.session_state.top_url_data
        current_metadata = st.session_state.current_metadata
        
        st.success(f"✅ {len(results)} oportunidades encontradas")
        
        col_btn1, col_btn2 = st.columns([1, 4])
        
        with col_btn1:
            if st.button("🔄 Nuevo análisis"):
                st.session_state.analysis_results = None
                st.session_state.top_url_data = None
                st.session_state.current_metadata = None
                st.rerun()
        
        with col_btn2:
            st.link_button("💎 Comprar Versión Pro - Desbloquear Todas las URLs", "https://tudominio.com/checkout", type="primary")
        
        st.markdown("---")
        st.subheader("🏆 TOP Oportunidad")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Score", f"{top_url['score']:.1f}/100")
        
        with col2:
            change_emoji = "🔴" if top_url['position_change'] > 0 else "🟢" if top_url['position_change'] < 0 else "⚪"
            st.metric("Posición", 
                     f"{int(top_url['position_current'])} {change_emoji}", 
                     f"{top_url['position_change']:+.0f} posiciones")
        
        with col3:
            st.metric("Clicks", 
                     f"{int(top_url['clicks_current'])}", 
                     f"{top_url['clicks_change']:+.1f}%")
        
        with col4:
            st.metric("CTR", f"{top_url['ctr_current']:.1f}%")
        
        st.markdown(f"**URL:** `{top_url['url']}`")
        
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
            
            st.markdown("---")
            st.subheader("💡 Recomendaciones IA")
            
            with st.spinner("Generando análisis personalizado..."):
                metrics = {
                    'position': int(top_url['position_current']),
                    'position_change': f"{top_url['position_change']:+.0f}",
                    'clicks': int(top_url['clicks_current']),
                    'clicks_change': top_url['clicks_change'],
                    'impressions': int(top_url['impressions_current']),
                    'ctr': top_url['ctr_current']
                }
                insight = get_groq_insight(top_url['url'], metrics, current_metadata)
            
            st.info(insight)
            
            st.markdown("---")
            st.subheader("🔗 Recomendaciones de Enlaces Internos")
            
            internal_link_recs = recommend_internal_links(top_url['url'], results, n=3)
            
            if internal_link_recs:
                st.write(f"**Actual:** Tu página tiene {current_metadata['internal_links']} enlaces internos en el contenido.")
                st.write("**Sugerencia:** Añade enlaces a estas páginas de alto rendimiento:")
                
                for idx, rec in enumerate(internal_link_recs, 1):
                    st.write(f"{idx}. `{rec['url']}` (Posición: #{rec['position']}, Score: {rec['score']}/100)")
            
            st.markdown("---")
            st.subheader("📊 Comparativa vs Top 10 de Google")
            
            keyword_input = st.text_input(
                "Ingresa la keyword principal de esta URL:",
                placeholder="Ej: tipos de colirios con y sin receta"
            )
            
            if keyword_input:
                if st.button("🔍 Comparar con Top 10", type="primary"):
                    with st.spinner(f"Obteniendo top 10 para '{keyword_input}'..."):
                        top_10_urls = get_google_top_10(keyword_input, debug=debug_mode)
                    
                    if top_10_urls and len(top_10_urls) > 0:
                        with st.expander("🔗 URLs del Top 10 analizadas"):
                            for idx, url in enumerate(top_10_urls, 1):
                                st.write(f"{idx}. {url}")
                        
                        st.info(f"Analizando {len(top_10_urls)} URLs del top 10...")
                        
                        comparison_data = []
                        competitors_metadata = []
                        
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
                        
                        comparison_df = pd.DataFrame(comparison_data)
                        
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
                        
                        st.markdown("---")
                        st.subheader("📑 Recomendaciones de Headings para Optimizar")
                        
                        with st.spinner("Generando recomendaciones de estructura con IA..."):
                            competitors_h2_sample = []
                            for meta in competitors_metadata[:5]:
                                if meta['success'] and meta.get('h2_tags'):
                                    competitors_h2_sample.extend(meta['h2_tags'][:3])
                            
                            heading_prompt = f"""Eres un experto SEO. Analiza esta página y recomienda una estructura de headings optimizada.

**Keyword objetivo:** {keyword_input}

**Headings actuales:**
- H1: {', '.join(current_metadata['h1_tags'][:2]) if current_metadata['h1_tags'] else 'Ninguno'}
- H2 actuales ({current_metadata['h2_count']}): {', '.join(current_metadata['h2_tags'][:5]) if current_metadata['h2_tags'] else 'Ninguno'}

**Promedio competidores:**
- H2 promedio: {avg_row['H2']:.0f}
- Ejemplos de H2 en competidores: {', '.join(competitors_h2_sample[:8]) if competitors_h2_sample else 'No disponible'}

**Genera:**

1. **H1 recomendado** (1 solo, optimizado para la keyword)

2. **5-8 H2 recomendados** que deberías tener, priorizados por:
   - Intención de búsqueda del usuario
   - Cobertura de subtemas importantes
   - Keywords relacionadas long-tail

3. **3 H3 de ejemplo** para uno de los H2

Formato:
**H1:**
[Tu H1 optimizado]

**H2 (ordenados por prioridad):**
1. [H2 principal]
2. [H2 secundario]
...

**H3 de ejemplo para H2 #1:**
- [H3 ejemplo 1]
- [H3 ejemplo 2]
- [H3 ejemplo 3]"""

                            try:
                                client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                                
                                chat_completion = client.chat.completions.create(
                                    messages=[{"role": "user", "content": heading_prompt}],
                                    model="llama-3.3-70b-versatile",
                                    temperature=0.4,
                                    max_tokens=800
                                )
                                
                                heading_recommendations = chat_completion.choices[0].message.content
                                st.markdown(heading_recommendations)
                                
                            except Exception as e:
                                st.error(f"Error generando recomendaciones: {str(e)}")
                    
                    else:
                        st.error("❌ No se pudo obtener el top 10.")
        
        else:
            st.warning("⚠️ No se pudo analizar la página")
        
        st.markdown("---")
        
        with st.expander("ℹ️ ¿Cómo se calcula la prioridad?"):
            st.markdown("""
            **Fórmula de Score:**
            - 🎯 **Posición actual (50%)**: URLs en posiciones 5-10 tienen mayor prioridad que 11-20
            - 📈 **Tráfico actual (30%)**: URLs con más clicks tienen mayor prioridad
            - 📉 **Tendencias (20%)**: Penaliza pérdidas de posición y tráfico
            
            **Bonificaciones especiales:**
            - 🚨 **+30 puntos**: Si cayó de página 1 (posiciones 1-10) a página 2 (11-20)
            - ⚠️ **+15 puntos**: Si perdió más de 3 posiciones
            - 📊 **+10 puntos**: Si perdió más del 20% de tráfico
            
            **Resultado:** URLs que cayeron de página 1 o perdieron tráfico significativo aparecen primero.
            """)
        
        st.markdown("---")
        
        col_upgrade1, col_upgrade2 = st.columns([3, 1])
        
        with col_upgrade1:
            st.info(f"🔓 **Desbloquea las otras {len(results)-1} URLs prioritarias con la versión Pro**")
        
        with col_upgrade2:
            st.link_button("💎 Comprar Pro", "https://tudominio.com/checkout", type="primary")
                
else:
    st.info("👆 Sube tu CSV de Google Search Console para comenzar")
    
    with st.expander("📖 ¿Cómo exportar desde GSC?"):
        st.markdown("""
        ### Tutorial paso a paso:
        
        1. Ve a **Google Search Console** → **Performance** → **Pages**
        2. Click en **Compare** (arriba derecha)
        3. Selecciona: **Últimos 28 días** vs **28 días anteriores**
        4. Click en **Export** → **Download CSV**
        
        ---
        
        ### 📺 Video Tutorial (próximamente)
        
        """)
        
        # Placeholder para video de YouTube
        # Descomenta y reemplaza VIDEO_ID cuando tengas el video
        # st.markdown("[![Tutorial GSC](https://img.youtube.com/vi/VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=VIDEO_ID)")
        
        st.info("💡 **Tip:** Asegúrate de comparar periodos iguales para obtener datos precisos de tendencias.")
        
        # Aquí puedes agregar imágenes locales cuando las tengas
        # st.image("tutorial_1.png", caption="Paso 1: Performance → Pages")
        # st.image("tutorial_2.png", caption="Paso 2: Compare")
        # st.image("tutorial_3.png", caption="Paso 3: Export CSV")
