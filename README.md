#  RDF Converter

A pure Python implementation for converting documents to RDF that works on Streamlit Cloud without requiring Java or external dependencies.

## Overview

This application is specifically designed to work on Streamlit Cloud:

- Converts XML, JSON, and CSV files to RDF (Turtle format)
- Uses pure Python implementation (no Java or external dependencies)
- Simplified interface with file preview and RDF output
- Download functionality for the generated RDF

## Deployment on Streamlit Cloud

### 1. Fork/Create a GitHub Repository

Create a new repository with these files:
- `streamlit_cloud_app.py`
- `requirements.txt`
- `README.md`

### 2. Deploy on Streamlit Cloud

1. Go to [Streamlit Cloud](https://streamlit.io/cloud)
2. Sign in with your GitHub account
3. Select "New app"
4. Select your repository, branch, and the `streamlit_cloud_app.py` file
5. Click "Deploy"

## How It Works

Instead of using the SPARQL-Anything library (which requires Java), this application:

1. Parses files using standard Python libraries (xml.etree, json, pandas)
2. Implements custom logic to convert the parsed data to RDF Turtle format
3. Generates RDF triples that roughly follow the Facade-X model
4. Returns the RDF for display and download

## Limitations

This pure Python implementation has some limitations compared to the full SPARQL-Anything toolkit:

- Only supports XML, JSON, and CSV files (not Excel, HTML, etc.)
- Uses a simplified RDF transformation model 
- Does not support SPARQL queries for transformation
- Limited customization options

## Future Improvements

If you need the full power of SPARQL-Anything in the cloud:

1. Consider deploying on a platform that supports Java (Heroku, AWS, etc.)
2. Build a containerized version with Docker that includes both Python and Java
3. Use a serverless function to handle the transformation as a backend service
