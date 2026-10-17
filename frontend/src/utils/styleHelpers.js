export const VALID_COUNCILORS = [
  "青野仁志", "赤阪仁", "天方ひろゆき", "井﨑敦子", "井崎敦子", "井上よしひろ", "宇佐美賢一",
  "江村理紗", "えもとかよこ", "大津裕太", "おんづか功", "片桐直哉", "加藤あい",
  "加藤昌洋", "神谷修平", "河合ようこ", "かわしま優子", "河村諒", "きくち一秀",
  "北尾ゆか", "北川みき", "北山ただお", "久保田正紀", "くまざわ真昭", "くらた共子",
  "こうち大輔", "小島信太郎", "さくらい泰広", "繁隆夫", "しまもと京司", "下村あきら",
  "菅谷浩平", "田中明秀", "田中たかのり", "谷口みゆき", "玉本なるみ", "津田大三",
  "寺田一博", "とがし豊", "富きくお", "中高しゅうじ", "中野洋一", "中村まり",
  "西野さち子", "西村義直", "西山信昌", "橋村芳和", "土方莉紗", "兵藤しんいち",
  "平井良人", "平田圭", "平山たかお", "平山よしかず", "増成竜治", "松田けい子",
  "みちはた弘之", "椋田隆知", "森かれん", "森田守", "森田ゆみ子", "もりもと英靖",
  "山田こうじ", "やまね智史", "山本恵一", "山本しゅうじ", "山本陽子", "湯浅光彦",
  "吉田孝雄"
];

export const cleanName = (name) => (name ? String(name).replace(/[\s ]+/g, '') : '');

export const determineCouncilorStyle = (evidence, solution, localFocus, constructive) => {
  if (solution >= 3.5 && evidence >= 3.5) {
    return {
      label: "政策ビルダー型",
      desc: "具体的対案と客観データで制度設計・改善をリード",
      badgeClass: "bg-blue-50 text-blue-700 border-blue-200"
    };
  }
  if (localFocus >= 3.5 && constructive >= 3.5) {
    return {
      label: "地域フロントライン型",
      desc: "生活現場・特定地域の課題を議場に持ち込み動かす",
      badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200"
    };
  }
  if (constructive >= 3.5 && evidence >= 3.5) {
    return {
      label: "行政チェッカー型",
      desc: "行政答弁の論理破綻や制度不備を的確に追及・是正",
      badgeClass: "bg-rose-50 text-rose-700 border-rose-200"
    };
  }
  if (localFocus >= 3.0) {
    return {
      label: "現場代弁型",
      desc: "地域住民や当事者の切実な声を届ける",
      badgeClass: "bg-amber-50 text-amber-700 border-amber-200"
    };
  }
  return {
    label: "論点提起型",
    desc: "多角的な視点から市政の新たな論点を掘り起こす",
    badgeClass: "bg-purple-50 text-purple-700 border-purple-200"
  };
};

export const cleanAuditorNote = (text) => {
  if (!text) return '';

  let str = '';
  if (typeof text === 'string') {
    str = text;
  } else if (Array.isArray(text)) {
    str = text.map((item) => (typeof item === 'object' ? JSON.stringify(item) : String(item))).join('\n');
  } else if (typeof text === 'object') {
    str = Object.entries(text)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n');
  } else {
    str = String(text);
  }

  return str
    .replace(/\bevidence\s*:\s*/gi, '根拠・データ: ')
    .replace(/\bsolution\s*:\s*/gi, '対案・是正策: ')
    .replace(/\blocal_focus\s*:\s*/gi, '地域解像度: ')
    .replace(/\bconstructive\s*:\s*/gi, '議論の進展: ')
    .replace(/\bevidence\b/gi, '根拠・データ')
    .replace(/\bsolution\b/gi, '対案・是正策')
    .replace(/\blocal_focus\b/gi, '地域解像度')
    .replace(/\bconstructive\b/gi, '議論の進展');
};

export const TRENDING_TAGS = [
  "オーバーツーリズム", "中小企業支援", "伝統産業", "市バス",
  "空き家対策", "学童保育", "PFI", "敬老乗車証"
];