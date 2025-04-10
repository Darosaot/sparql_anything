# RDF Converter

A minimalist Streamlit application that uses SPARQL-Anything to convert various file formats to RDF.

## Overview

This simplified application focuses on the core functionality:
- Upload a single file (XML, JSON, CSV, etc.)
- Transform it to RDF (Turtle format)
- Display and download the results

## Requirements

- Python 3.8 or higher
- Java 11 or higher (required for SPARQL-Anything)

## Deployment Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Proper Permissions for Temp Directory

SPARQL-Anything needs to download a JAR file to a temporary directory. Make sure the app has write permissions to the temp directory:

```bash
# Check the default temp directory
python -c "import tempfile; print(tempfile.gettempdir())"

# Ensure write permissions
chmod -R 777 /your/temp/directory
```

### 3. Run the Application

```bash
streamlit run simplified_app.py
```

## Troubleshooting Permission Issues

If you still encounter permission issues when deploying:

1. **Pre-download the JAR file**: You can manually download the SPARQL-Anything JAR and place it in the temp directory:
   ```bash
   mkdir -p /tmp/sparql-anything
   wget https://github.com/SPARQL-Anything/sparql.anything/releases/download/v0.8.2/sparql-anything-0.8.2.jar -O /tmp/sparql-anything/sparql-anything-0.8.2.jar
   chmod 755 /tmp/sparql-anything/sparql-anything-0.8.2.jar
   ```

2. **Set environment variable**: Modify the app to use a specific directory for the JAR:
   ```bash
   export SPARQL_ANYTHING_JAR_DIR=/path/to/writable/directory
   ```

3. **Run with elevated permissions**: If deploying in a Docker container, ensure the container has proper permissions.

## How It Works

1. The application patches the SPARQL-Anything library to use a fixed temporary directory
2. When a file is uploaded, it's saved to a temporary location
3. A simple SPARQL query is constructed to transform the file to RDF
4. The SPARQL-Anything engine processes the query and returns the result as Turtle (TTL) format
5. The result is displayed and made available for download
