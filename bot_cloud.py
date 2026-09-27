import os
import sys
import re
import time
import threading
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- KONFIGURASI DARI ENVIRONMENT / DEFAULT ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8814411159:AAFeaPFeh7MIGdRF3BczOJ3mkpr0X_Mcto0")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8261740135")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "20"))
PORT = int(os.getenv("PORT", "10000"))

seen_items = set()

# --- DUMMY HTTP SERVER (Agar Render Mendeteksi Web Service Aktif & Tetap Gratis) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""
        <html>
        <head><title>Multi-AI Promo Hunter</title></head>
        <body style="font-family: Arial, sans-serif; background: #121212; color: #fff; padding: 30px;">
            <h1 style="color: #F97316;">🔥 Multi-AI Promo Hunter Online</h1>
            <p>Status: <b>RUNNING 24/7</b></p>
            <p>Target: Claude Guest Pass, Perplexity Pro, ChatGPT Trial</p>
            <p>Notifikasi aktif ke Telegram: {CHAT_ID}</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        return  # Matikan log HTTP agar terminal bersih

def start_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    print(f"[SERVER] Web health check server aktif di port {PORT}")
    server.serve_forever()

# --- FUNGSI PENGIRIM TELEGRAM ---
def send_telegram(category, title, link, source_url):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        text = (
            f"🔥 <b>PROMO AI BARU DITEMUKAN (24/7 CLOUD)!</b>\n\n"
            f"<b>Kategori:</b> {category}\n"
            f"<b>Info:</b> {title}\n"
            f"<b>Link:</b> {link}\n"
        )
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "⚡ Buka / Klaim Promo", "url": link}],
                    [{"text": "🟠 Sumber Post Reddit", "url": source_url}]
                ]
            }
        }
        res = requests.post(url, json=payload, timeout=10)
        print(f"[TELEGRAM] Notifikasi terkirim: {title} (Status: {res.status_code})")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# --- PEMBURU RADAR REAL-TIME ---
def hunter_loop():
    print("[RADAR] Memulai pemburuan promo 24/7 di latar belakang...")
    # Kirim salam pertama saat bot cloud online
    try:
        startup_msg = "🚀 <b>Bot Hunter Cloud Berhasil Online 24/7 di Render!</b>\nKomputer Anda sekarang bisa dimatikan dengan aman. Bot akan memantau terus dan mengirimkan promo ke sini."
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": startup_msg, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass

    regex_claude_pass = r"claude\.ai/referral/([a-zA-Z0-9_-]+)"
    regex_pplx_link = r"perplexity\.ai/(?:pro\?referral_code=|join/|promo/)([a-zA-Z0-9_-]+)"
    regex_chatgpt_invite = r"(?:chatgpt\.com|chat\.openai\.com)/invite/([a-zA-Z0-9_-]+)"

    scan_round = 0
    while True:
        try:
            scan_round += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Pemindaian ke-{scan_round}...")

            endpoints = [
                ("claude", "https://www.reddit.com/r/ClaudeAI/new.json?limit=20"),
                ("claude", "https://www.reddit.com/r/ClaudeAI/search.json?q=referral+OR+guest+pass+OR+coupon&sort=new&limit=15"),
                ("claude", "https://www.reddit.com/r/Anthropic/new.json?limit=15"),
                ("perplexity", "https://www.reddit.com/r/perplexity_ai/new.json?limit=20"),
                ("perplexity", "https://www.reddit.com/r/perplexity_ai/search.json?q=free+pro+OR+promo+OR+referral&sort=new&limit=15"),
                ("chatgpt", "https://www.reddit.com/r/ChatGPT/new.json?limit=20"),
                ("chatgpt", "https://www.reddit.com/r/OpenAI/new.json?limit=15")
            ]

            headers = {
                "User-Agent": f"CloudPromoRadar/2.0 (Ubuntu; Linux x86_64) Bot_{int(time.time())}"
            }

            for target_type, url in endpoints:
                try:
                    resp = requests.get(url, headers=headers, timeout=8)
                    if resp.status_code == 200:
                        posts = resp.json().get("data", {}).get("children", [])
                        for p in posts:
                            post_data = p.get("data", {})
                            title = post_data.get("title", "")
                            body = post_data.get("selftext", "")
                            permalink = f"https://reddit.com{post_data.get('permalink', '')}"
                            full_text = f"{title} {body}"

                            # 1. Claude Pass
                            if target_type == "claude":
                                for code in re.findall(regex_claude_pass, full_text):
                                    key = f"claude_{code}"
                                    if key not in seen_items:
                                        seen_items.add(key)
                                        send_telegram("Claude 7-Day Pass", f"Code: {code}", f"https://claude.ai/referral/{code}", permalink)

                                if any(w in full_text.lower() for w in ["promo code", "discount code", "coupon", "free credit"]):
                                    for c in re.findall(r"\b[A-Z0-9]{5,15}\b", full_text):
                                        if c not in ["CLAUDE", "ANTHROPIC", "REDDIT", "UPDATE", "FAILED", "ONLINE", "PROMO"]:
                                            key = f"claude_kupon_{c}"
                                            if key not in seen_items:
                                                seen_items.add(key)
                                                send_telegram("Claude Promo/Credit", f"Kupon: {c} ({title[:30]})", permalink, permalink)

                            # 2. Perplexity Pro
                            elif target_type == "perplexity":
                                for p_code in re.findall(regex_pplx_link, full_text):
                                    key = f"pplx_{p_code}"
                                    if key not in seen_items:
                                        seen_items.add(key)
                                        send_telegram("Perplexity Pro", f"Code: {p_code}", f"https://perplexity.ai/pro?referral_code={p_code}", permalink)

                                if any(w in full_text.lower() for w in ["1 year free", "free 1 year", "free 1 month", "paypal promo", "uber promo"]):
                                    key = f"pplx_promo_{post_data.get('id')}"
                                    if key not in seen_items:
                                        seen_items.add(key)
                                        send_telegram("Perplexity Pro", f"Promo: {title[:40]}", permalink, permalink)

                            # 3. ChatGPT Trial
                            elif target_type == "chatgpt":
                                for gpt_code in re.findall(regex_chatgpt_invite, full_text):
                                    key = f"gpt_{gpt_code}"
                                    if key not in seen_items:
                                        seen_items.add(key)
                                        send_telegram("ChatGPT Trial", f"Invite: {gpt_code}", f"https://chatgpt.com/invite/{gpt_code}", permalink)

                except Exception:
                    pass
                time.sleep(1)

        except Exception as e:
            print(f"[ERROR LOOP] {e}")

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    # Jalankan HTTP server di thread terpisah untuk keepalive Render
    t_web = threading.Thread(target=start_http_server, daemon=True)
    t_web.start()

    # Jalankan Scraper loop
    hunter_loop()
