
# Website Scraping RAG Application

## 🏗️ Architecture Explanation
WebRAG Studio follows an end-to-end RAG architecture where website content is collected and converted into a searchable knowledge base.
The website is crawled, cleaned, split into chunks, converted into embeddings, and stored in ChromaDB.
When a user asks a question, the system performs semantic search to retrieve the most relevant chunks.
These chunks are given as context to the Qwen3:8B LLM running through Ollama to generate a grounded answer.
Finally, Streamlit displays the retrieved information and generated answer to the user.

## 🏗️ Architecture

![WebsiteScraping-Architecture](https://github.com/user-attachments/assets/d84bd6b3-0bc3-4591-9e95-6aa0c00c978f)

**WebRAG Studio — End-to-End Project Demo**

https://github.com/user-attachments/assets/b8f6fc74-b405-4d38-b839-9754d570c256

# 🚀 Installation & Running the Project in Google Colab

Follow these steps to run the Website Scraping RAG Application in Google Colab.

## 1. Clone the Repository

```bash
!git clone https://github.com/lakshmiprasannaadi499-del/website-scraping-rag.git
```

## 2. Go to the Project Directory

```bash
%cd website-scraping-rag
```

## 3. Install Ollama

Install Ollama inside the Google Colab runtime:

```bash
!curl -fsSL https://ollama.com/install.sh | sh
```

## 4. Start Ollama Server

Start the Ollama server in the background:

```bash
!ollama serve > /content/ollama.log 2>&1 &
```

Wait a few seconds for the server to start.

## 5. Install Python Dependencies

Install all required libraries from `requirements.txt`:

```bash
!pip install -r requirements.txt
```

### Main Libraries Used

The project uses the following major libraries:

* **Streamlit** – Web application interface
* **Firecrawl** – Website crawling and content extraction
* **LangChain** – RAG and document processing components
* **ChromaDB** – Vector database for storing embeddings
* **Sentence Transformers** – Text embedding generation
* **BAAI/bge-small-en-v1.5** – Embedding model
* **Ollama** – Local LLM serving
* **Qwen3:8B** – Local language model
* **BeautifulSoup4** – HTML processing
* **Requests** – HTTP/API requests
* **python-dotenv** – Environment variable management

## 6. Pull Qwen3:8B Model

Download the Qwen3 8B model into Ollama:

```bash
!ollama pull qwen3:8b
```

> **Note:** The model name used by the project is `qwen3:8b`.

## 7. Check Ollama and Model

Verify that Ollama is installed and that the Qwen3 model is available:

```bash
!ollama list
```

You should see something similar to:

```text
NAME        ID        SIZE
qwen3:8b    ...       ...
```

You can also check the Ollama server:

```bash
!curl http://127.0.0.1:11434/api/tags
```

## 8. Start the Streamlit Application

Run the Streamlit application on port `8501`:

```bash
!streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false \
    > /content/streamlit.log 2>&1 &
```

The application will run in the background.

## 9. Check Streamlit Logs

Check whether Streamlit started successfully:

```bash
!cat /content/streamlit.log
```

A successful startup should show information about the Streamlit server running on port `8501`.

## 10. Create a Google Colab Public Access URL

Run:

```python
from google.colab import output

url = output.eval_js("google.colab.kernel.proxyPort(8501)")

print(url)
```

Google Colab will generate a URL.

**Click the generated URL to open WebRAG Studio.**

---

# 📁 Project Structure

```text
website-scraping-rag/
│
├── app/
│   ├── config.py
│   ├── crawler.py
│   ├── scraper.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── rag.py
│   └── llm.py
│
├── Evaluation/
│   └── evaluate_ragas.py
│
├── data/
│   └── chroma/
│
├── streamlit_app.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
└── ...
```

## 🔄 Application Workflow

```text
Website URL
     │
     ▼
Firecrawl
     │
     ▼
Website Content Extraction
     │
     ▼
Text Cleaning
     │
     ▼
Text Chunking
     │
     ▼
BAAI/bge-small-en-v1.5
     │
     ▼
Vector Embeddings
     │
     ▼
ChromaDB
     │
     ▼
Semantic Retrieval
     │
     ▼
Relevant Context
     │
     ▼
Qwen3:8B via Ollama
     │
     ▼
Grounded Answer
     │
     ▼
Streamlit UI
```

## 💡 How the RAG System Works

1. The user provides a documentation website URL.
2. Firecrawl crawls the website and extracts the relevant content.
3. The extracted content is cleaned and divided into smaller text chunks.
4. The chunks are converted into vector embeddings using `BAAI/bge-small-en-v1.5`.
5. The embeddings are stored in ChromaDB.
6. When the user asks a question, the system searches ChromaDB for relevant chunks.
7. The retrieved chunks are provided as context to Qwen3:8B.
8. Qwen3:8B runs locally through Ollama and generates an answer using the retrieved website evidence.
9. Streamlit displays the answer and relevant source pages.

## ⚙️ Configuration

The main model configuration is:

```text
LLM Provider: Ollama
LLM Model: Qwen3:8B
LLM Server: http://127.0.0.1:11434
Embedding Model: BAAI/bge-small-en-v1.5
Vector Database: ChromaDB
```

The project uses environment variables for configuration and API keys. Keep `.env` out of GitHub by adding it to `.gitignore`.

## ▶️ Quick Start

For a quick Colab setup, run the commands in this order:

```bash
!git clone https://github.com/lakshmiprasannaadi499-del/website-scraping-rag.git
%cd website-scraping-rag

!curl -fsSL https://ollama.com/install.sh | sh
!ollama serve > /content/ollama.log 2>&1 &

!pip install -r requirements.txt

!ollama pull qwen3:8b
!ollama list

!streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false \
    > /content/streamlit.log 2>&1 &

!cat /content/streamlit.log
```

Then:

```python
from google.colab import output

url = output.eval_js("google.colab.kernel.proxyPort(8501)")
print(url)
```

Open the printed URL to access the application.
