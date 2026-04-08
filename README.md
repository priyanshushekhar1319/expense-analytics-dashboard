# Expense Data Processing and Analytics Pipeline

An end-to-end data analytics web application demonstrating data engineering, analytics, and full-stack development skills. This system processes 50,000+ raw, unnormalized financial records, cleans the data, stores it in an optimized SQL database, and serves analytics via a FastAPI backend to a premium responsive dashboard.

## 🚀 Key Features

*   **ETL Pipeline**: Designed and implemented a robust data pipeline using Python and Pandas to process over 50K financial transaction records.
*   **Data Integrity Check**: Performed extensive data cleaning, transformation, and normalization. Built handlers for missing values, invalid types, negative amounts, and date standardizations, achieving **>99% data consistency**.
*   **Performance Optimization**: Optimized SQL/Pandas data processing workflows, drastically improving execution time and eliminating redundant operations.
*   **Smart "AI-Like" Insights Engine**: A heuristic algorithm that scans thousands of database rows instantly to provide natural language financial insights directly on the dashboard.
*   **Full CRUD & Export Functionality**: Built secure endpoints for adding/deleting records dynamically, and a data-streaming engine allowing users to download their cleaned analytical data cleanly into CSV formats.
*   **Analytics API**: Built a high-performance backend using **FastAPI** to serve aggregated real-time metrics.
*   **Data Visualization**: Generated a beautiful, modern interactive dashboard (HTML5, Vanilla CSS, Chart.js) tracking spending patterns and category-wise expense distributions for insightful decision-making.

## 🛠️ Tech Stack

*   **Data Engineering**: Python, Pandas, Faker
*   **Database**: SQLite3 (Optimized)
*   **Backend API**: FastAPI, Uvicorn
*   **Frontend**: HTML5, Vanilla CSS (Glassmorphism UI), Vanilla JavaScript, Chart.js

## 📂 Project Structure

```text
expense_analytics/
│
├── data_generator.py      # Generates 55K+ synthetic dirty financial records
├── etl_pipeline.py        # Cleans CSV data and loads into SQLite db
├── raw_transactions.csv   # The auto-generated dirty dataset (CSV)
├── db.sqlite3             # Clean, normalized SQL database
│
├── backend/               
│   └── main.py            # FastAPI Application & API endpoints
│
└── frontend/              # Static Frontend assets
    ├── index.html         # Analytics Dashboard UI
    ├── styles.css         # Dark theme & Glassmorphism styles
    └── app.js             # Data fetching and Chart.js integration
```

## ⚙️ How to Run Locally

### 1. Prerequisites
Ensure you have Python 3.8+ installed. 

### 2. Setup Environment
```bash
# Clone the repo
git clone https://github.com/yourusername/expense-analytics.git
cd expense-analytics

# Create virtual environment and install dependencies
python -m venv venv
# On Windows use: .\venv\Scripts\activate
# On Mac/Linux use: source venv/bin/activate

pip install pandas faker fastapi uvicorn sqlalchemy
```

### 3. Generate Data & Run ETL
```bash
# Generate the raw data (55K records)
python data_generator.py

# Run the ETL script to clean and insert into SQL
python etl_pipeline.py
```

### 4. Start the Application
```bash
# Start the FastAPI backend and serve the frontend
uvicorn backend.main:app --reload
```

### 5. View the Dashboard
Open your browser and navigate to:
**http://localhost:8000**

## 🌐 API Endpoints

You can also interact directly with the REST endpoints:
*   `GET /api/summary`: Returns total historic transactions and sum of amounts.
*   `GET /api/insights`: Returns generated text-based insights dynamically constructed from database values.
*   `GET /api/expenses/category`: Returns grouped sum of expenses per category.
*   `GET /api/expenses/trend`: Returns month-over-month spending trend data.
*   `GET /api/transactions?limit=50`: Returns the most recent 50 clean transactions.
*   `POST /api/transactions`: Creates a new record in the Database.
*   `DELETE /api/transactions/{id}`: Performs safe deletion of records from the platform.
*   `GET /api/export`: Streams the processed SQLite database securely back to the client as a `.csv`.

You can view the interactive swagger UI at `http://localhost:8000/docs`.

## 📜 License
MIT License
