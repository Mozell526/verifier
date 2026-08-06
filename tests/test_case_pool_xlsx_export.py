import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_HTML = ROOT / "impl" / "frontend" / "summary.html"
EXPORTER_JS = ROOT / "impl" / "frontend" / "case_pool_export.js"
EXCELJS_JS = ROOT / "impl" / "frontend" / "vendor" / "exceljs.min.js"


def _summary_source() -> str:
    return SUMMARY_HTML.read_text(encoding="utf-8")


def _function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\nfunction ", start + 1)
    return source[start:] if end == -1 else source[start:end]


def test_summary_places_xlsx_export_next_to_filters_and_keeps_json_action():
    source = _summary_source()

    scenario_filter = source.index('id="scenarioFilter"')
    status_filter = source.index('id="caseFilter"')
    export_button = source.index('id="exportCasePoolButton"')
    assert scenario_filter < status_filter < export_button
    assert "导出当前筛选 (.xlsx)" in source
    assert "生成已选 JSON" in source
    assert "已生成已选择用例 JSON" in source

    exceljs_script = source.index('src="vendor/exceljs.min.js"')
    exporter_script = source.index('src="case_pool_export.js"')
    page_script = source.index("<script>\nconst PAGE_VERSION")
    assert exceljs_script < exporter_script < page_script


def test_render_and_export_share_complete_filtered_case_views_before_page_slice():
    source = _summary_source()
    filterer = _function(source, "currentFilteredCaseViews")
    renderer = _function(source, "renderCasePool")

    assert "casePool.map((item,poolIndex)=>({item,view:caseView(item),poolIndex}))" in filterer
    assert "fulfillmentStatus(entry.view)" in filterer
    assert "inferCaseScenario(entry.view)===scenarioFilter" in filterer
    assert "const visible=currentFilteredCaseViews();" in renderer
    assert "const page=visible.slice((casePage-1)*CASE_PAGE_SIZE,casePage*CASE_PAGE_SIZE);" in renderer
    assert "当前筛选命中 '+visible.length+' 条" in renderer


def test_export_mapping_has_exact_business_columns_without_trace():
    source = _summary_source()
    mapper = _function(source, "buildCasePoolExportRows")
    exporter = _function(source, "exportCurrentCasePoolXlsx")

    expected_keys = [
        "id",
        "source",
        "executionMode",
        "scenario",
        "input",
        "output",
        "reference",
        "status",
        "judgeSummary",
        "judgeJson",
        "attributionSummary",
        "attributeJson",
    ]
    for key in expected_keys:
        assert f"{key}:" in mapper
    assert "trace:" not in mapper
    assert "currentFilteredCaseViews()" in exporter
    assert "buildCasePoolExportRows(entries)" in exporter
    assert "当前筛选没有可导出用例" in exporter
    assert "button.disabled=true" in exporter
    assert "finally{button.disabled=false" in exporter


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required to exercise the vendored browser workbook")
def test_exporter_generates_readable_xlsx_with_styles_and_safe_long_cells():
    script = f"""
const ExcelJS = require({json.dumps(str(EXCELJS_JS))});
globalThis.ExcelJS = ExcelJS;
require({json.dumps(str(EXPORTER_JS))});
const exporter = globalThis.CasePoolExporter;
(async () => {{
  const longText = 'x'.repeat(40000);
  const workbook = exporter.createWorkbook([
    {{
      id: 'case-1', source: 'manual', executionMode: 'live / api', scenario: 'demo',
      input: {{query: 'alpha'}}, output: {{answer: 'beta'}}, reference: {{answer: 'gold'}},
      status: 'fulfilled', judgeSummary: 'ok', judgeJson: {{score: 1}},
      attributionSummary: 'none', attributeJson: {{findings: []}}
    }},
    {{id: 'case-2', input: longText}}
  ]);
  const buffer = await workbook.xlsx.writeBuffer();
  const loaded = new ExcelJS.Workbook();
  await loaded.xlsx.load(buffer);
  const sheet = loaded.getWorksheet('用例池候选区');
  const result = {{
    headers: sheet.getRow(1).values.slice(1),
    rowCount: sheet.rowCount,
    firstInput: sheet.getCell('E2').value,
    truncatedLength: sheet.getCell('E3').value.length,
    truncatedMarker: sheet.getCell('E3').value.endsWith(exporter.TRUNCATION_MARKER),
    frozen: sheet.views.some(view => view.state === 'frozen' && view.ySplit === 1),
    autoFilter: sheet.autoFilter,
    filename: exporter.fileName('client/search', new Date(2026, 6, 22, 15, 30, 45))
  }};
  process.stdout.write(JSON.stringify(result));
}})().catch(error => {{ console.error(error); process.exit(1); }});
"""
    result = subprocess.run(
        [shutil.which("node"), "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    workbook = json.loads(result.stdout)

    assert workbook["headers"] == [
        "ID",
        "来源",
        "执行模式",
        "Scenario",
        "Input / Live Request",
        "Output / 被评估输出",
        "Reference",
        "状态",
        "Judge 摘要",
        "Judge JSON",
        "归因摘要",
        "Attribute JSON",
    ]
    assert workbook["rowCount"] == 3
    assert workbook["firstInput"] == '{\n  "query": "alpha"\n}'
    assert workbook["truncatedLength"] == 32767
    assert workbook["truncatedMarker"] is True
    assert workbook["frozen"] is True
    assert workbook["autoFilter"] == "A1:L1"
    assert workbook["filename"] == "verifier-client-search-cases-20260722-153045.xlsx"
