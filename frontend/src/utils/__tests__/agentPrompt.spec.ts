import { agentGuideUrl, agentPrompt } from '@/utils/agentPrompt'
import { describe, expect, it } from 'vitest'

describe('agentPrompt', () => {
  it('points to the agent guide of the database, through the API prefix', () => {
    expect(agentGuideUrl('braces', 'https://hub.test')).toBe(
      'https://hub.test/api/agent/guide/braces'
    )
    expect(agentGuideUrl('ductile-fracture', 'https://hub.test')).toBe(
      'https://hub.test/api/agent/guide/ductile-fracture'
    )
  })

  it('names the database and the guide, and leaves a slot for the files', () => {
    const prompt = agentPrompt('hss', 'https://hub.test')
    expect(prompt).toContain('"hss" database')
    expect(prompt).toContain('https://hub.test/api/agent/guide/hss')
    expect(prompt).toContain('[write where your files are, or attach them]')
    expect(prompt).toContain('ask me about each warning')
  })
})
