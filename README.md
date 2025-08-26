# Provider Directory PDF Processor

A simple Python tool that:

1. **Extracts** pages from an unstructured provider directory PDF
2. **Parses** each page to pull out detailed provider information (name, ID, specialty, address, phone, telehealth details, etc.)
3. **Stores** the cleaned, structured data into a SQL database for easy querying and reporting

This guide will walk you through setup, configuration, and use—step by step—even if you’re new to development.

---

## 📦 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [How It Works](#how-it-works)
6. [Running the Project](#running-the-project)
7. [Code Structure](#code-structure)
8. [Getting API Keys](#getting-api-keys)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)

---

## 🌟 Overview

This project (`provider_unstructured_to_structured`) takes a PDF listing of healthcare providers (often a messy, multi-column directory) and turns it into clean, row-based records in your SQL database.

* **Input:** Any PDF file of a provider directory (e.g. Humana sample PDF)
* **Processing:** Uses a combination of PDF text extraction (via `pdfplumber` or a cloud LLM parser) and a custom chain-of-thought model to reliably identify provider details.
* **Output:** A set of structured records in SQL, one row per provider, complete with name, credentials, contact info, specialties, etc.

Whether you need to integrate provider data into dashboards, analytics tools, or your own applications, this script makes it painless.

---

## 🔧 Prerequisites

Before you begin, make sure you have:

* **Python 3.8+** installed.
* **Access** to a SQL database (SQL Server, MySQL, Postgres, etc.) and credentials to write data.
* *(Optional)* An account on [OpenRouter.ai](https://openrouter.ai/) for the LLM-based parsing (if you choose the `llama_parser` option).

---

## 🚀 Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Teg-analytics/provider_pdf_processor.git
   cd provider_pdf_processor
   ```

2. **Create a virtual environment** (isolates your project’s Python packages):

   * On Windows:

     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   * On macOS / Linux:

     ```bashsource
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install required packages**

   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration

All secrets and paths live in a single file named `.env` in your project root.  Copy `.env.example` (if present) or create one yourself:

```dotenv
# PDF location
PDF_PATH=C:/Users/You/Downloads/YourProviderDirectory.pdf

# Parser choice: "pdfplumber" or "llama_parser"
PARSER=llama_parser

# Llama parser (if using "llama_parser")
LLAMA_API_KEY=llx-abcdef123456

# OpenRouter settings
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_API_BASE=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-xyz987654321
DEFAULT_LLAMA_MODEL=google/gemini-2.0-flash-001

# Database connection string: replace with your own (SQL Server, Postgres, etc.)
DATABASE_URL=Driver={SQL Server};Server=YOUR_SERVER;Database=YOUR_DB;UID=USER;PWD=PASSWORD

# Batch & timing options (optional)
BATCH_SIZE=10
STORE_INTERVAL=5
```

### Keys & Values

* `PDF_PATH`: Full path to your input PDF file.
* `PARSER`: Choose `pdfplumber` (local PDF text) or `llama_parser` (cloud LLM).
* `LLAMA_API_KEY`: Your token for llama-based PDF parsing (if used).
* `OPENROUTER_API_KEY`: Your API key from [OpenRouter.ai](https://openrouter.ai/) for the model chain.
* `DEFAULT_LLAMA_MODEL`: Name of the LLM model you prefer (Gemini, etc.).
* `DATABASE_URL`: A connection string or URL that your `db_utils` understands to connect and write to your SQL database.

> **Tip:** Never commit `.env` to Git—this keeps your secrets safe.

---

## ⚙️ How It Works

1. **PDF Extraction** (`parse.py`):

   * If `pdfplumber`, it pulls raw text and tables page-by-page.
   * If `llama_parser`, it uploads each page to a cloud LLM with special instructions to preserve every piece of text.

2. **Provider Extraction** (`provider_data_extractor.py`):

   * Takes each page’s text and runs it through a DSPy chain (backed by OpenRouter) that splits text into provider “blocks.”
   * Extracts fields (ID, name, address, specialties, telehealth info, languages, etc.) into a strict JSON schema.

3. **Storage** (`main.py` + `db_utils.py`):

   * Collects extractions in batches and writes them to your SQL database on an interval (every N seconds or M records).

---

## ▶️ Running the Project

With your environment activated and `.env` configured:

```bash
python main.py
```

You will see console logs like:

```
📄 Extracting pages from: C:/...
✅ Extracted 23 pages
✅ Extracted 8 providers from page 1
✅ Extracted 11 providers from page 2
⏳ Finalizing provider storage...
✅ Completed processing 23 pages
```

At the end, your database will contain a table (created or appended) with one row per provider.

---

## 🔍 Code Structure

```
├── config.py            # Centralizes all settings and API keys
├── main.py              # Orchestrates extraction and storage
├── parse.py             # Reads PDF pages and outputs raw text
├── provider_data_extractor.py  # Transforms text into structured JSON
├── db_utils.py          # Connects to your SQL database and writes data
├── requirements.txt     # Python dependencies
└── .env.example         # Example environment file
```

* **config.py**: Reads `.env` and exposes constants (paths, API keys, batch size).
* **main.py**: Uses `PDFExtractor` and `extract_providers()`, parallelizes page parsing, and calls `store_providers_in_sql` in batches.
* **parse.py**: Implements `PDFExtractor` class (both pdfplumber & llama-based).
* **provider\_data\_extractor.py**: Defines Pydantic models and a DSPy chain that extracts provider data in JSON form.
* **db\_utils.py**: Contains `store_providers_in_sql()`, which you can tweak to fit your database library (e.g. SQLAlchemy, ODBC).

---

## 🗝️ Getting API Keys

* **LlamaParse Key**: Follow instructions at your LlamaCloud provider to generate an API key.
* **OpenRouter Key**: Sign up at [https://openrouter.ai/](https://openrouter.ai/) and find your secret key under the API dashboard.
* **Database URL**: Connect with IT Team to get URL.

---

## 🛠️ Troubleshooting

* **Missing `.env` variables**: You’ll get a `None` or empty string—double check your `.env` spelling and that you ran `source .env` or restarted your terminal.
* **PDF parsing skips pages**: Try switching from `pdfplumber` to `llama_parser` (requires a working API key).
* **Database errors**: Confirm your `DATABASE_URL` is correct and that you can connect to your SQL instance independently (e.g. via a GUI).

---

## 🤝 Contributing

1. Fork the repo on GitHub
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m "Add feature X"`)
4. Push to your branch and open a Pull Request

Please keep your changes focused and update `README.md` if you add new environment variables or commands.

---

## 📄 License

This project is released under the [MIT License](LICENSE).

---

❤️ Built with care at HealthWorksAI by Jishu Dayal
# LLamaParse-Structuring
