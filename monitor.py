import asyncio
import logging
import os
import time
import requests
from datetime import datetime
from patchright.async_api import async_playwright

# ... (الإعدادات ودالة send_telegram_message كما هي تمامًا بدون تغيير) ...
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
        if response.status_code == 200:
            logger.info("✅ تم إرسال الإشعار")
            return True
        return False
    except Exception as e:
        logger.error(f"⚠️ خطأ في الإرسال: {e}")
        return False

async def check_availability() -> bool:
    async with async_playwright() as p:
        # إطلاق متصفح Chromium المعدل بواسطة Patchright
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )
        
        # إنشاء سياق بمعلومات واقعية
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ar-DZ',
            timezone_id='Africa/Algiers',
        )
        
        # إضافة سكريبت لإخفاء علامات الأتمتة
        await context.add_init_script("""
            () => {
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                // إخفاء علامات أخرى...
            }
        """)
        
        page = await context.new_page()
        
        try:
            logger.info(f"🚀 فتح الموقع: {TARGET_URL}")
            # استخدام 'domcontentloaded' أسرع من 'networkidle'
            await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=90000)
            
            # انتظار إضافي لأمان
            await page.wait_for_timeout(5000)
            
            # ... (باقي الكود الخاص بالضغط على القائمة والبحث يبقى كما هو دون تغيير) ...
            # التمرير لأسفل
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # البحث عن حقل الولاية والضغط عليه
            logger.info(f"🔍 البحث عن الحقل id='{INPUT_ELEMENT_ID}'")
            await page.wait_for_selector(f"#{INPUT_ELEMENT_ID}", timeout=30000)
            await page.click(f"#{INPUT_ELEMENT_ID}")
            logger.info("🖱️ تم النقر على حقل الولاية")
            await page.wait_for_timeout(3000)
            
            # انتظار ظهور القائمة
            await page.wait_for_selector("ul[role='listbox']", timeout=15000)
            items = await page.query_selector_all("li[role='option']")
            
            if not items:
                logger.warning("⚠️ لم يتم العثور على ولايات")
                return False
            
            logger.info(f"📋 تم العثور على {len(items)} ولاية")
            
            # البحث عن كلمة "متاح"
            for item in items:
                text = await item.inner_text()
                if "متاح" in text and "غير متوفر" not in text:
                    logger.info(f"✅ تم العثور على حجز في: {text}")
                    return True
            return False
                
        except Exception as e:
            logger.error(f"⚠️ خطأ: {e}")
            return False
        finally:
            await browser.close()

def main():
    logger.info("=" * 50)
    logger.info("بدء فحص المواعيد باستخدام Patchright...")
    result = asyncio.run(check_availability())
    if result:
        send_telegram_message(f"✅ تم العثور على موعد متاح!\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logger.info("لا توجد مواعيد متاحة حالياً")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
