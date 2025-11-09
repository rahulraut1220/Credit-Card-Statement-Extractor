# app.py
import os
import json
from flask import Flask, request, render_template, send_from_directory, url_for
from werkzeug.utils import secure_filename
import pandas as pd

# import the extractor functions (make sure extractor.py is in the same folder)
from extractor import run_full, extract_transactions_conservative

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(saved_path)

        # Run full extractor (returns dict)
        result = run_full(saved_path)

        # save full json
        full_json_path = os.path.join(app.config['OUTPUT_FOLDER'], 'result_full.json')
        with open(full_json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # save transactions csv (if available)
        txs = result.get('transactions', [])
        tx_csv_path = os.path.join(app.config['OUTPUT_FOLDER'], 'transactions_full.csv')
        try:
            pd.DataFrame(txs).to_csv(tx_csv_path, index=False)
        except Exception:
            # if transactions empty or malformed, still write an empty CSV
            pd.DataFrame(txs).to_csv(tx_csv_path, index=False)

        # Also produce the minimal result (optional)
        minimal = {
            'card_last4': result.get('card_last4'),
            'statement_date': result.get('statement_date'),
            'billing_period': result.get('billing_period'),
            'due_date': result.get('due_date'),
            'total_balance': result.get('total_balance')
        }
        minimal_json_path = os.path.join(app.config['OUTPUT_FOLDER'], 'result_minimal.json')
        with open(minimal_json_path, 'w', encoding='utf-8') as f:
            json.dump(minimal, f, ensure_ascii=False, indent=2)

        # Print concise summary to console
        print('\n=== Extraction summary ===')
        for k in ['card_last4', 'statement_date', 'billing_period', 'due_date', 'total_balance']:
            print(f"{k}: {minimal.get(k)}")
        print('Transactions extracted:', len(txs))

        # show user results page with download links
        return render_template('upload.html', result=minimal, downloads={
            'full_json': url_for('download_output', filename='result_full.json'),
            'tx_csv': url_for('download_output', filename='transactions_full.csv'),
            'minimal_json': url_for('download_output', filename='result_minimal.json')
        })
    return 'File type not allowed', 400


@app.route('/output/<path:filename>')
def download_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    # debug=True for development; set to False in production
    app.run(host='0.0.0.0', port=5000, debug=True)
