/**
 * Export utility  (T9)  — TypeScript version of the former export.js
 *
 * Triggers browser-native CSV or JSON Blob downloads for query results.
 * Compatible with any browser that supports URL.createObjectURL.
 */

import type { ExportFormat } from '../types/api'

/**
 * Download query results as a CSV or JSON file.
 *
 * @param rows     - Array of result row objects
 * @param columns  - Column order override (uses Object.keys(rows[0]) if omitted)
 * @param format   - 'csv' | 'json'
 * @param filename - Download filename without extension (default: 'o2c_export')
 */
export function exportResults(
  rows: Record<string, unknown>[],
  columns: string[] | undefined,
  format: ExportFormat,
  filename = 'o2c_export',
): void {
  if (!rows || rows.length === 0) return

  const cols = columns ?? Object.keys(rows[0])

  let blob: Blob
  let ext: string

  if (format === 'csv') {
    const header = cols.join(',')
    const body = rows
      .map(row =>
        cols
          .map(c => {
            const v = row[c]
            const s = v == null ? '' : String(v)
            // Quote cells that contain commas, double-quotes, or newlines
            return s.includes(',') || s.includes('"') || s.includes('\n')
              ? `"${s.replace(/"/g, '""')}"`
              : s
          })
          .join(','),
      )
      .join('\n')
    blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8;' })
    ext = 'csv'
  } else {
    blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' })
    ext = 'json'
  }

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}.${ext}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
