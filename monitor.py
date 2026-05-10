import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

TARGET_URL = "https://adhahi.dz/register"
AVAILABILITY_KEYWORDS = ["حجز", "حاليًا", "حجز غير متوفر"]

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8751693358:AAE4vABzUA3GxNCi7G23u8M4Aj62gU1JqOc')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8624250308')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
        return True
    except:
        return False

def check_availability():
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(90)
        driver.get(TARGET_URL)
        time.sleep(5)
        
        wilaya_input = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "reg-wilaya"))
        )
        
        driver.execute_script("arguments[0].scrollIntoView(true);", wilaya_input)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", wilaya_input)
        time.sleep(2)
        
        items = driver.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        available = []
        for item in items:
            text = item.text
            if any(k in text for k in AVAILABILITY_KEYWORDS) :
                available.append(text)
        
        if available:
            send_telegram_message("✅ المواعيد المتاحة:\n" + "\n".join(available))
            return True
        return False
        
    except Exception as e:
        logger.error(f"خطأ: {e}")
        return False
    finally:
        if driver:
            driver.quit()

def main():
    logger.info("بدء الفحص...")
    check_availability()

if __name__ == "__main__":
    main()
