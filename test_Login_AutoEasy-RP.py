import os
import time
import sys
from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

# 1. โหลด Config (ดึงจาก Environment Variables บน CI/CD หรือไฟล์ .env บนเครื่อง)
load_dotenv()
USER_ID = os.getenv("ISUZU_USER")
PASSWORD = os.getenv("ISUZU_PASS")
BASE_URL = "https://autoeasy.isuzu-dealers.com:2443/AutoEasy.Web/Account/Login"

def run(playwright: Playwright) -> None:
    # --- TURBO SETTING: ไม่ใช้ slow_mo และเปิดโหมด Headless ---
    browser = playwright.chromium.launch(headless=True)
    # กำหนด Viewport ให้คงที่ เพื่อให้ Element ไม่ขยับที่
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()

    # --- TURBO OPTIMIZATION: บล็อกรูปภาพทั้งหมด (ลดโหลดหน้าเว็บ 50-70%) ---
    page.route("**/*.{png,jpg,jpeg,svg,webp,gif}", lambda route: route.abort())

    try:
        start_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] 🏁 เริ่มต้นการทดสอบแบบความเร็วสูง...")

        # ไปหน้าเว็บโดยไม่ต้องรอให้โหลดทรัพยากรครบ (เอาแค่โครงสร้างหลัก)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        
        # กรอกข้อมูล Login (ใช้ fill() ซึ่งเร็วกว่าการจำลองพิมพ์ทีละตัว)
        page.get_by_role("textbox", name="User Id *").fill(USER_ID)
        page.get_by_role("textbox", name="Password *").fill(PASSWORD)
        
        page.get_by_role("textbox", name="Select").click()
        page.get_by_role("searchbox").fill("เกาะ")
        page.get_by_role("option", name="เกาะแก้ว -").click()

        print(f"[{time.strftime('%H:%M:%S')}] >> คลิก Login")
        page.get_by_role("button", name="Login - RPL (QA-RP)").click()

        # --- 🛡️ SMART STATE MONITORING (Fast Polling) ---
        success = False
        # วนลูปเช็คถี่ขึ้น (ทุก 0.8 วินาที) เพื่อลดเวลา Idle
        for attempt in range(60): 
            
            # สถานะ A: พบหน้า Dashboard แล้ว (OK)
            ok_btn = page.locator("button:has-text('OK'), button:has-text('ตกลง')").first
            if ok_btn.is_visible():
                ok_btn.click()
                print(f"[{time.strftime('%H:%M:%S')}] ✅ Success! เข้าถึง Dashboard ในรอบที่ {attempt+1}")
                success = True
                break

            # สถานะ B: พบปุ่ม Yes
            yes_btn = page.get_by_role("button", name="Yes")
            if yes_btn.is_visible():
                yes_btn.click()
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ กดยืนยันปุ่ม Yes")

            # สถานะ C: พบช่องกรอกรหัสรอบสอง
            pass_2 = page.get_by_role("textbox", name="Password *")
            if pass_2.is_visible():
                pass_2.fill(PASSWORD)
                # ใช้ระยะเวลารอสั้นๆ (500ms) ให้ปุ่มรับรู้การพิมพ์
                page.wait_for_timeout(500)
                page.get_by_role("button", name="Login - RPL (QA-RP)").click()
                print(f"[{time.strftime('%H:%M:%S')}] >> ยืนยันรหัสรอบสอง")

            # สถานะ D: พบ Error
            error_msg = page.locator(".text-danger, .alert-danger").first
            if error_msg.is_visible():
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Error: {error_msg.inner_text()}")
                break

            # หน่วงเวลาสั้นๆ แล้วเช็คใหม่ทันที
            page.wait_for_timeout(800)

        if not success:
            raise TimeoutError("หมดเวลาการรอคอยหน้า Dashboard")

        duration = time.time() - start_time
        print(f"--- 🎉 จบภารกิจในเวลา: {duration:.2f} วินาที ---")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        if not os.path.exists("screenshots"): os.makedirs("screenshots")
        page.screenshot(path=f"screenshots/turbo_fail_{int(time.time())}.png")
        sys.exit(1)

    finally:
        context.close()
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as p:
        run(p)