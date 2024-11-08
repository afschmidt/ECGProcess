#!/usr/bin/env python3
'''
A module to extract, metadata, median beats and raw waveforms from ECG XMLs.
'''
import xmltodict
from lxml import etree

xml_file='example_data/example_datasets/example-XML1.xml'
xsd_file='example_data/example_datasets/example-XML1_d.xsd'
strict=False
verbose=True

def validate_xml(xml_file, xsd_file, strict=True):
    """
    Validates an XML file against an XSD schema.
    
    Parameters:
        xml_file (str): Path to the XML file.
        xsd_file (str): Path to the XSD file.
        strict (bool): If False, ignores elements in the XML that are not in the XSD.
        
    Returns:
        xml_doc (etree._ElementTree or None): The parsed XML document if valid, else None.
    """
    # Load the XSD schema
    with open(xsd_file, 'rb') as xsd:
        schema_root = etree.XML(xsd.read())
    schema = etree.XMLSchema(schema_root)
    
    # Parse the XML file
    with open(xml_file, 'rb') as xml:
        xml_doc = etree.parse(xml)
    
    # Try validating the XML file against the XSD schema
    is_valid = schema.validate(xml_doc)
    
    # If strict mode is off, filter out unexpected element errors
    if not is_valid and not strict:
        filtered_errors = [error for error in schema.error_log if "expected" not in error.message]
        is_valid = len(filtered_errors) == 0
        if is_valid:
            print("XML file is valid (ignoring unexpected elements).")
        else:
            print("XML file is invalid.")
            for error in filtered_errors:
                print(error.message)
    elif is_valid:
        print("XML file is valid.")
    else:
        print("XML file is invalid.")
        # Print validation errors
        for error in schema.error_log:
            print(error.message)
                
    return xml_doc if is_valid else None


def xml_to_dict(xml_doc):
    """
    Converts an lxml ElementTree document to a Python dictionary.
    
    Parameters:
        xml_doc (etree._ElementTree): The validated XML document.
        
    Returns:
        dict: A dictionary representation of the XML data.
    """
    # Convert the ElementTree document to a string
    xml_str = etree.tostring(xml_doc, encoding='utf-8')
    
    # Parse the XML string to a dictionary
    xml_dict = xmltodict.parse(xml_str)
    
    return xml_dict

def flatten_dict(d, parent_key='', sep='.', skip_root=False):
    """
    Recursively flattens a nested dictionary, optionally skipping the root element.
    
    Parameters:
        d (dict): The dictionary to flatten.
        parent_key (str): The base key string for recursion (used for nested keys).
        sep (str): The separator to use for the keys.
        skip_root (bool): If True, skips the first level (root) key.
        
    Returns:
        dict: A flattened dictionary.
    """
    items = []
    
    # If skipping the root, adjust d to be the first nested dictionary level
    if skip_root and isinstance(d, dict) and len(d) == 1:
        root_key, d = next(iter(d.items()))
    
    for k, v in d.items():
        # print(k)
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        # print(new_key)
        if isinstance(v, dict):
            # Only recurse if v is a dictionary and not None
            if v is not None:
                items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Iterate over list items, flattening each with an index
            for i, item in enumerate(v):
                # Only recurse if item is not None
                if item is not None and isinstance(item, dict):
                    items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
                else:
                    # Directly add non-dictionary list items
                    items.append((f"{new_key}[{i}]", item))
        else:
            # Add simple values (str, int, etc.) directly
            items.append((new_key, v))
    return dict(items)


# Strict mode: True for strict validation, False to ignore unexpected elements
validated_doc = validate_xml(xml_file, xsd_file, strict=False)
# xml_data_dict = xml_to_dict(validated_doc)
# flattened_dict = flatten_dict(xml_data_dict)
# NOTE the validation in validate_xml is optional.
# can also simply call
    # # Parse the XML file
    # with open(xml_file, 'rb') as xml:
    #     xml_doc = etree.parse(xml)
flattened_dict['CardiologyXML.RestingECGMeasurements.PQInterval.#text']

# xml_data_dict['CardiologyXML']['RestingECGMeasurements']

# if validated_doc:
#     # If valid, you can parse or manipulate the XML as needed
#     root = validated_doc.getroot()
#     print("Root element:", root.tag)
