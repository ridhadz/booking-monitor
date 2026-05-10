"""
سكربت مراقبة مواعيد الحجز - نسخة مخفية بالكامل
"""
import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        
        # إعدادات إخفاء الهوية (Anti-detection)
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # إخفاء أن selenium هو من يتحكم
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User Agent واقعي
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # إخفاء علامة webdriver في JavaScript
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(60)
        
        logger.info(f"🚀 فتح الموقع")
        driver.get(TARGET_URL)
        
        # انتظار أطول للصفحة البطيئة
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # انتظار إضافي للجافا سكريبت
        time.sleep(5)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # البحث عن حقل الولاية
        input_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, INPUT_ELEMENT_ID))
        )
        
        # النقر باستخدام JavaScript (أكثر فعالية)
        driver.execute_script("arguments[0].click();", input_field)
        logger.info("🖱️ تم النقر على الحقل")
        time.sleep(3)
        
        # انتظار ظهور القائمة
        listbox = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='listbox']"))
        )
        
        items = listbox.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        if not items:
            logger.warning("⚠️ لم يتم العثور على عناصر")
            return False
        
        logger.info(f"📋 تم العثور على {len(items)} ولاية")
        
        for item in items:
            text = item.text.strip()
            for keyword in AVAILABILITY_KEYWORDS:
                if keyword in text and "غير متوفر" not in text:
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
        send_telegram_message(f"✅ تم العثور على موعد متاح!\n\n{time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logger.info("لا توجد مواعيد متاحة")

if __name__ == "__main__":
    main()
