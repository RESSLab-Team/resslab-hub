import type { Type } from '@/backend'
import { axiosInstance, baseUrl } from '@/plugins/axios'

/**
 * Hand-written client for the two write endpoints of the contribution flow.
 *
 * Both send the batch as a gzipped tar in a multipart form: `POST` opens a
 * pull request on the resslab-hub-data repository, `PUT` pushes a new commit
 * on an open one. The server re-validates the archive either way.
 */

export interface ContributorInfo {
  name: string
  email: string
  institution: string
  orcid: string
}

/** The pull request a submission lives in. */
export interface ContributionResult {
  pr_url: string
  pr_number: number
  branch: string
  /** Commit the submission points at; sent back when updating it. */
  head_sha: string
}

/** The branch and commit an edit is written against. */
export interface EditTarget {
  prNumber: number
  prUrl: string
  branch: string
  headSha: string
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

function contributionForm(
  contributor: ContributorInfo,
  dismissedWarnings: string[],
  archive: File
): FormData {
  const form = new FormData()
  form.append('file', archive)
  form.append('contributor_name', contributor.name)
  form.append('contributor_email', contributor.email)
  form.append('institution', contributor.institution)
  form.append('orcid', contributor.orcid)
  form.append('dismissed_warnings', JSON.stringify(dismissedWarnings))
  return form
}

export async function postContribution(
  type: Type,
  archive: File,
  contributor: ContributorInfo,
  dismissedWarnings: string[]
): Promise<ContributionResult> {
  const form = contributionForm(contributor, dismissedWarnings, archive)
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
 * pushed in between.
 */
export async function putContribution(
  archive: File,
  target: EditTarget,
  contributor: ContributorInfo,
  dismissedWarnings: string[]
): Promise<ContributionResult> {
  const form = contributionForm(contributor, dismissedWarnings, archive)
  form.append('branch', target.branch)
  form.append('head_sha', target.headSha)
  const { data } = await axiosInstance.put(`${baseUrl}/contributions/${target.prNumber}`, form)
  if (!isContributionResult(data)) {
    throw new Error('Unexpected submission response shape.')
  }
  return data
}

const CONTRIBUTOR_STORAGE_KEY = 'resslab.contributor'

/** Remembered contributor details, so repeat submissions start prefilled. */
export function loadContributor(): ContributorInfo {
  try {
    const raw = localStorage.getItem(CONTRIBUTOR_STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        name: String(parsed.name ?? ''),
        email: String(parsed.email ?? ''),
        institution: String(parsed.institution ?? ''),
        orcid: String(parsed.orcid ?? '')
      }
    }
  } catch {
    // Corrupt or unavailable storage falls through to a blank form.
  }
  return { name: '', email: '', institution: '', orcid: '' }
}

export function saveContributor(contributor: ContributorInfo): void {
  try {
    localStorage.setItem(CONTRIBUTOR_STORAGE_KEY, JSON.stringify(contributor))
  } catch {
    // Private-mode storage errors are not worth surfacing.
  }
}
