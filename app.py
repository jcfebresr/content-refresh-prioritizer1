import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Content Refresh Prioritizer", page_icon="🎯", layout="wide")

# Selector de idioma
language = st.sidebar.selectbox("🌐 Language / Idioma", ["Español", "English"])

# Input para API Key
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 Groq API Key")

if language == "Español":
    st.sidebar.markdown("""
    **Necesitas tu propia API Key de Groq (gratuita)**
    
    1. Ve a [console.groq.com](https://console.groq.com)
    2. Crea una cuenta (gratis)
    3. Genera tu API Key
    4. Pégala aquí abajo 👇
    """)
    api_key_input = st.sidebar.text_input(
        "Tu Groq API Key:",
        type="password",
        placeholder="gsk_...",
        help="Tu API key es privada y no se guarda"
    )
else:
    st.sidebar.markdown("""
    **You need your own Groq API Key (free)**
    
    1. Go to [console.groq.com](https://console.groq.com)
    2. Create an account (free)
    3. Generate your API Key
    4. Paste it here 👇
    """)
    api_key_input = st.sidebar.text_input(
        "Your Groq API Key:",
        type="password",
        placeholder="gsk_...",
        help="Your API key is private and not saved"
    )

if api_key_input:
    st.session_state['groq_api_key'] = api_key_input

# Textos según idioma
if language == "Español":
    TEXTS = {
        'title': '🎯 Content Refresh Prioritizer',
        'subtitle': 'Descubre qué páginas optimizar primero basándote en Google Search Console',
        'upload': '📊 Google Search Console CSV',
        'analyze_btn': '🚀 Analizar',
        'analyzing': 'Analizando datos...',
        'success': 'oportunidades encontradas',
        'new_analysis': '🔄 Nuevo análisis',
        'prioritized_urls': '📋 URLs Priorizadas',
        'select_url': '💡 **Selecciona una URL** de la lista escribiendo su número para ver el análisis completo',
        'enter_number': 'Ingresa el número (#) de la URL que quieres analizar:',
        'analyze_selected': '🔍 Analizar URL seleccionada',
        'deep_analysis': '🎯 Análisis Profundo',
        'on_page': '🔍 Análisis On-Page',
        'ai_recommendations': '💡 Recomendaciones IA',
        'generating': 'Generando análisis personalizado...',
        'internal_links': '🔗 Recomendaciones de Enlaces Internos',
        'current': 'Actual',
        'suggestion': 'Sugerencia',
        'your_page_has': 'Tu página tiene',
        'internal_links_text': 'enlaces internos en el contenido.',
        'add_links_to': 'Añade enlaces a estas páginas de alto rendimiento:',
        'comparativa': '📊 Comparativa vs Top 10 de Google',
        'auto_scraping': '🤖 Scraping Automático',
        'manual_input': '✍️ Input Manual',
        'auto_desc': '**Intenta obtener automáticamente las URLs del top 10 de Google**',
        'enter_keyword': 'Ingresa la keyword principal de esta URL:',
        'keyword_placeholder': 'Ej: how to build app with bubble',
        'get_top10': '🔍 Obtener Top 10 automáticamente',
        'getting_top10': 'Obteniendo top 10 para',
        'urls_obtained': 'Se obtuvieron',
        'obtained_urls': 'URLs obtenidas',
        'analyze_urls': '▶️ Analizar estas URLs',
        'scraping_blocked': 'No se pudo obtener el top 10 automáticamente',
        'use_manual': 'Google está bloqueando el scraping. Usa el método **Input Manual** en la pestaña de al lado.',
        'manual_desc': '**Pega manualmente las URLs del top 10 de Google**',
        'manual_tip': '💡 Abre Google en modo incógnito, busca tu keyword, y copia las URLs de los primeros 10 resultados',
        'keyword': 'Keyword:',
        'paste_urls': 'Pega las URLs del top 10 (una por línea):',
        'urls_ready': 'URLs listas para analizar',
        'need_3_urls': 'Necesitas al menos 3 URLs válidas',
        'analyzing_urls': 'Analizando',
        'for_keyword': 'URLs para la keyword:',
        'analyzing_position': 'Analizando posición',
        'heading_recommendations': '📑 Recomendaciones de Headings Faltantes',
        'heading_structure': '📑 Estructura de Encabezados de la Competencia',
        'heading_structure_desc': 'Analiza cómo estructuran su contenido los competidores del Top 10',
        'generating_headings': 'Generando análisis de headings faltantes...',
        'new_comparativa': '🔄 Nueva comparativa',
        'back_to_list': '⬅️ Volver a la lista de URLs',
        'priority_calculation': '¿Cómo se calcula la prioridad?',
        'tutorial': '¿Cómo exportar desde GSC?',
        'upload_csv': 'Sube tu CSV de Google Search Console para comenzar',
        'fell': 'Empeoró',
        'rose': 'Mejoró',
        'pos': 'pos',
        'no_change': 'Sin cambio',
        'api_key_required': '⚠️ Necesitas ingresar tu Groq API Key en el sidebar para usar las recomendaciones con IA',
        'api_key_invalid': '❌ API Key inválida. Verifica que la copiaste correctamente desde console.groq.com'
    }
else:
    TEXTS = {
        'title': '🎯 Content Refresh Prioritizer',
        'subtitle': 'Discover which pages to optimize first based on Google Search Console',
        'upload': '📊 Google Search Console CSV',
        'analyze_btn': '🚀 Analyze',
        'analyzing': 'Analyzing data...',
        'success': 'opportunities found',
        'new_analysis': '🔄 New analysis',
        'prioritized_urls': '📋 Prioritized URLs',
        'select_url': '💡 **Select a URL** from the list by entering its number to see the full analysis',
        'enter_number': 'Enter the number (#) of the URL you want to analyze:',
        'analyze_selected': '🔍 Analyze selected URL',
        'deep_analysis': '🎯 Deep Analysis',
        'on_page': '🔍 On-Page Analysis',
        'ai_recommendations': '💡 AI Recommendations',
        'generating': 'Generating personalized analysis...',
        'internal_links': '🔗 Internal Links Recommendations',
        'current': 'Current',
        'suggestion': 'Suggestion',
        'your_page_has': 'Your page has',
        'internal_links_text': 'internal links in content.',
        'add_links_to': 'Add links to these high-performance pages:',
        'comparativa': '📊 Comparison vs Google Top 10',
        'auto_scraping': '🤖 Automatic Scraping',
        'manual_input': '✍️ Manual Input',
        'auto_desc': '**Try to automatically get the top 10 URLs from Google**',
        'enter_keyword': 'Enter the main keyword for this URL:',
        'keyword_placeholder': 'Ex: how to build app with bubble',
        'get_top10': '🔍 Get Top 10 automatically',
        'getting_top10': 'Getting top 10 for',
        'urls_obtained': 'URLs obtained:',
        'obtained_urls': 'Obtained URLs',
        'analyze_urls': '▶️ Analyze these URLs',
        'scraping_blocked': 'Could not get top 10 automatically',
        'use_manual': 'Google is blocking scraping. Use the **Manual Input** method in the next tab.',
        'manual_desc': '**Manually paste the top 10 URLs from Google**',
        'manual_tip': '💡 Open Google in incognito mode, search your keyword, and copy the URLs of the first 10 results',
        'keyword': 'Keyword:',
        'paste_urls': 'Paste top 10 URLs (one per line):',
        'urls_ready': 'URLs ready to analyze',
        'need_3_urls': 'You need at least 3 valid URLs',
        'analyzing_urls': 'Analyzing',
        'for_keyword': 'URLs for keyword:',
        'analyzing_position': 'Analyzing position',
        'heading_recommendations': '📑 Missing Headings Recommendations',
        'heading_structure': '📑 Competitor Heading Structure',
        'heading_structure_desc': 'Analyze how Top 10 competitors structure their content',
        'generating_headings': 'Generating missing headings analysis...',
        'new_comparativa': '🔄 New comparison',
        'back_to_list': '⬅️ Back to URL list',
        'priority_calculation': 'How is priority calculated?',
        'tutorial': 'How to export from GSC?',
        'upload_csv': 'Upload your Google Search Console CSV to start',
        'fell': 'Worsened',
        'rose': 'Improved',
        'pos': 'pos',
        'no_change': 'No change',
        'api_key_required': '⚠️ You need to enter your Groq API Key in the sidebar to use AI recommendations',
        'api_key_invalid': '❌ Invalid API Key. Verify you copied it correctly from console.groq.com'
    }

def get_random_user_agent():
    """Retorna un User-Agent aleatorio para evitar bloqueos"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    ]
    return random.choice(user_agents)

def get_groq_insight(url, metrics, metadata, lang, api_key):
    if not api_key:
        return TEXTS['api_key_required']
    
    try:
        client = Groq(api_key=api_key)
        
        if lang == "Español":
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
        else:
            prompt = f"""You are an SEO expert. Analyze this URL and generate 3 SPECIFIC and ACTIONABLE recommendations in English:

URL: {url}

**GSC Data:**
- Position: {metrics['position']} (change: {metrics['position_change']})
- Clicks: {metrics['clicks']} (change: {metrics['clicks_change']}%)
- CTR: {metrics['ctr']:.1f}%

**On-Page Data:**
- Title: "{metadata['title']}" ({metadata['title_length']} characters)
- Meta Description: ({metadata['description_length']} characters)
- Word Count: {metadata['word_count']} words
- H1: {metadata['h1_count']}, H2: {metadata['h2_count']}, H3: {metadata['h3_count']}
- Schemas: {metadata['schemas_count']}
- FAQs: {metadata['faqs_count']}
- Internal links in content: {metadata['internal_links']}

Generate 3 concrete recommendations prioritized by impact. Each in 1 line, format:
1. [Specific action with number/data]
2. [Specific action with number/data]
3. [Specific action with number/data]"""

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=300
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        if "invalid" in str(e).lower() or "unauthorized" in str(e).lower():
            return TEXTS['api_key_invalid']
        return f"Error: {str(e)}"

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
    """Scraping mejorado con User-Agent aleatorio y mejor extracción de headings"""
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        
        if not url or url == 'https://' or len(url) < 10:
            raise ValueError("URL inválida")
        
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        response.raise_for_status()
        
        if response.encoding is None:
            response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Limpiar antes de extraer
        for script in soup(['script', 'style', 'nav', 'footer', 'aside', 'form']):
            script.decompose()
        
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""
        
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ""
        
        # Extracción mejorada de headers
        h1_tags = [h.get_text(" ", strip=True) for h in soup.find_all('h1') if h.get_text(strip=True)]
        h2_tags = [h.get_text(" ", strip=True) for h in soup.find_all('h2') if h.get_text(strip=True)]
        h3_tags = [h.get_text(" ", strip=True) for h in soup.find_all('h3') if h.get_text(strip=True)]
        
        # Word count
        text = soup.get_text(" ", strip=True)
        words = len(text.split())
        
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
        
    except Exception as e:
        return {
            'success': False, 'url': url, 'error': str(e),
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
    """Mejorado con User-Agent aleatorio"""
    try:
        headers = {
            'User-Agent': get_random_user_agent()
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
            return results[:10]
            
    except:
        pass
    
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en-US,en;q=0.8',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Cookie': 'CONSENT=YES+cb.20210720-07-p0.en+FX+417;'
        }
        
        url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&num=15"
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for selector in [
            soup.find_all('div', class_='g'),
            soup.find_all('div', class_='yuRUbf'),
            soup.find_all('a', jsname='UWckNb')
        ]:
            for elem in selector:
                link = elem.find('a', href=True) if elem.name == 'div' else elem
                if link:
                    href = link.get('href', '')
                    
                    if '/url?q=' in href:
                        href = href.split('/url?q=')[1].split('&')[0]
                    
                    if (href.startswith('http') and 
                        'google.com' not in href and 
                        'youtube.com' not in href and
                        href not in results):
                        results.append(href)
            
            if len(results) >= 10:
                break
        
        if len(results) >= 5:
            return results[:10]
            
    except:
        pass
    
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
st.title(TEXTS['title'])
st.markdown(TEXTS['subtitle'])

# Session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'selected_url' not in st.session_state:
    st.session_state.selected_url = None

gsc_file = st.file_uploader(TEXTS['upload'], type=['csv'])

if gsc_file:
    if st.session_state.analysis_results is None:
        if st.button(TEXTS['analyze_btn'], type="primary"):
            with st.spinner(TEXTS['analyzing']):
                try:
                    gsc_df = pd.read_csv(gsc_file, encoding='utf-8', on_bad_lines='skip')
                    results = process_gsc_data(gsc_df)
                    
                    if results is None or len(results) == 0:
                        st.error("❌ No opportunities found")
                    else:
                        st.session_state.analysis_results = results
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    if st.session_state.analysis_results is not None:
        results = st.session_state.analysis_results
        
        st.success(f"✅ {len(results)} {TEXTS['success']}")
        
        if st.button(TEXTS['new_analysis']):
            st.session_state.analysis_results = None
            st.session_state.selected_url = None
            st.rerun()
        
        st.markdown("---")
        st.subheader(TEXTS['prioritized_urls'])
        
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
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.info(TEXTS['select_url'])
        
        selected_index = st.number_input(
            TEXTS['enter_number'],
            min_value=1,
            max_value=len(results),
            value=1,
            step=1
        )
        
        if st.button(TEXTS['analyze_selected'], type="primary"):
            st.session_state.selected_url = results.iloc[selected_index - 1]
            st.rerun()
        
        if st.session_state.selected_url is not None:
            selected = st.session_state.selected_url
            
            st.markdown("---")
            st.markdown("---")
            st.subheader(TEXTS['deep_analysis'])
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Score", f"{selected['score']:.1f}/100")
            
            with col2:
                pos_change = int(selected['position_change'])
                
                if pos_change > 0:
                    pos_color = "🔴"
                    pos_text = f"{TEXTS['fell']} {pos_change} {TEXTS['pos']}"
                elif pos_change < 0:
                    pos_color = "🟢"
                    pos_text = f"{TEXTS['rose']} {abs(pos_change)} {TEXTS['pos']}"
                else:
                    pos_color = "⚪"
                    pos_text = TEXTS['no_change']
                
                st.metric(
                    "Posición", 
                    f"{int(selected['position_current'])} {pos_color}", 
                    pos_text
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
            
            with st.spinner(f"{TEXTS['analyzing']}..."):
                target_domain = extract_domain(selected['url'])
                metadata = scrape_url_metadata(selected['url'], target_domain)
            
            if metadata['success']:
                st.markdown("---")
                st.subheader(TEXTS['on_page'])
                
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
                
                st.markdown("---")
                st.subheader(TEXTS['ai_recommendations'])
                
                user_api_key = st.session_state.get('groq_api_key', '')
                
                if not user_api_key:
                    st.warning(TEXTS['api_key_required'])
                else:
                    with st.spinner(TEXTS['generating']):
                        metrics = {
                            'position': int(selected['position_current']),
                            'position_change': f"{int(selected['position_change']):+d}",
                            'clicks': int(selected['clicks_current']),
                            'clicks_change': selected['clicks_change'],
                            'impressions': int(selected['impressions_current']),
                            'ctr': selected['ctr_current']
                        }
                        insight = get_groq_insight(selected['url'], metrics, metadata, language, user_api_key)
                    
                    st.info(insight)
                
                st.markdown("---")
                st.subheader(TEXTS['internal_links'])
                
                internal_link_recs = recommend_internal_links(selected['url'], results, n=3)
                
                if internal_link_recs:
                    st.write(f"**{TEXTS['current']}:** {TEXTS['your_page_has']} {metadata['internal_links']} {TEXTS['internal_links_text']}")
                    st.write(f"**{TEXTS['suggestion']}:** {TEXTS['add_links_to']}")
                    
                    for idx, rec in enumerate(internal_link_recs, 1):
                        st.write(f"{idx}. `{rec['url']}` (Posición: #{rec['position']}, Score: {rec['score']}/100)")
                
                st.markdown("---")
                st.subheader(TEXTS['comparativa'])
                
                tab1, tab2 = st.tabs([TEXTS['auto_scraping'], TEXTS['manual_input']])
                
                with tab1:
                    st.markdown(TEXTS['auto_desc'])
                    
                    keyword_input = st.text_input(
                        TEXTS['enter_keyword'],
                        placeholder=TEXTS['keyword_placeholder'],
                        key="keyword_auto"
                    )
                    
                    if keyword_input:
                        if st.button(TEXTS['get_top10'], type="primary"):
                            with st.spinner(f"{TEXTS['getting_top10']} '{keyword_input}'..."):
                                top_10_urls = get_google_top_10(keyword_input)
                            
                            if top_10_urls and len(top_10_urls) >= 5:
                                st.session_state['top_10_urls'] = top_10_urls
                                st.session_state['keyword'] = keyword_input
                                st.success(f"✅ {TEXTS['urls_obtained']} {len(top_10_urls)} URLs")
                                
                                with st.expander(f"🔗 {TEXTS['obtained_urls']}"):
                                    for idx, url in enumerate(top_10_urls, 1):
                                        st.write(f"{idx}. {url}")
                                
                                if st.button(TEXTS['analyze_urls'], type="primary", key="analyze_auto"):
                                    st.session_state['start_analysis'] = True
                                    st.rerun()
                            else:
                                st.error(f"❌ {TEXTS['scraping_blocked']}")
                                st.warning(f"💡 {TEXTS['use_manual']}")
                
                with tab2:
                    st.markdown(TEXTS['manual_desc'])
                    st.info(TEXTS['manual_tip'])
                    
                    keyword_manual = st.text_input(
                        f"{TEXTS['keyword']}",
                        placeholder=TEXTS['keyword_placeholder'],
                        key="keyword_manual"
                    )
                    
                    urls_manual = st.text_area(
                        TEXTS['paste_urls'],
                        placeholder="https://example.com/page1\nhttps://example.com/page2\n...",
                        height=200,
                        key="urls_manual"
                    )
                    
                    if keyword_manual and urls_manual:
                        if st.button(TEXTS['analyze_urls'], type="primary", key="analyze_manual"):
                            urls = [url.strip() for url in urls_manual.split('\n') if url.strip() and url.startswith('http')]
                            
                            if len(urls) >= 3:
                                st.session_state['top_10_urls'] = urls[:10]
                                st.session_state['keyword'] = keyword_manual
                                st.session_state['start_analysis'] = True
                                st.success(f"✅ {len(urls[:10])} {TEXTS['urls_ready']}")
                                st.rerun()
                            else:
                                st.error(f"❌ {TEXTS['need_3_urls']}")
                
                # ANÁLISIS PARALELO DE COMPETIDORES
                if st.session_state.get('start_analysis'):
                    top_10_urls = st.session_state.get('top_10_urls', [])
                    keyword = st.session_state.get('keyword', '')
                    
                    if top_10_urls and keyword:
                        st.markdown("---")
                        st.info(f"{TEXTS['analyzing_urls']} {len(top_10_urls)} {TEXTS['for_keyword']} **{keyword}**")
                        
                        # Barra de progreso
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        competitors_metadata = []
                        
                        # EJECUCIÓN PARALELA
                        def fetch_url(url):
                            return scrape_url_metadata(url)
                        
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            future_to_url = {executor.submit(fetch_url, url): url for url in top_10_urls[:10]}
                            
                            completed_count = 0
                            for future in as_completed(future_to_url):
                                data = future.result()
                                competitors_metadata.append(data)
                                
                                completed_count += 1
                                progress = completed_count / len(top_10_urls[:10])
                                progress_bar.progress(progress)
                                status_text.text(f"Analizando: {data['url'][:40]}... ({completed_count}/{len(top_10_urls[:10])})")
                        
                        status_text.empty()
                        progress_bar.empty()
                        
                        # Reordenar para mantener orden original
                        competitors_metadata.sort(key=lambda x: top_10_urls.index(x['url']) if x['url'] in top_10_urls else 999)
                        
                        # Tabla comparativa
                        comparison_data = []
                        
                        comparison_data.append({
                            'Posición': f"#{int(selected['position_current'])} (TU URL)",
                            'Title': metadata['title'],
                            'H1': metadata['h1_count'],
                            'H2': metadata['h2_count'],
                            'H3': metadata['h3_count'],
                            'Words': metadata['word_count']
                        })
                        
                        for idx, meta in enumerate(competitors_metadata):
                            if meta['success']:
                                comparison_data.append({
                                    'Posición': f"#{idx+1}",
                                    'Title': meta['title'],
                                    'H1': meta['h1_count'],
                                    'H2': meta['h2_count'],
                                    'H3': meta['h3_count'],
                                    'Words': meta['word_count']
                                })
                        
                        comparison_df = pd.DataFrame(comparison_data)
                        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
                        
                        # VISUALIZADOR DE ESTRUCTURA DE HEADINGS
                        st.markdown("---")
                        st.subheader(TEXTS['heading_structure'])
                        st.markdown(TEXTS['heading_structure_desc'])
                        
                        tabs = st.tabs([f"#{i+1}" for i in range(len(competitors_metadata))])
                        
                        for i, tab in enumerate(tabs):
                            with tab:
                                comp = competitors_metadata[i]
                                if comp['success']:
                                    st.markdown(f"**URL:** [{comp['url']}]({comp['url']})")
                                    st.markdown(f"**Title:** {comp['title']}")
                                    
                                    col_h1, col_structure = st.columns([1, 3])
                                    
                                    with col_h1:
                                        st.info(f"**Word Count:** {comp['word_count']}")
                                        st.markdown("### H1")
                                        if comp['h1_tags']:
                                            for h1 in comp['h1_tags']:
                                                st.write(f"• {h1}")
                                        else:
                                            st.warning("No H1 found")
                                    
                                    with col_structure:
                                        st.markdown("### Estructura H2 y H3")
                                        if not comp['h2_tags'] and not comp['h3_tags']:
                                            st.warning("No se detectaron H2 o H3.")
                                        
                                        for h2 in comp['h2_tags']:
                                            st.markdown(f"**H2: {h2}**")
                                        
                                        if comp['h3_tags']:
                                            st.markdown("---")
                                            st.caption("Subtemas (H3):")
                                            for h3 in comp['h3_tags']:
                                                st.markdown(f"- *{h3}*")
                                else:
                                    st.error(f"No se pudo analizar esta URL: {comp.get('error', 'Error desconocido')}")
                        
                        # Recomendaciones de headings faltantes
                        st.markdown("---")
                        st.subheader(TEXTS['heading_recommendations'])
                        
                        user_api_key = st.session_state.get('groq_api_key', '')
                        
                        if not user_api_key:
                            st.warning(TEXTS['api_key_required'])
                        else:
                            with st.spinner(TEXTS['generating_headings']):
                                all_competitor_h2 = []
                                for meta in competitors_metadata:
                                    if meta['success'] and meta.get('h2_tags'):
                                        all_competitor_h2.extend(meta['h2_tags'])
                                
                                current_h2 = set([h.lower() for h in metadata['h2_tags']])
                                
                                missing_h2_candidates = []
                                for h2 in all_competitor_h2:
                                    h2_lower = h2.lower()
                                    if h2_lower not in current_h2:
                                        if h2 not in missing_h2_candidates:
                                            missing_h2_candidates.append(h2)
                                
                                if language == "Español":
                                    heading_prompt = f"""Eres un experto SEO. Analiza los headings FALTANTES en esta página comparando con la competencia.

**Keyword objetivo:** {keyword}

**H2 ACTUALES en la página (YA EXISTEN, NO recomendar):**
{', '.join(metadata['h2_tags']) if metadata['h2_tags'] else 'Ninguno'}

**H2 que tienen los COMPETIDORES pero TÚ NO TIENES:**
{', '.join(missing_h2_candidates[:15]) if missing_h2_candidates else 'Los competidores no tienen H2 adicionales relevantes'}

**INSTRUCCIÓN CRÍTICA:** 
Solo recomienda H2 que:
1. Los competidores SÍ tienen
2. Tú NO tienes actualmente
3. Son relevantes para la keyword "{keyword}"

**NO recomiendes H2 que ya existen en la lista de "H2 ACTUALES".**

Genera:
**H2 FALTANTES recomendados (5-8 máximo):**
1. [H2 que tienen competidores pero tú no]
2. [H2 que tienen competidores pero tú no]
...

**Justificación:**
Explica brevemente por qué estos H2 son importantes para cubrir la intención de búsqueda."""
                                else:
                                    heading_prompt = f"""You are an SEO expert. Analyze the MISSING headings on this page compared to competitors.

**Target keyword:** {keyword}

**CURRENT H2s on the page (ALREADY EXIST, DO NOT recommend):**
{', '.join(metadata['h2_tags']) if metadata['h2_tags'] else 'None'}

**H2s that COMPETITORS have but YOU DON'T:**
{', '.join(missing_h2_candidates[:15]) if missing_h2_candidates else 'Competitors do not have additional relevant H2s'}

**CRITICAL INSTRUCTION:** 
Only recommend H2s that:
1. Competitors DO have
2. You DON'T currently have
3. Are relevant to the keyword "{keyword}"

**DO NOT recommend H2s that already exist in the "CURRENT H2s" list.**

Generate:
**MISSING H2s recommended (5-8 maximum):**
1. [H2 competitors have but you don't]
2. [H2 competitors have but you don't]
...

**Justification:**
Briefly explain why these H2s are important to cover search intent."""

                                try:
                                    client = Groq(api_key=user_api_key)
                                    
                                    chat_completion = client.chat.completions.create(
                                        messages=[{"role": "user", "content": heading_prompt}],
                                        model="llama-3.3-70b-versatile",
                                        temperature=0.4,
                                        max_tokens=800
                                    )
                                    
                                    heading_recommendations = chat_completion.choices[0].message.content
                                    st.markdown(heading_recommendations)
                                    
                                except Exception as e:
                                    if "invalid" in str(e).lower() or "unauthorized" in str(e).lower():
                                        st.error(TEXTS['api_key_invalid'])
                                    else:
                                        st.error(f"Error: {str(e)}")
                        
                        st.session_state['start_analysis'] = False
                        
                        if st.button(TEXTS['new_comparativa']):
                            st.session_state['top_10_urls'] = None
                            st.session_state['keyword'] = None
                            st.rerun()
            else:
                st.warning("⚠️ Could not analyze the page")
            
            st.markdown("---")
            if st.button(TEXTS['back_to_list']):
                st.session_state.selected_url = None
                st.rerun()
        
        with st.expander(f"ℹ️ {TEXTS['priority_calculation']}"):
            if language == "Español":
                st.markdown("""
                **Fórmula de Score:**
                - 🎯 **Posición actual (50%)**: URLs en posiciones 5-10 tienen mayor prioridad que 11-20
                - 📈 **Tráfico actual (30%)**: URLs con más clicks tienen mayor prioridad
                - 📉 **Tendencias (20%)**: Penaliza pérdidas de posición y tráfico
                
                **Bonificaciones especiales:**
                - 🚨 **+30 puntos**: Si cayó de página 1 (posiciones 1-10) a página 2 (11-20)
                - ⚠️ **+15 puntos**: Si perdió más de 3 posiciones
                - 📊 **+10 puntos**: Si perdió más del 20% de tráfico
                
                **Indicadores de posición:**
                - 🟢 Verde "Mejoró X pos": La posición BAJÓ en número (ej: de 12 a 8) = MEJOR ranking
                - 🔴 Rojo "Empeoró X pos": La posición SUBIÓ en número (ej: de 8 a 12) = PEOR ranking
                - ⚪ Blanco: Sin cambios
                
                **Recuerda:** En Google, posición 1 es la mejor, posición 100 es la peor.
                """)
            else:
                st.markdown("""
                **Score Formula:**
                - 🎯 **Current position (50%)**: URLs in positions 5-10 have higher priority than 11-20
                - 📈 **Current traffic (30%)**: URLs with more clicks have higher priority
                - 📉 **Trends (20%)**: Penalizes position and traffic losses
                
                **Special bonuses:**
                - 🚨 **+30 points**: If dropped from page 1 (positions 1-10) to page 2 (11-20)
                - ⚠️ **+15 points**: If lost more than 3 positions
                - 📊 **+10 points**: If lost more than 20% traffic
                
                **Position indicators:**
                - 🟢 Green "Improved X pos": Position number DECREASED (ex: from 12 to 8) = BETTER ranking
                - 🔴 Red "Worsened X pos": Position number INCREASED (ex: from 8 to 12) = WORSE ranking
                - ⚪ White: No change
                
                **Remember:** In Google, position 1 is best, position 100 is worst.
                """)
                
else:
    st.info(f"👆 {TEXTS['upload_csv']}")
    
    with st.expander(f"📖 {TEXTS['tutorial']}", expanded=True):
        if language == "Español":
            st.markdown("""
            ### 📋 Tutorial paso a paso para exportar datos de Google Search Console
            
            #### **Paso 1: Accede a Google Search Console**
            - Ve a [search.google.com/search-console](https://search.google.com/search-console)
            - Selecciona tu propiedad (sitio web)
            
            #### **Paso 2: Navega a Pages**
            - En el menú lateral izquierdo, haz click en **"Performance"** (Rendimiento)
            - Haz click en la pestaña **"Pages"** (Páginas) en la parte superior
            
            #### **Paso 3: Configura la comparación de fechas**
            - En la parte superior, verás el selector de fechas
            - Haz click en el selector de fechas actual (ej: "Last 3 months")
            - Selecciona: **"Last 28 days"** (Últimos 28 días)
            - Activa la opción **"Compare"** (Comparar)
            - En el segundo selector que aparece, elige: **"Previous period"** (Período anterior)
            - Esto comparará los últimos 28 días con los 28 días anteriores
            - Haz click en **"Apply"** (Aplicar)
            
            #### **Paso 4: Exporta los datos**
            - En la esquina superior derecha de la tabla, haz click en el ícono de **exportar** (📥)
            - Selecciona **"Download CSV"** (Descargar CSV)
            - El archivo se descargará con el nombre: **"Pages.csv"** o similar
            
            #### **Paso 5: Sube el archivo aquí**
            - Arrastra el archivo **"Pages.csv"** al área de carga arriba ☝️
            - O haz click en "Browse files" para seleccionarlo desde tu computadora
            
            ---
            
            ### 💡 Tips importantes:
            
            ✅ **Asegúrate de:**
            - Estar en la pestaña **"Pages"** (no en "Queries" o "Countries")
            - Activar la opción **"Compare"** para ver cambios entre períodos
            - Seleccionar períodos de **igual duración** (28 días vs 28 días)
            - Exportar el archivo en formato **CSV** (no Excel)
            
            ❌ **Errores comunes:**
            - Exportar desde "Queries" en lugar de "Pages"
            - No activar la comparación (botón "Compare")
            - Usar períodos de diferente duración (ej: 28 días vs 3 meses)
            - Exportar sin datos suficientes (necesitas tráfico en tu sitio)
            
            ---
            
            ### 🎥 ¿Necesitas ayuda visual?
            
            Si tienes dudas, busca en YouTube: **"How to export GSC pages data"**
            """)
        else:
            st.markdown("""
            ### 📋 Step-by-step tutorial to export Google Search Console data
            
            #### **Step 1: Access Google Search Console**
            - Go to [search.google.com/search-console](https://search.google.com/search-console)
            - Select your property (website)
            
            #### **Step 2: Navigate to Pages**
            - In the left sidebar menu, click on **"Performance"**
            - Click on the **"Pages"** tab at the top
            
            #### **Step 3: Configure date comparison**
            - At the top, you'll see the date selector
            - Click on the current date selector (e.g., "Last 3 months")
            - Select: **"Last 28 days"**
            - Enable the **"Compare"** option
            - In the second selector that appears, choose: **"Previous period"**
            - This will compare the last 28 days with the previous 28 days
            - Click **"Apply"**
            
            #### **Step 4: Export the data**
            - In the top right corner of the table, click the **export** icon (📥)
            - Select **"Download CSV"**
            - The file will download with the name: **"Pages.csv"** or similar
            
            #### **Step 5: Upload the file here**
            - Drag the **"Pages.csv"** file to the upload area above ☝️
            - Or click "Browse files" to select it from your computer
            
            ---
            
            ### 💡 Important tips:
            
            ✅ **Make sure to:**
            - Be in the **"Pages"** tab (not "Queries" or "Countries")
            - Enable the **"Compare"** option to see changes between periods
            - Select periods of **equal duration** (28 days vs 28 days)
            - Export the file in **CSV** format (not Excel)
            
            ❌ **Common mistakes:**
            - Exporting from "Queries" instead of "Pages"
            - Not enabling comparison ("Compare" button)
            - Using periods of different duration (e.g., 28 days vs 3 months)
            - Exporting without sufficient data (you need traffic on your site)
            
            ---
            
            ### 🎥 Need visual help?
            
            If you have questions, search on YouTube: **"How to export GSC pages data"**
            """)
