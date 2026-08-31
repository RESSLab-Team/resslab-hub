import type { Type } from '@/backend'
import { axiosInstance, baseUrl } from '@/plugins/axios'

/**
 * Hand-written client for `POST /contributions` (the generated client does not
 * cover it yet — regenerate with `make api` to add it). The endpoint
 * re-validates the archive server-side and opens a pull request on the
 * resslab-hub-data repository.
 */

export interface ContributorInfo {
  name: string
  email: string
  institution: string
  orcid: string
}

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
  contributor: ContributorInfo,
  dismissedWarnings: string[]
): Promise<ContributionResult> {
  const form = new FormData()
  form.append('file', archive)
  form.append('contributor_name', contributor.name)
  form.append('contributor_email', contributor.email)
  form.append('institution', contributor.institution)
  form.append('orcid', contributor.orcid)
  form.append('dismissed_warnings', JSON.stringify(dismissedWarnings))
  const { data } = await axiosInstance.post(`${baseUrl}/contributions`, form, {
    params: { type }
  })
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
