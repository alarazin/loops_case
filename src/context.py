import json
import pandas as pd
from typing import Dict, Any
import os
import io
from google.cloud import storage

# --- Configuration ---
# It's good practice to centralize configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "alara-case-study-bucket")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "alara-case-study")
SPEC_CATALOG_PATH = "spec_catalog.csv"

def load_spec_catalog() -> pd.DataFrame:
    """Loads the product specification catalog from Google Cloud Storage."""
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(SPEC_CATALOG_PATH)
        
        print(f"Loading spec catalog from GCS: gs://{GCS_BUCKET_NAME}/{SPEC_CATALOG_PATH}")
        
        content = blob.download_as_string()
        csv_file = io.StringIO(content.decode('utf-8'))
        
        df = pd.read_csv(csv_file)
        # Convert to a more useful dictionary structure, indexed by SKU
        return df.set_index('sku').to_dict('index')
    except Exception as e:
        raise FileNotFoundError(f"Specification file not found at gs://{GCS_BUCKET_NAME}/{SPEC_CATALOG_PATH}. Error: {e}")

def get_sku_specs(sku: str, spec_catalog: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves the specifications for a single SKU from the catalog.
    """
    if sku not in spec_catalog:
        raise ValueError(f"SKU '{sku}' not found in the specification catalog.")
    return spec_catalog[sku]

def load_context_file(context_id: str) -> Dict[str, Any]:
    """
    Args:
        context_id: The identifier for the context file (e.g., 'brand_rules_shoes_v1').

    Returns:
        A dictionary containing the parsed JSON content.
    """
    from google.cloud import storage

    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob_name = f"context/{context_id}.json"
        blob = bucket.blob(blob_name)
        
        print(f"Loading context from GCS: gs://{GCS_BUCKET_NAME}/{blob_name}")
        
        content = blob.download_as_string()
        return json.loads(content)
    except Exception as e:
        raise FileNotFoundError(f"Could not load context '{context_id}' from GCS. Error: {e}")


def compose_context_card(product_specs: Dict[str, Any], contexts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Composes a compact, citable context card from product specs and various context files.
    """
    context_card = {
        "product_attributes": {k: v for k, v in product_specs.items() if pd.notna(v)},
        "rules": []
    }

    for context_id, content in contexts.items():
        if "brand_voice" in content:
            context_card["brand_voice"] = content["brand_voice"]
        
        if "rules" in content:
            for rule in content["rules"]:
                # Ensure rules are in a consistent, citable format
                context_card["rules"].append({
                    "id": rule.get("id"),
                    "text": rule.get("text"),
                    "mandatory": rule.get("mandatory", False)
                })
                
    return context_card
