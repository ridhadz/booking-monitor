import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# ========== إعداداتك ==========
TARGET_URL = "https://adhahi.dz/register"  # ⚠️ ضع الرابط الصحيح هنا
AVAILABILITY_KEYWORDS = ["متاح", "موجود", "حجز متوفر"]
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
        else:
            logger.error(f"❌ فشل الإرسال: {response.text}")
            return False
    except Exception as e:
        logger.error(f"⚠️ خطأ: {e}")
        return False

def check_availability():
    driver = None
    try:
        logger.info("1️⃣ جاري إعداد المتصفح...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        logger.info("2️⃣ جاري تشغيل Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        
        logger.info(f"3️⃣ جاري فتح الموقع: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        logger.info("4️⃣ انتظار تحميل الصفحة...")
        time.sleep(5)
        
        logger.info("5️⃣ جاري أخذ لقطة للصفحة للتحقق...")
        page_text = driver.find_element(By.TAG_NAME, "body").text
        logger.info(f"6️⃣ أول 500 حرف من الصفحة: {page_text[:500]}")
        
        # البحث عن كلمات المفتاح
        found = False
        for keyword in AVAILABILITY_KEYWORDS:
            if keyword in page_text:
                logger.info(f"✅ تم العثور على كلمة '{keyword}' في الصفحة!")
                found = True
                break
        
        if not found:
            logger.info("❌ لم يتم العثور على أي كلمة تدل على التوفر")
        
        return found
        
    except Exception as e:
        logger.error(f"⚠️ خطأ مفصل: {type(e).__name__} - {str(e)}")
        return False
    finally:
        if driver:
            logger.info("7️⃣ جاري إغلاق المتصفح...")
            driver.quit()
            logger.info("8️⃣ تم الإغلاق بنجاح")

def main():
    logger.info("=" * 50)
    logger.info("بدء فحص المواعيد...")
    
    # إرسال إشعار بدء التشغيل (للتأكد من أن البوت يعمل)
    send_telegram_message("🟢 سكربت المراقبة يعمل الآن! جاري فحص المواعيد...")
    
    is_available = check_availability()
    
    if is_available:
        message = f"✅ <b>تم العثور على موعد متاح!</b>\n\nالموقع: {TARGET_URL}\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(message)
    else:
        logger.info("لا توجد مواعيد متاحة حالياً")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
