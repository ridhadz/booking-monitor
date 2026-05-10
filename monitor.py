import requests
import time
import logging
import os

# إعدادات
TARGET_URL = "https://adhahi.dz/register"
AVAILABILITY_KEYWORDS = ["متاح", "موجود", "حجز متوفر"]
FLARESOLVERR_URL = "http://localhost:8191/v1"  # عنوان خدمة FlareSolverr
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram_message(message: str) -> bool:
    # ... (نفس دالة الإرسال من الكود القديم) ...
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False

def check_availability():
    """إرسال طلب إلى FlareSolverr للتحقق من الموقع"""
    payload = {
        "cmd": "request.get",
        "url": TARGET_URL,
        "maxTimeout": 60000,  # مهلة 60 ثانية
    }
    headers = {'Content-Type': 'application/json'}

    try:
        logger.info(f"🚀 إرسال الطلب إلى FlareSolverr لفتح: {TARGET_URL}")
        response = requests.post(FLARESOLVERR_URL, json=payload, headers=headers, timeout=90)

        if response.status_code != 200:
            logger.error(f"فشل الاتصال بـ FlareSolverr: {response.status_code}")
            return False

        result = response.json()
        
        # 1. التحقق من حل المشكلة بنجاح
        if result.get("status") != "ok":
            logger.error(f"فشل حل التحدي: {result.get('message')}")
            return False

        # 2. الحصول على محتوى الصفحة وحلها (text/html)
        solution = result.get("solution", {})
        html_content = solution.get("response", "")
        status_code = solution.get("status", 0)

        logger.info(f"استجابة الموقع: Status Code = {status_code}")
        
        if status_code != 200:
            logger.warning(f"الموقع لم يرد برمز نجاح: {status_code}")
            return False

        # 3. البحث عن كلمات المفتاح في محتوى (text/html) الذي تم جلبه
        for keyword in AVAILABILITY_KEYWORDS:
            if keyword in html_content and "غير متوفر" not in html_content:
                logger.info(f"✅ تم العثور على الكلمة '{keyword}'!")
                return True
                
        logger.info("❌ لم يتم العثور على مواعيد متاحة.")
        return False

    except Exception as e:
        logger.error(f"خطأ في الطلب إلى FlareSolverr: {e}")
        return False

def main():
    logger.info("=" * 50)
    logger.info("بدء فحص المواعيد عبر FlareSolverr...")
    if check_availability():
        send_telegram_message(f"✅ تم العثور على موعد متاح!\n\n{time.strftime('%Y-%m-%d %H:%M:%S')}\nرابط: {TARGET_URL}")
    else:
        logger.info("لا توجد مواعيد متاحة حالياً.")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
