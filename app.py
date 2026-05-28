import os
import json
import threading
from flask import Flask, render_template, request, jsonify
from saju_logic import SajuLogic
from ai_analysis import AIAnalysis
from datetime import datetime
from collections import Counter
from korean_lunar_calendar import KoreanLunarCalendar
import requests

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR   = os.path.join(BASE_DIR, 'static')

app  = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
saju = SajuLogic()
ai   = AIAnalysis()

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
RESEND_API_KEY     = os.environ.get("RESEND_API_KEY")
FROM_EMAIL         = os.environ.get("SHOPIFY_FROM_EMAIL", "hello@honsignature.com")

# 중복 방지
processed_orders = set()


# ── 유틸 ──────────────────────────────────────────────────────────

def lunar_to_solar(y, m, d):
    calendar = KoreanLunarCalendar()
    calendar.setLunarDate(y, m, d, False)
    solar = calendar.SolarIsoFormat()
    parts = solar.split('-')
    return int(parts[0]), int(parts[1]), int(parts[2])


def format_saju_text(text):
    lines = text.split('\n')
    html = ''
    for line in lines:
        line = line.strip()
        if not line:
            continue
        import re
        title_match = re.match(r'^([A-Z][A-Z\s&0-9]+):(.*)$', line)
        if title_match and len(title_match.group(1).strip()) > 3:
            title = title_match.group(1).strip()
            rest  = title_match.group(2).strip()
            html += f'''<div style="margin:32px 0 12px;">
  <p style="margin:0 0 2px;color:#c9a96e;font-size:10px;letter-spacing:3px;font-family:Arial,sans-serif;text-transform:uppercase;">{title}</p>
  <div style="width:24px;height:1px;background:#c9a96e;margin:6px 0 12px;"></div>
  {f'<p style="margin:0;color:#2c2c2c;font-size:15px;line-height:1.9;font-family:Georgia,serif;">{rest}</p>' if rest else ''}
</div>'''
        else:
            html += f'<p style="margin:0 0 14px;color:#2c2c2c;font-size:15px;line-height:1.9;font-family:Georgia,serif;">{line}</p>'
    return html


def generate_saju_claude(info):
    is_lunar = info.get('calendar', '').lower() in ['lunar', '음력']
    calendar_note = (
        "IMPORTANT: The birth date provided is in the LUNAR calendar system."
        if is_lunar else
        "The birth date is in the Solar (Gregorian) calendar."
    )
    prompt = f"""You are a grandmaster of Korean Saju (Four Pillars of Destiny). Create a premium, deeply personal Soul Reading Report for HON. Soul Signature luxury brand.

Client:
- Name: {info.get('customerName', 'Guest')}
- Date of Birth: {info.get('birthDate')} ({calendar_note})
- Hour of Birth: {info.get('birthTime') or 'Not provided'}
- Gender: {info.get('gender') or 'Not provided'}

Write a premium Soul Signature Report in English. Be specific, poetic, and deeply insightful. Do NOT use markdown symbols (**, ##, *, #). Use SECTION TITLES IN ALL CAPS followed by a colon.

Include these sections with 4-5 sentences each:

SOUL ESSENCE:
THE FOUR PILLARS:
INNATE CHARACTER AND GIFTS:
LIFE PATH AND DESTINY:
WEALTH AND CAREER:
LOVE AND RELATIONSHIPS:
HEALTH AND VITALITY:
2026 COSMIC FORECAST:
SOUL GUIDANCE:

Write 1500-2000 words total. Make it feel like a bespoke luxury reading."""

    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model":      "claude-sonnet-4-5",
            "max_tokens": 4000,
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=300,  # 5분 타임아웃
    )
    res.raise_for_status()
    return res.json()["content"][0]["text"]


def send_email_resend(info, saju_text):
    formatted = format_saju_text(saju_text)
    calendar_label = "Lunar Calendar" if info.get('calendar', '').lower() in ['lunar', '음력'] else "Solar Calendar"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f0ede8;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0ede8;padding:48px 20px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;background:#fff;overflow:hidden;box-shadow:0 8px 60px rgba(0,0,0,0.15);">

  <tr><td style="background:#0a0a0a;padding:56px 60px 48px;text-align:center;">
    <p style="margin:0 0 4px;color:#c9a96e;font-size:9px;letter-spacing:6px;font-family:Arial,sans-serif;">H · O · N</p>
    <p style="margin:0 0 20px;color:#c9a96e;font-size:8px;letter-spacing:4px;font-family:Arial,sans-serif;">SOUL SIGNATURE</p>
    <div style="width:1px;height:40px;background:linear-gradient(to bottom,transparent,#c9a96e,transparent);margin:0 auto 20px;"></div>
    <h1 style="margin:0 0 8px;color:#f5f0e8;font-size:30px;font-weight:400;letter-spacing:3px;font-family:Georgia,serif;">Your Soul Reading</h1>
    <p style="margin:0;color:#666;font-size:11px;letter-spacing:3px;font-family:Arial,sans-serif;text-transform:uppercase;">A Personal Cosmic Report</p>
  </td></tr>

  <tr><td style="padding:48px 60px 32px;">
    <p style="margin:0 0 4px;color:#c9a96e;font-size:9px;letter-spacing:3px;font-family:Arial,sans-serif;text-transform:uppercase;">Prepared exclusively for</p>
    <h2 style="margin:0 0 20px;color:#0a0a0a;font-size:26px;font-weight:400;font-family:Georgia,serif;letter-spacing:1px;">{info.get('customerName')}</h2>
    <table cellpadding="0" cellspacing="0">
      <tr><td style="padding:4px 16px 4px 0;color:#999;font-size:11px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;">Date of Birth</td>
          <td style="color:#333;font-size:13px;font-family:Georgia,serif;">{info.get('birthDate')} <span style="color:#c9a96e;font-size:11px;">({calendar_label})</span></td></tr>
      <tr><td style="padding:4px 16px 4px 0;color:#999;font-size:11px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;">Hour of Birth</td>
          <td style="color:#333;font-size:13px;font-family:Georgia,serif;">{info.get('birthTime') or 'Not provided'}</td></tr>
      <tr><td style="padding:4px 16px 4px 0;color:#999;font-size:11px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;">Order</td>
          <td style="color:#333;font-size:13px;font-family:Georgia,serif;">#{info.get('orderNumber')}</td></tr>
    </table>
  </td></tr>

  <tr><td style="padding:0 60px 32px;"><div style="border-top:1px solid #e8e4dc;"></div></td></tr>

  <tr><td style="padding:0 60px 32px;">
    <p style="margin:0;color:#666;font-size:14px;line-height:1.9;font-family:Georgia,serif;font-style:italic;border-left:2px solid #c9a96e;padding-left:20px;">
      The ancient Korean art of Saju — the Four Pillars of Destiny — holds within it the cosmic blueprint of your soul. What follows is a deeply personal reading, drawn from the exact moment of your birth and the elemental forces that shaped your arrival into this world.
    </p>
  </td></tr>

  <tr><td style="padding:0 60px 32px;"><div style="border-top:1px solid #e8e4dc;"></div></td></tr>

  <tr><td style="padding:0 60px 48px;">{formatted}</td></tr>

  <tr><td style="background:#0a0a0a;padding:44px 60px;text-align:center;">
    <div style="width:30px;height:1px;background:#c9a96e;margin:0 auto 20px;"></div>
    <p style="margin:0 0 6px;color:#c9a96e;font-size:9px;letter-spacing:5px;font-family:Arial,sans-serif;">H · O · N · S O U L · S I G N A T U R E</p>
    <p style="margin:0 0 16px;color:#444;font-size:11px;font-family:Arial,sans-serif;">K-Heritage of Soul · Crafted by Time · Sealed in Korea</p>
    <p style="margin:0 0 4px;color:#444;font-size:11px;font-family:Arial,sans-serif;">Questions? <a href="mailto:{FROM_EMAIL}" style="color:#c9a96e;text-decoration:none;">{FROM_EMAIL}</a></p>
    <p style="margin:0;color:#333;font-size:10px;font-family:Arial,sans-serif;">This report is for personal use only.</p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    res = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "from":    f"HON. Soul Signature <{FROM_EMAIL}>",
            "to":      [info["email"]],
            "subject": f"✦ {info.get('customerName')}, Your Soul Signature Report is Ready — HON.",
            "html":    html_body,
        },
        timeout=30,
    )
    res.raise_for_status()
    print(f"Email sent: {info['email']} / {res.json().get('id')}")
    return res.json()


def process_saju_background(info):
    """백그라운드에서 Claude 호출 + 이메일 발송"""
    order_id = str(info.get('orderId', ''))
    try:
        print(f"[START] {info.get('orderNumber')} / {info.get('email')}")
        saju_text = generate_saju_claude(info)
        print(f"[CLAUDE OK] length={len(saju_text)}")
        send_email_resend(info, saju_text)
        print(f"[DONE] {info.get('orderNumber')}")
    except Exception as e:
        # 실패 시 중복 방지 캐시에서 제거 (재시도 가능하게)
        processed_orders.discard(order_id)
        print(f"[ERROR] {info.get('orderNumber')}: {e}")
        import traceback
        traceback.print_exc()


# ── /process-saju 엔드포인트 (Netlify에서 호출) ───────────────────
@app.route('/process-saju', methods=['POST'])
def process_saju():
    try:
        info = request.get_json()
        if not info:
            return jsonify({"error": "No data"}), 400

        order_id = str(info.get('orderId', ''))

        # 중복 방지
        if order_id and order_id in processed_orders:
            print(f"[SKIP] Already processing: {order_id}")
            return jsonify({"success": True, "skipped": True}), 200

        if order_id:
            processed_orders.add(order_id)

        # 백그라운드 스레드로 처리 (즉시 200 반환)
        t = threading.Thread(target=process_saju_background, args=(info,))
        t.daemon = True
        t.start()

        return jsonify({"success": True, "queued": True}), 200

    except Exception as e:
        print(f"[ERROR] process_saju: {e}")
        return jsonify({"error": str(e)}), 500


# ── 기존 엔드포인트 유지 ──────────────────────────────────────────

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "HON. Saju Python Engine"})


@app.route('/loading', methods=['POST'])
def loading():
    return render_template('loading.html', data=request.form)


@app.route('/result', methods=['POST'])
def result():
    name       = request.form.get('name', 'Guest')
    gender     = request.form.get('gender', 'female')
    birth_date = request.form.get('birth_date')
    birth_time = request.form.get('birth_time')
    try:
        if not birth_date or not birth_time:
            return "Please provide both birth date and time.", 400
        y, m, d   = map(int, birth_date.split('-'))
        hh, mm    = map(int, birth_time.split(':'))
        pillars   = saju.get_gan_zhi(y, m, d, hh, mm)
        ohaeng    = saju.get_ohaeng_distribution(pillars)
        interp    = saju.interpret(pillars, ohaeng, {'gender': gender})
        age       = datetime.now().year - y + 1
        birth_context = f"Born {y} (Age {age})"
        ten_gods_all = []
        for pk in interp['ten_gods']:
            ten_gods_all.append(interp['ten_gods'][pk]['gan'])
            ten_gods_all.append(interp['ten_gods'][pk]['zhi'])
        counts        = Counter(ten_gods_all)
        ten_stars_str = ", ".join([f"{k}×{v}" for k, v in counts.items()])
        current_daewun = (
            f"{interp['daewoon'][0]['age']}s cycle "
            f"({interp['daewoon'][0]['gan']}{interp['daewoon'][0]['zhi']})"
        )
        ai_data = ai.get_deep_analysis(name, gender, pillars, interp['ohaeng_analysis'], ten_stars_str, current_daewun, birth_context)
        if ai_data:
            interp['total_summary']   = ai_data.get('total_summary', interp.get('total_summary', ''))
            interp['personality_deep']= ai_data.get('personality_deep', interp.get('core', ''))
            interp['social_analysis'] = ai_data.get('social_analysis', interp.get('career', ''))
            interp['health_analysis'] = ai_data.get('health_analysis', interp.get('advice', ''))
            interp['daewoon_trend']   = ai_data.get('daewoon_trend', '')
            interp['love_romance']    = ai_data.get('love_romance', interp.get('love', ''))
            interp['wealth_strategy'] = ai_data.get('wealth_strategy', interp.get('wealth', ''))
            interp['core']            = ai_data.get('personality_deep', interp.get('core', ''))
            interp['advice']          = ai_data.get('health_analysis', interp.get('advice', ''))
            if 'gmhs' in ai_data and isinstance(ai_data['gmhs'], dict):
                for period in ['year', 'month', 'day', 'hour']:
                    if period in ai_data['gmhs'] and period in interp['gmhs']:
                        interp['gmhs'][period]['desc'] = ai_data['gmhs'][period]
            if 'today_luck' in ai_data:
                interp['today_luck']['desc'] = str(ai_data['today_luck'])
        return render_template('result.html', name=name, pillars=pillars, ohaeng=ohaeng, interp=interp)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"An error occurred: {str(e)}", 400


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400

        birth_date = data.get('birth_date')
        birth_time = data.get('birth_time', '12:00')
        gender     = data.get('gender', 'female')
        calendar   = data.get('calendar', 'solar')
        name       = data.get('name', 'Guest')

        if not birth_date:
            return jsonify({"error": "birth_date required"}), 400

        hh, mm = (map(int, birth_time.split(':')[:2]) if birth_time and ':' in birth_time else (12, 0))
        parts  = birth_date.replace('.', '-').split('-')
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])

        solar_y, solar_m, solar_d = y, m, d
        if calendar and calendar.lower() in ['lunar', '음력']:
            try:
                solar_y, solar_m, solar_d = lunar_to_solar(y, m, d)
            except Exception as e:
                print(f"음력 변환 오류: {e}")

        pillars   = saju.get_gan_zhi(solar_y, solar_m, solar_d, hh, mm)
        ohaeng    = saju.get_ohaeng_distribution(pillars)
        interp    = saju.interpret(pillars, ohaeng, {'gender': gender})

        ten_gods_all = []
        for pk in interp.get('ten_gods', {}):
            ten_gods_all.append(interp['ten_gods'][pk]['gan'])
            ten_gods_all.append(interp['ten_gods'][pk]['zhi'])
        counts        = Counter(ten_gods_all)
        ten_stars_str = ", ".join([f"{k}×{v}" for k, v in counts.items()])

        daewoon_list   = interp.get('daewoon', [])
        current_daewun = ""
        if daewoon_list:
            current_daewun = f"{daewoon_list[0]['age']}s cycle ({daewoon_list[0]['gan']}{daewoon_list[0]['zhi']})"

        age = datetime.now().year - solar_y + 1
        return jsonify({
            "success":        True,
            "pillars":        pillars,
            "ohaeng":         ohaeng,
            "ten_stars":      ten_stars_str,
            "current_daewun": current_daewun,
            "birth_context":  f"Born {y}, Age {age}",
            "ohaeng_analysis":interp.get('ohaeng_analysis', {}).get('balance_text', ''),
            "solar_date":     f"{solar_y}-{solar_m:02d}-{solar_d:02d}",
            "lunar_date":     f"{y}-{m:02d}-{d:02d}" if calendar and calendar.lower() in ['lunar', '음력'] else None,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print(f"HON. Soul Signature — Server starting at: {BASE_DIR}")
    app.run(debug=True, port=5000)
