"""
سكربت مراقبة مواعيد الحجز - يعمل على GitHub Actions
"""
import time
import logging
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests

# ===================== إعدادات المستخدم =====================
TARGET_URL = "https://adhahi.dz/register"
INPUT_ELEMENT_ID = "reg-wilaya"
AVAILABILITY_KEYWORDS = ["متاح", "حاليًا", "حجز غير متوفر", "حجز"]
EXTRA_WAIT = 3  # وقت قصير
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def send_telegram_message(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ لم يتم تعيين توكن التليجرام")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ تم إرسال الإشعار إلى Telegram")
            return True
        else:
            logger.error(f"❌ فشل الإرسال: {response.text}")
            return False
    except Exception as e:
        logger.error(f"⚠️ خطأ في الاتصال: {e}")
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
        
        logger.info(f"🚀 فتح الموقع: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        logger.info("📜 التمرير لأسفل الصفحة...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        logger.info(f"🔍 البحث عن الحقل id='{INPUT_ELEMENT_ID}'")
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, INPUT_ELEMENT_ID))
        )
        
        input_field.click()
        logger.info("🖱️ تم النقر على الحقل - انتظار ظهور القائمة...")
        time.sleep(EXTRA_WAIT)
        
        listbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='listbox']"))
        )
        
        items = listbox.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        if not items:
            logger.warning("⚠️ لم يتم العثور على عناصر في القائمة")
            return False
        
        logger.info(f"📋 تم العثور على {len(items)} ولاية")
        
        available_items = []
        for item in items:
            text = item.text.strip()
            for keyword in AVAILABILITY_KEYWORDS:
                if keyword in text:
                    available_items.append(text)
                    logger.info(f"   ✅ {text}")
                    break
        
        if available_items:
            logger.info(f"🎉 تم العثور على {len(available_items)} ولاية بها مواعيد!")
            return True
        else:
            logger.info("❌ لا توجد مواعيد متاحة حالياً")
            return False
        
    except TimeoutException:
        logger.error("⏰ انتهى الوقت")
        return False
    except NoSuchElementException as e:
        logger.error(f"🔍 لم يتم العثور على العنصر: {e}")
        return False
    except Exception as e:
        logger.error(f"⚠️ خطأ: {e}")
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("🛑 تم إغلاق المتصفح")

def main():
    logger.info("=" * 50)
    logger.info("بدء فحص المواعيد...")
    
    is_available = check_availability()
    
    if is_available:
        message = (
            f"✅ <b>تم العثور على موعد متاح!</b>\n\n"
            f"الموقع: {TARGET_URL}\n"
            f"⏰ الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔗 يرجى الدخول سريعاً للحجز."
        )
        send_telegram_message(message)
    else:
        logger.info("لا توجد مواعيد متاحة")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
