import streamlit as st
import requests
import pandas as pd
import os
import ast
from collections import Counter
import time
import html
import urllib.parse
import google.generativeai as genai
import random
import base64
import streamlit.components.v1 as components 

# --- CONFIGURAÇÃO ---
# As chaves NÃO ficam mais no código. Configure em:
#   - Local:  .streamlit/secrets.toml  (veja secrets.toml.example)
#   - Nuvem:  painel "Secrets" da plataforma de deploy
#   - Ou:     variáveis de ambiente GEMINI_KEY e TMDB_API_KEY
def _segredo(nome):
    try:
        return st.secrets[nome]
    except Exception:
        return os.environ.get(nome, "")

GEMINI_KEY = _segredo("GEMINI_KEY")
API_KEY = _segredo("TMDB_API_KEY")  # TMDB Key
ARQUIVO_BANCO = "meus_filmes.csv"
ARQUIVO_LISTA = "minha_lista.csv"

st.set_page_config(page_title="CineDrogas", page_icon="🍿", layout="wide")

if not API_KEY:
    st.error("Chave do TMDB não configurada. Defina TMDB_API_KEY nos secrets (veja o README).")
    st.stop()

# --- CONEXÃO IA GLOBAL (CORREÇÃO DE PERSISTÊNCIA) ---
if 'model' not in st.session_state:
    st.session_state['model'] = None
    st.session_state['model_name'] = ""

if st.session_state['model'] is None and GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        modelos_disponiveis = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_disponiveis.append(m.name)
        
        escolhido = None
        for m in modelos_disponiveis:
            if 'flash' in m: escolhido = m; break
        if not escolhido and modelos_disponiveis: escolhido = modelos_disponiveis[0]
        
        if escolhido:
            st.session_state['model'] = genai.GenerativeModel(escolhido)
            st.session_state['model_name'] = escolhido
    except Exception as e:
        st.error(f"Erro silencioso ao conectar IA: {e}")

model = st.session_state['model']

# --- GERENCIAMENTO DE ESTADO ---
query_params = st.query_params

if "add_watchlist" in query_params:
    titulo_add = query_params["add_watchlist"]
    poster_add = query_params["poster_add"]
    df_lista = pd.DataFrame(columns=["Titulo", "Poster"])
    if os.path.exists(ARQUIVO_LISTA):
        df_lista = pd.read_csv(ARQUIVO_LISTA)
    if titulo_add not in df_lista["Titulo"].values:
        novo_item = pd.DataFrame({"Titulo": [titulo_add], "Poster": [poster_add]})
        novo_item.to_csv(ARQUIVO_LISTA, mode='a', header=not os.path.exists(ARQUIVO_LISTA), index=False)
        st.toast(f"✅ {titulo_add} salvo!", icon="📌")
    st.query_params.clear()

if "remove_watchlist" in query_params:
    titulo_rem = query_params["remove_watchlist"]
    if os.path.exists(ARQUIVO_LISTA):
        df_lista = pd.read_csv(ARQUIVO_LISTA)
        df_lista = df_lista[df_lista["Titulo"] != titulo_rem]
        df_lista.to_csv(ARQUIVO_LISTA, index=False)
        st.toast(f"🗑️ Removido.", icon="👋")
    st.query_params.clear(); time.sleep(0.5); st.rerun()

filme_selecionado = ""
if "filme_clicado" in query_params:
    filme_selecionado = query_params["filme_clicado"]

# --- CSS (DESIGN NETFLIX) ---

st.markdown("""

<style>

    .block-container { padding-top: 2rem; }

    

    /* ENVELOPE DO CARROSSEL */

    .carousel-wrapper {

        position: relative;

        width: 100%;

    }

    

    /* BOTÕES LATERAIS DE ROLAGEM (< e >) */

    .scroll-btn {

        position: absolute;

        top: 40px; 

        height: 240px; 

        width: 45px;

        background: rgba(0,0,0,0.6);

        color: white;

        font-size: 35px;

        border: none;

        z-index: 105; 

        cursor: pointer;

        opacity: 0; 

        transition: all 0.3s ease-in-out;

        display: flex;

        align-items: center;

        justify-content: center;

    }

    .carousel-wrapper:hover .scroll-btn { opacity: 1; }

    .scroll-btn:hover { background: rgba(0,0,0,0.9); font-size: 45px; }

    .scroll-btn.left { left: 0; border-top-right-radius: 6px; border-bottom-right-radius: 6px;}

    .scroll-btn.right { right: 0; border-top-left-radius: 6px; border-bottom-left-radius: 6px;}


    /* LINHA DE FILMES */

    .netflix-row { 

        display: flex; 

        overflow-x: auto; 

        padding: 40px 10px 80px 10px;

        gap: 12px; 

        -ms-overflow-style: none;  

        scrollbar-width: none;  

    }

    .netflix-row::-webkit-scrollbar { display: none; }

    

    /* Cartão do Filme */

    .movie-card { 

        flex: 0 0 auto; 

        width: 160px; 

        position: relative; 

        transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s ease; 

        border-radius: 4px; 

        z-index: 1; 

        cursor: pointer;

        background-color: #141414; 

    }

    .movie-card:hover { transform: scale(1.3) translateY(-15px); z-index: 1000; box-shadow: 0 10px 25px rgba(0,0,0,0.9); }

    

    .movie-img { width: 100%; border-radius: 4px; display: block; aspect-ratio: 2/3; object-fit: cover; }

    

    /* Painel de Informações */

    .movie-info-panel { 

        position: absolute; top: 100%; left: 0; width: 100%; background: #141414; padding: 12px; 

        border-radius: 0 0 4px 4px; opacity: 0; visibility: hidden; transition: opacity 0.2s ease-in-out; 

        box-shadow: 0 15px 20px rgba(0,0,0,0.9); display: flex; flex-direction: column; pointer-events: none; 

    }

    .movie-card:hover .movie-info-panel { opacity: 1; visibility: visible; pointer-events: auto; }


    /* Botões Circulares de Ação */

    .action-row { display: flex; gap: 8px; margin-bottom: 12px; z-index: 102; }

    .btn-circle { width: 32px; height: 32px; border-radius: 50%; background: rgba(42,42,42,0.6); color: white; display: flex; align-items: center; justify-content: center; font-size: 14px; border: 2px solid rgba(255, 255, 255, 0.4); text-decoration: none; transition: all 0.2s ease; }

    .btn-circle:hover { border-color: white; background: rgba(255, 255, 255, 0.1); color: white; }

    .btn-play { background: white; color: black; border: none; font-size: 16px; padding-left: 2px; }

    .btn-play:hover { background: #d4d4d4; color: black; }

    

    .quality-badge { font-size: 9px; color: #46d160; font-weight: bold; border: 1px solid #46d160; padding: 2px 4px; border-radius: 2px; margin-right: 6px; text-transform: uppercase; }

    .meta-data { font-size: 12px; color: #fff; font-weight: bold; margin-top: 6px; line-height: 1.2; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

    

    /* Hero Section */

    .hero-container { position: relative; width: 100%; height: 400px; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }

    .hero-content { position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px; background: linear-gradient(to top, rgba(0,0,0,1), rgba(0,0,0,0)); }

    .hero-title { font-size: 3rem; font-weight: bold; text-shadow: 2px 2px 4px black; margin-bottom: 10px; }

    .hero-desc { font-size: 1rem; color: #ddd; max-width: 600px; margin-bottom: 20px; text-shadow: 1px 1px 2px black; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;}

    .stChatMessage { background-color: #262730; border-radius: 10px; padding: 10px; margin-bottom: 10px; }

    .stExpander { border: 1px solid #333; border-radius: 8px; margin-bottom: 10px; background-color: #0e1117; }

</style>

""", unsafe_allow_html=True)


# --- FUNÇÕES ---
def carregar_dados():
    colunas = ["Titulo", "Alícia", "Matheus", "Taylla", "Média", "Data", "Poster", "Genero", "Comentario"]
    if os.path.exists(ARQUIVO_BANCO):
        try:
            df = pd.read_csv(ARQUIVO_BANCO, sep=";", encoding='utf-8-sig', on_bad_lines='skip')
            for col in colunas:
                if col not in df.columns: df[col] = ""
            return df
        except: pass
    return pd.DataFrame(columns=colunas)

def carregar_minha_lista():
    if os.path.exists(ARQUIVO_LISTA): return pd.read_csv(ARQUIVO_LISTA)
    return pd.DataFrame(columns=["Titulo", "Poster"])

# BUSCA EXTENSA PARA O CATÁLOGO
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_catalogo_genero(tags, sort_by="popularity.desc", min_vote=7.0, min_count=300, max_pages=8):
    filmes_coletados = []
    for pag in range(1, max_pages + 1):
        try:
            url = (f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}"
                   f"&with_genres={tags}&sort_by={sort_by}&vote_average.gte={min_vote}"
                   f"&vote_count.gte={min_count}&language=pt-BR&include_adult=false&page={pag}")
            res = requests.get(url).json()
            novos = res.get('results', [])
            if not novos: break 
            filmes_coletados.extend(novos)
            time.sleep(0.05) 
        except: break
    return filmes_coletados

def obter_trailer(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}&language=pt-BR"
        res = requests.get(url).json()
        for v in res.get('results', []):
            if v['type'] == "Trailer" and v['site'] == "YouTube": return v['key']
        url_en = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}&language=en-US"
        res_en = requests.get(url_en).json()
        for v in res_en.get('results', []):
            if v['type'] == "Trailer" and v['site'] == "YouTube": return v['key']
    except: pass
    return None

def buscar_detalhes_filme(nome_filme):
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={urllib.parse.quote(nome_filme)}&language=pt-BR"
        res = requests.get(url).json()
        if res.get('results'):
            return res['results'][0]
    except: pass
    return None

# --- INTERFACE ---
st.title("🎬 CineDrogas")

# --- TRILHA SONORA GLOBAL ISOLADA ---
pasta_musicas = "musicas"
caminho_mp3 = f"{pasta_musicas}/trilha_sonora.mp3"

if not os.path.exists(pasta_musicas):
    os.makedirs(pasta_musicas)

if os.path.exists(caminho_mp3):
    with open(caminho_mp3, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        
        html_code = f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; padding-right: 5px;">
            <audio id="cine-audio" autoplay loop>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <button id="mute-btn" onclick="toggleMute()" title="Mutar/Desmutar Trilha Sonora" style="
                background-color: #E50914; 
                color: white; 
                border: 2px solid #fff; 
                border-radius: 50%; 
                width: 40px; 
                height: 40px; 
                font-size: 18px; 
                cursor: pointer;
                box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                🔊
            </button>
        </div>
        <script>
            var audio = document.getElementById("cine-audio");
            var btn = document.getElementById("mute-btn");
            audio.volume = 0.05;
            function toggleMute() {{
                audio.muted = !audio.muted;
                btn.innerHTML = audio.muted ? "🔇" : "🔊";
            }}
        </script>
        """
        components.html(html_code, height=50)
# ---------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(["🍿 Sala de Cinema", "🏆 Ranking", "📺 Catálogo", "🤖 IA Assistente"])

# ABA 1: Sala de Cinema
with tab1:
    valor_inicial = filme_selecionado if filme_selecionado else ""
    if filme_selecionado: st.query_params.clear() 
    nome = st.text_input("Filme em foco:", value=valor_inicial, key="input_princ")

    if nome:
        res = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={nome}&language=pt-BR").json()
        if res.get('results'):
            f = res['results'][0]
            ano = f.get('release_date', '0000')[:4]
            trailer_key = obter_trailer(f['id'])
            
            if trailer_key: st.video(f"https://www.youtube.com/watch?v={trailer_key}")
            else: st.image(f"https://image.tmdb.org/t/p/original{f['backdrop_path']}", use_container_width=True)

            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader(f['title'])
                st.write(f"**Sinopse:** {f.get('overview', 'Sem sinopse.')}")
                st.divider()
                st.markdown("### 🛠 Opções de Torrent (Uso Pessoal)")
                query_torrent = urllib.parse.quote(f"{f['title']} {ano} 1080p magnet link")
                st.link_button("🔍 Buscar Magnet Link", f"https://www.google.com/search?q={query_torrent}", use_container_width=True)

            with c2:
                with st.container(border=True):
                    st.write("### 📝 Avaliar")
                    chk1, chk2, chk3 = st.columns(3)
                    viu_a = chk1.checkbox("Alícia", True); viu_m = chk2.checkbox("Matheus", True); viu_t = chk3.checkbox("Taylla", True)
                    val_a = st.number_input("Alícia", 0.0, 10.0, 5.0, step=0.1) if viu_a else None
                    val_m = st.number_input("Matheus", 0.0, 10.0, 5.0, step=0.1) if viu_m else None
                    val_t = st.number_input("Taylla", 0.0, 10.0, 5.0, step=0.1) if viu_t else None
                    com = st.text_area("Notas")
                    if st.button("Salvar Histórico", type="primary", use_container_width=True):
                        notas = [n for n in [val_a, val_m, val_t] if n is not None]
                        if notas:
                            media = sum(notas) / len(notas)
                            novo = pd.DataFrame({"Titulo": [f['title']], "Alícia": [val_a if viu_a else ""], "Matheus": [val_m if viu_m else ""], "Taylla": [val_t if viu_t else ""], "Média": [round(media, 2)], "Data": [pd.Timestamp.now().strftime("%d/%m/%Y")], "Poster": [f"https://image.tmdb.org/t/p/w500{f['poster_path']}"], "Genero": [str(f.get('genre_ids', []))], "Comentario": [com]})
                            novo.to_csv(ARQUIVO_BANCO, mode='a', header=not os.path.exists(ARQUIVO_BANCO), index=False, sep=";")
                            st.success("Salvo!")
                            time.sleep(1)
                            st.switch_page("app.py")

# ABA 2: Ranking Visual & Editor
with tab2:
    st.markdown("### 🏆 Hall da Fama do CineDrogas")
    
    df = carregar_dados()
    if df.empty:
        st.info("Nenhum filme avaliado ainda.")
    else:
        termo_busca = st.text_input("🔍 Buscar filme no ranking:", placeholder="Digite o nome do filme...")
        
        df_sorted = df.sort_values(by="Média", ascending=False).reset_index(drop=True)
        if termo_busca:
            df_sorted = df_sorted[df_sorted['Titulo'].str.contains(termo_busca, case=False, na=False)]

        for index, row in df_sorted.iterrows():
            original_idx = df.index[df['Titulo'] == row['Titulo']].tolist()[0]
            
            rank = index + 1
            poster = row['Poster'] if pd.notna(row['Poster']) and "http" in str(row['Poster']) else "https://via.placeholder.com/100"
            
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            label_card = f"{medal} {row['Titulo']} — ⭐ {row['Média']}"
            
            with st.expander(label_card, expanded=False):
                c_img, c_edit = st.columns([1, 4])
                
                with c_img:
                    st.image(poster, use_container_width=True)
                
                with c_edit:
                    st.caption(f"📅 {row['Data']} | 💬 {row['Comentario']}")
                    
                    with st.form(key=f"form_edit_{original_idx}"):
                        st.markdown("**✏️ Editar Avaliação**")
                        col_notes = st.columns(3)
                        
                        def safe_val(val):
                            try: return float(val)
                            except: return 0.0

                        new_a = col_notes[0].number_input("Alícia", 0.0, 10.0, safe_val(row['Alícia']), step=0.1)
                        new_m = col_notes[1].number_input("Matheus", 0.0, 10.0, safe_val(row['Matheus']), step=0.1)
                        new_t = col_notes[2].number_input("Taylla", 0.0, 10.0, safe_val(row['Taylla']), step=0.1)
                        
                        new_com = st.text_area("Comentário", value=str(row['Comentario']) if pd.notna(row['Comentario']) else "")
                        
                        c_save, c_del = st.columns([1, 1])
                        saved = c_save.form_submit_button("💾 Salvar Alterações", type="primary")
                        
                        if saved:
                            df.at[original_idx, "Alícia"] = new_a
                            df.at[original_idx, "Matheus"] = new_m
                            df.at[original_idx, "Taylla"] = new_t
                            df.at[original_idx, "Comentario"] = new_com
                            
                            notas_validas = [n for n in [new_a, new_m, new_t] if n > 0]
                            media = sum(notas_validas) / len(notas_validas) if notas_validas else 0.0
                            df.at[original_idx, "Média"] = round(media, 2)
                            
                            df.to_csv(ARQUIVO_BANCO, index=False, sep=";", encoding='utf-8-sig')
                            st.toast(f"✅ Atualizado: {row['Titulo']}")
                            time.sleep(1)
                            st.rerun()

                    if st.button("🗑️ Excluir Filme", key=f"btn_del_{original_idx}"):
                        df_dropped = df.drop(original_idx)
                        df_dropped.to_csv(ARQUIVO_BANCO, index=False, sep=";", encoding='utf-8-sig')
                        st.toast(f"🗑️ Filme removido!")
                        time.sleep(1)
                        st.rerun()

# ABA 3: Catálogo Premium 
with tab3:
    df = carregar_dados()
    favs = df[df['Média'] >= 7.5]
    exibidos = set(df['Titulo'].tolist())
    
    col_force, _ = st.columns([1, 4])
    if col_force.button("🔄 Recarregar Catálogo", key="clear_cache"):
        st.cache_data.clear(); st.rerun()

    with st.spinner("Preparando as prateleiras do cinema..."):
        filmes_tendencia = buscar_catalogo_genero("28,12", "popularity.desc", 7.0, 300, 2) 
        if filmes_tendencia:
            destaque = random.choice(filmes_tendencia)
            backdrop_url = f"https://image.tmdb.org/t/p/original{destaque['backdrop_path']}"
            
            st.markdown(f"""
            <div class="hero-container" style="background-image: url('{backdrop_url}'); background-size: cover; background-position: center;">
                <div class="hero-content">
                    <div class="hero-title">{destaque['title']}</div>
                    <div class="hero-desc">{destaque['overview']}</div>
                    <a href="?filme_clicado={urllib.parse.quote(destaque['title'])}" target="_self" style="text-decoration:none;">
                        <button style="background-color: #E50914; color: white; border: none; padding: 10px 25px; font-size: 16px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                            ▶ Assistir Agora
                        </button>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    def renderizar_carrossel_funcional(id_secao, html_conteudo):
        return f"""
        <div class="carousel-wrapper" id="wrap-{id_secao}">
            <button class="scroll-btn left" id="left-{id_secao}">&#10094;</button>
            <div class="netflix-row" id="row-{id_secao}">{html_conteudo}</div>
            <button class="scroll-btn right" id="right-{id_secao}">&#10095;</button>
        </div>
        """

    # --- SESSÃO DE RECOMENDAÇÃO INTELIGENTE DA IA ---
    st.subheader("✨ Curadoria da Besta-Fera")
    col_ia_btn, _ = st.columns([1, 3])
    if col_ia_btn.button("🧠 Gerar Recomendações Mágicas"):
        if model is None:
            st.error("IA não conectada. Verifique sua chave.")
        else:
            with st.spinner("A IA está analisando todos os filmes que vocês já viram..."):
                historico_txt = df[['Titulo', 'Média']].to_string(index=False)
                prompt_rec = f"""
                Analise este histórico de filmes assistidos pelo grupo:
                {historico_txt}
                Me dê uma lista Python de 5 nomes de filmes QUE NÃO ESTÃO NA LISTA, que eles provavelmente vão amar.
                Retorne APENAS a lista Python pura, ex: ['Filme A', 'Filme B']. Sem texto extra.
                """
                try:
                    resp = model.generate_content(prompt_rec)
                    lista_sugestoes = ast.literal_eval(resp.text.strip())
                    
                    filmes_ia_objetos = []
                    for nome_f in lista_sugestoes:
                        f_obj = buscar_detalhes_filme(nome_f)
                        if f_obj: filmes_ia_objetos.append(f_obj)
                    
                    if filmes_ia_objetos:
                        html_items = ""
                        for f in filmes_ia_objetos:
                            img = f"https://image.tmdb.org/t/p/w500{f['poster_path']}"
                            tit = html.escape(f['title'])
                            overview = html.escape(f.get('overview', '') or 'Sem sinopse disponível.')
                            link_play = f"?filme_clicado={urllib.parse.quote(tit)}"
                            link_add = f"?add_watchlist={urllib.parse.quote(tit)}&poster_add={urllib.parse.quote(img)}"
                            
                            html_items += f"""
                            <div class="movie-card">
                                <img src="{img}" class="movie-img">
                                <div class="movie-info-panel">
                                    <div class="meta-data">{tit}</div>
                                    <div class="movie-stats">
                                        <span class="rating-text">Recomendado por IA 🤖</span>
                                    </div>
                                    <div class="movie-synopsis">{overview}</div>
                                    <div class="action-row">
                                        <a href="{link_play}" class="btn-circle btn-play" title="Assistir">▶</a>
                                        <a href="{link_add}" class="btn-circle" title="Adicionar à Lista">+</a>
                                    </div>
                                </div>
                            </div>"""
                        
                        st.markdown(renderizar_carrossel_funcional("recomenda", html_items), unsafe_allow_html=True)
                        st.success("Recomendações geradas com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao gerar recomendações: {e}")

    # --- MINHA LISTA ---
    df_lista = carregar_minha_lista()
    if not df_lista.empty:
        st.subheader(f"📌 Minha Lista ({len(df_lista)})")
        html_lista = ""
        for _, row in df_lista.iterrows():
            tit = html.escape(row['Titulo'])
            poster = row['Poster']
            link_play = f"?filme_clicado={urllib.parse.quote(tit)}"
            link_remove = f"?remove_watchlist={urllib.parse.quote(tit)}"
            
            html_lista += f"""
            <div class="movie-card">
                <img src="{poster}" class="movie-img">
                <div class="movie-info-panel">
                    <div class="meta-data">{tit}</div>
                    <div class="action-row" style="margin-top:10px;">
                        <a href="{link_play}" class="btn-circle btn-play" title="Assistir">▶</a>
                        <a href="{link_remove}" class="btn-circle btn-remove" title="Remover da Lista">✖</a>
                    </div>
                </div>
            </div>"""
        
        st.markdown(renderizar_carrossel_funcional("minhalista", html_lista), unsafe_allow_html=True)
        st.divider()

    # --- NOVO CATÁLOGO EXTENSO ---
    if not favs.empty:
        tags = []
        for g in favs['Genero']:
            try: tags.extend(ast.literal_eval(g))
            except: pass
        if tags:
            top_tags = ",".join([str(t[0]) for t in Counter(tags).most_common(3)])
            
            def renderizar_sessao(titulo, lista, id_secao, num_exibir=25):
                validos = [f for f in lista if f['title'] not in exibidos]
                
                if validos:
                    random.shuffle(validos)
                    validos = validos[:num_exibir] 
                
                for f in validos: exibidos.add(f['title'])
                if not validos: return
                
                html_items = ""
                for f in validos:
                    img = f"https://image.tmdb.org/t/p/w500{f['poster_path']}"
                    tit = html.escape(f['title'])
                    nota = round(f['vote_average'], 1)
                    qualidade = "4K ULTRA HD" if nota > 7.5 else "FULL HD"
                    overview = html.escape(f.get('overview', '') or 'Sem sinopse disponível.')
                    link_play = f"?filme_clicado={urllib.parse.quote(tit)}"
                    link_add = f"?add_watchlist={urllib.parse.quote(tit)}&poster_add={urllib.parse.quote(img)}"
                    
                    html_items += f"""
                    <div class="movie-card">
                        <img src="{img}" class="movie-img">
                        <div class="movie-info-panel">
                            <div class="meta-data">{tit}</div>
                            <div class="movie-stats">
                                <span class="quality-badge">{qualidade}</span>
                                <span class="rating-text">{nota}★</span>
                            </div>
                            <div class="movie-synopsis">{overview}</div>
                            <div class="action-row">
                                <a href="{link_play}" class="btn-circle btn-play" title="Assistir">▶</a>
                                <a href="{link_add}" class="btn-circle" title="Adicionar à Lista">+</a>
                            </div>
                        </div>
                    </div>"""
                
                st.subheader(f"{titulo}")
                st.markdown(renderizar_carrossel_funcional(id_secao, html_items), unsafe_allow_html=True)
                
            with st.spinner("Atualizando as prateleiras do cinema..."):
                lista_grupo = buscar_catalogo_genero(top_tags, "popularity.desc", 7.0, 300, max_pages=8)
                renderizar_sessao("🍿 Recomendação da boa", lista_grupo, "grupo")
                
                lista_cult = buscar_catalogo_genero(top_tags, "vote_average.desc", 7.5, 100, max_pages=8)
                renderizar_sessao("💎 Escondido na lama igual minha bondade", lista_cult, "cult")
                
                lista_tensao = buscar_catalogo_genero("27,53", "popularity.desc", 6.5, 200, max_pages=6)
                renderizar_sessao("🔪 Terror que ninguém gosta", lista_tensao, "tensao")
                
                lista_mentes = buscar_catalogo_genero("878,9648", "vote_average.desc", 7.0, 200, max_pages=6)
                renderizar_sessao("🤯 Ficção & Mistério", lista_mentes, "mentes")
                
                lista_comedia = buscar_catalogo_genero("35,16", "popularity.desc", 7.0, 300, max_pages=6)
                renderizar_sessao("😂 Comédia", lista_comedia, "comedia")
    else: st.warning("Avalie filmes para liberar o catálogo.")

# --- INJETOR JAVASCRIPT GLOBAL (O MOTOR ORGÂNICO DA NETFLIX) ---

    # Aqui criamos uma animação matemática perfeita (Easing in-out)

    components.html("""

    <script>

        // Função matemática para fazer o deslize começar suave, acelerar e frear suavemente.

        function smoothScroll(element, distance, duration) {

            const start = element.scrollLeft;

            let startTime = null;


            function animation(currentTime) {

                if (startTime === null) startTime = currentTime;

                const timeElapsed = currentTime - startTime;

                let progress = timeElapsed / duration;

                if (progress > 1) progress = 1;

                

                // Cálculo de Easing (a mágica orgânica)

                let ease = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;

                

                element.scrollLeft = start + (distance * ease);


                if (timeElapsed < duration) {

                    window.requestAnimationFrame(animation);

                }

            }

            window.requestAnimationFrame(animation);

        }


        function ativarBotoesCarrossel() {

            const parent = window.parent.document;

            const leftBtns = parent.querySelectorAll('.scroll-btn.left');

            const rightBtns = parent.querySelectorAll('.scroll-btn.right');

            

            leftBtns.forEach(btn => {

                btn.onclick = function() {

                    const row = this.nextElementSibling;

                    // Move -688 pixels (4 filmes exatos) em 650 milissegundos

                    if(row) smoothScroll(row, -688, 650); 

                };

            });

            

            rightBtns.forEach(btn => {

                btn.onclick = function() {

                    const row = this.previousElementSibling;

                    // Move +688 pixels (4 filmes exatos) em 650 milissegundos

                    if(row) smoothScroll(row, 688, 650);

                };

            });

        }

        

        // Fica injetando a função nos primeiros segundos para garantir que a página "pegue" os botões

        let tentativas = 0;

        let intervalo = setInterval(() => {

            ativarBotoesCarrossel();

            tentativas++;

            if(tentativas > 10) clearInterval(intervalo);

        }, 500);

    </script>

    """, height=0, width=0)




# ABA 4: IA ASSISTENTE
with tab4:
    st.header("🤖 Besta-Fera: IA do CineDrogas")

    if model:
        st.success(f"IA Conectada: {st.session_state.get('model_name', 'Auto')}")
        df_historico = carregar_dados()
        df_lista = carregar_minha_lista()
        if "messages" not in st.session_state: st.session_state.messages = []
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): st.markdown(message["content"])
        
        if prompt := st.chat_input("Ex: Me indique um filme de terror leve"):
            with st.chat_message("user"): st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            contexto = f"Você é um assistente de cinema. DADOS: {df_historico.to_string(index=False)}. LISTA: {df_lista.to_string(index=False)}. Pergunta: {prompt}"
            
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    try:
                        response = model.generate_content(contexto)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        if "429" in str(e):
                            st.error("🚦 Calma aí! Você atingiu o limite de perguntas rápidas.")
                        else:
                            st.error(f"Erro na IA: {e}")
    else:
        st.error("Erro na conexão com a IA. Verifique sua chave.")