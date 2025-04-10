import streamlit as st
import pandas as pd
import io
import re
import xml.etree.ElementTree as ET
import json
import csv

def main():
    st.set_page_config(
        page_title="Simple RDF Converter",
        page_icon="🔄",
        layout="wide",
    )
    
    st.title("Simple RDF Converter for Streamlit Cloud")
    st.markdown("Upload a document and transform it to basic RDF")
    
    # Create a simple two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Upload File")
        
        # File uploader
        uploaded_file = st.file_uploader("Upload a file (XML, JSON, CSV)", type=["xml", "json", "csv"])
        
        if uploaded_file is not None:
            # Determine file type
            file_type = uploaded_file.name.split('.')[-1].lower()
            st.success(f"File uploaded: {uploaded_file.name}")
            
            # Display file preview
            st.subheader("File Preview")
            try:
                if file_type == 'xml':
                    # Parse XML content
                    xml_content = uploaded_file.getvalue().decode('utf-8')
                    st.code(xml_content[:1000] + "..." if len(xml_content) > 1000 else xml_content, language="xml")
                elif file_type == 'json':
                    # Parse JSON content
                    json_content = json.load(uploaded_file)
                    st.json(json_content)
                elif file_type == 'csv':
                    # Parse CSV content
                    df = pd.read_csv(uploaded_file)
                    st.dataframe(df.head())
            except Exception as e:
                st.error(f"Error previewing file: {str(e)}")
            
            # Transform button
            if st.button("Transform to RDF"):
                try:
                    with st.spinner("Transforming..."):
                        # Reset file pointer
                        uploaded_file.seek(0)
                        
                        # Transform based on file type
                        if file_type == 'xml':
                            rdf_content = convert_xml_to_rdf(uploaded_file)
                        elif file_type == 'json':
                            rdf_content = convert_json_to_rdf(uploaded_file)
                        elif file_type == 'csv':
                            rdf_content = convert_csv_to_rdf(uploaded_file)
                        else:
                            st.error(f"Unsupported file type: {file_type}")
                            return
                        
                        # Save result to session state
                        st.session_state.result = rdf_content
                    
                except Exception as e:
                    st.error(f"Error during transformation: {str(e)}")
    
    with col2:
        st.header("RDF Output")
        if 'result' in st.session_state:
            # Display result
            st.code(st.session_state.result, language='turtle')
            
            # Provide download link
            st.download_button(
                label="Download RDF (Turtle format)",
                data=st.session_state.result,
                file_name="result.ttl",
                mime="text/turtle"
            )

def convert_xml_to_rdf(xml_file):
    """Convert XML to basic RDF Turtle format"""
    try:
        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Create RDF turtle representation
        rdf = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix fx: <http://sparql.xyz/facade-x/ns/> .",
            "@prefix xyz: <http://sparql.xyz/facade-x/data/> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            ""
        ]
        
        # Function to generate a safe URI
        def safe_uri(text):
            if text is None:
                return "item_" + str(hash(str(id)))
            # Remove special characters and spaces
            return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
        
        # Process all elements
        def process_element(element, parent_path=""):
            element_path = parent_path + "/" + element.tag
            element_id = safe_uri(element_path)
            
            # Add basic type
            rdf.append(f"<http://example.org/{element_id}> a fx:root ;")
            rdf.append(f"    rdfs:label \"{element.tag}\" ;")
            
            # Add attributes
            for attr_name, attr_value in element.attrib.items():
                safe_attr = safe_uri(attr_name)
                rdf.append(f"    xyz:{safe_attr} \"{attr_value}\" ;")
            
            # Add text content if any
            if element.text and element.text.strip():
                text_content = element.text.strip().replace('"', '\\"')
                rdf.append(f"    xyz:hasContent \"{text_content}\" ;")
            
            # Process children
            for i, child in enumerate(element):
                child_id = safe_uri(element_path + "/" + child.tag + f"_{i}")
                rdf.append(f"    xyz:hasChild <http://example.org/{child_id}> ;")
            
            # Close statement
            rdf[-1] = rdf[-1][:-2] + "."
            
            # Process all children
            for i, child in enumerate(element):
                process_element(child, element_path)
        
        # Start processing from root
        process_element(root)
        
        return "\n".join(rdf)
    
    except Exception as e:
        raise Exception(f"Error converting XML to RDF: {str(e)}")

def convert_json_to_rdf(json_file):
    """Convert JSON to basic RDF Turtle format"""
    try:
        # Parse JSON
        json_data = json.load(json_file)
        
        # Create RDF turtle representation
        rdf = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix fx: <http://sparql.xyz/facade-x/ns/> .",
            "@prefix xyz: <http://sparql.xyz/facade-x/data/> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            ""
        ]
        
        # Function to generate a safe URI
        def safe_uri(text):
            if text is None:
                return "item_" + str(hash(str(id)))
            # Remove special characters and spaces
            return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
        
        # Process JSON object
        def process_json(data, path="root", is_array_item=False):
            node_id = safe_uri(path)
            
            if isinstance(data, dict):
                # Create node
                rdf.append(f"<http://example.org/{node_id}> a fx:object ;")
                
                # Add all properties
                for key, value in data.items():
                    safe_key = safe_uri(key)
                    
                    if isinstance(value, (dict, list)):
                        child_path = f"{path}/{safe_key}"
                        child_id = safe_uri(child_path)
                        rdf.append(f"    xyz:{safe_key} <http://example.org/{child_id}> ;")
                        process_json(value, child_path)
                    else:
                        # Handle primitive values
                        if isinstance(value, str):
                            escaped_value = value.replace('"', '\\"').replace('\n', '\\n')
                            rdf.append(f"    xyz:{safe_key} \"{escaped_value}\" ;")
                        elif value is None:
                            rdf.append(f"    xyz:{safe_key} \"null\" ;")
                        else:
                            rdf.append(f"    xyz:{safe_key} {str(value)} ;")
                
                # Close statement
                if rdf[-1].endswith(" ;"):
                    rdf[-1] = rdf[-1][:-2] + "."
                else:
                    rdf.append(".")
                    
            elif isinstance(data, list):
                # Create array node
                rdf.append(f"<http://example.org/{node_id}> a fx:array ;")
                rdf.append(f"    rdfs:label \"array\" ;")
                
                # Add array items
                for i, item in enumerate(data):
                    item_path = f"{path}/item_{i}"
                    item_id = safe_uri(item_path)
                    rdf.append(f"    xyz:item_{i} <http://example.org/{item_id}> ;")
                    process_json(item, item_path, True)
                
                # Close statement
                if rdf[-1].endswith(" ;"):
                    rdf[-1] = rdf[-1][:-2] + "."
                else:
                    rdf.append(".")
            
            elif is_array_item:
                # Create node for primitive array item
                rdf.append(f"<http://example.org/{node_id}> a fx:value ;")
                
                if isinstance(data, str):
                    escaped_value = data.replace('"', '\\"').replace('\n', '\\n')
                    rdf.append(f"    xyz:hasValue \"{escaped_value}\" .")
                elif data is None:
                    rdf.append(f"    xyz:hasValue \"null\" .")
                else:
                    rdf.append(f"    xyz:hasValue {str(data)} .")
        
        # Start processing from root
        process_json(json_data)
        
        return "\n".join(rdf)
    
    except Exception as e:
        raise Exception(f"Error converting JSON to RDF: {str(e)}")

def convert_csv_to_rdf(csv_file):
    """Convert CSV to basic RDF Turtle format"""
    try:
        # Parse CSV
        df = pd.read_csv(csv_file)
        
        # Create RDF turtle representation
        rdf = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix fx: <http://sparql.xyz/facade-x/ns/> .",
            "@prefix xyz: <http://sparql.xyz/facade-x/data/> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            ""
        ]
        
        # Add dataset node
        rdf.append("<http://example.org/dataset> a fx:root ;")
        rdf.append("    rdfs:label \"CSV Dataset\" ;")
        
        # Add rows
        for i, (_, row) in enumerate(df.iterrows()):
            row_id = f"row_{i}"
            rdf.append(f"    xyz:{row_id} <http://example.org/{row_id}> ;")
        
        # Close dataset statement
        rdf[-1] = rdf[-1][:-2] + "."
        rdf.append("")
        
        # Function to generate a safe URI
        def safe_uri(text):
            if text is None:
                return "item_" + str(hash(str(id)))
            # Remove special characters and spaces
            return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
        
        # Process each row
        for i, (_, row) in enumerate(df.iterrows()):
            row_id = f"row_{i}"
            rdf.append(f"<http://example.org/{row_id}> a fx:row ;")
            rdf.append(f"    rdfs:label \"Row {i}\" ;")
            
            # Add all columns
            for col in df.columns:
                safe_col = safe_uri(col)
                value = row[col]
                
                if pd.isna(value):
                    rdf.append(f"    xyz:{safe_col} \"\" ;")
                elif isinstance(value, str):
                    escaped_value = value.replace('"', '\\"').replace('\n', '\\n')
                    rdf.append(f"    xyz:{safe_col} \"{escaped_value}\" ;")
                else:
                    rdf.append(f"    xyz:{safe_col} {str(value)} ;")
            
            # Close row statement
            rdf[-1] = rdf[-1][:-2] + "."
        
        return "\n".join(rdf)
    
    except Exception as e:
        raise Exception(f"Error converting CSV to RDF: {str(e)}")

if __name__ == "__main__":
    main()
