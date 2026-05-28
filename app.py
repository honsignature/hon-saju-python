/**
 * HON. Soul Signature — 사주 자동화 Webhook v7
 * Shopify → Netlify → Railway(정확한 사주 계산) → Claude(영문 해석) → Resend(이메일)
 */

const crypto = require("crypto");

const ANTHROPIC_API_KEY      = process.env.ANTHROPIC_API_KEY;
const SHOPIFY_WEBHOOK_SECRET = process.env.SHOPIFY_WEBHOOK_SECRET;
const SHOPIFY_ADMIN_TOKEN    = process.env.SHOPIFY_ADMIN_TOKEN;
const SHOPIFY_SHOP_DOMAIN    = process.env.SHOPIFY_SHOP_DOMAIN;
const FROM_EMAIL             = process.env.SHOPIFY_FROM_EMAIL;
const RESEND_API_KEY         = process.env.RESEND_API_KEY;
const RAILWAY_URL            = "https://web-production-ce5982.up.railway.app";

function verifyWebhook(body, hmacHeader) {
  if (!SHOPIFY_WEBHOOK_SECRET) return true;
  try {
    const digest = crypto.createHmac("sha256", SHOPIFY_WEBHOOK_SECRET).update(body, "utf8").digest("base64");
    return digest === hmacHeader;
  } catch (e) {
    return true;
  }
}

function extractSajuInfo(order) {
  const noteAttrs = order.note_attributes || [];
  const get = (key) => {
    const attr = noteAttrs.find((a) => a.name === key || a.name.toLowerCase().includes(key.toLowerCase()));
    return attr ? attr.value : null;
  };
  return {
    customerName: order.billing_address?.first_name || order.customer?.first_name || "Guest",
    email:        order.email || order.customer?.email,
    birthDate:    get("Your_Date_of_Birth"),
    birthTime:    get("Your_Birth_Hour"),
    gender:       get("Your_Gender"),
    calendar:     get("Your_Calendar") || "solar",
    orderNumber:  order.order_number || order.name,
    orderId:      order.id,
  };
}

async function isAlreadyProcessed(orderId) {
  try {
    const res = await fetch(
      `https://${SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/orders/${orderId}.json?fields=tags`,
      { headers: { "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN } }
    );
    if (!res.ok) return false;
    const data = await res.json();
    return (data.order?.tags || "").includes("saju-sent");
  } catch (e) {
    return false;
  }
}

async function markAsProcessed(orderId) {
  try {
    const res = await fetch(
      `https://${SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/orders/${orderId}.json?fields=tags`,
      { headers: { "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN } }
    );
    const data = await res.json();
    const currentTags = data.order?.tags || "";
    const newTags = currentTags ? `${currentTags}, saju-sent` : "saju-sent";
    await fetch(`https://${SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/orders/${orderId}.json`, {
      method: "PUT",
      headers: {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ order: { id: orderId, tags: newTags } }),
    });
  } catch (e) {
    console.error("Tag error:", e.message);
  }
}

// Railway Python 앱에서 정확한 사주 계산
async function calculateSaju(info) {
  // 시간 파싱 (예: "Sasi / 사시 (09:00-11:00)" → "10:00")
  let birthTime = "12:00";
  if (info.birthTime) {
    const timeMatch = info.birthTime.match(/(\d{2}):(\d{2})/);
    if (timeMatch) {
      birthTime = `${timeMatch[1]}:${timeMatch[2]}`;
    }
  }

  const res = await fetch(`${RAILWAY_URL}/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name:       info.customerName,
      birth_date: info.birthDate,
      birth_time: birthTime,
      gender:     info.gender || "female",
      calendar:   info.calendar || "solar",
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Railway 계산 오류: ${res.status} ${err}`);
  }

  const data = await res.json();
  if (!data.success) {
    throw new Error(`사주 계산 실패: ${data.error}`);
  }
  return data;
}

// Claude로 영문 해석 생성
async function generateInterpretation(info, sajuData) {
  const pillars = sajuData.pillars || {};
  const ohaeng  = sajuData.ohaeng || {};
  const isLunar = info.calendar && info.calendar.toLowerCase().includes("lunar");

  const prompt = `You are a grandmaster of Korean Saju (Four Pillars of Destiny). Create a premium Soul Reading Report for HON. Soul Signature luxury brand.

Client: ${info.customerName}
Date of Birth: ${info.birthDate} (${isLunar ? "Lunar Calendar" : "Solar Calendar"})
Hour of Birth: ${info.birthTime || "Not provided"}
Gender: ${info.gender || "Not provided"}

CALCULATED FOUR PILLARS (100% accurate):
- Year Pillar: ${pillars.year?.gan || ""}${pillars.year?.zhi || ""} 
- Month Pillar: ${pillars.month?.gan || ""}${pillars.month?.zhi || ""}
- Day Pillar: ${pillars.day?.gan || ""}${pillars.day?.zhi || ""}
- Hour Pillar: ${pillars.hour?.gan || ""}${pillars.hour?.zhi || ""}

ELEMENTAL DISTRIBUTION:
${Object.entries(ohaeng).map(([k,v]) => `- ${k}: ${v}`).join('\n')}

Ten Stars: ${sajuData.ten_stars || ""}
Current Major Cycle: ${sajuData.current_daewun || ""}
${sajuData.ohaeng_analysis ? `Elemental Analysis: ${sajuData.ohaeng_analysis}` : ""}

Write a premium Soul Signature Report in English based on these EXACT calculated pillars. Be specific, poetic, and deeply insightful. Do NOT use markdown symbols (**, ##, *, #). Use SECTION TITLES IN ALL CAPS followed by a colon.

Include these sections with 4-5 rich sentences each:

SOUL ESSENCE:
THE FOUR PILLARS:
INNATE CHARACTER AND GIFTS:
LIFE PATH AND DESTINY:
WEALTH AND CAREER:
LOVE AND RELATIONSHIPS:
HEALTH AND VITALITY:
2026 COSMIC FORECAST:
SOUL GUIDANCE:

Write 1500-2000 words. Reference the specific pillars and elements calculated above.`;

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type":      "application/json",
      "x-api-key":         ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model:      "claude-sonnet-4-5",
      max_tokens: 4000,
      messages:   [{ role: "user", content: prompt }],
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Claude API error: ${res.status} ${err}`);
  }
  const data = await res.json();
  return data.content[0].text;
}

function formatSajuText(text) {
  const lines = text.split('\n');
  let html = '';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const titleMatch = line.match(/^([A-Z][A-Z\s&0-9]+):(.*)$/);
    if (titleMatch && titleMatch[1].trim().length > 3) {
      const title = titleMatch[1].trim();
      const rest = titleMatch[2].trim();
      html += `<div style="margin:32px 0 12px;">
        <p style="margin:0 0 2px;color:#c9a96e;font-size:10px;letter-spacing:3px;font-family:Arial,sans-serif;text-transform:uppercase;">${title}</p>
        <div style="width:24px;height:1px;background:#c9a96e;margin:6px 0 12px;"></div>
        ${rest ? `<p style="margin:0;color:#2c2c2c;font-size:15px;line-height:1.9;font-family:Georgia,serif;">${rest}</p>` : ''}
      </div>`;
    } else {
      html += `<p style="margin:0 0 14px;color:#2c2c2c;font-size:15px;line-height:1.9;font-family:Georgia,serif;">${line}</p>`;
    }
  }
  return html;
}

async function sendEmailViaResend(info, sajuText, sajuData) {
  const formattedContent = formatSajuText(sajuText);
  const calendarLabel = info.calendar && info.calendar.toLowerCase().includes("lunar") ? "Lunar Calendar" : "Solar Calendar";
  const pillars = sajuData.pillars || {};

  const pillarsTable = `
  <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;margin:16px 0;">
    <tr style="background:#0a0a0a;">
      <td style="padding:10px 16px;color:#c9a96e;font-size:10px;letter-spacing:2px;font-family:Arial,sans-serif;text-align:center;">YEAR</td>
      <td style="padding:10px 16px;color:#c9a96e;font-size:10px;letter-spacing:2px;font-family:Arial,sans-serif;text-align:center;">MONTH</td>
      <td style="padding:10px 16px;color:#c9a96e;font-size:10px;letter-spacing:2px;font-family:Arial,sans-serif;text-align:center;">DAY</td>
      <td style="padding:10px 16px;color:#c9a96e;font-size:10px;letter-spacing:2px;font-family:Arial,sans-serif;text-align:center;">HOUR</td>
    </tr>
    <tr style="background:#f5f0e8;">
      <td style="padding:14px 16px;color:#0a0a0a;font-size:22px;font-family:Georgia,serif;text-align:center;">${pillars.year?.gan || ""}${pillars.year?.zhi || ""}</td>
      <td style="padding:14px 16px;color:#0a0a0a;font-size:22px;font-family:Georgia,serif;text-align:center;">${pillars.month?.gan || ""}${pillars.month?.zhi || ""}</td>
      <td style="padding:14px 16px;color:#0a0a0a;font-size:22px;font-family:Georgia,serif;text-align:center;">${pillars.day?.gan || ""}${pillars.day?.zhi || ""}</td>
      <td style="padding:14px 16px;color:#0a0a0a;font-size:22px;font-family:Georgia,serif;text-align:center;">${pillars.hour?.gan || ""}${pillars.hour?.zhi || ""}</td>
    </tr>
  </table>`;

  const htmlBody = `<!DOCTYPE html>
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
    <h2 style="margin:0 0 20px;color:#0a0a0a;font-size:26px;font-weight:400;font-family:Georgia,serif;letter-spacing:1px;">${info.customerName}</h2>
    <table cellpadding="0" cellspacing="0">
      <tr><td style="padding:4px 16px 4px 0;color:#999;font-size:11px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;">Date of Birth</td><td style="color:#333;font-size:13px;font-family:Georgia,serif;">${info.birthDate} <span style="color:#c9a96e;font-size:11px;">(${calendarLabel})</span></td></tr>
      <tr><td style="padding:4px 16px 4px 0;color:#999;font-size:11px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;">Hour of Birth</td><td style="color:#333;font-size:13px;font-family:Georgia,serif;">${info.birthTime || "Not provided"}</td></tr>
      <tr><td style="padding:4px 16px 4px 0;color:#999;font-size:11px;font-family:Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;">Order</td><td style="color:#333;font-size:13px;font-family:Georgia,serif;">#${info.orderNumber}</td></tr>
    </table>
  </td></tr>

  <tr><td style="padding:0 60px 32px;"><div style="border-top:1px solid #e8e4dc;"></div></td></tr>

  <tr><td style="padding:0 60px 32px;">
    <p style="margin:0 0 12px;color:#c9a96e;font-size:10px;letter-spacing:3px;font-family:Arial,sans-serif;text-transform:uppercase;">Your Four Pillars</p>
    ${pillarsTable}
  </td></tr>

  <tr><td style="padding:0 60px 32px;"><div style="border-top:1px solid #e8e4dc;"></div></td></tr>

  <tr><td style="padding:0 60px 32px;">
    <p style="margin:0;color:#666;font-size:14px;line-height:1.9;font-family:Georgia,serif;font-style:italic;border-left:2px solid #c9a96e;padding-left:20px;">
      The ancient Korean art of Saju — the Four Pillars of Destiny — holds within it the cosmic blueprint of your soul. What follows is a deeply personal reading, drawn from the exact moment of your birth and the elemental forces that shaped your arrival into this world.
    </p>
  </td></tr>

  <tr><td style="padding:0 60px 32px;"><div style="border-top:1px solid #e8e4dc;"></div></td></tr>

  <tr><td style="padding:0 60px 48px;">${formattedContent}</td></tr>

  <tr><td style="background:#0a0a0a;padding:44px 60px;text-align:center;">
    <div style="width:30px;height:1px;background:#c9a96e;margin:0 auto 20px;"></div>
    <p style="margin:0 0 6px;color:#c9a96e;font-size:9px;letter-spacing:5px;font-family:Arial,sans-serif;">H · O · N · S O U L · S I G N A T U R E</p>
    <p style="margin:0 0 16px;color:#444;font-size:11px;font-family:Arial,sans-serif;">K-Heritage of Soul · Crafted by Time · Sealed in Korea</p>
    <p style="margin:0 0 4px;color:#444;font-size:11px;font-family:Arial,sans-serif;">Questions? <a href="mailto:${FROM_EMAIL}" style="color:#c9a96e;text-decoration:none;">${FROM_EMAIL}</a></p>
    <p style="margin:0;color:#333;font-size:10px;font-family:Arial,sans-serif;">This report is for personal use only.</p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>`;

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RESEND_API_KEY}`,
      "Content-Type":  "application/json",
    },
    body: JSON.stringify({
      from:    `HON. Soul Signature <${FROM_EMAIL}>`,
      to:      [info.email],
      subject: `✦ ${info.customerName}, Your Soul Signature Report is Ready — HON.`,
      html:    htmlBody,
    }),
  });

  const result = await res.json();
  if (!res.ok) {
    throw new Error(`Email failed: ${JSON.stringify(result)}`);
  }
  console.log("Email sent:", info.email, result.id);
  return result;
}

exports.handler = async (event) => {
  console.log("Webhook received! Method:", event.httpMethod);

  if (event.httpMethod === "GET") {
    return { statusCode: 200, body: JSON.stringify({ status: "ok" }) };
  }

  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  try {
    verifyWebhook(event.body, event.headers["x-shopify-hmac-sha256"]);

    const order = JSON.parse(event.body);
    console.log("Order received:", order.order_number);

    const info = extractSajuInfo(order);
    console.log("Info:", JSON.stringify({ email: info.email, birthDate: info.birthDate, calendar: info.calendar }));

    if (!info.email || !info.birthDate) {
      console.log("Missing info — skipping");
      return { statusCode: 200, body: "Skipped - missing info" };
    }

    // 중복 방지
    const done = await isAlreadyProcessed(info.orderId);
    if (done) {
      console.log("Already processed:", info.orderNumber);
      return { statusCode: 200, body: "Already processed" };
    }

    // 즉시 태그 달기
    await markAsProcessed(info.orderId);

    // Railway에서 정확한 사주 계산
    console.log("Calculating saju via Railway...");
    const sajuData = await calculateSaju(info);
    console.log("Saju calculated:", sajuData.ten_stars);

    // Claude로 영문 해석
    console.log("Generating interpretation...");
    const sajuText = await generateInterpretation(info, sajuData);
    console.log("Interpretation generated, length:", sajuText.length);

    // 이메일 발송
    await sendEmailViaResend(info, sajuText, sajuData);
    console.log("Done:", info.orderNumber);

    return { statusCode: 200, body: JSON.stringify({ success: true }) };

  } catch (err) {
    console.error("Error:", err.message);
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
};
