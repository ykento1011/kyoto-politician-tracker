from pathlib import Path
import re

hook_file = Path("frontend/src/hooks/useStatements.js")
text = hook_file.read_text(encoding="utf-8")

# 1. 大阪マスターの import 追加
if "getOsakaCouncilorMasterInfo" not in text:
    text = text.replace(
        "import { getCouncilorMasterInfo } from '../utils/councilorMaster';",
        "import { getCouncilorMasterInfo } from '../utils/councilorMaster';\nimport { getOsakaCouncilorMasterInfo } from '../utils/osakaCouncilorMaster';"
    )

# 2. 引数に cityCode を受けるようシグネチャを修正
text = re.sub(
    r'export function useStatements\([^)]*\)',
    "export function useStatements(cityCode = 'kyoto')",
    text
)

# 3. useEffect の依存配列に cityCode を追加
text = re.sub(
    r'useEffect\(\(\) => \{\s*fetchStatements\(\);\s*\}, \[[^\]]*\]\);',
    "useEffect(() => {\n    fetchStatements();\n  }, [cityCode]);",
    text
)

# 4. fetchStatements 内のデータ読み込みパスを動的化
old_fetch = "const res = await fetch('/data/statements_summary.json');"
if old_fetch in text:
    new_fetch = """const prefix = cityCode === 'kyoto' ? '' : `${cityCode}_`;
        const res = await fetch(`/data/${prefix}statements_summary.json`);"""
    text = text.replace(old_fetch, new_fetch)

# 5. 京都以外では VALID_COUNCILORS 照合をスキップ
text = re.sub(
    r'if \((?:cityCode === [\'"]kyoto[\'"] && )?VALID_COUNCILORS && Array\.isArray\(VALID_COUNCILORS\)\)',
    "if (cityCode === 'kyoto' && VALID_COUNCILORS && Array.isArray(VALID_COUNCILORS))",
    text
)

# 6. speakerStats 内で大阪マスター (getOsakaCouncilorMasterInfo) を参照
text = re.sub(
    r'const masterInfo = [^;]*getCouncilorMasterInfo\(spk\)[^;]*;',
    "const masterInfo = cityCode === 'kyoto' ? (getCouncilorMasterInfo ? getCouncilorMasterInfo(spk) : {}) : (getOsakaCouncilorMasterInfo ? getOsakaCouncilorMasterInfo(spk) : {});",
    text
)

# 7. filteredThreads 内で大阪マスターを参照
text = re.sub(
    r'const info = [^;]*getCouncilorMasterInfo\(s\.speaker\)[^;]*;',
    "const info = cityCode === 'kyoto' ? (getCouncilorMasterInfo ? getCouncilorMasterInfo(s.speaker) : {}) : (getOsakaCouncilorMasterInfo ? getOsakaCouncilorMasterInfo(s.speaker) : {});",
    text
)

# 8. handleViewContext 内のタイムライン取得パスを動的化
old_tl = "const res = await fetch(`/data/timelines/${meetingId}.json`);"
if old_tl in text:
    new_tl = """const prefix = cityCode === 'kyoto' ? '' : `${cityCode}_`;
            const res = await fetch(`/data/${prefix}timelines/${meetingId}.json`);"""
    text = text.replace(old_tl, new_tl)

# 9. useMemo の依存配列に cityCode を追加
text = re.sub(
    r'\}\, \[statements\]\);',
    "}, [statements, cityCode]);",
    text
)
text = re.sub(
    r'\}\, \[statements, submittedQuery, selectedCategory, selectedCommittee, selectedDistrict, sortPerspective, miniSearch\]\);',
    "}, [statements, submittedQuery, selectedCategory, selectedCommittee, selectedDistrict, sortPerspective, miniSearch, cityCode]);",
    text
)

hook_file.write_text(text, encoding="utf-8")
print("✅ useStatements.js のマルチテナント更新が正常に完了しました。")
