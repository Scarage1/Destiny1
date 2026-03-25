/**
 * export.js — Download query results as CSV or JSON (T9)
 * Usage: exportResults(results, columns, format)
 */

/**
 * Convert an array of row objects to a CSV string.
 */
function rowsToCsv(rows, columns) {
  if (!rows || rows.length === 0) return ''
  const headers = columns || Object.keys(rows[0])
  const escape = (val) => {
    const str = val == null ? '' : String(val)
    return str.includes(',') || str.includes('"') || str.includes('\n')
      ? `"${str.replace(/"/g, '""')}"`
      : str
  }
  const headerLine = headers.map(escape).join(',')
  const dataLines = rows.map(row => headers.map(h => escape(row[h])).join(','))
  return [headerLine, ...dataLines].join('\n')
}

/**
 * Trigger a file download in the browser.
 */
function triggerDownload(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

/**
 * Export results to the given format.
 * @param {Array}  rows    - Array of result objects
 * @param {Array}  columns - Ordered column names (optional)
 * @param {'csv'|'json'} format
 */
export function exportResults(rows, columns, format = 'csv') {
  if (!rows || rows.length === 0) return

  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
  const base = `o2c-results-${timestamp}`

  if (format === 'json') {
    triggerDownload(
      JSON.stringify(rows, null, 2),
      `${base}.json`,
      'application/json',
    )
  } else {
    triggerDownload(
      rowsToCsv(rows, columns),
      `${base}.csv`,
      'text/csv;charset=utf-8;',
    )
  }
}
