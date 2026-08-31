import { bugReportUrl, describeFailure, failureToMarkdown, ISSUES_URL } from '@/utils/failureReport'
import { describe, expect, it } from 'vitest'

const CONTEXT = {
  operation: 'submit' as const,
  message: 'The generated archive could not be read by the server.',
  database: 'cyclic',
  type: 'all-material',
  experiments: 11,
  files: 11
}

function axiosLike(status: number, data: unknown, url = '/contributions') {
  return {
    isAxiosError: true,
    message: `Request failed with status code ${status}`,
    config: { method: 'post', url },
    response: { status, data }
  }
}

describe('describeFailure', () => {
  it('records the request, status and server response of an HTTP failure', () => {
    const report = describeFailure(axiosLike(400, { detail: 'Could not read archive: x' }), CONTEXT)
    expect(report.request).toBe('POST /contributions')
    expect(report.status).toBe(400)
    expect(report.response).toContain('"detail": "Could not read archive: x"')
    expect(report.operation).toBe('submit')
    expect(report.experiments).toBe(11)
    expect(report.at).toMatch(/^\d{4}-\d{2}-\d{2}T/)
  })

  it('keeps the transport message when there was no response at all', () => {
    const caught = { isAxiosError: true, message: 'Network Error', config: { url: '/validate' } }
    const report = describeFailure(caught, { ...CONTEXT, operation: 'validate' })
    expect(report.status).toBeUndefined()
    expect(report.response).toBe('Network Error')
  })

  it('records a thrown error and trims long bodies', () => {
    const report = describeFailure(new Error('Unexpected submission response shape.'), CONTEXT)
    expect(report.response).toContain('Unexpected submission response shape.')
    const long = describeFailure(axiosLike(502, 'x'.repeat(5000)), CONTEXT)
    expect(long.response!.length).toBeLessThan(1300)
    expect(long.response!.endsWith('…')).toBe(true)
  })
})

describe('bugReportUrl', () => {
  it('opens a new issue with a [BUG] title, the bug label and the report as body', () => {
    const report = describeFailure(axiosLike(400, { detail: 'nope' }), CONTEXT)
    const url = new URL(bugReportUrl(report))
    expect(url.origin + url.pathname).toBe(ISSUES_URL)
    expect(url.searchParams.get('title')).toBe(
      '[BUG] Contribution submission failed: The generated archive could not be read by the server.'
    )
    expect(url.searchParams.get('labels')).toBe('bug')
    const body = url.searchParams.get('body')!
    expect(body).toBe(failureToMarkdown(report))
    expect(body).toContain('- HTTP status: 400')
    expect(body).toContain('- Batch: cyclic (`all-material`) 11 experiment(s) 11 test-data file(s)')
    expect(body).toContain('"detail": "nope"')
    // No contributor identity ever travels in the report.
    expect(body).not.toMatch(/@/)
  })
})
