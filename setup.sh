# Load environment variables from .env file
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Check if project ID is set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID is not set. Please create a .env file and set it."
    exit 1
fi

# Check if bucket name is set
if [ -z "$GCS_BUCKET_NAME" ]; then
    echo "Error: GCS_BUCKET_NAME is not set. Please create a .env file and set it."
    exit 1
fi

echo "--- Starting Setup ---"

# 1. Create and activate virtual environment
echo "1. Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
echo "2. Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Enable Vertex AI API
echo "3. Enabling Vertex AI API for project $GCP_PROJECT_ID..."
gcloud services enable aiplatform.googleapis.com --project=$GCP_PROJECT_ID

# 4. Create GCS Bucket
echo "4. Creating GCS bucket: gs://$GCS_BUCKET_NAME..."
# The `-b on` flag makes the bucket name globally unique under the project.
# The `-l` flag sets the location.
gsutil mb -p $GCP_PROJECT_ID -l us-central1 gs://$GCS_BUCKET_NAME

# 5. Update file contents with the correct bucket name
echo "5. Configuring dataset files with bucket name: $GCS_BUCKET_NAME..."
sed -i.bak "s|gs://YOUR_BUCKET/|gs://$GCS_BUCKET_NAME/|g" datasets/shoes/spec_catalog.csv
sed -i.bak "s|gs://YOUR_BUCKET/|gs://$GCS_BUCKET_NAME/|g" datasets/shoes/spec_catalog.json
sed -i.bak "s|gs://YOUR_BUCKET/|gs://$GCS_BUCKET_NAME/|g" datasets/shoes/eval_samples.jsonl
# Clean up backup files created by sed
rm datasets/shoes/*.bak

# 6. Upload datasets to GCS
echo "6. Uploading datasets to gs://$GCS_BUCKET_NAME..."
gsutil -m cp -r datasets/shoes/images gs://$GCS_BUCKET_NAME/images/
gsutil -m cp datasets/shoes/brand_rules_shoes_v1.json gs://$GCS_BUCKET_NAME/context/
gsutil -m cp datasets/shoes/policy_shoes_v1.json gs://$GCS_BUCKET_NAME/context/
gsutil -m cp datasets/shoes/spec_catalog.csv gs://$GCS_BUCKET_NAME/

echo "--- Setup Complete ---"
echo "Next steps:"
echo "1. Run 'gcloud auth application-default login' to authenticate."
echo "2. Start the server with 'bash run_server.sh'."
echo "3. In a new terminal, run the evaluation with 'bash run_evaluation.sh'."
