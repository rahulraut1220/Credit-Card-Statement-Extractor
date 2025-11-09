# extractor.py
import os
import re
import json
import traceback
from datetime import datetime

import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import pandas as pd
import dateparser
from dateutil import parser as du_parser

# ---------- Helpers ----------
def extract_text_pages(pdf_path):
    try:
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    pages.append(page.extract_text() or "")
                except:
                    pages.append("")
        return pages
    except Exception as e:
        print("pdfplumber error:", e)
        return []


def ocr_text_pages(pdf_path, dpi=300):
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
    except Exception as e:
        print("pdf2image error:", e)
        return []
    pages = []
    for img in images:
        try:
            pages.append(pytesseract.image_to_string(img) or "")
        except Exception as e:
            pages.append("")
    return pages


def join_pages(pages):
    return "\n\n".join(pages)


def is_scanned(pages):
    total = sum(len(p) for p in pages)
    if total < 300:
        return True
    nonempty = sum(1 for p in pages if p and len(p.strip()) > 50)
    if nonempty < max(1, len(pages) // 2):
        return True
    return False


def clean_amount(s):
    if not s:
        return None
    t = str(s)
    t = t.replace('\u20b9', '').replace('Rs.', '').replace('Rs', '').replace('INR', '')
    t = t.replace(',', '').strip()
    neg = False
    if t.startswith('(') and t.endswith(')'):
        neg = True
        t = t[1:-1].strip()
    t = re.sub(r'[^\d\.\-]', '', t)
    try:
        v = float(t)
        return -v if neg else v
    except:
        return None


def parse_date_safe(s):
    if not s:
        return None
    st = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', str(s))
    try:
        dp = dateparser.parse(st, settings={'PREFER_DAY_OF_MONTH': 'first'})
        if dp and 1900 < dp.year <= datetime.now().year + 2:
            return dp.date().isoformat()
    except:
        pass
    try:
        du = du_parser.parse(st, fuzzy=True)
        if du and 1900 < du.year <= datetime.now().year + 2:
            return du.date().isoformat()
    except:
        pass
    return None


date_regex = r'(?:\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b|\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b|\b[A-Za-z]{3,9}\s+\d{1,2}\b)'
currency_regex = r'\(?\s*(?:₹|Rs\.?|INR|USD|\$)?\s*\d{1,3}(?:[,\d]{0,})(?:\.\d{1,2})\s*\)?'


# ---------- Improved extractors ----------
def find_card_last4_from_header(header_text):
    # Prefer explicit "Card No" line and take last 4 digits
    m = re.search(r'Card\s*No[:\s]*([^\n\r]+)', header_text, flags=re.IGNORECASE)
    if m:
        line = m.group(1)
        g = re.findall(r'(\d{4})', line)
        if g:
            return g[-1], 'High'
    # fallback: any masked-like pattern with trailing 4 digits
    m2 = re.search(r'(?:Card|Account)[^\n\r]{0,40}(\d{4})', header_text, flags=re.IGNORECASE)
    if m2:
        return m2.group(1), 'Medium'
    # last resort: first 4-digit
    m3 = re.search(r'\b(\d{4})\b', header_text)
    if m3:
        return m3.group(1), 'Low'
    return None, 'Low'


def find_statement_date(first_page):
    m = re.search(r'(?:Statement Date|Date of Statement|Statement as on|Statement on)[:\s]{0,60}(.{0,80})', first_page, flags=re.IGNORECASE)
    if m:
        dr = re.search(date_regex, m.group(1))
        if dr:
            d = parse_date_safe(dr.group(0))
            if d:
                return d, 'High'
    top = "\n".join(first_page.splitlines()[:60])
    dr2 = re.search(date_regex, top)
    if dr2:
        d = parse_date_safe(dr2.group(0))
        if d:
            return d, 'Medium'
    return None, 'Low'


def find_billing_period(first_page, second_page=""):
    m = re.search(r'(?:Statement Period|Billing Period|Statement From|Statement For).{0,250}', first_page, flags=re.IGNORECASE)
    if m:
        ds = re.findall(date_regex, m.group(0))
        if len(ds) >= 2:
            d1 = parse_date_safe(ds[0])
            d2 = parse_date_safe(ds[1])
            if d1 and d2:
                a, b = sorted([d1, d2])
                return f"{a} to {b}", 'High'
        mm = re.search(r'from\s+(.{0,60})\s+to\s+(.{0,60})', m.group(0), flags=re.IGNORECASE)
        if mm:
            d1 = parse_date_safe(mm.group(1))
            d2 = parse_date_safe(mm.group(2))
            if d1 and d2:
                a, b = sorted([d1, d2])
                return f"{a} to {b}", 'High'
    # fallback across first two pages
    combined = first_page + "\n\n" + second_page
    ds = re.findall(date_regex, combined)
    parsed = []
    for d in ds:
        pd = parse_date_safe(d)
        if pd and pd not in parsed:
            parsed.append(pd)
        if len(parsed) >= 2:
            break
    if len(parsed) >= 2:
        a, b = sorted(parsed[:2])
        return f"{a} to {b}", 'Medium'
    return None, 'Low'


def parse_header_columns_for_due_and_min(first_page):
    lines = [ln for ln in first_page.splitlines() if ln.strip()]
    for idx, ln in enumerate(lines):
        if re.search(r'Payment\s+Due\s+Date', ln, flags=re.IGNORECASE):
            if idx + 1 < len(lines):
                values = lines[idx + 1].strip()
                # try splitting by big gaps
                cols = re.split(r'\s{2,}|\t', values)
                if len(cols) < 2:
                    cols = values.split()
                due = None
                minimum = None
                # look for date + numeric values
                dm = re.search(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', values)
                if dm:
                    due = parse_date_safe(dm.group(1))
                nums = re.findall(r'(\(?\s*(?:₹|Rs\.?|INR|\$)?\s*[\d,]+\.\d{2}\s*\)?)', values)
                if nums:
                    # if two or more numbers, assume last is minimum
                    if len(nums) >= 2:
                        minimum = clean_amount(nums[-1])
                    else:
                        minimum = clean_amount(nums[0])
                return due, minimum
    return None, None


def find_total_balance(first_page):
    labels = ['statement balance', 'total balance', 'amount due', 'current balance', 'balance due', 'amount payable']
    header = first_page[:5000]
    for lb in labels:
        m = re.search(re.escape(lb) + r'[:\s]{0,40}([^\n\r]{0,80})', header, flags=re.IGNORECASE)
        if m:
            amt = re.search(currency_regex, m.group(1))
            if amt:
                v = clean_amount(amt.group(0))
                if v is not None:
                    return v, 'High'
    # fallback: largest currency-like number in header
    all_amt = re.findall(currency_regex, header)
    parsed = [(a, clean_amount(a)) for a in all_amt if clean_amount(a) is not None]
    if parsed:
        parsed_sorted = sorted(parsed, key=lambda x: abs(x[1]), reverse=True)
        return parsed_sorted[0][1], 'Medium'
    return None, 'Low'


def extract_transactions_conservative(full_text):
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    tx = []
    for i, ln in enumerate(lines):
        left = ln[:18]
        right = ln[-40:]
        d = re.search(date_regex, left)
        a = re.search(currency_regex, right)
        if d and a:
            dt = parse_date_safe(d.group(0))
            amt = clean_amount(a.group(0))
            desc = ln.replace(d.group(0), '').replace(a.group(0), '').strip(' -–—:,')
            if amt is not None:
                tx.append({'date': dt, 'description': desc, 'amount': amt})
    # dedupe
    seen = set()
    out = []
    for t in tx:
        key = (t.get('date'), round(t.get('amount'), 2) if isinstance(t.get('amount', None), float) else t.get('amount'), (t.get('description') or '')[:40])
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


# ---------- Orchestration ----------
def run_full(pdf_path):
    pages = extract_text_pages(pdf_path)
    if not pages or is_scanned(pages):
        ocr_pages = ocr_text_pages(pdf_path)
        merged = []
        for i in range(max(len(pages), len(ocr_pages))):
            p = pages[i] if i < len(pages) else ""
            o = ocr_pages[i] if i < len(ocr_pages) else ""
            merged.append(p if len(p.strip()) > 100 else o)
        pages = merged
    first_page = pages[0] if pages else ""
    full_text = join_pages(pages)
    # diagnostics preview (printed to console)
    try:
        print("\n--- First page preview (first 60 lines) ---")
        for idx, ln in enumerate(first_page.splitlines()[:60], 1):
            print(f"{idx:02d}: {ln}")
        print("--- end preview ---\n")
    except Exception:
        pass

    # extract fields
    card_last4, cconf = find_card_last4_from_header(first_page)
    stmt_date, sconf = find_statement_date(first_page)
    billing_period, bconf = find_billing_period(first_page, pages[1] if len(pages) > 1 else "")
    due_date, min_from_header = parse_header_columns_for_due_and_min(first_page)
    minimum_payment_due = min_from_header
    if due_date is None:
        # fallback label search
        m = re.search(r'(?:Due Date|Payment Due Date|Please pay by)[:\s]{0,80}(.{0,80})', first_page, flags=re.IGNORECASE)
        if m:
            dr = re.search(date_regex, m.group(1))
            if dr:
                due_date = parse_date_safe(dr.group(0))
    total_balance, tbconf = find_total_balance(first_page)
    # if billing period found but dates reversed (start later than end), normalize
    if billing_period:
        parts = re.split(r'\bto\b', billing_period, flags=re.IGNORECASE)
        if len(parts) >= 2:
            d1 = parse_date_safe(parts[0])
            d2 = parse_date_safe(parts[1])
            if d1 and d2:
                a, b = sorted([d1, d2])
                billing_period = f"{a} to {b}"
    transactions = extract_transactions_conservative(full_text)
    result = {
        'pdf_path': pdf_path,
        'card_last4': card_last4,
        'card_last4_confidence': cconf,
        'statement_date': stmt_date,
        'statement_date_confidence': sconf,
        'billing_period': billing_period,
        'billing_period_confidence': bconf,
        'due_date': due_date,
        'total_balance': total_balance,
        'total_balance_confidence': tbconf,
        'minimum_payment_due': minimum_payment_due,
        'transactions': transactions
    }
    return result


# Minimal single-run helper (keeps the same concise logic used in the notebook's minimal cell)
def run_minimal(pdf_path):
    pages = extract_text_pages(pdf_path)
    if not pages or is_scanned(pages):
        ocr_pages = ocr_text_pages(pdf_path)
        merged = []
        for i in range(max(len(pages), len(ocr_pages))):
            p = pages[i] if i < len(pages) else ""
            o = ocr_pages[i] if i < len(ocr_pages) else ""
            merged.append(p if len(p.strip()) > 100 else o)
        pages = merged
    first_page = pages[0] if pages else ""
    full_text = join_pages(pages)

    # Extract minimal fields
    card_last4, _ = find_card_last4_from_header(first_page)
    stmt_date, _ = find_statement_date(first_page)
    billing_period, _ = find_billing_period(first_page, pages[1] if len(pages) > 1 else "")
    due, minimum = parse_header_columns_for_due_and_min(first_page)
    if not due:
        m = re.search(r'(?:Due Date|Payment Due Date)[:\s]{0,80}(.{0,80})', first_page, flags=re.IGNORECASE)
        if m:
            dr = re.search(date_regex, m.group(1))
            if dr:
                due = parse_date_safe(dr.group(0))
    total_balance, _ = find_total_balance(first_page)
    transactions = extract_transactions_conservative(full_text)

    # normalize billing period if reversed
    if billing_period:
        parts = re.split(r'\bto\b', billing_period, flags=re.IGNORECASE)
        if len(parts) >= 2:
            d1 = parse_date_safe(parts[0])
            d2 = parse_date_safe(parts[1])
            if d1 and d2:
                a, b = sorted([d1, d2])
                billing_period = f"{a} to {b}"

    result = {
        'card_last4': card_last4,
        'statement_date': stmt_date,
        'billing_period': billing_period,
        'due_date': due,
        'total_balance': total_balance,
        'minimum_payment_due': minimum,
        'transactions': transactions
    }
    return result
