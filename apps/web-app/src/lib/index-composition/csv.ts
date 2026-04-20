import type { IndexRow } from './types';

function escapeCsvField(value: string): string {
  if (!/[,"\r\n]/.test(value)) return value;
  return `"${value.replace(/"/g, '""')}"`;
}

function formatCell(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return '';
  return typeof value === 'number' ? value.toString() : value;
}

/**
 * Serialize index-composition rows to an RFC 4180 compliant CSV string.
 * Columns: Rank, Code, Name, Rebal Date, AUM($M), {peer1}, {peer2}, ...
 * Null/undefined values serialize as empty fields.
 */
export function rowsToCsv(rows: IndexRow[], peers: string[]): string {
  const header = ['Rank', 'Code', 'Name', 'Rebal Date', 'AUM($M)', ...peers];
  const lines: string[] = [header.map(escapeCsvField).join(',')];
  for (const row of rows) {
    const cells = [
      formatCell(row.rank),
      row.indexCode,
      row.indexName,
      row.nextRebalancingDate ?? '',
      formatCell(row.indexedAumMillionUsd),
      ...peers.map(p => formatCell(row.weights[p])),
    ];
    lines.push(cells.map(escapeCsvField).join(','));
  }
  return lines.join('\r\n');
}
