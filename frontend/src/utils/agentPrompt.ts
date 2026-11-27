/**
 * The prompt a researcher gives to their own AI agent (Claude, ChatGPT, ...)
 * to convert their files to the hub template. The prompt stays short: it
 * points to the agent guide (`GET /agent/guide/{database}`, backend
 * routers/agent.py), which has the method, the folder layout, the dictionary
 * and how to check the result with `POST /agent/validate`.
 *
 * In English whatever the page language: it is read by the agent, and the
 * guide it points to is in English too.
 */

import type { DatabaseId } from '@/utils/navigation'

const API_BASE: string = import.meta.env.VITE_APP_BACKEND_URL ?? '/api'

/** Absolute URL of the agent guide of one database. */
export function agentGuideUrl(database: DatabaseId, origin = window.location.origin): string {
  return new URL(`${API_BASE}/agent/guide/${database}`, origin).href
}

export function agentPrompt(database: DatabaseId, origin = window.location.origin): string {
  return [
    `I want to publish my test data on RESSLab Hub, in the "${database}" database.`,
    `First read this guide and follow it: ${agentGuideUrl(database, origin)}`,
    'My files are here: [write where your files are, or attach them]',
    'Please:',
    '- show me how you map my columns before you convert anything,',
    '- never invent a value, and ask me when something is missing or unclear,',
    '- check the result with the hub as the guide says, and ask me about each warning,',
    '- give me the folder to upload and a short conversion report.'
  ].join('\n')
}
