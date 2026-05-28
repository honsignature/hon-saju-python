import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

class AIAnalysis:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def get_deep_analysis(self, name, gender, pillars, ohaeng, ten_stars_str, current_daewun, birth_context):
        if not self.client:
            return None

        ohaeng_str = ", ".join([
            f"{k.capitalize()}({v:.0f}%)" for k, v in ohaeng['percentages'].items()
        ])

        pillars_summary = (
            f"Year:[{pillars['year']['gan']}{pillars['year']['zhi']}] "
            f"Month:[{pillars['month']['gan']}{pillars['month']['zhi']}] "
            f"Day:[{pillars['day']['gan']}{pillars['day']['zhi']}] "
            f"Hour:[{pillars['hour']['gan']}{pillars['hour']['zhi']}]"
        )

        day_stem    = pillars['day']['gan']
        day_element = pillars['day']['gan_element'].capitalize()

        prompt = f"""
You are the master analyst behind HON. Soul Signature — the world's most coveted Korean Four Pillars (Saju) wellness brand. Your words carry the weight of centuries of Korean shamanic tradition, yet feel as fresh and resonant as the finest self-help literature published today. HON. Soul Signature clients are global, discerning, and soulful: think Gwyneth Paltrow meets Carl Jung, filtered through the lens of Seoul's most exclusive wellness sanctuary. Every word you write must feel worthy of the HON. Soul Signature name.

## Verified Saju Data (Calculated by Precision Python Engine — Do Not Alter)
- **Name**: {name} | **Gender**: {gender} | **{birth_context}**
- **Day Master (Core Self)**: {day_stem} — {day_element} Element
- **Four Pillars**: {pillars_summary}
- **Ten Gods Composition**: {ten_stars_str}
- **Five Element Balance**: {ohaeng_str}
- **Current Major Cycle (Daewoon)**: {current_daewun}

## Your Mission
Using ONLY the verified data above, craft a deeply personal, luxuriously written soul report in English. Each section must read like an excerpt from a $500 personalized wellness book — not a fortune cookie. Use rich metaphor, psychological depth, and poetic precision. Never say "your saju says" — speak directly to the soul.

## Output Format
Respond ONLY in valid JSON. All values must be strings. No markdown inside JSON values.

{{
  "total_summary": "A sweeping, cinematic life overview — 10 to 14 sentences. Open with a powerful metaphor about the {day_element} element. Weave in the elemental balance, the Ten Gods pattern, and the arc of this person's destiny. End with an aspirational vision of their highest potential.",

  "gmhs": {{
    "year": "Early Life (Birth–19): 5 to 7 sentences. Describe the energetic blueprint of childhood — parental influences, innate gifts, early wounds, and the seeds of character that were planted.",
    "month": "Young Adulthood (20–39): 5 to 7 sentences. The season of ambition, identity formation, and social discovery. What calling emerges? What tensions must be navigated?",
    "day": "Midlife (40–59): 5 to 7 sentences. The harvest years. Power, mastery, and the deepening of relationships. What legacy is being built?",
    "hour": "Later Life (60+): 5 to 7 sentences. The elder sage. Wisdom crystallized. The gifts they offer the world simply by existing."
  }},

  "daewoon_trend": "8 to 10 sentences on the current major cycle — its elemental flavor, the opportunities it opens, the shadow it casts, and how to ride its energy with grace.",

  "health_analysis": "6 to 8 sentences. Rooted in the Five Element balance, describe constitutional strengths and vulnerabilities with the elegance of a functional medicine practitioner. Suggest lifestyle, nutrition, and mindfulness practices that harmonize the element pattern.",

  "social_analysis": "6 to 8 sentences. Illuminate this person's relational style, leadership archetype, and ideal professional ecosystem. Name 3 specific career domains where they would thrive and briefly explain why.",

  "personality_deep": "8 to 10 sentences. A soul portrait. Go beneath the surface — the paradoxes, the hidden gifts, the emotional intelligence, the shadow tendencies. Make the reader feel seen in a way they rarely experience.",

  "love_romance": "6 to 8 sentences. Describe the love archetype, attachment style, and what this person truly needs in a partnership to flourish. Frame challenges as invitations to growth.",

  "wealth_strategy": "6 to 8 sentences. Translate the elemental and Ten God data into a concrete wealth philosophy — how they naturally generate value, where they leak energy financially, and what strategy aligns with their cosmic design.",

  "today_luck": "3 to 4 sentences. A luminous, poetic daily intention — not a prediction, but an energetic invitation for how to move through today with alignment and grace."
}}
"""

        try:
            message = self.client.messages.create(
                model="claude-opus-4-5",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            raw = message.content[0].text.strip()

            # JSON 추출
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            return json.loads(raw)

        except Exception as e:
            print(f"[AIAnalysis] Error: {e}")
            return None
