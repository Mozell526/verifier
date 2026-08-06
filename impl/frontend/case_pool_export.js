(function (global) {
  'use strict';

  const MAX_EXCEL_CELL_LENGTH = 32767;
  const TRUNCATION_MARKER = '[已因 Excel 单元格 32767 字符上限截断]';
  const MIME_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  const SHEET_NAME = '用例池候选区';
  const COLUMNS = [
    {header: 'ID', key: 'id', width: 24},
    {header: '来源', key: 'source', width: 20},
    {header: '执行模式', key: 'executionMode', width: 22},
    {header: 'Scenario', key: 'scenario', width: 24},
    {header: 'Input / Live Request', key: 'input', width: 48},
    {header: 'Output / 被评估输出', key: 'output', width: 48},
    {header: 'Reference', key: 'reference', width: 48},
    {header: '状态', key: 'status', width: 22},
    {header: 'Judge 摘要', key: 'judgeSummary', width: 42},
    {header: 'Judge JSON', key: 'judgeJson', width: 54},
    {header: '归因摘要', key: 'attributionSummary', width: 42},
    {header: 'Attribute JSON', key: 'attributeJson', width: 54},
  ];

  function truncateCell(text) {
    const value = String(text ?? '');
    if (value.length <= MAX_EXCEL_CELL_LENGTH) {
      return value;
    }
    return value.slice(0, MAX_EXCEL_CELL_LENGTH - TRUNCATION_MARKER.length) + TRUNCATION_MARKER;
  }

  function cellText(value) {
    if (value === null || value === undefined || value === '') {
      return '';
    }
    if (typeof value === 'string') {
      return truncateCell(value);
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return truncateCell(String(value));
    }
    return truncateCell(JSON.stringify(value, null, 2));
  }

  function sanitizedProjectId(projectId) {
    const value = String(projectId || 'project')
      .trim()
      .replace(/[^A-Za-z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
    return value || 'project';
  }

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function timestamp(date) {
    const value = date instanceof Date ? date : new Date(date);
    if (Number.isNaN(value.getTime())) {
      throw new Error('导出时间无效');
    }
    return value.getFullYear()
      + pad(value.getMonth() + 1)
      + pad(value.getDate())
      + '-'
      + pad(value.getHours())
      + pad(value.getMinutes())
      + pad(value.getSeconds());
  }

  function fileName(projectId, exportedAt) {
    return 'verifier-' + sanitizedProjectId(projectId) + '-cases-' + timestamp(exportedAt) + '.xlsx';
  }

  function requireExcelJS(override) {
    const library = override || global.ExcelJS;
    if (!library || typeof library.Workbook !== 'function') {
      throw new Error('本地 Excel 导出组件未加载');
    }
    return library;
  }

  function createWorkbook(rows, excelJsOverride) {
    if (!Array.isArray(rows)) {
      throw new Error('导出数据必须是数组');
    }
    const ExcelJS = requireExcelJS(excelJsOverride);
    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'Verifier';
    workbook.created = new Date();

    const worksheet = workbook.addWorksheet(SHEET_NAME, {
      views: [{state: 'frozen', ySplit: 1}],
    });
    worksheet.columns = COLUMNS.map(column => ({...column}));
    worksheet.autoFilter = {from: 'A1', to: 'L1'};

    const header = worksheet.getRow(1);
    header.height = 24;
    header.font = {bold: true, color: {argb: 'FFFFFFFF'}};
    header.fill = {type: 'pattern', pattern: 'solid', fgColor: {argb: 'FF2563EB'}};
    header.alignment = {vertical: 'middle', horizontal: 'left', wrapText: true};

    rows.forEach(item => {
      const rowData = {};
      COLUMNS.forEach(column => {
        rowData[column.key] = cellText(item && item[column.key]);
      });
      const row = worksheet.addRow(rowData);
      row.height = 60;
      row.eachCell({includeEmpty: true}, cell => {
        cell.alignment = {vertical: 'top', horizontal: 'left', wrapText: true};
      });
    });

    return workbook;
  }

  async function download(options) {
    const settings = options || {};
    const rows = settings.rows || [];
    const exportedAt = settings.exportedAt || new Date();
    const workbook = createWorkbook(rows, settings.ExcelJS);
    const buffer = await workbook.xlsx.writeBuffer();
    const BlobType = settings.Blob || global.Blob;
    const URLType = settings.URL || global.URL;
    const documentValue = settings.document || global.document;
    if (!BlobType || !URLType || typeof URLType.createObjectURL !== 'function' || !documentValue) {
      throw new Error('当前浏览器不支持文件下载');
    }

    const name = fileName(settings.projectId, exportedAt);
    const blob = new BlobType([buffer], {type: MIME_TYPE});
    const url = URLType.createObjectURL(blob);
    const anchor = documentValue.createElement('a');
    anchor.href = url;
    anchor.download = name;
    anchor.style.display = 'none';
    documentValue.body.appendChild(anchor);
    try {
      anchor.click();
    } finally {
      anchor.remove();
      global.setTimeout(() => URLType.revokeObjectURL(url), 0);
    }
    return {fileName: name, rowCount: rows.length};
  }

  global.CasePoolExporter = Object.freeze({
    COLUMNS,
    MAX_EXCEL_CELL_LENGTH,
    TRUNCATION_MARKER,
    cellText,
    createWorkbook,
    download,
    fileName,
    truncateCell,
  });
})(typeof globalThis === 'undefined' ? window : globalThis);
