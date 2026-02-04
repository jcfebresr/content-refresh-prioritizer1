import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
import requests
from bs4 import BeautifulSoup
import json
import time

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

def scrape_url_metadata(url):
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
            'h3_count': len(h3_tags),
            'word_count': words,
            'images_total': images_total,
            'images_without_alt': images_without_alt,
            'schemas': schemas,
            'schemas_count': len(schemas),
            'faqs_count': len(faqs),
            'faqs': faqs
        }
        
    except Exception as e:
        return {
            'success': False,
            'url': url,
            'error': str(e),
            'title_length': 0,
            'description_length': 0,
            'h1_count': 0,
            'h2_count': 0,
            'h3_count': 0,
            'word_count': 0,
            'images_total': 0,
            'images_without_alt': 0,
            'schemas_count': 0,
            'faqs_count': 0
        }

def get_top_keyword_for_url(gsc_df, url):
    """Obtiene la keyword principal para una URL desde GSC"""
    # Esto requeriría un export diferente de GSC con queries
    # Por ahora, extraemos del title/URL
    return None

def get_google_top_10(keyword):
    """Scrape top 10 de Google para una keyword"""
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&num=10"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')
        
        results = []
        
        # Buscar divs de resultados orgánicos
        for result in soup.find_all('div', class_='g'):
            link = result.find('a', href=True)
            if link and link['href'].startswith('http'):
                results.append(link['href'])
                if len(results) >= 10:
                    break
        
        return results[:10]
        
    except Exception as e:
        st.warning(f"No se pudo obtener top 10 de Google: {str(e)}")
        return []

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
st.title("🎯 Content Refresh Prioritizer")
st.markdown("Descubre qué páginas optimizar primero basándote en Google Search Console")

gsc_file = st.file_uploader("📊 Google Search Console CSV", type=['csv'])

# Input manual de keyword para comparativa
keyword_input = st.text_input("🔍 (Opcional) Keyword para comparar con top 10 de Google", 
                              placeholder="Ej: vitamina b12 alta efectos vision")

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
                    
                    # Insight IA
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
                    
                    # Análisis On-Page
                    st.markdown("---")
                    st.subheader("🔍 Análisis On-Page")
                    
                    with st.spinner("Analizando metadata de tu página..."):
                        current_metadata = scrape_url_metadata(top_url['url'])
                    
                    if current_metadata['success']:
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
                        
                        # Comparativa con Top 10
                        if keyword_input:
                            st.markdown("---")
                            st.subheader("📊 Comparativa vs Top 10 de Google")
                            
                            with st.spinner(f"Obteniendo top 10 para '{keyword_input}'..."):
                                top_10_urls = get_google_top_10(keyword_input)
                            
                            if top_10_urls:
                                st.info(f"Analizando {len(top_10_urls)} URLs del top 10...")
                                
                                comparison_data = []
                                
                                # Tu URL
                                comparison_data.append({
                                    'Posición': f"#{int(top_url['position_current'])} (TU URL)",
                                    'Title Length': current_metadata['title_length'],
                                    'Desc Length': current_metadata['description_length'],
                                    'Word Count': current_metadata['word_count'],
                                    'H1': current_metadata['h1_count'],
                                    'H2': current_metadata['h2_count'],
                                    'Schemas': current_metadata['schemas_count'],
                                    'FAQs': current_metadata['faqs_count']
                                })
                                
                                # Top 10
                                for idx, url in enumerate(top_10_urls[:10], 1):
                                    with st.spinner(f"Analizando posición #{idx}..."):
                                        metadata = scrape_url_metadata(url)
                                        time.sleep(1)  # Rate limiting
                                        
                                        comparison_data.append({
                                            'Posición': f"#{idx}",
                                            'Title Length': metadata['title_length'],
                                            'Desc Length': metadata['description_length'],
                                            'Word Count': metadata['word_count'],
                                            'H1': metadata['h1_count'],
                                            'H2': metadata['h2_count'],
                                            'Schemas': metadata['schemas_count'],
                                            'FAQs': metadata['faqs_count']
                                        })
                                
                                # Crear tabla
                                comparison_df = pd.DataFrame(comparison_data)
                                
                                # Calcular promedios
                                avg_row = {
                                    'Posición': '📊 PROMEDIO TOP 10',
                                    'Title Length': int(comparison_df.iloc[1:]['Title Length'].mean()),
                                    'Desc Length': int(comparison_df.iloc[1:]['Desc Length'].mean()),
                                    'Word Count': int(comparison_df.iloc[1:]['Word Count'].mean()),
                                    'H1': round(comparison_df.iloc[1:]['H1'].mean(), 1),
                                    'H2': round(comparison_df.iloc[1:]['H2'].mean(), 1),
                                    'Schemas': round(comparison_df.iloc[1:]['Schemas'].mean(), 1),
                                    'FAQs': round(comparison_df.iloc[1:]['FAQs'].mean(), 1)
                                }
                                
                                comparison_df = pd.concat([comparison_df, pd.DataFrame([avg_row])], ignore_index=True)
                                
                                st.dataframe(comparison_df, use_container_width=True)
                                
                                # Recomendaciones
                                st.subheader("💡 Recomendaciones basadas en la competencia")
                                
                                recs = []
                                
                                avg_words = avg_row['Word Count']
                                if current_metadata['word_count'] < avg_words * 0.8:
                                    recs.append(f"📝 Tu contenido ({current_metadata['word_count']} palabras) es más corto que el promedio ({avg_words}). Considera ampliar.")
                                
                                avg_h2 = avg_row['H2']
                                if current_metadata['h2_count'] < avg_h2 * 0.7:
                                    recs.append(f"📑 Tienes {current_metadata['h2_count']} H2 vs promedio de {avg_h2:.1f}. Mejora la estructura.")
                                
                                avg_schemas = avg_row['Schemas']
                                if current_metadata['schemas_count'] < avg_schemas:
                                    recs.append(f"🏷️ Tu página tiene {current_metadata['schemas_count']} schemas vs promedio de {avg_schemas:.1f}. Añade más markup.")
                                
                                avg_faqs = avg_row['FAQs']
                                if current_metadata['faqs_count'] == 0 and avg_faqs > 0:
                                    recs.append(f"❓ El promedio tiene {avg_faqs:.1f} FAQs y tú no tienes. Añade una sección FAQ.")
                                
                                if not recs:
                                    st.success("✅ Tu página está bien optimizada comparada con la competencia")
                                else:
                                    for rec in recs:
                                        st.warning(rec)
                            
                            else:
                                st.warning("No se pudo obtener el top 10 de Google. Intenta con otra keyword.")
                        
                        else:
                            st.info("💡 Ingresa una keyword arriba para comparar con el top 10 de Google")
                        
                        with st.expander("📄 Ver detalles completos de tu URL"):
                            st.write("**Title:**", current_metadata['title'])
                            st.write("**Meta Description:**", current_metadata['description'])
                            
                            if current_metadata['h1_tags']:
                                st.write("**H1:**")
                                for h1 in current_metadata['h1_tags']:
                                    st.write(f"- {h1}")
                            
                            if current_metadata['schemas']:
                                st.write("**Schema Markup:**")
                                st.write(", ".join(current_metadata['schemas']))
                            
                            if current_metadata['faqs']:
                                st.write("**FAQs encontradas:**")
                                for faq in current_metadata['faqs']:
                                    st.write(f"- {faq}")
                    
                    else:
                        st.warning(f"⚠️ No se pudo analizar la página: {current_metadata.get('error', 'Error desconocido')}")
                    
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
