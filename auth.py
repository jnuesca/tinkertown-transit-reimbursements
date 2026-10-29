from playwright.sync_api import sync_playwright

def save_login_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://app.getbenepass.com/login")  # adjust to actual login URL
        print("Log in manually in the browser window, then press Enter here...")
        input()
        page.context.storage_state(path="benepass_auth.json")
        browser.close()

if __name__ == "__main__":
    save_login_session()