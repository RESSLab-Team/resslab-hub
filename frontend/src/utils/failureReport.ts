/**
 * What to keep when a contribution request fails, so the contributor can see
 * more than one line and hand the maintainers something they can act on
 * without asking for a screenshot.
 *
 * Only what the request already carried is recorded — no contributor name or
 * email — and the server's response is trimmed so the report fits in a GitHub
 * "new issue" link.
 */

import { isAxiosError } from 'axios'

export const ISSUES_URL = 'https://github.com/RESSLab-Team/resslab-hub/issues/new'

/** Keep the response readable in the issue and the link under browsers' limits. */
const MAX_RESPONSE_CHARS = 1200

export interface FailureReport {
  /** The line shown to the contributor. */
  message: string
  /** Which request failed. */
  operation: 'validate' | 'submit'
  /** ISO timestamp. */
  at: string
  /** The hub page, without query or hash. */
  page: string
  /** `METHOD /path` of the failed request, when known. */
  request?: string
  status?: number
  /** The server's response body, stringified and trimmed. */
  response?: string
  /** The batch that was being checked or submitted. */
  database?: string
  type?: string
  experiments?: number
  files?: number
  /** Browser identification. */
  client: string
}

export interface FailureContext {
  operation: FailureReport['operation']
  message: string
  database?: string
  type?: string
  experiments?: number
  files?: number
}

function trim(text: string): string {
  return text.length > MAX_RESPONSE_CHARS ? `${text.slice(0, MAX_RESPONSE_CHARS)}…` : text
}

function stringify(body: unknown): string | undefined {
  if (body === undefined || body === null || body === '') return undefined
  if (typeof body === 'string') return trim(body)
  try {
    return trim(JSON.stringify(body, null, 2))
  } catch {
    return trim(String(body))
  }
}

/** Build the report for a failed request from whatever was thrown. */
export function describeFailure(caught: unknown, context: FailureContext): FailureReport {
  const report: FailureReport = {
    message: context.message,
    operation: context.operation,
    at: new Date().toISOString(),
    page: typeof location === 'undefined' ? '' : `${location.origin}${location.pathname}`,
    database: context.database,
    type: context.type,
    experiments: context.experiments,
    files: context.files,
    client: typeof navigator === 'undefined' ? '' : navigator.userAgent
  }
  if (isAxiosError(caught)) {
    const method = (caught.config?.method ?? 'get').toUpperCase()
    const url = caught.config?.url ?? ''
    report.request = url ? `${method} ${url}` : undefined
    report.status = caught.response?.status
    report.response =
      stringify(caught.response?.data) ?? (caught.response ? undefined : caught.message)
  } else if (caught instanceof Error) {
    report.response = trim(caught.stack ?? caught.message)
  } else if (caught !== undefined) {
    report.response = stringify(caught)
  }
  return report
}

/** The report as the body of a bug issue. */
export function failureToMarkdown(report: FailureReport): string {
  const batch = [
    report.database,
    report.type ? `(\`${report.type}\`)` : '',
    report.experiments !== undefined ? `${report.experiments} experiment(s)` : '',
    report.files !== undefined ? `${report.files} test-data file(s)` : ''
  ]
    .filter(Boolean)
    .join(' ')
  const lines = [
    '### What happened',
    '',
    `The contribution ${report.operation === 'submit' ? 'submission' : 'check'} failed: ${
      report.message
    }`,
    '',
    '### Details',
    '',
    `- When: ${report.at}`,
    `- Page: ${report.page}`,
    batch ? `- Batch: ${batch}` : '',
    report.request ? `- Request: \`${report.request}\`` : '',
    report.status !== undefined ? `- HTTP status: ${report.status}` : '',
    `- Browser: ${report.client}`,
    ''
  ].filter((line) => line !== '')
  if (report.response) {
    lines.push('', '### Server response', '', '```', report.response, '```')
  }
  lines.push('', '_Reported from the contribution editor._')
  return lines.join('\n')
}

/** A GitHub "new issue" link with the report prefilled. */
export function bugReportUrl(report: FailureReport): string {
  const what = report.operation === 'submit' ? 'submission' : 'check'
  const title = `[BUG] Contribution ${what} failed: ${report.message}`.slice(0, 120)
  const params = new URLSearchParams({
    title,
    body: failureToMarkdown(report),
    labels: 'bug'
  })
  return `${ISSUES_URL}?${params.toString()}`
}
