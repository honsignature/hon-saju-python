"""
HON. Soul Signature — Saju Logic Engine
Korean Four Pillars calculation using korean_lunar_calendar package
"""
from datetime import datetime
from korean_lunar_calendar import KoreanLunarCalendar
import random

class SajuLogic:
    def __init__(self):
        self.CHEONGAN = ['갑','을','병','정','무','기','경','신','임','계']
        self.JIJI     = ['자','축','인','묘','진','사','오','미','신','유','술','해']

        self.STEM_ELEMENT = {
            '갑':'wood','을':'wood','병':'fire','정':'fire','무':'earth',
            '기':'earth','경':'metal','신':'metal','임':'water','계':'water'
        }
        self.BRANCH_ELEMENT = {
            '자':'water','축':'earth','인':'wood','묘':'wood','진':'earth',
            '사':'fire','오':'fire','미':'earth','신':'metal','유':'metal',
            '술':'earth','해':'water'
        }

        # 천간 오행 인덱스 (wood=0, fire=1, earth=2, metal=3, water=4)
        self.EL_IDX = {'wood':0,'fire':1,'earth':2,'metal':3,'water':4}
        self.EL_KOR = {
            'wood':'목(木)','fire':'화(火)','earth':'토(土)',
            'metal':'금(金)','water':'수(水)'
        }

        # 천간 음양 (0=양, 1=음)
        self.STEM_POL   = [0,1,0,1,0,1,0,1,0,1]
        self.BRANCH_POL = [1,1,0,1,0,0,1,1,0,1,0,0]

        # 시간 → 지지 인덱스
        self.HOUR_TO_ZHI = {
            23:0,0:0,1:1,2:1,3:2,4:2,5:3,6:3,7:4,8:4,
            9:5,10:5,11:6,12:6,13:7,14:7,15:8,16:8,
            17:9,18:9,19:10,20:10,21:11,22:11
        }

        # 일간별 시간 시작 천간
        self.HOUR_START = {0:0,5:0,1:2,6:2,2:4,7:4,3:6,8:6,4:8,9:8}

    # ── 사주 원국 계산 ─────────────────────────────────────────
    def get_gan_zhi(self, year, month, day, hour, minute=0):
        """
        korean_lunar_calendar 패키지로 년/월/일주 계산
        시주는 일간 기준 일상기시법(日上起時法)으로 계산
        """
        calendar = KoreanLunarCalendar()
        calendar.setSolarDate(year, month, day)
        gapja = calendar.getGapJaString().split()
        # gapja[0]=년주, gapja[1]=월주, gapja[2]=일주 (예: ['갑자', '병인', '무오'])

        def parse_pillar(s):
            g, z = s[0], s[1]
            g_idx = self.CHEONGAN.index(g)
            z_idx = self.JIJI.index(z)
            return {
                'gan': g, 'zhi': z,
                'gan_idx': g_idx, 'zhi_idx': z_idx,
                'gan_element': self.STEM_ELEMENT[g],
                'zhi_element': self.BRANCH_ELEMENT[z]
            }

        year_p  = parse_pillar(gapja[0])
        month_p = parse_pillar(gapja[1])
        day_p   = parse_pillar(gapja[2])

        # 시주 계산
        h_zhi_idx = self.HOUR_TO_ZHI.get(hour, 0)
        d_gan_idx = day_p['gan_idx']
        h_gan_idx = (self.HOUR_START[d_gan_idx % 10] + h_zhi_idx) % 10
        h_gan = self.CHEONGAN[h_gan_idx]
        h_zhi = self.JIJI[h_zhi_idx]

        hour_p = {
            'gan': h_gan, 'zhi': h_zhi,
            'gan_idx': h_gan_idx, 'zhi_idx': h_zhi_idx,
            'gan_element': self.STEM_ELEMENT[h_gan],
            'zhi_element': self.BRANCH_ELEMENT[h_zhi]
        }

        return {'year': year_p, 'month': month_p, 'day': day_p, 'hour': hour_p}

    # ── 오행 분포 ──────────────────────────────────────────────
    def get_ohaeng_distribution(self, pillars):
        counts = {'wood':0,'fire':0,'earth':0,'metal':0,'water':0}
        for p in pillars.values():
            counts[p['gan_element']] += 1
            counts[p['zhi_element']] += 1
        return counts

    # ── 십성 판정 ──────────────────────────────────────────────
    def _ten_god(self, me_el, me_pol, target_el, target_pol):
        names = [
            ['비견','겁재'],
            ['식신','상관'],
            ['편재','정재'],
            ['편관','정관'],
            ['편인','정인'],
        ]
        diff = (self.EL_IDX[target_el] - self.EL_IDX[me_el]) % 5
        same = 0 if me_pol == target_pol else 1
        return names[diff][same]

    # ── 대운 계산 ──────────────────────────────────────────────
    def _calc_daewoon(self, pillars, gender, birth_day):
        year_gan_idx = pillars['year']['gan_idx']
        month_gan_idx = pillars['month']['gan_idx']
        month_zhi_idx = pillars['month']['zhi_idx']

        is_yang = year_gan_idx % 2 == 0
        is_male = gender == 'male'
        forward = (is_yang and is_male) or (not is_yang and not is_male)
        step = 1 if forward else -1

        start_age = birth_day % 10 or 10
        daewoon = []
        for i in range(8):
            g_idx = (month_gan_idx + step * (i + 1)) % 10
            z_idx = (month_zhi_idx + step * (i + 1)) % 12
            g = self.CHEONGAN[g_idx]
            z = self.JIJI[z_idx]
            age = start_age + i * 10
            daewoon.append({
                'age': age,
                'gan': g, 'zhi': z,
                'gan_element': self.STEM_ELEMENT[g],
                'zhi_element': self.BRANCH_ELEMENT[z],
                'text': self._daewoon_text(pillars['day']['gan_idx'], g_idx)
            })
        return daewoon

    def _daewoon_text(self, day_master_idx, dw_idx):
        me_el  = self.STEM_ELEMENT[self.CHEONGAN[day_master_idx]]
        dw_el  = self.STEM_ELEMENT[self.CHEONGAN[dw_idx]]
        me_pol = self.STEM_POL[day_master_idx]
        dw_pol = self.STEM_POL[dw_idx]
        god = self._ten_god(me_el, me_pol, dw_el, dw_pol)
        texts = {
            '비견': '[비견] 동료와의 협력이 강조되는 시기입니다. 독립심과 추진력이 강해지며 새로운 도전이 시작됩니다.',
            '겁재': '[겁재] 경쟁이 치열해지고 재물의 변동이 있을 수 있습니다. 협력보다 독자적 판단이 요구됩니다.',
            '식신': '[식신] 재능과 창의력이 꽃피는 시기입니다. 여유와 표현, 전문성으로 인정받을 수 있습니다.',
            '상관': '[상관] 변화와 혁신을 추구하는 에너지가 강합니다. 기존 틀을 벗어나 새로운 길을 개척하세요.',
            '편재': '[편재] 사업 수완과 투자 감각이 빛나는 시기입니다. 과감한 도전이 결실을 맺을 수 있습니다.',
            '정재': '[정재] 안정적인 수입과 성실한 노력이 보상받는 시기입니다. 꾸준함이 최고의 전략입니다.',
            '편관': '[편관] 책임과 리더십이 강조됩니다. 도전적인 환경에서 진가를 발휘할 수 있습니다.',
            '정관': '[정관] 명예와 신뢰가 높아지는 시기입니다. 조직 내 승진이나 공적인 인정이 따릅니다.',
            '편인': '[편인] 학문, 연구, 특수 기술에서 두각을 나타냅니다. 직관과 영감이 강해집니다.',
            '정인': '[정인] 귀인의 도움과 학문적 성취가 기대됩니다. 안정적인 배움과 성장의 시기입니다.',
        }
        return texts.get(god, f'[{god}] 새로운 변화와 도약의 시기입니다.')

    # ── 오행 분석 ──────────────────────────────────────────────
    def _ohaeng_analysis(self, counts):
        total = sum(counts.values())
        pct = {k: round(v / total * 100, 1) for k, v in counts.items()}
        details = []
        for el, p in pct.items():
            if p >= 37.5:
                details.append({'element': el, 'status': 'excess',
                    'msg': f'{self.EL_KOR[el]} 기운이 매우 강합니다. 과도한 에너지를 조절하세요.'})
            elif p == 0:
                details.append({'element': el, 'status': 'missing',
                    'msg': f'{self.EL_KOR[el]} 기운이 없습니다. 의식적으로 보완이 필요합니다.'})
        missing = [el for el, p in pct.items() if p == 0]
        if not details:
            balance = "오행이 골고루 갖춰진 황금 밸런스입니다! 타고난 조화로움이 큰 강점입니다."
        elif missing:
            balance = f"{', '.join([self.EL_KOR[e] for e in missing])} 기운이 부족합니다. 해당 기운을 보완하면 균형이 잡힙니다."
        else:
            balance = "특정 기운의 쏠림이 보입니다. 균형을 위한 의식적 노력이 필요합니다."
        return {'percentages': pct, 'details': details, 'balance_text': balance}

    # ── 근묘화실 ──────────────────────────────────────────────
    def _gmhs(self, pillars, day_master_el):
        periods = {
            'year':  ('초년기 (0~19세)',  '인생의 뿌리가 형성되는 시기입니다. 부모의 영향과 초년의 환경이 평생의 기질을 결정짓습니다.'),
            'month': ('청년기 (20~39세)', '사회에 첫발을 내딛고 자아를 실현하는 시기입니다. 직업과 인간관계에서 가장 역동적인 변화가 일어납니다.'),
            'day':   ('중년기 (40~59세)', '인생의 꽃이 피는 시기입니다. 가정과 커리어에서 결실을 맺고 진정한 자신을 발견합니다.'),
            'hour':  ('말년기 (60세~)',   '지혜와 여유로 빛나는 시기입니다. 평생 쌓아온 것들이 아름다운 결실로 돌아옵니다.'),
        }
        result = {}
        for k, (period, base_desc) in periods.items():
            p = pillars[k]
            result[k] = {'period': period, 'desc': base_desc, 'pillar': p}
        return result

    # ── 오늘의 운세 ───────────────────────────────────────────
    def _today_luck(self, day_master_el):
        today = datetime.now()
        fortunes = [
            {'title': '✨ 귀인의 도움이 있는 날', 'desc': '뜻밖의 도움이 찾아오는 날입니다. 주변의 인연에 열린 마음을 가지세요.'},
            {'title': '🌱 새로운 시작의 날', 'desc': '새로운 도전을 시작하기 좋은 날입니다. 작은 한 걸음이 큰 변화를 만듭니다.'},
            {'title': '💰 재물운이 좋은 날', 'desc': '재물과 관련된 일에 긍정적인 에너지가 흐릅니다. 중요한 결정을 내리기 좋습니다.'},
            {'title': '🤝 관계가 빛나는 날', 'desc': '대인관계에서 좋은 에너지가 흐릅니다. 소중한 사람들과의 시간을 만들어보세요.'},
            {'title': '🎯 집중력이 높은 날', 'desc': '오늘은 집중력과 판단력이 특히 뛰어납니다. 중요한 업무나 결정에 집중하세요.'},
        ]
        import hashlib
        seed = int(hashlib.md5(f"{today.date()}{day_master_el}".encode()).hexdigest(), 16) % len(fortunes)
        fortune = fortunes[seed]
        return {
            'title': fortune['title'],
            'desc': fortune['desc'],
            'pillar': '오늘',
            'date': today.strftime('%Y년 %m월 %d일')
        }

    # ── 일간별 핵심 성향 ──────────────────────────────────────
    def _core_trait(self, gan):
        traits = {
            '갑': "🌲 **곧게 뻗은 소나무의 기운** — 강한 추진력과 리더십을 타고났습니다. 새로운 일을 시작하는 데 두려움이 없으며 명예를 중시합니다.",
            '을': "🌿 **유연한 넝쿨의 기운** — 뛰어난 적응력과 내면의 강인함을 가집니다. 섬세한 감각과 조화로운 대인관계가 강점입니다.",
            '병': "☀️ **세상을 비추는 태양의 기운** — 열정적이고 솔직하며 화려한 존재감을 가집니다. 주변을 밝히는 타고난 리더입니다.",
            '정': "🕯️ **은근히 타오르는 촛불의 기운** — 따뜻함과 섬세함, 깊은 헌신으로 주변을 감동시킵니다.",
            '무': "⛰️ **묵직한 태산의 기운** — 믿음직하고 포용력이 크며 신중한 판단력을 가집니다.",
            '기': "🌱 **비옥한 대지의 기운** — 현실적이고 실속 있으며 넓은 수용력과 배려심이 강점입니다.",
            '경': "🪨 **단단한 원석의 기운** — 강한 의리와 결단력, 확고한 신념으로 어떤 어려움도 이겨냅니다.",
            '신': "💎 **빛나는 보석의 기운** — 섬세한 미적 감각과 높은 자존심, 완벽을 추구하는 기질을 가집니다.",
            '임': "🌊 **드넓은 바다의 기운** — 깊은 지혜와 유연한 창의력으로 어떤 상황도 헤쳐나갑니다.",
            '계': "🌧️ **촉촉한 단비의 기운** — 섬세한 감수성과 친화력, 깊은 지혜로 주변을 이롭게 합니다.",
        }
        return traits.get(gan, f"**{gan}의 기운** — 독특한 매력과 강인한 생명력을 지닌 사주입니다.")

    # ── 메인 해석 ─────────────────────────────────────────────
    def interpret(self, pillars, ohaeng, user_info):
        gender = user_info.get('gender', 'female')
        day_gan = pillars['day']['gan']
        day_el  = pillars['day']['gan_element']
        day_gan_idx = pillars['day']['gan_idx']
        day_pol = self.STEM_POL[day_gan_idx]

        # 십성
        ten_gods = {}
        for k in ['year','month','day','hour']:
            p = pillars[k]
            if k == 'day':
                ten_gods[k] = {'gan': '나', 'zhi': self._ten_god(
                    day_el, day_pol, p['zhi_element'], self.BRANCH_POL[p['zhi_idx']])}
            else:
                ten_gods[k] = {
                    'gan': self._ten_god(day_el, day_pol, p['gan_element'], self.STEM_POL[p['gan_idx']]),
                    'zhi': self._ten_god(day_el, day_pol, p['zhi_element'], self.BRANCH_POL[p['zhi_idx']])
                }

        ohaeng_analysis = self._ohaeng_analysis(ohaeng)
        daewoon = self._calc_daewoon(pillars, gender, pillars['day']['zhi_idx'])
        gmhs = self._gmhs(pillars, day_el)
        today = self._today_luck(day_el)
        core = self._core_trait(day_gan)

        # 기본 해석 텍스트
        missing = [k for k, v in ohaeng.items() if v == 0]
        strong  = max(ohaeng, key=ohaeng.get)

        summary = (
            f"**{day_gan}({self.EL_KOR[day_el]})** 일간을 가진 당신은 {core.split('—')[1].strip() if '—' in core else '독특한 매력을 가지고 있습니다.'} "
            f"사주 원국에서 **{self.EL_KOR[strong]}** 기운이 두드러지며, "
            + (f"**{', '.join([self.EL_KOR[e] for e in missing])}** 기운을 보완하면 더욱 균형 잡힌 삶을 살 수 있습니다." if missing
               else "오행이 고르게 분포된 이상적인 구성입니다.")
        )

        wealth_texts = {
            'wood': '꾸준한 성장형 재물운입니다. 장기적 투자와 사업 확장에서 결실을 맺습니다.',
            'fire': '활발한 활동과 네트워크를 통해 재물이 들어옵니다. 인맥이 곧 재물입니다.',
            'earth': '안정적이고 견고한 재물운입니다. 부동산이나 실물 자산에 강점이 있습니다.',
            'metal': '정확한 판단과 분석력으로 재물을 모읍니다. 금융이나 투자에 뛰어납니다.',
            'water': '유동적인 재물운으로 다양한 분야에서 수입이 생깁니다. 아이디어가 돈이 됩니다.',
        }
        love_texts = {
            'wood': '순수하고 진지한 사랑을 추구합니다. 한번 마음을 주면 깊고 오래갑니다.',
            'fire': '열정적이고 솔직한 사랑 스타일입니다. 감정 표현이 풍부해 주변을 설레게 합니다.',
            'earth': '안정과 신뢰를 중시합니다. 든든한 파트너로 오랜 관계를 유지하는 능력이 있습니다.',
            'metal': '이상이 높고 완벽한 사랑을 추구합니다. 진정한 인연을 만나면 헌신적입니다.',
            'water': '감수성이 풍부하고 깊은 교감을 나눕니다. 감정적 교류가 사랑의 핵심입니다.',
        }

        return {
            'core':             core,
            'total_summary':    summary,
            'personality_deep': core,
            'social_analysis':  f"{self.EL_KOR[day_el]} 기운을 바탕으로 창의적이고 전문적인 분야에서 두각을 나타냅니다.",
            'health_analysis':  ohaeng_analysis['balance_text'],
            'daewoon_trend':    f"현재 대운은 {daewoon[0]['gan']}{daewoon[0]['zhi']} 시기로, {daewoon[0]['text'].split(']')[1].strip() if ']' in daewoon[0]['text'] else '새로운 변화의 시기입니다.'}",
            'love_romance':     love_texts.get(day_el, '진실한 사랑을 추구합니다.'),
            'wealth_strategy':  wealth_texts.get(day_el, '꾸준한 노력으로 재물을 축적합니다.'),
            'advice':           ohaeng_analysis['balance_text'],
            'today_luck':       today,
            'gmhs':             gmhs,
            'daewoon':          daewoon,
            'ten_gods':         ten_gods,
            'ohaeng_analysis':  ohaeng_analysis,
        }
