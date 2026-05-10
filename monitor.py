"""
سكربت مراقبة مواعيد الحجز - Playwright مع تقنيات التخفي
"""
import asyncio
import logging
import os
from datetime import datetime
import requests

# استخدام Patchright بدلاً من Playwright العادي (أفضل للتخفي)
from playwright.async_api import async_playwright

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

async def check_availability_playwright() -> bool:
    """فحص الموقع باستخدام Playwright مع إعدادات تخفي متقدمة"""
    
    async with async_playwright() as p:
        # إعدادات المتصفح للتخفي
        browser = await p.chromium.launch(
            headless=True,  # تشغيل بدون واجهة
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--window-size=1920,1080',
            ]
        )
        
        # إنشاء سياق بمعلومات متصفح واقعية
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ar-DZ',
            timezone_id='Africa/Algiers',
        )
        
        # إخفاء علامات الأتمتة
        await context.add_init_script("""
            () => {
                // إخفاء خاصية webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // إخفاء علامات Playwright
                delete window.navigator.__proto__.webdriver;
                
                // تعديل خصائص إضافية
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ar', 'en-US', 'en']
                });
            }
        """)
        
        page = await context.new_page()
        
        try:
            logger.info(f"🚀 فتح الموقع: {TARGET_URL}")
            
            # ضبط مهلة التحميل
            page.set_default_timeout(60000)  # 60 ثانية
            
            # الانتقال إلى الموقع
            await page.goto(TARGET_URL, wait_until='networkidle')
            
            # انتظار تحميل الصفحة
            await page.wait_for_timeout(3000)
            
            # التمرير لأسفل
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # البحث عن حقل الولاية
            logger.info(f"🔍 البحث عن الحقل id='{INPUT_ELEMENT_ID}'")
            
            # انتظار ظهور الحقل
            await page.wait_for_selector(f"#{INPUT_ELEMENT_ID}", timeout=30000)
            
            # الضغط على الحقل (إذا كان input)
            await page.click(f"#{INPUT_ELEMENT_ID}")
            logger.info("🖱️ تم النقر على حقل الولاية")
            await page.wait_for_timeout(3000)
            
            # انتظار ظهور القائمة
            await page.wait_for_selector("ul[role='listbox']", timeout=15000)
            
            # استخراج عناصر القائمة
            items = await page.query_selector_all("li[role='option']")
            
            if not items:
                logger.warning("⚠️ لم يتم العثور على ولايات")
                return False
            
            logger.info(f"📋 تم العثور على {len(items)} ولاية")
            
            # قراءة النصوص والبحث عن كلمة "متاح"
            available_wilayas = []
            for item in items:
                text = await item.inner_text()
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
            logger.error(f"⚠️ خطأ في Playwright: {e}")
            return False
        finally:
            await browser.close()

def main():
    """الدالة الرئيسية"""
    logger.info("=" * 50)
    logger.info("بدء فحص المواعيد باستخدام Playwright...")
    
    # تشغيل الدالة غير المتزامنة
    result = asyncio.run(check_availability_playwright())
    
    if result:
        message = f"✅ <b>تم العثور على موعد متاح!</b>\n\nالموقع: {TARGET_URL}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(message)
    else:
        logger.info("لا توجد مواعيد متاحة حالياً")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
