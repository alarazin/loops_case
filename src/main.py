from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict
import time

from .context import load_spec_catalog, get_sku_specs, load_context_file, compose_context_card
from .vertex_client import query_gemini, init_vertex

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initializes Vertex AI on application startup."""
    print("Application startup: Initializing Vertex AI...")
    init_vertex()
    print("Application startup: Vertex AI initialized.")


class AnalyzeRequest(BaseModel):
    sku: str = Field(..., description="SKU of the product to analyze.")
    question: Optional[str] = Field(None, description="Optional user question about the image.")
    context_ids: List[str] = Field(..., description="List of context IDs to use (e.g., 'brand_rules_v1').")
    metadata: Optional[Dict] = Field(None, description="Optional metadata.")

class Grounding(BaseModel):
    citations: List[str] = Field(..., description="List of rule IDs or spec fields that support the answer.")
    visual_refs: List[str] = Field(..., description="Descriptions of visual evidence from the image.")

class Attribute(BaseModel):
    value: str
    source: str

class Structured(BaseModel):
    attributes: Dict[str, Attribute] = Field(..., description="Extracted product attributes.")
    compliance: Dict[str, Dict] = Field(..., description="Compliance check results for each rule.")

class Diagnostics(BaseModel):
    latency: float = Field(..., description="Total processing time in seconds.")
    model: str = Field(..., description="Name of the model used for inference.")
    tokens: int = Field(..., description="Number of tokens processed.")

class AnalyzeResponse(BaseModel):
    answer: str = Field(..., description="The generated answer to the question.")
    grounding: Grounding
    structured: Structured
    diagnostics: Diagnostics

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyzes a shoe product image with structured context to produce grounded, verifiable outputs.
    """
    start_time = time.time()

    # --- 1. Load Context & Find Image URI ---
    spec_catalog = load_spec_catalog()
    sku = request.sku
    
    try:
        product_specs = get_sku_specs(sku, spec_catalog)
        image_gcs_uri = product_specs.get("image_gcs_uri")
        if not image_gcs_uri:
            # This should be a proper HTTP exception
            return {"error": f"Image GCS URI not found for SKU: {sku}"}

        # Load context files based on IDs
        contexts = {ctx_id: load_context_file(ctx_id) for ctx_id in request.context_ids}
        
    except (FileNotFoundError, ValueError) as e:

        return {"error": str(e)}

    # --- 2. Compose Context Card ---
    context_card = compose_context_card(product_specs, contexts)
    
    # --- 3. Query Model ---
    model_response = query_gemini(
        image_gcs_uri=image_gcs_uri,
        context_card=context_card,
        question=request.question or "Describe the product based on the image and context."
    )

    if "error" in model_response:
        # Handle error from the model client
        raise HTTPException(
            status_code=500, 
            detail=f"Model query failed: {model_response.get('error')} - {model_response.get('details')}"
        )

    # --- 4. Process Response & Format Output ---
    latency = time.time() - start_time

    try:
        # Add latency and other missing fields to the diagnostics from the model
        if "diagnostics" not in model_response:
            model_response["diagnostics"] = {}
        model_response["diagnostics"]["latency"] = round(latency, 2)
        # Ensure tokens is present, even if it's a placeholder
        if "tokens" not in model_response["diagnostics"]:
            model_response["diagnostics"]["tokens"] = 0

        # Validate the model's response against our Pydantic model
        validated_response = AnalyzeResponse(**model_response)
        
        return validated_response

    except ValidationError as e:
        print(f"Pydantic Validation Error: {e}")
        print(f"Raw model response was: {model_response}")
        raise HTTPException(
            status_code=500, 
            detail=f"Model returned an invalid data format. Details: {e}"
        )

@app.get("/")
def read_root():
    return {"message": "API running"}
