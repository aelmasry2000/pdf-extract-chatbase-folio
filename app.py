from flask import Flask, render_template, request
import PyPDF2
import os
import requests
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# FOLIO settings
FOLIO_BASE_URL = "https://folio-snapshot.dev.folio.org"
FOLIO_TENANT = "diku"
FOLIO_USERNAME = "diku_admin"
FOLIO_PASSWORD = "admin"
INSTANCE_TYPE_ID = "6312d172-f0cf-40f6-b27d-9fa8feaf332f"  # Books

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_text = ''
    folio_instance_id = ''
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            filename = file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            extracted_text = extract_text_from_pdf(filepath)
            os.remove(filepath)

            # Create FOLIO Instance
            folio_instance_id = create_folio_instance(extracted_text)

    return render_template('index.html', extracted_text=extracted_text, folio_instance_id=folio_instance_id)

def extract_text_from_pdf(filepath):
    text = ''
    with open(filepath, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
    return text.strip()

def get_folio_token():
    login_data = {
        "username": FOLIO_USERNAME,
        "password": FOLIO_PASSWORD
    }
    headers = {
        "x-okapi-tenant": FOLIO_TENANT,
        "Content-Type": "application/json"
    }
    response = requests.post(f"{FOLIO_BASE_URL}/authn/login", headers=headers, json=login_data)
    if response.status_code == 201:
        return response.headers["x-okapi-token"]
    else:
        return None

def create_folio_instance(extracted_text):
    token = get_folio_token()
    if not token:
        return "Failed to authenticate with FOLIO."

    # Use first line of text as the title
    title = extracted_text.split('\n')[0] if extracted_text else "Untitled PDF"

    instance_data = {
        "title": title[:255],
        "instanceTypeId": INSTANCE_TYPE_ID
    }

    headers = {
        "x-okapi-tenant": FOLIO_TENANT,
        "x-okapi-token": token,
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{FOLIO_BASE_URL}/instance-storage/instances",
        headers=headers,
        json=instance_data
    )

    if response.status_code == 201:
        instance = response.json()
        return instance.get("id", "Instance created but ID not returned.")
    else:
        return f"Failed to create instance: {response.status_code} - {response.text}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)