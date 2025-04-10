from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pysparql_anything as sa
import tempfile
import os
import base64
import json
from typing import Dict, Optional, Any

# Initialize FastAPI app
app = FastAPI(
    title="RDF Converter API",
    description="API for converting various file formats to RDF using SPARQL-Anything",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request and response models
class ConversionRequest(BaseModel):
    file: str  # Base64 encoded file content
    filename: str
    query: str
    output_format: str = "ttl"
    variables: Optional[Dict[str, str]] = None
    jvm_options: Optional[list] = None

class ConversionResponse(BaseModel):
    success: bool
    result: Optional[str] = None  # Base64 encoded result
    format: Optional[str] = None
    error: Optional[str] = None

@app.post("/api/convert", response_model=ConversionResponse)
async def convert_to_rdf(request: ConversionRequest):
    try:
        # Decode file content
        file_content = base64.b64decode(request.file)
        
        # Save to temporary file
        file_ext = os.path.splitext(request.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(file_content)
            temp_file_path = tmp_file.name
        
        try:
            # Create output file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{request.output_format}") as out_file:
                output_path = out_file.name
            
            # Initialize SPARQL-Anything with JVM options
            jvm_opts = request.jvm_options if request.jvm_options else ["-Xmx2g"]
            engine = sa.SparqlAnything(*jvm_opts)
            
            # Replace {file_path} placeholder in query
            query = request.query.replace("{file_path}", temp_file_path)
            
            # Execute the query
            engine.run(
                query=query,
                format=request.output_format.lower(),
                output=output_path,
                values=request.variables
            )
            
            # Read the result
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # Clean up output file
            os.unlink(output_path)
            
            # Encode result as base64
            result_b64 = base64.b64encode(result.encode()).decode()
            
            return ConversionResponse(
                success=True,
                result=result_b64,
                format=request.output_format.lower()
            )
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    except Exception as e:
        return ConversionResponse(
            success=False,
            error=str(e)
        )

@app.get("/api/templates")
async def get_templates():
    """Return available transformation templates"""
    templates = {
        "Generic Conversion": {
            "description": "Convert any file to RDF with a basic structure",
            "query": """
PREFIX xyz: <http://sparql.xyz/facade-x/data/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX fx: <http://sparql.xyz/facade-x/ns/>

CONSTRUCT {
    ?s ?p ?o .
}
WHERE {
    SERVICE <x-sparql-anything:{file_path}> {
        ?s ?p ?o .
    }
}
"""
        },
        "JSON to People": {
            "description": "Convert JSON data to a people dataset with FOAF ontology",
            "query": """
PREFIX xyz: <http://sparql.xyz/facade-x/data/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX fx: <http://sparql.xyz/facade-x/ns/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

CONSTRUCT {
    ?person a foaf:Person ;
            foaf:name ?name ;
            foaf:age ?age ;
            foaf:mbox ?email .
}
WHERE {
    SERVICE <x-sparql-anything:{file_path}> {
        ?person xyz:name ?name .
        OPTIONAL { ?person xyz:age ?age . }
        OPTIONAL { ?person xyz:email ?email . }
    }
}
"""
        },
        "Public Procurement to RDF": {
            "description": "Convert procurement data to an RDF representation using the PCO ontology",
            "query": """
PREFIX xyz: <http://sparql.xyz/facade-x/data/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX fx: <http://sparql.xyz/facade-x/ns/>
PREFIX pco: <http://purl.org/procurement/public-contracts#>
PREFIX gr: <http://purl.org/goodrelations/v1#>
PREFIX dcterms: <http://purl.org/dc/terms/>

CONSTRUCT {
    ?contract a pco:Contract ;
             dcterms:title ?title ;
             pco:startDate ?startDate ;
             pco:endDate ?endDate ;
             pco:contractingAuthority ?authority ;
             pco:supplier ?supplier ;
             gr:valueAddedTaxIncluded ?vatIncluded ;
             gr:hasCurrencyValue ?value .

    ?authority a pco:ContractingAuthority ;
              dcterms:title ?authorityName .
              
    ?supplier a gr:BusinessEntity ;
             dcterms:title ?supplierName .
}
WHERE {
    SERVICE <x-sparql-anything:{file_path}> {
        ?contract xyz:title ?title .
        OPTIONAL { ?contract xyz:startDate ?startDate . }
        OPTIONAL { ?contract xyz:endDate ?endDate . }
        OPTIONAL { ?contract xyz:contractingAuthority ?authorityRef . }
        OPTIONAL { ?contract xyz:supplier ?supplierRef . }
        OPTIONAL { ?contract xyz:value ?value . }
        OPTIONAL { ?contract xyz:vatIncluded ?vatIncluded . }
        
        OPTIONAL { ?authorityRef xyz:name ?authorityName . }
        OPTIONAL { ?supplierRef xyz:name ?supplierName . }
        
        BIND(IRI(CONCAT("http://example.org/contract/", STRUUID())) AS ?contract)
        BIND(IRI(CONCAT("http://example.org/authority/", STRUUID())) AS ?authority)
        BIND(IRI(CONCAT("http://example.org/supplier/", STRUUID())) AS ?supplier)
    }
}
"""
        }
    }
    return templates

@app.get("/")
async def root():
    return {"message": "Welcome to the RDF Converter API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
