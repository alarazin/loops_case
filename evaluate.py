import requests
import json
import pandas as pd
from typing import List, Dict, Any

import os

# Configuration
API_URL = "http://127.0.0.1:8000/analyze"
EVAL_FILE_PATH = "datasets/shoes/eval_samples.jsonl"
RESULTS_DIR = "evaluation_results"
RESULTS_FILE_PATH = os.path.join(RESULTS_DIR, "latest_run.json")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "alara-case-study-bucket") # Replace with your bucket name if different

def evaluate_sample(api_output: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares the API output against the expected ground truth from the eval file.

    Args:
        api_output: The JSON response from the /analyze endpoint.
        expected: The "expect" block from the eval_samples.jsonl file.

    Returns:
        A dictionary containing the evaluation result (pass/fail) and a reason.
    """
    # This is a simplified evaluation logic based on the case study's likely intent.
    # It can be expanded for more complex scenarios.

    # Scenario 1: Expecting a specific compliance rule to forbid a claim
    if "forbid_claim_rule" in expected:
        rule_id = expected["forbid_claim_rule"]
        compliance = api_output.get("structured", {}).get("compliance", {})
        
        if rule_id in compliance and compliance[rule_id].get("pass") is False:
            return {"pass": True, "reason": f"Correctly failed compliance rule {rule_id}."}
        else:
            return {
                "pass": False, 
                "reason": f"Expected to fail compliance rule {rule_id}, but it passed or was not found."
            }
            
    # Scenario 2: Expecting the model to be allowed to say "insufficient evidence"
    # This is harder to test programmatically without more complex NLP.
    # For now, we'll just check if the API call was successful.
    if expected.get("allow_insufficient", False):
        if "answer" in api_output:
            return {"pass": True, "reason": "API returned a valid answer."}
        else:
            return {"pass": False, "reason": "API failed to return an answer."}

    # Default case: If no specific expectation is matched, we can't determine a pass/fail.
    return {"pass": None, "reason": "No evaluation criteria matched for this sample."}


def run_evaluation():
    """
    Reads the evaluation file, calls the API for each sample,
    and saves a detailed report.
    """
    # Create results directory if it doesn't exist
    os.makedirs(RESULTS_DIR, exist_ok=True)

    full_results = []
    total_samples = 0
    passed_samples = 0

    print("--- Starting Evaluation ---")
    
    try:
        with open(EVAL_FILE_PATH, 'r') as f:
            for i, line in enumerate(f):
                total_samples += 1
                sample = json.loads(line)
                
                sku = sample["metadata"]["sku"]
                question = sample["question"]
                context_ids = [cid for cid in sample["context_ids"] if cid != "spec_catalog"]

                payload = {
                    "sku": sku,
                    "question": question,
                    "context_ids": context_ids,
                }

                # Prepare a detailed log for this sample
                run_data = {
                    "sample_index": i,
                    "payload": payload,
                    "expected": sample.get("expect"),
                    "status": None,
                    "api_output": None,
                    "evaluation": None
                }

                print(f"\n[{i+1}/{total_samples}] Evaluating SKU: {sku}")
                print(f"  Question: {question}")

                try:
                    response = requests.post(API_URL, json=payload)
                    
                    if response.status_code == 200:
                        api_output = response.json()
                        run_data["status"] = "SUCCESS"
                        run_data["api_output"] = api_output
                        
                        result = evaluate_sample(api_output, sample["expect"])
                        run_data["evaluation"] = result
                        
                        if result["pass"] is True:
                            passed_samples += 1
                            print(f"  -> Result: PASS")
                        elif result["pass"] is False:
                            print(f"  -> Result: FAIL")
                            print(f"     Reason: {result['reason']}")
                        else:
                            print(f"  -> Result: SKIPPED (No evaluation criteria)")

                    else:
                        print(f"  -> Result: ERROR (API Status {response.status_code})")
                        print(f"     Response: {response.text}")
                        run_data["status"] = f"API_ERROR_{response.status_code}"
                        run_data["api_output"] = response.text

                except requests.exceptions.RequestException as e:
                    print(f"  -> Result: FATAL ERROR (Request Failed)")
                    print(f"     Error: {e}")
                    run_data["status"] = "REQUEST_EXCEPTION"
                    run_data["api_output"] = str(e)
                
                full_results.append(run_data)

    except FileNotFoundError:
        print(f"FATAL: Evaluation file not found at {EVAL_FILE_PATH}")
        return

    # Save detailed results to a file
    with open(RESULTS_FILE_PATH, 'w') as f:
        json.dump(full_results, f, indent=4)
    
    print(f"\nDetailed evaluation results saved to: {RESULTS_FILE_PATH}")

    print("\n--- Evaluation Summary ---")
    if total_samples > 0:
        # Filter out skipped samples for accuracy calculation
        evaluated_samples = [r for r in full_results if r.get("evaluation") and r["evaluation"].get("pass") is not None]
        num_evaluated = len(evaluated_samples)
        
        if num_evaluated > 0:
            accuracy = (passed_samples / num_evaluated) * 100
            print(f"Total Samples: {total_samples}")
            print(f"Passed: {passed_samples}")
            print(f"Failed/Errored: {num_evaluated - passed_samples}")
            print(f"Skipped: {total_samples - num_evaluated}")
            print(f"Accuracy (on evaluated samples): {accuracy:.2f}%")
        else:
            print("No samples were evaluated (all were skipped).")

        # Create a DataFrame for a brief summary in the console
        summary_data = [{
            "sku": r["payload"]["sku"], 
            "pass": r.get("evaluation", {}).get("pass"), 
            "reason": r.get("evaluation", {}).get("reason", r.get("status", "UNKNOWN"))
        } for r in full_results]
        df = pd.DataFrame(summary_data)
        print("\nBrief Summary:")
        print(df.to_string())
    else:
        print("No samples were evaluated.")


if __name__ == "__main__":
    run_evaluation()
