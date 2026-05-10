import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import requests

# ========== إعداداتك ==========
TARGET_URL = "https://adhahi.dz/register"  # ⚠️ غير هذا بالرابط الحقيقي
AVAILABILITY_KEYWORDS = ["حجز", "حاليًا", "حجز غير متوفر"]
# ================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8751693358:AAE4vABzUA3GxNCi7G23u8M4Aj62gU1JqOc')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8624250308')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        if response.status_code == 200:
            logger.info("✅ تم إرسال الإشعار")
            return True
        return False
    except Exception as e:
        logger.error(f"⚠️ خطأ في الإرسال: {e}")
        return False

def check_availability():
    driver = None
    try:
        logger.info("🚀 جاري تشغيل Chrome...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # استخدام ChromeDriver المثبت مسبقاً
        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logger.info(f"🌐 فتح الموقع: {TARGET_URL}")
        driver.get(TARGET_URL)
        time.sleep(5)
        
        # قراءة نص الصفحة
        page_text = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"📄 تم تحميل الصفحة، طول النص: {len(page_text)} حرف")
        
        # البحث عن الكلمات المطلوبة
        for keyword in AVAILABILITY_KEYWORDS:
            if keyword in page_text:
                logger.info(f"✅ تم العثور على '{keyword}'!")
                return True
        
        logger.info("❌ لم يتم العثور على مواعيد متاحة")
        return False
        
    except Exception as e:
        logger.error(f"⚠️ خطأ: {e}")
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("🔒 تم إغلاق المتصفح")

def main():
    logger.info("=" * 50)
    logger.info("بدء فحص المواعيد...")
    
    # إشعار بدء التشغيل (مرة واحدة فقط)
    if time.strftime('%H') == '18':  # في الساعة 18 فقط
        send_telegram_message("🟢 سكربت المراقبة يعمل الآن")
    
    if check_availability():
        send_telegram_message(f"✅ <b>تم العثور على موعد متاح!</b>\n\n{time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
