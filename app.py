import os
from flask import Flask, render_template, request
from saju_logic import SajuLogic
from ai_analysis import AIAnalysis
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
saju = SajuLogic()
ai = AIAnalysis()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/loading', methods=['POST'])
def loading():
    return render_template('loading.html', data=request.form)

@app.route('/result', methods=['POST'])
def result():
    name    = request.form.get('name', 'Guest')
    gender  = request.form.get('gender', 'female')
    birth_date = request.form.get('birth_date')
    birth_time = request.form.get('birth_time')

    try:
        if not birth_date or not birth_time:
            return "Please provide both birth date and time.", 400

        y, m, d    = map(int, birth_date.split('-'))
        hh, mm     = map(int, birth_time.split(':'))

        # ── 1. 사주 계산 (Python 로컬 엔진 100% 정확) ──────────────
        pillars      = saju.get_gan_zhi(y, m, d, hh, mm)
        ohaeng       = saju.get_ohaeng_distribution(pillars)
        interp       = saju.interpret(pillars, ohaeng, {'gender': gender})

        # ── 2. AI 전달용 데이터 정제 ────────────────────────────────
        age           = datetime.now().year - y + 1
        birth_context = f"Born {y} (Age {age})"

        from collections import Counter
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

        # ── 3. Claude API 영문 해석 ──────────────────────────────────
        ai_data = ai.get_deep_analysis(
            name, gender, pillars,
            interp['ohaeng_analysis'],
            ten_stars_str,
            current_daewun,
            birth_context
        )

        # ── 4. AI 결과 병합 (계산값은 절대 덮어쓰지 않음) ───────────
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

if __name__ == '__main__':
    print(f"HON. Soul Signature — Server starting at: {BASE_DIR}")
    app.run(debug=True, port=5000)
