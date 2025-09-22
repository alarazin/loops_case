# Multimodal Product Analysis API

This project is a demonstration of a multimodal AI system that uses Google's Gemini Pro Vision model to analyze product images and associated contextual data. It exposes a REST API built with FastAPI to answer questions, extract structured attributes, and check for policy compliance.

## Features

- **Multimodal Analysis**: Processes both images and text (product specifications, brand rules).
- **FastAPI Backend**: A robust and fast API server.
- **Google Vertex AI**: Integrates with the Gemini Pro Vision model for analysis.
- **Google Cloud Storage (GCS)**: Loads images and context files from GCS.
- **Automated Evaluation**: Includes a script to evaluate the model's performance against a predefined test set.

## Prerequisites

- Python 3.9+
- An active Google Cloud Platform (GCP) project with billing enabled.
- The `gcloud` command-line tool installed and authenticated.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-name>
```

### 2. Configure Your Environment

Create a `.env` file in the root of the project directory. This file will store your specific GCP configuration.

```bash
# .env
GCP_PROJECT_ID="your-gcp-project-id"
GCS_BUCKET_NAME="your-unique-gcs-bucket-name"
```

Replace `"your-gcp-project-id"` and `"your-unique-gcs-bucket-name"` with your actual GCP project ID and a unique name for your GCS bucket.

### 3. Run the Setup Script

A setup script is provided to automate the environment creation, dependency installation, and GCS bucket setup.

```bash
bash setup.sh
```

This script will:
- Create a Python virtual environment (`venv`).
- Install the required Python packages from `requirements.txt`.
- Create the GCS bucket you specified in the `.env` file.
- Upload the necessary datasets (images, rules) to your GCS bucket.
- Enable the Vertex AI API in your GCP project.

### 4. Set Up Application Default Credentials

The application uses your local GCP credentials to authenticate. Run the following command and follow the prompts to log in:

```bash
gcloud auth application-default login
```

## Running the Application

### 1. Start the API Server

Use the provided script to start the FastAPI server. It will load the environment variables from your `.env` file.

```bash
bash run_server.sh
```

The API will be available at `http://127.0.0.1:8000`. You can access the interactive documentation at `http://127.0.0.1:8000/docs`.

### 2. Run the Evaluation Script

To verify that everything is working correctly, run the evaluation script in a new terminal:

```bash
bash run_evaluation.sh
```

This will execute the tests defined in `datasets/shoes/eval_samples.jsonl` and should report 100% accuracy.

## How It Works

1.  **API Request**: The user sends a `POST` request to `/analyze` with an SKU, a question, and context IDs.
2.  **Context Loading**: The server fetches product specifications from the local CSV and loads context files (e.g., `brand_rules_shoes_v1.json`) from GCS.
3.  **Vertex AI Query**: An image URI, a composed context card, and the user's question are sent to the Gemini model.
4.  **JSON Response**: The model returns a structured JSON object containing the answer, extracted attributes, and compliance checks, which is then sent back to the user.
