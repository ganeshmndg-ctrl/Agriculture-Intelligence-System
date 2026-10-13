# Agriculture Intelligence System



A Python-based agricultural news intelligence pipeline designed to transform newspaper content into structured information relevant to Indian agriculture, agribusiness, economic developments, and government policy.



## Overview



Agriculture is influenced by developments across agricultural markets, economic policy, banking, international trade, energy, and government initiatives.



The Agriculture Intelligence System aims to bring these developments into a structured intelligence workflow rather than treating every news article as an isolated event.



The system processes newspaper PDFs, identifies relevant articles, uses AI-assisted analysis, consolidates related stories, maintains historical intelligence records, and generates daily priority reports.



## Key Features



* PDF-based newspaper text extraction.

* Article grouping and candidate detection.

* Local relevance filtering before AI analysis.

* Article validity checks.

* Gemini-assisted article analysis.

* Consolidation of related stories.

* Structured intelligence curation.

* Historical master database maintenance.

* Government intelligence and scheme knowledge resources.

* Connections between related developments.

* Daily intelligence database generation.

* Daily priority report generation.



## Architecture



The daily workflow consists of:



1\. Newspaper PDF ingestion.

2\. Text and block extraction.

3\. Cleaning and article grouping.

4\. Local relevance filtering.

5\. Article validity checks.

6\. Gemini-assisted analysis.

7\. Story consolidation.

8\. Intelligence curation.

9\. Master database updates.

10\. Government intelligence and connections processing.

11\. Daily intelligence generation.

12\. Priority report generation.



## Technology Stack



* Python

* PyMuPDF

* Pandas

* Google Gemini API

* JSON-based structured data storage

* Microsoft Word report generation



The exact package requirements will be maintained in `requirements.txt`.



## Intended Applications



* Agricultural market intelligence.

* Monitoring government schemes and policy developments.

* Agribusiness research and supply-chain analysis.

* Understanding relationships between economic developments and agriculture.

* Preparing evidence-based discussion points for management and placement interviews.



## Getting Started



### Prerequisites



* Python installed on your computer.

* Access to the Google Gemini API if AI-assisted analysis is enabled.

* Newspaper PDFs that you are authorized to process.



### Installation



Clone the repository and enter the project directory.



Install the required dependencies:



`python -m pip install -r requirements.txt`



Configure the required API credentials using a local environment file. Never commit API keys or other secrets to the repository.



### Running the Pipeline



Place the newspaper PDFs to be processed in:



`Newspapers/Raw/`



Run:



`python run\_daily\_pipeline.py`



The pipeline is designed to execute the processing stages and generate a daily priority report.



Review the configuration and data requirements before running the pipeline on a new machine.



## Data and Copyright



The repository should contain source code, documentation, and appropriately licensed or synthetic example data.



Original newspaper PDFs and extracted article collections are not included unless redistribution is authorized.



Users should verify generated information against the original sources before using it for business or policy decisions.



## Project Status



Under development.



## Author



Ganesh Genakihal



MBA / PGDM â€” Agri-Business Management



Interests: Agribusiness, agricultural sustainability, market intelligence, data analytics, and supply-chain research.




