export async function onRequestPost(context) {
  try {
    const { request, env } = context;

    // ① セキュリティ防壁: 自サイト以外からのリクエストを遮断
    const referer = request.headers.get('referer') || '';
    const origin = request.headers.get('origin') || '';
    const isAllowedOrigin = 
      referer.includes('gikai-mikata.jp') || 
      origin.includes('gikai-mikata.jp') || 
      referer.includes('localhost') || 
      origin.includes('localhost') ||
      referer.includes('pages.dev'); // Cloudflareプレビュー環境用

    if (!isAllowedOrigin) {
      return new Response(JSON.stringify({ error: 'アクセスが拒否されました (Unauthorized origin)' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { query, contexts } = await request.json();
    const cleanQuery = (query || '').trim();

    // ② クエリ検証: 短すぎる、または長すぎる悪意ある入力を遮断
    if (cleanQuery.length < 2 || cleanQuery.length > 80) {
      return new Response(JSON.stringify({ error: '質問は2文字以上80文字以内で入力してください' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const apiKey = env.GEMINI_API_KEY;
    if (!apiKey) {
      return new Response(JSON.stringify({ error: 'GEMINI_API_KEY が設定されていません' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // ③ エッジキャッシュの確認（同一質問のスパイクを完全無力化）
    const cache = caches.default;
    const cacheKey = new Request(
      `https://gikai-mikata.jp/api/ask?q=${encodeURIComponent(cleanQuery.toLowerCase())}`,
      request
    );
    const cachedResponse = await cache.match(cacheKey);
    if (cachedResponse) {
      return cachedResponse;
    }

    // 質疑ログのコンテキスト整形（最大3件、各250文字に制限してトークン節約）
    const contextText = (contexts || []).slice(0, 3).map((c, i) => {
      return `【質疑ログ${i + 1}】
日付: ${c.meeting_date || ''}
会議名: ${c.meeting_title || ''}
発言者: ${c.speaker || ''}
要旨: ${c.summary || ''}
発言抜粋: ${(c.statement_text || '').slice(0, 250)}`;
    }).join('\n\n');

    const systemInstruction = `あなたは京都市議会の公式会議録を客観的に解説する中立な政策アナリストです。
提供された【質疑ログ】の情報のみを根拠として、利用者の質問に簡潔に回答してください。

【厳格なルール】
1. 回答は140〜180文字程度で、結論から述べること。
2. 提供された質疑ログに書かれていない事実は推測で補足せず、「提供された議事録の範囲内では具体的な方針は確認できません」と正直に答えること。
3. 特定の議員や会派に肩入れせず、中立なトーンを維持すること。`;

    const prompt = `【利用者の質問・検索ワード】:
${cleanQuery}

【参考にする京都市議会の質疑ログ】:
${contextText}

上記質疑ログを根拠に、利用者の疑問に対する回答を作成してください。`;

    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;

    const res = await fetch(geminiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: systemInstruction }] },
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.1,
          maxOutputTokens: 250 // トークン上限を絞ってコスト保護
        }
      })
    });

    if (!res.ok) {
      const errText = await res.text();
      return new Response(JSON.stringify({ error: `API エラー: ${errText}` }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const data = await res.json();
    const answer = data.candidates?.[0]?.content?.parts?.[0]?.text || '該当する議事録から明確な回答を生成できませんでした。';

    const responseBody = JSON.stringify({ answer });
    const response = new Response(responseBody, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        // ④ 同一クエリを Cloudflare エッジに24時間キャッシュ
        'Cache-Control': 'public, max-age=86400, s-maxage=86400'
      }
    });

    // キャッシュ保存（バックグラウンド非同期）
    context.waitUntil(cache.put(cacheKey, response.clone()));

    return response;

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}