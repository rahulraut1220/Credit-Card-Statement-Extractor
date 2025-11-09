# 💳 Credit Card Statement Extractor

A lightweight Flask application that automatically extracts key fields and transactions from credit card statement PDFs and exports them as JSON and CSV files.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-latest-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- 📄 Extract key information from credit card statement PDFs
- 💰 Parse transaction details automatically
- 📊 Export to JSON and CSV formats
- 🖥️ Simple web interface for file uploads
- 🐳 Docker support for easy deployment
- 🔒 Privacy-focused: all processing happens locally

## 📋 Prerequisites

### System Requirements

- Python 3.8 or higher
- Poppler (for PDF processing)
- Tesseract OCR (for text extraction)

## 🚀 Quick Start

### Ubuntu / Debian Linux

1. **Install system dependencies:**

   ```bash
   sudo apt-get update
   sudo apt-get install -y poppler-utils tesseract-ocr
   ```

2. **Set up Python environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start the application:**

   ```bash
   python app.py
   ```

4. **Access the app:**

   Open your browser and navigate to `http://localhost:5000`

### Windows

1. **Install Tesseract OCR:**

   - Download from [GitHub](https://github.com/tesseract-ocr/tesseract)
   - Run the installer
   - Or use Chocolatey: `choco install tesseract`

2. **Install Poppler:**

   - Download binaries from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows)
   - Add the `bin/` folder to your system PATH
   - Or use Chocolatey: `choco install poppler`

3. **Set up Python environment (PowerShell):**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Start the application:**

   ```powershell
   python app.py
   ```

5. **Access the app:**

   Open your browser and navigate to `http://localhost:5000`

### 🐳 Docker (Optional)

For a containerized setup:

1. **Build the Docker image:**

   ```bash
   docker build -t cc-extractor .
   ```

2. **Run the container:**

   ```bash
   docker run -p 5000:5000 cc-extractor
   ```

3. **Access the app:**

   Open your browser and navigate to `http://localhost:5000`

## 📁 Project Structure

```
cc-statement-extractor/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── uploads/                    # Uploaded PDFs (not committed)
└── output/                     # Extraction results (not committed)
    ├── result_full.json        # Complete extraction data
    ├── result_minimal.json     # Minimal 5-field extraction
    └── transactions_full.csv   # Transaction details
```

## 📤 Output Files

After processing a PDF, you'll find the following files in the `output/` directory:

| File                    | Description                                               |
| ----------------------- | --------------------------------------------------------- |
| `result_full.json`      | Complete extraction including all fields and transactions |
| `result_minimal.json`   | Minimal extraction with 5 essential fields                |
| `transactions_full.csv` | All transactions in CSV format for easy analysis          |

### Example Output Structure

**result_minimal.json:**

```json
{
  "card_holder": "John Doe",
  "statement_date": "2024-03-15",
  "total_amount": "1,234.56",
  "due_date": "2024-04-10",
  "card_number": "**** **** **** 1234"
}
```

**transactions_full.csv:**

```csv
Date,Description,Amount,Category
2024-03-01,AMAZON.COM,45.99,Shopping
2024-03-02,STARBUCKS,5.50,Food & Dining
2024-03-03,SHELL GAS,52.00,Gas & Fuel
```

## 🔧 Troubleshooting

### OCR Issues

- **Problem:** Poor text extraction quality
- **Solution:** Verify Tesseract is installed and available in your PATH
  ```bash
  tesseract --version
  ```

### PDF Conversion Errors

- **Problem:** Failed to convert PDF to images
- **Solution:** Ensure Poppler's `pdftoppm` is installed and in PATH
  ```bash
  pdftoppm -v
  ```

### Permission Errors

- **Linux:** Run commands with `sudo` if needed
- **Windows:** Run PowerShell or Command Prompt as Administrator

### Common Issues

| Issue                    | Solution                                                               |
| ------------------------ | ---------------------------------------------------------------------- |
| Port 5000 already in use | Change port in `app.py` or stop the conflicting service                |
| Module not found         | Ensure virtual environment is activated and dependencies are installed |
| File upload fails        | Check `uploads/` directory permissions                                 |
| No output generated      | Verify PDF is readable and not password-protected                      |

## 🔒 Privacy & Security

- ⚠️ **Sensitive Data:** Credit card statements contain personal financial information
- 📁 Both `uploads/` and `output/` folders are in `.gitignore` by default
- 🚫 **Never commit PDFs or extracted data** to version control
- 🏠 All processing happens locally on your machine
- 🔐 Consider encrypting sensitive output files

## 🛠️ Development

### Required Python Packages

The `requirements.txt` includes:

- Flask - Web framework
- pdf2image - PDF to image conversion
- pytesseract - OCR wrapper
- pandas - Data manipulation and CSV export
- Pillow - Image processing

### Adding Features

To extend the extractor:

1. Modify parsing logic in `app.py`
2. Add new output formats
3. Implement additional validation rules
4. Create custom transaction categorization
