"""
سكربت مراقبة مواعيد الحجز - نسخة متخفية بالكامل (تتحقق فقط من وجود الحجز)
"""
import time
import logging
import os
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# ===================== إعداداتك =====================
TARGET_URL = "https://adhahi.dz/register"
INPUT_ELEMENT_ID = "reg-wilaya"
# الكلمة التي تبحث عنها (متاح)
AVAILABILITY_KEYWORDS = ["حجز متوفر", "موجود", "حجز متوفر"]
# ====================================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message: str) -> bool:
    """إرسال رسالة إلى Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        if response.status_code == 200:
            logger.info("✅ تم إرسال الإشعار")
            return True
        return False
    except Exception as e:
        logger.error(f"⚠️ خطأ في الإرسال: {e}")
        return False

def human_like_behavior(driver):
    """إضافة سلوكيات تشبه الإنسان"""
    # تمرير عشوائي للصفحة
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
    time.sleep(random.uniform(0.5, 1.5))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
    time.sleep(random.uniform(0.5, 1))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(0.8, 1.8))

def check_availability() -> bool:
    driver = None
    try:
        chrome_options = Options()
        
        # ========== إخفاء الهوية بالكامل ==========
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # إخفاء علامات الأتمتة
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User Agent واقعي (Windows 10 + Chrome)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # إعدادات إضافية للإخفاء
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        
        # ========== تشغيل المتصفح ==========
        driver = webdriver.Chrome(options=chrome_options)
        
        # إخفاء خاصية webdriver من JavaScript
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(90)
        
        logger.info(f"🚀 فتح الموقع")
        driver.get(TARGET_URL)
        
        # ========== سلوكيات إنسانية ==========
        time.sleep(random.uniform(3, 6))
        human_like_behavior(driver)
        
        # انتظار تحميل الصفحة
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # ========== البحث عن حقل الولاية ==========
        input_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, INPUT_ELEMENT_ID))
        )
        
        # تأخير إنساني قبل النقر
        time.sleep(random.uniform(1, 2))
        
        # النقر باستخدام JavaScript
        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
        time.sleep(random.uniform(0.5, 1))
        driver.execute_script("arguments[0].click();", input_field)
        logger.info("🖱️ تم النقر على حقل الولاية")
        
        # انتظار إنساني لظهور القائمة
        time.sleep(random.uniform(2, 4))
        
        # ========== استخراج القائمة ==========
        listbox = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='listbox']"))
        )
        
        items = listbox.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        if not items:
            logger.warning("⚠️ لم يتم العثور على ولايات")
            return False
        
        logger.info(f"📋 تم العثور على {len(items)} ولاية")
        
        # ========== البحث عن كلمة "متاح" ==========
        available_wilayas = []
        for item in items:
            text = item.text.strip()
            for keyword in AVAILABILITY_KEYWORDS:
                if keyword in text and "غير متوفر" not in text:
                    available_wilayas.append(text)
                    logger.info(f"   ✅ {text}")
                    break
        
        if available_wilayas:
            logger.info(f"🎉 تم العثور على {len(available_wilayas)} ولاية بها حجز متاح!")
            return True
        else:
            logger.info("❌ لا توجد ولايات بها حجز متاح حالياً")
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
    
    if check_availability():
        message = f"✅ <b>تم العثور على موعد متاح!</b>\n\nالموقع: {TARGET_URL}\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(message)
    else:
        logger.info("لا توجد مواعيد متاحة حالياً")

if __name__ == "__main__":
    main()
