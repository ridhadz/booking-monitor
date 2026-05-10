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

# ========== إعداداتك ==========
TARGET_URL = "https://adhahi.dz/register"
AVAILABILITY_KEYWORDS = ["حجز", "حاليًا", "حجز غير متوفر"]
# ================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8751693358:AAE4vABzUA3GxNCi7G23u8M4Aj62gU1JqOc')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8624250308')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        return response.status_code == 200
    except:
        return False

def check_availability():
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--page-load-strategy=eager")
        
        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        
        logger.info(f"🌐 فتح الموقع")
        driver.get(TARGET_URL)
        
        # انتظار حقل الولاية
        wilaya_input = WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.ID, "reg-wilaya"))
        )
        
        # الضغط لفتح القائمة
        driver.execute_script("arguments[0].click();", wilaya_input)
        time.sleep(3)
        
        # استخراج الخيارات من القائمة
        items = driver.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        available_wilayas = []
        for item in items:
            text = item.text.strip()
            for keyword in AVAILABILITY_KEYWORDS:
                if keyword in text :
                    available_wilayas.append(text)
                    break
        
        if available_wilayas:
            message = "✅ المواعيد المتاحة:\n" + "\n".join(available_wilayas)
            send_telegram_message(message)
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
