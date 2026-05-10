"""
سكربت مراقبة مواعيد الحجز - نسخة نظيفة
"""
import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests

# ===================== إعداداتك =====================
TARGET_URL = "https://adhahi.dz/register"
INPUT_ELEMENT_ID = "reg-wilaya"
AVAILABILITY_KEYWORDS = ["متاح", "موجود", "حجز متوفر", "متاحة"]
# ====================================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        return response.status_code == 200
    except:
        return False

def check_availability() -> bool:
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(90)
        
        logger.info(f"🚀 فتح الموقع")
        driver.get(TARGET_URL)
        
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        input_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, INPUT_ELEMENT_ID))
        )
        
        input_field.click()
        time.sleep(3)
        
        listbox = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='listbox']"))
        )
        
        items = listbox.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        if not items:
            return False
        
        logger.info(f"📋 تم العثور على {len(items)} ولاية")
        
        for item in items:
            text = item.text.strip()
            if "متاح" in text and "غير متوفر" not in text:
                logger.info(f"✅ وجد: {text}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"خطأ: {e}")
        return False
    finally:
        if driver:
            driver.quit()

def main():
    logger.info("=" * 50)
    logger.info("بدء الفحص...")
    
    if check_availability():
        send_telegram_message(f"✅ تم العثور على موعد متاح!\n\nالموقع: {TARGET_URL}")
    else:
        logger.info("لا توجد مواعيد متاحة")

if __name__ == "__main__":
    main()
