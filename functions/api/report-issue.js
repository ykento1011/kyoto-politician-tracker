/**
 * Cloudflare Pages Functions API: 一次資料不備報告の送信エンドポイント
 * 
 * エンドポイント: POST /api/report-issue
 * リクエストボディ: JSON
 *   - category: 報告カテゴリ (例: "link_broken", "wrong_file")
 *   - context: 自動収集されたメタデータ (自治体, 議員名, 日付, 発言ID, URLなど)
 *   - message: (任意) ユーザーからの補足コメント
 */

export async function onRequestPost(context) {
  const { request, env } = context;

  try {
    // 1. 環境変数から Discord Webhook URL を取得
    // Cloudflare Pages の設定画面で DISCORD_WEBHOOK_URL_REPORT という変数を登録してください
    const webhookUrl = env.DISCORD_WEBHOOK_URL_REPORT;

    if (!webhookUrl) {
      console.error("DISCORD_WEBHOOK_URL_REPORT is not set in environment variables.");
      return new Response(JSON.stringify({ error: "Configuration error" }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }

    // 2. リクエストボディをパース
    const data = await request.json();
    const { category, context: reportContext, message } = data;

    // カテゴリ名の人間の可読化マッピング
    const categoryLabels = {
      "link_broken": "🔗 リンク切れ（404・開かない）",
      "wrong_file": "📄 リンク先の資料・発言が違う",
      "broken_pdf": "⚠️ PDFが壊れている・読めない",
      "other": "📝 その他・補足修正"
    };
    const categoryLabel = categoryLabels[category] || category;

    // 3. Discord 用の Embed ペイロードを組み立て
    const discordPayload = {
      username: "一次資料 修正報告Bot",
      avatar_url: "https://gikai-mikata.jp/favicon-96x96.png",
      embeds: [
        {
          title: "🚨 一次資料の不備報告を受信しました",
          description: message ? `**ユーザーメモ:**\n> ${message}` : "*（ユーザーメモなし）*",
          color: 0xe74c3c, // 赤
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

    // 4. Discord へ POST
    const discordResponse = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(discordPayload)
    });

    if (!discordResponse.ok) {
      throw new Error(`Discord API responded with ${discordResponse.status}`);
    }

    // 5. 成功レスポンスを返す
    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });

  } catch (error) {
    console.error("Error processing report:", error);
    return new Response(JSON.stringify({ error: "Internal Server Error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}
