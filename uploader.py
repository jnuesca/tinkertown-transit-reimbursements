import sys
import re
import argparse
import random
import time
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from pathlib import Path

class InsufficientBalanceError(Exception):
    """Raised when the charge amount exceeds the available reimbursement balance."""
    pass

def human_delay(min_seconds=0.5, max_seconds=2.0):
    """Pause for a random duration to mimic human interaction timing."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_data(pdf_path):
    reader = PdfReader(pdf_path)
    text = reader.pages[0].extract_text()

    # Match the Charge Summary data row: starts with the retrieval reference
    # (a long number), then captures the date and charge amount, skipping
    # over Product Type / Description / Payment Method in between.
    match = re.search(
        r"\d{9,}\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}).*?\$(\d+\.\d{2})",
        text,
        re.DOTALL
    )

    return {
        "date": match.group(1) if match else None,
        "charge_amount": match.group(2) if match else None,
    }

def get_available_balance(page):
    """Extract the reimbursable balance from the page, e.g. 'You can reimburse up to USD $62.00' -> 62.00"""
    balance_text = page.get_by_text("You can reimburse up to").inner_text()
    match = re.search(r"\$(\d+(?:\.\d{2})?)", balance_text)
    if not match:
        raise ValueError(f"Could not parse balance from: {balance_text!r}")
    return float(match.group(1))

def select_purchase_date(page, date_str):
    """date_str format: 'Jul 17, 2026' (matches your regex extraction)"""
    dt = datetime.strptime(date_str, "%b %d, %Y")

    # Open the date picker popup
    page.click('button[aria-label="Open calendar"]')
    page.wait_for_selector(".astryx-calendar")

    # Set month if needed
    target_month = dt.strftime("%B")  # "July"
    month_btn = page.locator('.astryx-calendar button[role="combobox"]').first
    if month_btn.inner_text() != target_month:
        month_btn.click()
        page.get_by_role("option", name=target_month, exact=True).click()

    # Set year if needed
    target_year = dt.strftime("%Y")  # "2026"
    year_btn = page.locator('.astryx-calendar button[role="combobox"]').nth(1)
    if year_btn.inner_text() != target_year:
        year_btn.click()
        page.get_by_role("option", name=target_year, exact=True).click()

    # Click the specific day — target via data-date, exact match, no ambiguity
    target_date = dt.strftime("%Y-%m-%d")  # "2026-07-17"
    page.locator(f'button[data-date="{target_date}"]').click()

def fill_form(page, pdf_path, data):
    # Step 1: Select benefit — click to open the menu, then choose "Transit"
    page.goto("https://app.getbenepass.com/expenses/create")
    human_delay()

    page.click('button:has-text("Select benefit")')
    page.get_by_role("option").filter(has_text="Transit").click()

    available = get_available_balance(page)
    print(f"  ℹ Total reimburseable amount available is ${available:.2f}.")
    charge = float(data["charge_amount"])
    if charge > available:
        raise InsufficientBalanceError(
            f"Charge ${charge:.2f} exceeds available balance ${available:.2f}"
        )

    page.fill('input[name="amount"]', data["charge_amount"])
    human_delay(0.3, 1.0)
    page.fill('#merchant', "MTA OMNY")
    human_delay(0.3, 1.0)
    page.set_input_files('input[type="file"]', str(pdf_path))  # fixed
    human_delay(1.0, 2.5)

    select_purchase_date(page, data["date"])
    human_delay()
    page.click('button[type="submit"]')
    page.wait_for_url("**/transactions/expense_*", timeout=10000)
    
    expense_id = page.url.split("/")[-1]
    return expense_id    

def main():
    parser = argparse.ArgumentParser(description="Auto-fill Benepass reimbursement forms from split PDF receipts")
    parser.add_argument("pdf_folder", type=str, help="Path to folder containing split PDF pages")
    parser.add_argument("--auth", type=str, default="benepass_auth.json", help="Path to saved login session file")
    args = parser.parse_args()

    pdf_folder = Path(args.pdf_folder)
    if not pdf_folder.exists():
        print(f"Error: folder not found: {pdf_folder}")
        return
    
    auth_file = Path(args.auth)
    if not auth_file.exists():
        print(f"Error: auth session file not found: {auth_file}")
        print("Run your login script first to generate it.")
        return

    pdf_files = sorted(pdf_folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {pdf_folder}")
        return

    # Create destination folders
    processed_folder = pdf_folder / "processed"
    failed_folder = pdf_folder / "failed"
    processed_folder.mkdir(exist_ok=True)
    failed_folder.mkdir(exist_ok=True)

    print(f"Found {len(pdf_files)} PDF files to process")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context(storage_state=str(auth_file))
            page = context.new_page()

            for pdf_file in pdf_files:
                print(f"Processing: {pdf_file.name}")
                try:
                    data = extract_data(pdf_file)
                    expense_id = fill_form(page, pdf_file, data)
                    print(f"  ✓ Submitted {pdf_file.name} → {expense_id}")
                    shutil.move(str(pdf_file), str(processed_folder / pdf_file.name))
                except InsufficientBalanceError as e:
                    print(f"  ⛔ Stopping batch: {e}")
                    print(f"  {pdf_file.name} was NOT processed and remains in the original folder.")
                    break  # exit the loop entirely — don't touch remaining files
                except Exception as e:
                    print(f"  ✗ Failed on {pdf_file.name}: {e}")
                    shutil.move(str(pdf_file), str(failed_folder / pdf_file.name))
                human_delay(10, 30)
            
        except Exception as e:
            print(f"Error during automation: {e}")
            input("Press Enter to close the browser...")
            browser.close()

        print("Done processing.")
        input("Press Enter to close the browser...")
        browser.close() 

if __name__ == "__main__":
    main()

