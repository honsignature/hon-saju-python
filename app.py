import os
import json
from flask import Flask, render_template, request, jsonify
from saju_logic import SajuLogic
from ai_analysis import AIAnalysis
from datetime import datetime
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
saju = SajuLogic()
ai = AIAnalysis()

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

        y, m, d = map(int, birth_date.split('-'))
        hh, mm  = map(int, birth_time.split(':'))

        pillars = saju.get_gan_zhi(y, m, d, hh, mm)
        ohaeng  = saju.get_ohaeng_distribution(pillars)
        interp  = saju.interpret(pillars, ohaeng, {'gender': gender})

        age           = datetime.now().year - y + 1
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

        ai_data = ai.get_deep_analysis(
            name, gender, pillars,
            interp['ohaeng_analysis'],
            ten_stars_str,
            current_daewun,
            birth_context
        )

        if ai_data:
            interp['total_summary']    = ai_data.get('total_summary',    interp.get('total_summary', ''))
            interp['personality_deep'] = ai_data.get('personality_deep', interp.get('core', ''))
            interp['social_analysis']  = ai_data.get('social_analysis',  interp.get('career', ''))
            interp['health_analysis']  = ai_data.get('health_analysis',  interp.get('advice', ''))
            interp['daewoon_trend']    = ai_data.get('daewoon_trend',    '')
            interp['love_romance']     = ai_data.get('love_romance',     interp.get('love', ''))
            interp['wealth_strategy']  = ai_data.get('wealth_strategy',  interp.get('wealth', ''))
            interp['core']             = ai_data.get('personality_deep', interp.get('core', ''))
            interp['advice']           = ai_data.get('health_analysis',  interp.get('advice', ''))

            if 'gmhs' in ai_data and isinstance(ai_data['gmhs'], dict):
                for period in ['year', 'month', 'day', 'hour']:
                    if period in ai_data['gmhs'] and period in interp['gmhs']:
                        interp['gmhs'][period]['desc'] = ai_data['gmhs'][period]

            if 'today_luck' in ai_data:
                interp['today_luck']['desc'] = str(ai_data['today_luck'])

        return render_template('result.html',
                               name=name,
                               pillars=pillars,
                               ohaeng=ohaeng,
                               interp=interp)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"An error occurred: {str(e)}", 400


# ── /calculate 엔드포인트 (Netlify Webhook에서 호출) ──────────────
@app.route('/calculate', methods=['POST'])
def calculate():
    """
    Netlify saju-webhook.js 에서 POST로 호출
    Input JSON: { birth_date, birth_time, gender, calendar }
    Output JSON: { pillars, ohaeng, interp }
    """
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

        # 시간 파싱
        if birth_time and ':' in birth_time:
            hh, mm = map(int, birth_time.split(':')[:2])
        else:
            hh, mm = 12, 0

        # 날짜 파싱
        parts = birth_date.replace('.', '-').split('-')
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])

        # 사주 계산
        pillars = saju.get_gan_zhi(y, m, d, hh, mm)
        ohaeng  = saju.get_ohaeng_distribution(pillars)
        interp  = saju.interpret(pillars, ohaeng, {'gender': gender})

        # 십성 분석
        ten_gods_all = []
        for pk in interp.get('ten_gods', {}):
            ten_gods_all.append(interp['ten_gods'][pk]['gan'])
            ten_gods_all.append(interp['ten_gods'][pk]['zhi'])
        counts        = Counter(ten_gods_all)
        ten_stars_str = ", ".join([f"{k}×{v}" for k, v in counts.items()])

        # 대운
        daewoon_list = interp.get('daewoon', [])
        current_daewun = ""
        if daewoon_list:
            current_daewun = (
                f"{daewoon_list[0]['age']}s cycle "
                f"({daewoon_list[0]['gan']}{daewoon_list[0]['zhi']})"
            )

        age           = datetime.now().year - y + 1
        birth_context = f"Born {y} (Age {age}), Calendar: {calendar}"

        # 결과 반환
        return jsonify({
            "success": True,
            "pillars": pillars,
            "ohaeng": ohaeng,
            "ten_stars": ten_stars_str,
            "current_daewun": current_daewun,
            "birth_context": birth_context,
            "ohaeng_analysis": interp.get('ohaeng_analysis', ''),
            "summary": interp.get('total_summary', ''),
            "daewoon": daewoon_list[:3] if daewoon_list else [],
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print(f"HON. Soul Signature — Server starting at: {BASE_DIR}")
    app.run(debug=True, port=5000)
