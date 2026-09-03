import type { Type } from '@/backend'
import { axiosInstance, baseUrl } from '@/plugins/axios'

/**
 * Hand-written client for `POST /contributions` (the generated client does not
 * cover it yet — regenerate with `make api` to add it). The endpoint
 * re-validates the archive server-side and opens a pull request on the
 * resslab-hub-data repository.
 *
 * Who is submitting is no longer sent: since #247 the backend takes it from
 * the session, which is what makes the pull request attributable.
 */

/** The pull request opened for a submission. */
export interface ContributionResult {
  pr_url: string
  pr_number: number
  branch: string
}

export function isContributionResult(data: unknown): data is ContributionResult {
  const candidate = data as ContributionResult
  return (
    typeof candidate === 'object' &&
    candidate !== null &&
    typeof candidate.pr_url === 'string' &&
    typeof candidate.pr_number === 'number' &&
    typeof candidate.branch === 'string'
  )
}

export async function postContribution(
  type: Type,
  archive: File,
  dismissedWarnings: string[]
): Promise<ContributionResult> {
  const form = new FormData()
  form.append('file', archive)
  form.append('dismissed_warnings', JSON.stringify(dismissedWarnings))
  const { data } = await axiosInstance.post(`${baseUrl}/contributions`, form, {
    params: { type }
  })
  if (!isContributionResult(data)) {
    throw new Error('Unexpected submission response shape.')
  }
  return data
}
