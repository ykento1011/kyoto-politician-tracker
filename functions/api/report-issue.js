export async function onRequest(context) {
  const { request, env } = context;

  // CORS プリフライト対応
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      }
    });
  }

  // POST 以外のメソッドを弾く
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method Not Allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const webhookUrl = env.DISCORD_WEBHOOK_URL_REPORT;

    if (!webhookUrl) {
      console.error("DISCORD_WEBHOOK_URL_REPORT is missing in Cloudflare environment variables.");
      return new Response(JSON.stringify({ error: "Webhook configuration missing" }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }

    const data = await request.json();
    const { category, context: reportContext, message } = data;

    const categoryLabels = {
      "link_broken": "🔗 リンク切れ（404・開かない）",
      "wrong_file": "📄 リンク先の資料・発言が違う",
      "broken_pdf": "⚠️ PDFが壊れている・読めない",
      "other": "📝 その他・補足修正"
    };
    const categoryLabel = categoryLabels[category] || category;

    const discordPayload = {
      username: "一次資料 修正報告Bot",
      avatar_url: "https://gikai-mikata.jp/favicon-96x96.png",
      embeds: [
        {
          title: "🚨 一次資料の不備報告を受信しました",
          description: message ? `**ユーザーメモ:**\n> ${message}` : "*（ユーザーメモなし）*",
          color: 0xe74c3c,
          fields: [
            { name: "報告内容", value: categoryLabel, inline: false },
            { name: "対象URL", value: reportContext?.targetUrl || "不明", inline: false },
            { name: "自治体", value: reportContext?.municipality || "不明", inline: true },
            { name: "対象者/会議", value: `${reportContext?.speaker || "不明"} / ${reportContext?.meetingDate || "不明"}`, inline: true },
            { name: "発言/議案ID", value: `\`${reportContext?.targetId || "不明"}\``, inline: true }
          ],
          footer: { text: "Cloudflare Pages Functions" },
          timestamp: new Date().toISOString()
        }
      ]
    };

    const discordResponse = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(discordPayload)
    });

    if (!discordResponse.ok) {
      throw new Error(`Discord API returned status ${discordResponse.status}`);
    }

    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });

  } catch (error) {
    console.error("Report API Error:", error);
    return new Response(JSON.stringify({ error: error.message || "Internal Server Error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}
