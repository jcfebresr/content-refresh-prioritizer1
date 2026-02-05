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
    if not url.startswith('http'):
        url = 'https://' + url
    
    match = re.search(r'https?://([^/]+)', url)
    if match:
        return match.group(1).replace('www.', '')
    return None

def scrape_url_metadata(url, target_domain=None):
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
        
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""
        
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ""
        
        h1_tags = []
        h2_tags = []
        h3_tags = []
        
        try:
            h1_tags = [h.get_text().strip() for h in soup.find_all('h1') if h.get_text().strip()][:20]
            h2_tags = [h.get_text().strip() for h in soup.find_all('h2') if h.get_text().strip()][:30]
            h3_tags = [h.get_text().strip() for h in soup.find_all('h3') if h.get_text().strip()][:30]
        except:
            pass
        
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
        
        words = 0
        try:
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            text = soup.get_text()
            words = len(text.split())
        except:
            pass
        
        images_total = 0
        images_without_alt = 0
        try:
            images = soup.find_all('img')
            images_total = len(images)
            images_without_alt = len([img for img in images if not img.get('alt')])
        except:
            pass
        
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
        
    except:
        return {
            'success': False, 'url': url, 'error': 'Error',
            'title': '', 'title_length': 0, 'description': '', 'description_length': 0,
            'h1_count': 0, 'h1_tags': [], 'h2_count': 0, 'h2_tags': [],
            'h3_count': 0, 'h3_tags': [], 'word_count': 0,
            'images_total': 0, 'images_without_alt': 0,
            'schemas_count': 0, 'faqs_count': 0, 'internal_links': 0
        }

def recommend_internal_links(current_url, all_results_df, n=3):
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
    """Scrape top 10 con intentos mejorados"""
    
    # Intentar con DuckDuckGo primero (más permisivo)
    try:
        if debug:
            st.write("**🦆 Intentando DuckDuckGo**")
        
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
            if href.startswith('http') and href not in results:
                results.append(href)
                if len(results) >= 10:
                    break
        
        if len(results) >= 5:
            if debug:
                st.success(f"✅ DuckDuckGo: {len(results)} URLs")
            return results[:10]
            
    except Exception as e:
        if debug:
            st.error(f"DuckDuckGo falló: {str(e)}")
    
    # Intentar Google
    try:
        if debug:
            st.write("**🔍 Intentando Google**")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en-US,en;q=0.8',
            'Referer': 'https://www.google.com/',
            'DNT': '1'
        }
        
        url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&num=20"
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Probar múltiples selectores
        for selector in [
            soup.find_all('div', class_='g'),
            soup.find_all('div', class_='yuRUbf'),
            soup.find_all('a', jsname='UWckNb')
        ]:
            for elem in selector:
                link = elem.find('a', href=True) if elem.name == 'div' else elem
                if link:
                    href = link.get('href', '')
                    
                    # Limpiar /url?q=
                    if '/url?q=' in href:
                        href = href.split('/url?q=')[1].split('&')[0]
                    
                    # Validar
                    if (href.startswith('http') and 
                        'google.com' not in href and 
                        'youtube.com' not in href and
                        href not in results):
                        results.append(href)
            
            if len(results) >= 10:
                break
        
        if len(results) >= 5:
            if debug:
                st.success(f"✅ Google: {len(results)} URLs")
            return results[:10]
            
    except Exception as e:
        if debug:
            st.error(f"Google falló: {str(e)}")
    
    # Si todo falla, retornar lista vacía (NO fallback falso)
    return []

def process_gsc_data(df):
    df = df[~df.iloc[:, 0].astype(str).str.contains('Grand total|^total$', case=False, regex=True, na=False)]
    df = df[df.iloc[:, 0].notna()]
    
    if len(df) == 0:
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
        return None
    
    df = df[df['clicks_current'] > 0]
    avg_clicks = df['clicks_current'].mean()
    df = df[df['clicks_current'] >= (avg_clicks * 0.3)]
    
    if len(df) == 0:
        return None
    
    df['position_change'] = df['position_current'] - df['position_previous']
    df['clicks_change'] = ((df['clicks_current'] - df['clicks_previous']) / df['clicks_previous']) * 100
    
    df['position_score'] = (20 - df['position_current']) / 15 * 100
    
    if df['clicks_current'].max() > df['clicks_current'].min():
        df['traffic_score'] = (df['clicks_current'] - df['clicks_current'].min()) / (df['clicks_current'].max() - df['clicks_current'].min()) * 100
    else:
        df['traffic_score'] = 50
    
    df['trend_score'] = 50
    df.loc[df['position_change'] > 0, 'trend_score'] -= df['position_change'] * 5
    df.loc[df['clicks_change'] < 0, 'trend_score'] += df['clicks_change'] * 0.3
    df.loc[df['position_change'] < 0, 'trend_score'] += abs(df['position_change']) * 3
    df.loc[df['clicks_change'] > 0, 'trend_score'] += df['clicks_change'] * 0.2
    df['trend_score'] = df['trend_score'].clip(0, 100)
    
    df['score'] = (df['position_score'] * 0.5) + (df['traffic_score'] * 0.3) + (df['trend_score'] * 0.2)
    
    df['fell_from_page1'] = (df['position_previous'] <= 10) & (df['position_current'] > 10)
    df.loc[df['fell_from_page1'], 'score'] += 30
    df.loc[df['position_change'] > 3, 'score'] += 15
    df.loc[df['clicks_change'] < -20, 'score'] += 10
    
    df = df.sort_values('score', ascending=False)
    
    return df

# UI
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero basándote en Google Search Console")

# Session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'selected_url' not in st.session_state:
    st.session_state.selected_url = None

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
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # FASE 1: Mostrar tabla de URLs
    if st.session_state.analysis_results is not None:
        results = st.session_state.analysis_results
        
        st.success(f"✅ {len(results)} oportunidades encontradas")
        
        if st.button("🔄 Nuevo análisis"):
            st.session_state.analysis_results = None
            st.session_state.selected_url = None
            st.rerun()
        
        st.markdown("---")
        st.subheader("📋 URLs Priorizadas")
        
        # Preparar tabla para mostrar
        display_df = pd.DataFrame({
            '#': range(1, len(results) + 1),
            'Score': results['score'].round(1),
            'URL': results['url'].str[:60] + '...',
            'Posición': results['position_current'].astype(int),
            'Δ Pos': results['position_change'].astype(int),
            'Clicks': results['clicks_current'].astype(int),
            'Δ Clicks (%)': results['clicks_change'].round(1),
            'CTR (%)': results['ctr_current'].round(1)
        })
        
        # Mostrar tabla interactiva
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.info("💡 **Selecciona una URL** de la lista escribiendo su número para ver el análisis completo")
        
        # Input para seleccionar URL
        selected_index = st.number_input(
            "Ingresa el número (#) de la URL que quieres analizar:",
            min_value=1,
            max_value=len(results),
            value=1,
            step=1
        )
        
        if st.button("🔍 Analizar URL seleccionada", type="primary"):
            st.session_state.selected_url = results.iloc[selected_index - 1]
            st.rerun()
        
        # FASE 2: Análisis profundo de URL seleccionada
        if st.session_state.selected_url is not None:
            selected = st.session_state.selected_url
            
            st.markdown("---")
            st.markdown("---")
            st.subheader("🎯 Análisis Profundo")
            
            # Header con métricas principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Score", f"{selected['score']:.1f}/100")
            
            with col2:
                # Color corregido: +pos = ROJO (empeoró), -pos = VERDE (mejoró)
                pos_change = int(selected['position_change'])
                if pos_change > 0:
                    pos_color = "🔴"  # Empeoró
                elif pos_change < 0:
                    pos_color = "🟢"  # Mejoró
                else:
                    pos_color = "⚪"  # Sin cambio
                
                st.metric(
                    "Posición", 
                    f"{int(selected['position_current'])} {pos_color}", 
                    f"{pos_change:+d} posiciones"
                )
            
            with col3:
                st.metric(
                    "Clicks", 
                    f"{int(selected['clicks_current'])}", 
                    f"{selected['clicks_change']:+.1f}%"
                )
            
            with col4:
                st.metric("CTR", f"{selected['ctr_current']:.1f}%")
            
            st.markdown(f"**URL:** `{selected['url']}`")
            
            # Scraping de metadata
            with st.spinner("Analizando metadata de la página..."):
                target_domain = extract_domain(selected['url'])
                metadata = scrape_url_metadata(selected['url'], target_domain)
            
            if metadata['success']:
                st.markdown("---")
                st.subheader("🔍 Análisis On-Page")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Word Count", metadata['word_count'])
                    st.metric("H1", metadata['h1_count'])
                    st.metric("H2", metadata['h2_count'])
                
                with col2:
                    title_status = "✅" if 30 <= metadata['title_length'] <= 60 else "⚠️"
                    st.metric("Title Length", f"{metadata['title_length']} {title_status}")
                    
                    desc_status = "✅" if 120 <= metadata['description_length'] <= 160 else "⚠️"
                    st.metric("Meta Desc Length", f"{metadata['description_length']} {desc_status}")
                    
                    st.metric("Images sin ALT", metadata['images_without_alt'])
                
                with col3:
                    st.metric("Schemas", metadata['schemas_count'])
                    st.metric("FAQs", metadata['faqs_count'])
                    st.metric("Enlaces Internos", metadata['internal_links'])
                
                # Recomendaciones IA
                st.markdown("---")
                st.subheader("💡 Recomendaciones IA")
                
                with st.spinner("Generando análisis personalizado..."):
                    metrics = {
                        'position': int(selected['position_current']),
                        'position_change': f"{int(selected['position_change']):+d}",
                        'clicks': int(selected['clicks_current']),
                        'clicks_change': selected['clicks_change'],
                        'impressions': int(selected['impressions_current']),
                        'ctr': selected['ctr_current']
                    }
                    insight = get_groq_insight(selected['url'], metrics, metadata)
                
                st.info(insight)
                
                # Enlaces internos
                st.markdown("---")
                st.subheader("🔗 Recomendaciones de Enlaces Internos")
                
                internal_link_recs = recommend_internal_links(selected['url'], results, n=3)
                
                if internal_link_recs:
                    st.write(f"**Actual:** Tu página tiene {metadata['internal_links']} enlaces internos en el contenido.")
                    st.write("**Sugerencia:** Añade enlaces a estas páginas de alto rendimiento:")
                    
                    for idx, rec in enumerate(internal_link_recs, 1):
                        st.write(f"{idx}. `{rec['url']}` (Posición: #{rec['position']}, Score: {rec['score']}/100)")
                
                # Comparativa con Top 10
                st.markdown("---")
                st.subheader("📊 Comparativa vs Top 10 de Google")
                
                # Tabs para método automático o manual
                tab1, tab2 = st.tabs(["🤖 Scraping Automático", "✍️ Input Manual"])
                
                with tab1:
                    st.markdown("**Intenta obtener automáticamente las URLs del top 10 de Google**")
                    
                    keyword_input = st.text_input(
                        "Ingresa la keyword principal de esta URL:",
                        placeholder="Ej: how to build app with bubble",
                        key="keyword_auto"
                    )
                    
                    if keyword_input:
                        if st.button("🔍 Obtener Top 10 automáticamente", type="primary"):
                            with st.spinner(f"Obteniendo top 10 para '{keyword_input}'..."):
                                top_10_urls = get_google_top_10(keyword_input, debug=False)
                            
                            if top_10_urls and len(top_10_urls) >= 5:
                                st.session_state['top_10_urls'] = top_10_urls
                                st.session_state['keyword'] = keyword_input
                                st.success(f"✅ Se obtuvieron {len(top_10_urls)} URLs")
                                
                                with st.expander("🔗 URLs obtenidas"):
                                    for idx, url in enumerate(top_10_urls, 1):
                                        st.write(f"{idx}. {url}")
                                
                                if st.button("▶️ Analizar estas URLs", type="primary", key="analyze_auto"):
                                    st.session_state['start_analysis'] = True
                                    st.rerun()
                            else:
                                st.error("❌ No se pudo obtener el top 10 automáticamente")
                                st.warning("💡 Google está bloqueando el scraping. Usa el método **Input Manual** en la pestaña de al lado.")
                
                with tab2:
                    st.markdown("**Pega manualmente las URLs del top 10 de Google**")
                    st.info("💡 Abre Google en modo incógnito, busca tu keyword, y copia las URLs de los primeros 10 resultados")
                    
                    keyword_manual = st.text_input(
                        "Keyword:",
                        placeholder="Ej: how to build app with bubble",
                        key="keyword_manual"
                    )
                    
                    urls_manual = st.text_area(
                        "Pega las URLs del top 10 (una por línea):",
                        placeholder="https://example.com/page1\nhttps://example.com/page2\n...",
                        height=200,
                        key="urls_manual"
                    )
                    
                    if keyword_manual and urls_manual:
                        if st.button("▶️ Analizar estas URLs", type="primary", key="analyze_manual"):
                            # Procesar URLs
                            urls = [url.strip() for url in urls_manual.split('\n') if url.strip() and url.startswith('http')]
                            
                            if len(urls) >= 3:
                                st.session_state['top_10_urls'] = urls[:10]
                                st.session_state['keyword'] = keyword_manual
                                st.session_state['start_analysis'] = True
                                st.success(f"✅ {len(urls[:10])} URLs listas para analizar")
                                st.rerun()
                            else:
                                st.error("❌ Necesitas al menos 3 URLs válidas")
                
                # Ejecutar análisis si está activado
                if st.session_state.get('start_analysis'):
                    top_10_urls = st.session_state.get('top_10_urls', [])
                    keyword = st.session_state.get('keyword', '')
                    
                    if top_10_urls and keyword:
                        st.markdown("---")
                        st.info(f"Analizando {len(top_10_urls)} URLs para la keyword: **{keyword}**")
                        
                        comparison_data = []
                        competitors_metadata = []
                        
                        comparison_data.append({
                            'Posición': f"#{int(selected['position_current'])} (TU URL)",
                            'Title Length': metadata['title_length'],
                            'Desc Length': metadata['description_length'],
                            'Word Count': metadata['word_count'],
                            'H1': metadata['h1_count'],
                            'H2': metadata['h2_count'],
                            'H3': metadata['h3_count'],
                            'Schemas': metadata['schemas_count'],
                            'FAQs': metadata['faqs_count']
                        })
                        
                        progress_bar = st.progress(0)
                        for idx, url in enumerate(top_10_urls[:10], 1):
                            with st.spinner(f"Analizando posición #{idx}: {url[:50]}..."):
                                comp_metadata = scrape_url_metadata(url)
                                competitors_metadata.append(comp_metadata)
                                time.sleep(2)
                                
                                comparison_data.append({
                                    'Posición': f"#{idx}",
                                    'Title Length': comp_metadata['title_length'],
                                    'Desc Length': comp_metadata['description_length'],
                                    'Word Count': comp_metadata['word_count'],
                                    'H1': comp_metadata['h1_count'],
                                    'H2': comp_metadata['h2_count'],
                                    'H3': comp_metadata['h3_count'],
                                    'Schemas': comp_metadata['schemas_count'],
                                    'FAQs': comp_metadata['faqs_count']
                                })
                                
                                progress_bar.progress(idx / len(top_10_urls[:10]))
                        
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
                        
                        # Recomendaciones de headings con IA
                        st.markdown("---")
                        st.subheader("📑 Recomendaciones de Headings para Optimizar")
                        
                        with st.spinner("Generando recomendaciones de estructura con IA..."):
                            competitors_h2_sample = []
                            for meta in competitors_metadata[:5]:
                                if meta['success'] and meta.get('h2_tags'):
                                    competitors_h2_sample.extend(meta['h2_tags'][:3])
                            
                            heading_prompt = f"""Eres un experto SEO. Analiza esta página y recomienda una estructura de headings optimizada.

**Keyword objetivo:** {keyword}

**Headings actuales:**
- H1: {', '.join(metadata['h1_tags'][:2]) if metadata['h1_tags'] else 'Ninguno'}
- H2 actuales ({metadata['h2_count']}): {', '.join(metadata['h2_tags'][:5]) if metadata['h2_tags'] else 'Ninguno'}

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
                        
                        # Limpiar session state
                        st.session_state['start_analysis'] = False
                        
                        if st.button("🔄 Nueva comparativa"):
                            st.session_state['top_10_urls'] = None
                            st.session_state['keyword'] = None
                            st.rerun()
            else:
                st.warning("⚠️ No se pudo analizar la página")
            
            # Botón para volver a la lista
            st.markdown("---")
            if st.button("⬅️ Volver a la lista de URLs"):
                st.session_state.selected_url = None
                st.rerun()
        
        # Expander con info de cálculo
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
            
            **Colores de posición:**
            - 🔴 Rojo: Empeoró (perdió posiciones)
            - 🟢 Verde: Mejoró (ganó posiciones)
            - ⚪ Blanco: Sin cambios
            """)
                
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
        
        💡 **Tip:** Asegúrate de comparar periodos iguales para obtener datos precisos de tendencias.
        """)
