import asyncio
import random
import aiohttp
import time
import nest_asyncio
import os
from playwright.async_api import async_playwright

# تفعيل nest_asyncio (ضروري لـ Colab ومفيد لبعض بيئات السيرفرات)
nest_asyncio.apply()

# --- الإعدادات ---
TARGET = "https://ouo.io/umzOBoU"
PROXIES_FILE = "proxies.txt"
CONCURRENT_COUNT = 15  # تقليل العدد قليلاً لضمان استقرار السيرفر المجاني

class ProxyHunter:
    def __init__(self):
        self.proxies = []
        self.sources = [
            # --- GitHub المحدثة ---
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXY_LIST/master/http.txt",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt",
            # --- APIs ---
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000",
            "https://proxyspace.pro/http.txt",
            "https://proxyspace.pro/socks4.txt",
            "https://proxyspace.pro/socks5.txt"
        ]

    async def fetch_all(self):
        unique_proxies = set()
        async with aiohttp.ClientSession() as session:
            for url in self.sources:
                try:
                    async with session.get(url, timeout=10) as resp:
                        text = await resp.text()
                        lines = text.splitlines()
                        for p in lines:
                            p = p.strip()
                            if ":" in p and len(p) > 7:
                                # تحديد البروتوكول بناءً على الرابط
                                if "socks4" in url: unique_proxies.add(f"socks4://{p}")
                                elif "socks5" in url: unique_proxies.add(f"socks5://{p}")
                                else: unique_proxies.add(f"http://{p}")
                except: continue
        return list(unique_proxies)

    async def auto_update_loop(self):
        while True:
            print(f"\n[System] 🔄 جاري سحب بروكسيات جديدة من {len(self.sources)} مصدر...")
            new_list = await self.fetch_all()
            if new_list:
                self.proxies = new_list
                with open(PROXIES_FILE, "w") as f:
                    f.write("\n".join(new_list))
                print(f"[System] ✅ تم تحديث القائمة: {len(self.proxies)} بروكسي متاح.")
            await asyncio.sleep(600) # تحديث كل 10 دقائق

async def block_resources(route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()

async def attack_cycle(browser, proxy_url, sem):
    async with sem:
        context = None
        try:
            # تقسيم البروكسي لإدخاله في Playwright بشكل صحيح
            proxy_type = proxy_url.split("://")[0]
            proxy_server = proxy_url.split("://")[1]
            
            context = await browser.new_context(
                proxy={"server": f"{proxy_type}://{proxy_server}"},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.route("**/*", block_resources)

            print(f"[Bot] 🚀 دخول عبر: {proxy_server}")
            await page.goto(TARGET, timeout=40000, wait_until="domcontentloaded")

            # محاولة الضغط على الأزرار (تعديل السلكتور إذا تغير الموقع)
            for click_num in [1, 2]:
                btn = page.locator("#btn-main")
                await btn.wait_for(state="visible", timeout=8000)
                await asyncio.sleep(1)
                await btn.click(force=True)
                print(f"[Bot] ✅ ضغطة ({click_num}/2) ناجحة")
                await asyncio.sleep(2)

        except: pass
        finally:
            if context: await context.close()

async def worker_loop(browser, hunter, sem):
    while True:
        if not hunter.proxies:
            await asyncio.sleep(5)
            continue
        proxy = random.choice(hunter.proxies)
        await attack_cycle(browser, proxy, sem)

async def main():
    hunter = ProxyHunter()
    asyncio.create_task(hunter.auto_update_loop())

    print("⏳ بانتظار الدفعة الأولى من المصادر...")
    while not hunter.proxies:
        await asyncio.sleep(2)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        sem = asyncio.Semaphore(CONCURRENT_COUNT)
        workers = [asyncio.create_task(worker_loop(browser, hunter, sem)) for _ in range(CONCURRENT_COUNT)]
        await asyncio.gather(*workers)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 توقف.")
