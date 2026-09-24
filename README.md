# 🎬 CineDrogas

Catálogo de filmes com sistema de notas em grupo, ranking, recomendações e um assistente de IA — tudo com visual inspirado na Netflix.

Feito com **Python + Streamlit**, usando a API do **TMDB** para dados dos filmes e o **Google Gemini** para as recomendações e o chat.

---

## ✨ Funcionalidades

O app tem quatro abas:

| Aba | O que faz |
|---|---|
| 🍿 **Sala de Cinema** | Busca um filme pelo nome, mostra trailer (YouTube), sinopse e permite registrar as notas de cada pessoa do grupo, com comentário. |
| 🏆 **Ranking** | "Hall da Fama" com todos os filmes avaliados, ordenados pela média. Dá para buscar, **editar notas/comentários** e **excluir** filmes. |
| 📺 **Catálogo** | Prateleiras estilo Netflix com carrosséis, destaque (hero) aleatório, **Minha Lista** (para assistir depois) e seções montadas a partir dos gêneros que o grupo mais gosta. |
| 🤖 **IA Assistente** | Chat com o Gemini, que enxerga o histórico de notas e a Minha Lista para dar indicações personalizadas. |

### Detalhes

- **Notas por pessoa:** cada avaliação guarda a nota individual de Alícia, Matheus e Taylla (0–10, passo 0,1). Quem não assistiu pode ser desmarcado, e a **média** considera só quem avaliou.
- **Catálogo personalizado:** os filmes com média ≥ 7,5 definem os 3 gêneros favoritos do grupo, que alimentam as prateleiras "Recomendação da boa" e "Escondido na lama". Filmes já avaliados não reaparecem.
- **Recomendações mágicas:** o botão manda o histórico para o Gemini, que sugere 5 filmes inéditos; cada um é buscado no TMDB e exibido em um carrossel.
- **Minha Lista:** adicione (`+`) ou remova (`✖`) filmes direto dos cards. Fica salva em CSV.
- **Trilha sonora:** música de fundo em loop (volume baixo) com botão de mutar.
- **Botão de busca externa:** na Sala de Cinema há um atalho que abre uma busca no Google com o nome e o ano do filme.

---

## 🗂 Estrutura do projeto

```
cinedrogas/
├── app.py                          # Aplicação Streamlit (toda a lógica e interface)
├── meus_filmes.csv                 # Banco de dados das avaliações
├── minha_lista.csv                 # Lista "quero assistir"
├── musicas/
│   └── trilha_sonora.mp3           # Trilha sonora de fundo
├── requirements.txt                # Dependências Python
├── .streamlit/
│   └── secrets.toml.example        # Modelo para as chaves de API
└── .gitignore
```

### Formato dos dados

**`meus_filmes.csv`** — separador `;`, codificação UTF-8 com BOM:

| Coluna | Descrição |
|---|---|
| `Titulo` | Título do filme (pt-BR, via TMDB) |
| `Alícia`, `Matheus`, `Taylla` | Nota de cada pessoa (vazio = não assistiu) |
| `Média` | Média das notas preenchidas |
| `Data` | Data do registro (`dd/mm/aaaa`) |
| `Poster` | URL do pôster no TMDB |
| `Genero` | Lista de IDs de gênero do TMDB, ex.: `[28, 12]` |
| `Comentario` | Comentário livre |

**`minha_lista.csv`** — separador `,`, colunas `Titulo` e `Poster`.

---

## 🚀 Como rodar localmente

### 1. Pré-requisitos

- Python 3.10 ou superior
- Uma chave de API do **TMDB** (gratuita): <https://www.themoviedb.org/settings/api>
- Uma chave de API do **Google Gemini** (gratuita): <https://aistudio.google.com/apikey>

### 2. Instalação

```bash
git clone https://github.com/SEU-USUARIO/cinedrogas.git
cd cinedrogas

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure as chaves

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Abra o `.streamlit/secrets.toml` e preencha:

```toml
GEMINI_KEY = "sua_chave_do_gemini"
TMDB_API_KEY = "sua_chave_do_tmdb"
```

> Alternativa: definir as variáveis de ambiente `GEMINI_KEY` e `TMDB_API_KEY`.
> ⚠️ O arquivo `secrets.toml` está no `.gitignore`. **Nunca coloque chaves diretamente no código nem faça commit delas.**

### 4. Execute

```bash
streamlit run app.py
```

O app abre em <http://localhost:8501>.

---

## 🌐 Deploy

O projeto é um app Streamlit, então pode ser hospedado no [Streamlit Community Cloud](https://streamlit.io/cloud), Render, Railway, Hugging Face Spaces, entre outros. Em qualquer plataforma, configure `GEMINI_KEY` e `TMDB_API_KEY` como *secrets*.

> ⚠️ **Persistência de dados:** o app grava as notas em arquivos CSV. Em plataformas com disco temporário (como o Streamlit Community Cloud), as alterações feitas pelo site podem ser perdidas quando o app reinicia. Para uso contínuo, o ideal é migrar para um armazenamento persistente (veja *Ideias para o futuro*).

---

## 🧰 Tecnologias

- [Streamlit](https://streamlit.io/) — interface web em Python
- [pandas](https://pandas.pydata.org/) — leitura e escrita dos CSVs
- [TMDB API](https://developer.themoviedb.org/) — dados, pôsteres e trailers
- [Google Gemini](https://ai.google.dev/) — recomendações e chat
- HTML/CSS/JS injetados para os carrosséis e o player de áudio

*Este produto usa a API do TMDB, mas não é endossado nem certificado pelo TMDB.*

---

## 🛣 Ideias para o futuro

- [ ] Trocar o CSV por um banco persistente (Google Sheets, Supabase ou SQLite com volume)
- [ ] Login/perfis em vez de nomes fixos no código
- [ ] Estatísticas do grupo (gênero favorito, quem dá as notas mais altas, etc.)
- [ ] Migrar de `google-generativeai` para o SDK novo `google-genai`

---

Feito com 🍿 por Alícia, Matheus e Taylla.
