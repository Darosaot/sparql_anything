import streamlit as st
import pysparql_anything as sa
import tempfile
import os
import base64
import json
import time
from datetime import datetime
import uuid
import pandas as pd

# Define transformation templates
TEMPLATES = {
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

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'saved_configs' not in st.session_state:
    st.session_state.saved_configs = {}

def generate_default_query(file_path):
    """Generate a default SPARQL query based on the file path"""
    # Replace {file_path} placeholder with actual file path
    base_query = """
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
}"""
    return base_query.replace("{file_path}", file_path)

def get_download_link(content, filename, link_text):
    """Generate a download link for file content"""
    # Encode content as base64
    b64 = base64.b64encode(content.encode()).decode()
    
    # Create download link
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def main():
    st.set_page_config(
        page_title="RDF Converter",
        page_icon="🔄",
        layout="wide",
    )
    
    st.title("RDF Converter - Powered by SPARQL-Anything")
    st.markdown("Convert various file formats to RDF with ease using SPARQL-Anything")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        output_format = st.selectbox(
            "Output Format",
            ["TTL", "JSON", "XML", "CSV", "TEXT", "NT", "NQ"],
            index=0
        )
        
        advanced_options = st.expander("Advanced Options")
        with advanced_options:
            jvm_options = st.text_input("JVM Options (comma separated)", "-Xmx2g")
        
        # Templates section
        st.header("Templates")
        template_names = list(TEMPLATES.keys())
        selected_template = st.selectbox(
            "Transformation Templates", 
            ["None"] + template_names
        )
        
        if selected_template != "None":
            st.info(TEMPLATES[selected_template]["description"])
            
        # Saved configurations
        if st.session_state.saved_configs:
            st.header("Saved Configurations")
            saved_config_names = list(st.session_state.saved_configs.keys())
            selected_config = st.selectbox(
                "Load Configuration", 
                ["None"] + saved_config_names
            )
            
            if selected_config != "None":
                st.info(f"This will load your saved configuration: {selected_config}")
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app uses [SPARQL-Anything](https://sparql-anything.cc/) to convert files to RDF.")
    
    # Main content tabs
    tabs = st.tabs(["File Conversion", "Batch Processing", "Transformation History", "About"])
    
    with tabs[0]:  # File Conversion tab
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.header("Input")
            # File uploader
            uploaded_file = st.file_uploader("Upload a file", type=None)
            
            if uploaded_file is not None:
                # Save uploaded file to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_file_path = tmp_file.name
                
                st.success(f"File uploaded: {uploaded_file.name}")
                
                # Get query content
                st.subheader("SPARQL Query")
                
                # Check if we should load from saved config
                if 'selected_config' in locals() and selected_config != "None":
                    config = st.session_state.saved_configs[selected_config]
                    default_query = config["query"].replace("{file_path}", temp_file_path)
                    default_variables = config.get("variables", {})
                    default_format = config.get("output_format", output_format)
                # Use template if selected
                elif selected_template != "None":
                    default_query = TEMPLATES[selected_template]["query"].replace("{file_path}", temp_file_path)
                    default_variables = {}
                    default_format = output_format
                else:
                    default_query = generate_default_query(temp_file_path)
                    default_variables = {}
                    default_format = output_format
                
                query_text = st.text_area(
                    "Enter your SPARQL query here",
                    value=default_query,
                    height=200
                )
                
                # Parse variable placeholders
                variables = {}
                if st.checkbox("Add query variables"):
                    num_vars = st.number_input("Number of variables", min_value=1, max_value=10, value=1)
                    
                    for i in range(num_vars):
                        col_var, col_val = st.columns(2)
                        with col_var:
                            var_name = st.text_input(f"Variable name #{i+1}", 
                                                    value=list(default_variables.keys())[i] if i < len(default_variables) else "")
                        with col_val:
                            var_value = st.text_input(f"Value #{i+1}", 
                                                     value=list(default_variables.values())[i] if i < len(default_variables) else "")
                        
                        if var_name and var_value:
                            variables[var_name] = var_value
                
                # Save configuration option
                save_config = st.checkbox("Save this configuration for future use")
                config_name = None
                if save_config:
                    config_name = st.text_input("Configuration name")
                
                # Execute query button
                if st.button("Transform to RDF"):
                    try:
                        with st.spinner("Transforming..."):
                            # Initialize SPARQL-Anything with JVM options
                            jvm_opts = [opt.strip() for opt in jvm_options.split(",")] if jvm_options else []
                            engine = sa.SparqlAnything(*jvm_opts)
                            
                            # Create a temporary file for output
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format.lower()}") as out_file:
                                output_path = out_file.name
                            
                            # Execute the query
                            start_time = time.time()
                            engine.run(
                                query=query_text,
                                format=output_format.lower(),
                                output=output_path,
                                values=variables if variables else None
                            )
                            end_time = time.time()
                            
                            # Read the result
                            with open(output_path, 'r', encoding='utf-8') as f:
                                result = f.read()
                            
                            # Clean up output file
                            os.unlink(output_path)
                        
                        # Store result in session state for display
                        st.session_state.result = result
                        st.session_state.result_format = output_format.lower()
                        
                        # Save to history
                        history_entry = {
                            "id": str(uuid.uuid4()),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "filename": uploaded_file.name,
                            "query": query_text,
                            "variables": variables,
                            "output_format": output_format.lower(),
                            "duration": round(end_time - start_time, 2),
                            "result": result[:1000] + "..." if len(result) > 1000 else result,
                            "full_result": result
                        }
                        st.session_state.history.append(history_entry)
                        
                        # Save configuration if requested
                        if save_config and config_name:
                            st.session_state.saved_configs[config_name] = {
                                "query": query_text,
                                "variables": variables,
                                "output_format": output_format
                            }
                            st.success(f"Configuration '{config_name}' saved!")
                        
                    except Exception as e:
                        st.error(f"Error during transformation: {str(e)}")
                    
                    finally:
                        # Clean up temporary file
                        os.unlink(temp_file_path)
        
        with col2:
            st.header("Output")
            if 'result' in st.session_state:
                st.subheader(f"Result ({st.session_state.result_format})")
                
                # Display result based on format
                if st.session_state.result_format in ['json']:
                    try:
                        st.json(json.loads(st.session_state.result))
                    except:
                        st.text(st.session_state.result)
                elif st.session_state.result_format in ['ttl', 'nt', 'nq']:
                    st.code(st.session_state.result, language='turtle')
                elif st.session_state.result_format in ['xml']:
                    st.code(st.session_state.result, language='xml')
                else:
                    st.text(st.session_state.result)
                
                # Provide download link
                file_extension = st.session_state.result_format
                download_link = get_download_link(
                    st.session_state.result, 
                    f"result.{file_extension}", 
                    f"Download result as {file_extension.upper()}"
                )
                st.markdown(download_link, unsafe_allow_html=True)
    
    with tabs[1]:  # Batch Processing tab
        st.header("Batch Processing")
        st.markdown("Upload multiple files and process them in batch.")
        
        # Batch file uploader
        uploaded_files = st.file_uploader("Upload files", type=None, accept_multiple_files=True)
        
        if uploaded_files:
            st.success(f"{len(uploaded_files)} files uploaded")
            
            # Display file list
            file_df = pd.DataFrame({
                "Filename": [file.name for file in uploaded_files],
                "Size (KB)": [round(file.size / 1024, 2) for file in uploaded_files],
                "Type": [os.path.splitext(file.name)[1] for file in uploaded_files]
            })
            st.dataframe(file_df)
            
            # Query input
            st.subheader("SPARQL Query Template")
            
            # Use template if selected
            if selected_template != "None":
                default_query = TEMPLATES[selected_template]["query"]
            else:
                default_query = """
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
            
            query_template = st.text_area(
                "Enter your SPARQL query template (use {file_path} for file path)",
                value=default_query,
                height=200
            )
            
            # Batch processing options
            col1, col2 = st.columns(2)
            with col1:
                batch_output_format = st.selectbox(
                    "Output Format for Batch",
                    ["TTL", "JSON", "XML", "CSV", "TEXT", "NT", "NQ"],
                    index=0
                )
            with col2:
                output_method = st.radio(
                    "Output Method",
                    ["Individual Files", "Combined File"]
                )
            
            # Process batch button
            if st.button("Process Batch"):
                with st.spinner(f"Processing {len(uploaded_files)} files..."):
                    # Initialize results container
                    batch_results = []
                    
                    # Initialize SPARQL-Anything with JVM options
                    jvm_opts = [opt.strip() for opt in jvm_options.split(",")] if jvm_options else []
                    engine = sa.SparqlAnything(*jvm_opts)
                    
                    # Create output directory
                    output_dir = tempfile.mkdtemp()
                    
                    # Process each file
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, file in enumerate(uploaded_files):
                        status_text.text(f"Processing file {i+1} of {len(uploaded_files)}: {file.name}")
                        
                        try:
                            # Save file to temporary location
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
                                tmp_file.write(file.getvalue())
                                temp_file_path = tmp_file.name
                            
                            # Create output file path
                            output_filename = f"{os.path.splitext(file.name)[0]}.{batch_output_format.lower()}"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            # Execute query
                            file_query = query_template.replace("{file_path}", temp_file_path)
                            start_time = time.time()
                            engine.run(
                                query=file_query,
                                format=batch_output_format.lower(),
                                output=output_path
                            )
                            end_time = time.time()
                            
                            # Read result
                            with open(output_path, 'r', encoding='utf-8') as f:
                                result = f.read()
                            
                            # Store result
                            batch_results.append({
                                "filename": file.name,
                                "output_path": output_path,
                                "result": result,
                                "success": True,
                                "duration": round(end_time - start_time, 2)
                            })
                            
                            # Clean up temporary file
                            os.unlink(temp_file_path)
                            
                        except Exception as e:
                            batch_results.append({
                                "filename": file.name,
                                "error": str(e),
                                "success": False
                            })
                        
                        # Update progress
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    status_text.text("Processing complete!")
                    
                    # Prepare download options
                    if output_method == "Combined File" and all(r["success"] for r in batch_results):
                        # Combine all results
                        combined_result = "\n\n".join([r["result"] for r in batch_results])
                        combined_path = os.path.join(output_dir, f"combined_results.{batch_output_format.lower()}")
                        
                        with open(combined_path, 'w', encoding='utf-8') as f:
                            f.write(combined_result)
                        
                        with open(combined_path, 'r', encoding='utf-8') as f:
                            combined_data = f.read()
                        
                        # Provide download link for combined file
                        st.success("Batch processing successful. You can download the combined file:")
                        combined_link = get_download_link(
                            combined_data,
                            f"combined_results.{batch_output_format.lower()}",
                            f"Download Combined Results"
                        )
                        st.markdown(combined_link, unsafe_allow_html=True)
                    
                    # Show individual results
                    st.subheader("Batch Processing Results")
                    result_df = pd.DataFrame([
                        {
                            "Filename": r["filename"],
                            "Status": "Success" if r["success"] else "Failed",
                            "Duration (s)": r.get("duration", None),
                            "Error": r.get("error", "") if not r["success"] else ""
                        } for r in batch_results
                    ])
                    st.dataframe(result_df)
                    
                    # Provide individual download links
                    if output_method == "Individual Files":
                        st.subheader("Download Individual Files")
                        for r in batch_results:
                            if r["success"]:
                                file_link = get_download_link(
                                    r["result"],
                                    f"{os.path.splitext(r['filename'])[0]}.{batch_output_format.lower()}",
                                    f"Download {r['filename']} result"
                                )
                                st.markdown(file_link, unsafe_allow_html=True)
    
    with tabs[2]:  # Transformation History tab
        st.header("Transformation History")
        
        if not st.session_state.history:
            st.info("No transformations yet. Convert some files to see your history.")
        else:
            # Display history in a dataframe
            history_df = pd.DataFrame([
                {
                    "Timestamp": h["timestamp"],
                    "Filename": h["filename"],
                    "Format": h["output_format"].upper(),
                    "Duration (s)": h["duration"]
                } for h in st.session_state.history
            ])
            st.dataframe(history_df)
            
            # Allow viewing details of specific entries
            if st.session_state.history:
                selected_entry = st.selectbox(
                    "Select an entry to view details",
                    [f"{h['timestamp']} - {h['filename']}" for h in st.session_state.history]
                )
                
                selected_index = [i for i, h in enumerate(st.session_state.history) 
                                 if f"{h['timestamp']} - {h['filename']}" == selected_entry][0]
                entry = st.session_state.history[selected_index]
                
                st.subheader("Transformation Details")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Timestamp:** {entry['timestamp']}")
                    st.markdown(f"**Filename:** {entry['filename']}")
                    st.markdown(f"**Output Format:** {entry['output_format'].upper()}")
                    st.markdown(f"**Duration:** {entry['duration']} seconds")
                    
                    if entry['variables']:
                        st.markdown("**Variables:**")
                        for var, value in entry['variables'].items():
                            st.markdown(f"- {var}: {value}")
                
                with col2:
                    # Provide download link
                    download_link = get_download_link(
                        entry['full_result'],
                        f"result_{entry['id']}.{entry['output_format']}",
                        "Download Result"
                    )
                    st.markdown(download_link, unsafe_allow_html=True)
                    
                    # Option to reuse query
                    if st.button("Reuse this query"):
                        st.session_state.reuse_query = entry['query']
                        st.session_state.reuse_format = entry['output_format']
                        st.session_state.reuse_variables = entry['variables']
                        st.success("Query configuration copied! Go to the Single File tab to use it.")
                
                # Show query
                st.subheader("Query")
                st.code(entry['query'], language='sparql')
                
                # Show result preview
                st.subheader("Result Preview")
                if entry['output_format'] in ['json']:
                    try:
                        st.json(json.loads(entry['result']))
                    except:
                        st.text(entry['result'])
                elif entry['output_format'] in ['ttl', 'nt', 'nq']:
                    st.code(entry['result'], language='turtle')
                elif entry['output_format'] in ['xml']:
                    st.code(entry['result'], language='xml')
                else:
                    st.text(entry['result'])
    
    with tabs[3]:  # About tab
        st.header("About this Application")
        st.markdown("""
        ## RDF Converter Powered by SPARQL-Anything
        
        This application leverages the capabilities of SPARQL-Anything to transform various file formats into RDF data.
        
        ### Features
        
        - **Universal Format Support**: Convert JSON, XML, CSV, Excel, HTML, and many other formats to RDF
        - **Batch Processing**: Transform multiple files at once with the same query template
        - **Transformation Templates**: Pre-defined query templates for common conversion patterns
        - **Custom SPARQL Queries**: Create your own transformation logic using SPARQL
        - **Multiple Output Formats**: Generate RDF in various serialization formats (Turtle, JSON-LD, N-Triples, etc.)
        - **Transformation History**: Track past conversions and reuse successful queries
        - **Configuration Management**: Save and load transformation settings
        
        ### How it Works
        
        The app uses PySPARQL-Anything, a Python wrapper for the SPARQL-Anything tool. SPARQL-Anything implements the Façade-X meta-model, which maps source data structures onto RDF components without requiring upfront schema knowledge.
        
        ### Use Cases
        
        - **Data Integration**: Harmonize data from diverse sources into a unified RDF representation
        - **Knowledge Graph Construction**: Build knowledge graphs from various organizational data assets
        - **Legacy Data Migration**: Convert legacy data formats into modern, semantic representations
        - **Open Data Publishing**: Transform government or organizational data into linked open data
        - **Public Procurement Analysis**: Convert procurement data from different formats to a standard RDF model
        """)

if __name__ == "__main__":
    main()
