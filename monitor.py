"""
سكربت مراقبة مواعيد الحجز - مع دعم Cloudflare Tunnel
"""
import time
import logging
import os
import subprocess
import threading
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ===================== إعدادات المستخدم =====================
TARGET_URL = "https://adhahi.dz/register"
INPUT_ELEMENT_ID = "reg-wilaya"
AVAILABILITY_KEYWORDS = ["متاح", "موجود", "حجز متوفر", "متاحة"]
EXTRA_WAIT = 3
USE_CLOUDFLARE_TUNNEL = True  # ✅ غيّر إلى False إذا أردت تعطيل النفق
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_telegram_message(message: str) -> bool:
    """إرسال رسالة إلى Telegram"""
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


def start_cloudflare_tunnel(port=8080):
    """
    تشغيل Cloudflare Tunnel لإنشاء نفق مؤقت
    يعيد (tunnel_url, process) أو (None, None) عند الفشل
    """
    try:
        # تشغيل خادم HTTP بسيط على المنفذ المحدد
        def run_simple_server():
            subprocess.run(
                ["python", "-m", "http.server", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        server_thread = threading.Thread(target=run_simple_server, daemon=True)
        server_thread.start()
        logger.info(f"✅ خادم HTTP يعمل على المنفذ {port}")
        
        # تشغيل cloudflared لربط المنفذ
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # قراءة الرابط من المخرجات
        for _ in range(30):  # انتظار 30 ثانية كحد أقصى
            line = process.stderr.readline()
            if not line:
                time.sleep(1)
                continue
            if "https://" in line and ".trycloudflare.com" in line:
                # استخراج الرابط
                import re
                match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                if match:
                    tunnel_url = match.group(1)
                    logger.info(f"✅ Cloudflare Tunnel يعمل: {tunnel_url}")
                    return tunnel_url, process
        
        logger.error("❌ فشل في الحصول على رابط النفق")
        return None, None
        
    except Exception as e:
        logger.error(f"⚠️ خطأ في تشغيل النفق: {e}")
        return None, None


def check_availability():
    """فحص الموقع والبحث عن مواعيد متاحة"""
    driver = None
    tunnel_process = None
    original_url = TARGET_URL
    
    try:
        # إذا أردنا استخدام النفق، غيّر الوجهة
        if USE_CLOUDFLARE_TUNNEL:
            logger.info("🚇 جاري تشغيل Cloudflare Tunnel...")
            tunnel_url, tunnel_process = start_cloudflare_tunnel()
            if tunnel_url:
                # ملاحظة: هذا الحل يعمل فقط إذا كان الموقع يدعم الـ Proxy
                # للتبسيط، سنستخدم الـ tunnel كـ Proxy لطلب الموقع
                logger.info(f"🌐 سيتم استخدام النفق كوسيط")
                # نمرر إعدادات الـ Proxy إلى Chrome Options
                proxy_settings = {
                    "proxy": {
                        "httpProxy": tunnel_url.replace("https://", ""),
                        "sslProxy": tunnel_url.replace("https://", ""),
                        "noProxy": ""
                    }
                }
            else:
                logger.warning("⚠️ فشل تشغيل النفق، نستمر بدون وسيط")
        
        # إعدادات Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # إذا كان لدينا وكيل (Proxy) من النفق
        if USE_CLOUDFLARE_TUNNEL and tunnel_url:
            proxy_address = tunnel_url.replace("https://", "")
            chrome_options.add_argument(f'--proxy-server={proxy_address}')
            logger.info(f"🔐 تم تعيين الوكيل: {proxy_address}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(90)  # 90 ثانية مهلة التحميل
        
        logger.info(f"🚀 فتح الموقع: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # انتظار تحميل الصفحة
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        logger.info("📜 التمرير لأسفل الصفحة...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # البحث عن حقل الإدخال
        logger.info(f"🔍 البحث عن الحقل id='{INPUT_ELEMENT_ID}'")
        input_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, INPUT_ELEMENT_ID))
        )
        
        # النقر لفتح القائمة
        input_field.click()
        logger.info("🖱️ تم النقر على الحقل - انتظار ظهور القائمة...")
        time.sleep(EXTRA_WAIT)
        
        # انتظار ظهور القائمة
        listbox = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='listbox']"))
        )
        
        # استخراج جميع عناصر القائمة
        items = listbox.find_elements(By.CSS_SELECTOR, "li[role='option']")
        
        if not items:
            logger.warning("⚠️ لم يتم العثور على عناصر في القائمة")
            return False
        
        logger.info(f"📋 تم العثور على {len(items)} ولاية")
        
        available_items = []
        for item in items:
            text = item.text.strip()
            for keyword in AVAILABILITY_KEYWORDS:
                if keyword in text and "غير متوفر" not in text:
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
        logger.error("⏰ انتهى الوقت المحدد لتحميل الصفحة")
        return False
    except NoSuchElementException as e:
        logger.error(f"🔍 لم يتم العثور على العنصر: {e}")
        return False
    except Exception as e:
        logger.error(f"⚠️ خطأ غير متوقع: {e}")
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("🛑 تم إغلاق المتصفح")
        if tunnel_process:
            tunnel_process.terminate()
            logger.info("🛑 تم إغلاق نفق Cloudflare")


def main():
    """الدالة الرئيسية"""
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
        logger.info("لا توجد مواعيد متاحة حالياً")
    
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
