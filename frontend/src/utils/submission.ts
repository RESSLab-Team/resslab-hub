import type { Type } from '@/backend'
import { axiosInstance, baseUrl } from '@/plugins/axios'

/**
 * Hand-written client for the two write endpoints of the contribution flow.
 *
 * Both send the batch as a gzipped tar in a multipart form: `POST` opens a
 * pull request on the resslab-hub-data repository, `PUT` pushes a new commit
 * on an open one. The server re-validates the archive either way.
 *
 * Who is submitting is not sent: since #247 the backend takes it from the
 * session, which is what makes the pull request attributable.
 */

/** The pull request a submission lives in. */
export interface ContributionResult {
  pr_url: string
  pr_number: number
  branch: string
  /** Commit the submission points at; sent back when updating it. */
  head_sha: string
}

/** The submission and the commit an edit is written against. */
export interface EditTarget {
  prNumber: number
  prUrl: string
  headSha: string
  /** The submission's branch on the data repository, for the GitHub links. */
  branch: string
}

export function isContributionResult(data: unknown): data is ContributionResult {
  const candidate = data as ContributionResult
  return (
    typeof candidate === 'object' &&
    candidate !== null &&
    typeof candidate.pr_url === 'string' &&
    typeof candidate.pr_number === 'number' &&
    typeof candidate.branch === 'string' &&
    typeof candidate.head_sha === 'string'
  )
}

function contributionForm(dismissedWarnings: string[], archive: File): FormData {
  const form = new FormData()
  form.append('file', archive)
  form.append('dismissed_warnings', JSON.stringify(dismissedWarnings))
  return form
}

export async function postContribution(
  type: Type,
  archive: File,
  dismissedWarnings: string[]
): Promise<ContributionResult> {
  const form = contributionForm(dismissedWarnings, archive)
  const { data } = await axiosInstance.post(`${baseUrl}/contributions`, form, {
    params: { type }
  })
  if (!isContributionResult(data)) {
    throw new Error('Unexpected submission response shape.')
  }
  return data
}

/**
 * Push the batch again on an open submission's own branch.
 *
 * `target.headSha` is the commit the editor loaded: the server refuses the
 * update (409) when the branch moved since, rather than overwriting whoever
 * pushed in between. It also refuses (403) a submission made from another
 * account.
 */
export async function putContribution(
  archive: File,
  target: EditTarget,
  dismissedWarnings: string[]
): Promise<ContributionResult> {
  const form = contributionForm(dismissedWarnings, archive)
  form.append('head_sha', target.headSha)
  const { data } = await axiosInstance.put(`${baseUrl}/contributions/${target.prNumber}`, form)
  if (!isContributionResult(data)) {
    throw new Error('Unexpected submission response shape.')
  }
  return data
}
