import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
import json
import re
from typing import Dict, Any

import os


PROJECT_ID = os.getenv("GCP_PROJECT_ID", "alara-case-study")
LOCATION = "us-central1"

def init_vertex():
    vertexai.init(project=PROJECT_ID, location=LOCATION)

def query_gemini(image_gcs_uri: str, context_card: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Args:
        image_gcs_uri: The GCS URI of the image to analyze.
        context_card: The composed context card with product specs and rules.
        question: The user's question about the product.

    Returns:
        A dictionary containing the parsed JSON response from the model.
    """
    print("Querying Gemini model...")
    model_name = "gemini-2.5-flash"

    # Prepare the prompt for the model
    prompt = f"""
    You are an expert e-commerce analyst. Your task is to analyze a product image and its corresponding context card to answer a user's question, extract attributes, and check for policy compliance.

    **Context Card:**
    ```json
    {json.dumps(context_card, indent=2)}
    ```

    **User Question:** "{question}"

    **Your Tasks:**
    1.  **Answer the Question:** Based on both the image and the context card, answer the user's question. If the image provides insufficient evidence, state that clearly and cite rule R-102 if applicable.
    2.  **Extract Attributes:** Identify the following attributes from the image and reconcile them with the specs in the context card: `color`, `closure`, `style`, `outsole_pattern`.
    3.  **Check Compliance:** Evaluate all rules listed in the context card. For each rule, provide a "pass" or "fail" status and a brief justification. **Crucially, if the user's question probes a specific claim area that is governed by a rule (e.g., asking about "orthopedic" properties, "water resistance", etc.), you must find the corresponding policy rule (e.g., R-103, R-203) and explicitly fail that rule in your compliance check, explaining that the claim cannot be made.** This is a mandatory instruction.

    **Output Format:**
    You MUST respond with a single, valid JSON object. Do not include any text or formatting outside of this JSON object. The JSON object should follow this exact schema:
    {{
        "answer": "Your detailed answer to the user's question.",
        "grounding": {{
            "citations": ["List of rule IDs or spec fields supporting your answer, e.g., 'R-101', 'spec:material'"],
            "visual_refs": ["List of brief descriptions of visual evidence from the image, e.g., 'The image shows a lace-up closure.'"]
        }},
        "structured": {{
            "attributes": {{
                "color": {{"value": "extracted_color", "source": "image|spec"}},
                "closure": {{"value": "extracted_closure", "source": "image|spec"}},
                "style": {{"value": "extracted_style", "source": "image|spec"}},
                "outsole_pattern": {{"value": "extracted_outsole", "source": "image|spec"}}
            }},
            "compliance": {{
                "R-201": {{"pass": true/false, "reason": "Your justification here."}},
                "R-202": {{"pass": true/false, "reason": "Your justification here."}}
            }}
        }}
    }}
    """

    image_part = Part.from_uri(image_gcs_uri, mime_type="image/jpeg")

    model = GenerativeModel(model_name)
    generation_config = generative_models.GenerationConfig(
        temperature=0.1,
        top_p=0.95,
        top_k=32,
        max_output_tokens=8192,
    )

    response = model.generate_content(
        [image_part, prompt],
        generation_config=generation_config,
        stream=False,
    )

    print("--- Full Model Response ---")
    print(response)
    print("---------------------------")


    # Parse the response
    try:
        if not response.candidates:
            return {"error": "No candidates returned from model.", "details": "The model response was empty."}
        
        # Check the finish reason
        finish_reason = response.candidates[0].finish_reason
        if finish_reason != FinishReason.STOP:
            return {
                "error": "Model generation stopped prematurely.", 
                "details": f"Finish Reason: {finish_reason.name}. This might be due to safety settings or an issue with the input.",
                "safety_ratings": str(response.candidates[0].safety_ratings)
            }

        # Clean up the response to extract only the JSON part
        raw_text = response.text
        if not raw_text.strip():
            return {"error": "Model returned an empty text response.", "details": "This could be due to safety filters or a malformed prompt."}
            
        json_match = re.search(r"```json\n(.*)\n```", raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback
            json_str = raw_text
        
        parsed_response = json.loads(json_str)
        parsed_response["diagnostics"] = {"model": model_name}
        return parsed_response
    
    except (json.JSONDecodeError, IndexError) as e:
        return {"error": "Failed to parse model response.", "details": str(e), "raw_text": response.text}

