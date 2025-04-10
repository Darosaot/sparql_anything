import os
import tempfile
import sys
import streamlit as st
import base64

# Create a fixed temporary directory for the SPARQL Anything JAR
TEMP_DIR = tempfile.gettempdir()

# Monkey patch approach to fix permission issues
# Import pysparql_anything modules without initializing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# First, try to import without initialization to modify the download path
import pysparql_anything.utilities as sa_utilities
import pysparql_anything.__about__ as sa_about

# Store the original download function
original_download = sa_utilities.download_sparql_anything

# Create a new download function that uses the temp directory
def patched_download_sparql_anything(ghub, uri, version):
    """Patched download function that uses a temporary directory"""
    # Use the predefined temp directory
    jarname = f"sparql-anything-{version}.jar"
    path2jar = os.path.join(TEMP_DIR, jarname)
    
    # Print for debugging
    print(f"Downloading SPARQL Anything JAR to: {path2jar}")
    
    # Check if JAR already exists to avoid redownloading
    if os.path.exists(path2jar):
        print(f"JAR already exists at: {path2jar}")
        sa_about.__jarPath__ = path2jar
        return path2jar
    
    # Use the original function's logic but with the new path
    dl_link = sa_utilities.get_release_uri(ghub, uri, version)
    import requests
    from tqdm import tqdm
    
    request = requests.get(dl_link, stream=True, timeout=10.0)
    length = int(request.headers.get('content-length', 0))
    
    with open(path2jar, 'wb') as jar:
        with tqdm(colour='green', total=length, unit='iB', unit_scale=True, 
                 unit_divisor=1024) as pbar:
            for data in request.iter_content(chunk_size=1024):
                jar.write(data)
                pbar.update(len(data))
    
    # Set this path as the jar path for SPARQL Anything
    sa_about.__jarPath__ = path2jar
    
    return path2jar

# Replace the original function with our patched version
sa_utilities.download_sparql_anything = patched_download_sparql_anything

# Now import the actual package after the monkey patching
import pysparql_anything as sa

def get_download_link(content, filename, link_text):
    """Generate a download link for file content"""
    # Encode content as base64
    b64 = base64.b64encode(content.encode()).decode()
    
    # Create download link
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def main():
    st.set_page_config(
        page_title="Simple RDF Converter",
        page_icon="🔄",
        layout="wide",
    )
    
    st.title("Simple RDF Converter")
    st.markdown("Upload a document and transform it to RDF using SPARQL-Anything")
    
    # Create a simple one-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Upload File")
        # File uploader
        uploaded_file = st.file_uploader("Upload a file (XML, JSON, CSV, etc.)", type=None)
        
        if uploaded_file is not None:
            # Save uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_file_path = tmp_file.name
            
            st.success(f"File uploaded: {uploaded_file.name}")
            
            # Fixed transformation query (Generic)
            query = f"""
PREFIX xyz: <http://sparql.xyz/facade-x/data/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX fx: <http://sparql.xyz/facade-x/ns/>

CONSTRUCT {{
    ?s ?p ?o .
}}
WHERE {{
    SERVICE <x-sparql-anything:{temp_file_path}> {{
        ?s ?p ?o .
    }}
}}
"""
            
            st.subheader("SPARQL Query")
            st.code(query, language="sparql")
            
            # Fixed output format (TTL)
            output_format = "ttl"
            
            # Transform button
            if st.button("Transform to RDF"):
                try:
                    with st.spinner("Transforming..."):
                        # Initialize SPARQL-Anything with minimal JVM options
                        engine = sa.SparqlAnything("-Xmx512m")
                        
                        # Create a temporary file for output
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}") as out_file:
                            output_path = out_file.name
                        
                        # Execute the query
                        engine.run(
                            query=query,
                            format=output_format,
                            output=output_path
                        )
                        
                        # Read the result
                        with open(output_path, 'r', encoding='utf-8') as f:
                            result = f.read()
                        
                        # Save result to session state
                        st.session_state.result = result
                        
                        # Clean up output file
                        os.unlink(output_path)
                    
                except Exception as e:
                    st.error(f"Error during transformation: {str(e)}")
                
                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)
    
    with col2:
        st.header("RDF Output")
        if 'result' in st.session_state:
            # Display result
            st.code(st.session_state.result, language='turtle')
            
            # Provide download link
            download_link = get_download_link(
                st.session_state.result, 
                f"result.ttl", 
                f"Download RDF (Turtle format)"
            )
            st.markdown(download_link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
