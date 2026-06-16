import type { ResidualStressModel } from '@/backend'
import { createResidualModels, validateResidualModelParams } from '@/utils/residual'
import { describe, expect, it } from 'vitest'

const validParams = {
  fy_n: 355,
  b: 300,
  tf: 19,
  tw: 11,
  h: 340,
  A: 17000,
  h_over_b: 1.13
} as unknown as ResidualStressModel

describe('residual.validateResidualModelParams', () => {
  it('passes when every required field is present', () => {
    expect(validateResidualModelParams(validParams)).toBe(true)
  })

  it('fails when a required field is missing or null', () => {
    expect(
      validateResidualModelParams({ ...validParams, tw: null } as unknown as ResidualStressModel)
    ).toBe(false)
    expect(validateResidualModelParams({} as ResidualStressModel)).toBe(false)
  })
})

describe('residual.createResidualModels', () => {
  it('returns undefined when required params or coefficients are missing', () => {
    expect(createResidualModels({} as ResidualStressModel, [], [], [])).toBeUndefined()
  })

  it('returns a model when params and a QP coefficient set are provided', () => {
    const qpCoefficient = [[100], [-120], [150], [0.01]]
    const result = createResidualModels(validParams, qpCoefficient, [[0]], [[0]])
    expect(result).toBeDefined()
  })
})
