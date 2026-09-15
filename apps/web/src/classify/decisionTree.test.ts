import { expect, test } from 'vitest'
import { classify } from './decisionTree'

test('food intended use maps to ayurveda_aahara_or_nutraceutical regardless of basis', () => {
  const result = classify({ basis: 'not_sure', intendedUse: 'food' })
  expect(result.category).toBe('ayurveda_aahara_or_nutraceutical')
  expect(result.confidence).toBe('high')
})

test('cosmetic intended use maps to cosmetic', () => {
  const result = classify({ basis: 'classical', intendedUse: 'cosmetic' })
  expect(result.category).toBe('cosmetic')
})

test('classical basis + established evidence -> classical_or_generic_medicine', () => {
  const result = classify({
    basis: 'classical',
    intendedUse: 'therapeutic',
    evidenceBasis: 'established_classical',
  })
  expect(result.category).toBe('classical_or_generic_medicine')
})

test('new/proprietary basis + established evidence -> patent_or_proprietary_medicine', () => {
  const result = classify({
    basis: 'new_or_proprietary',
    intendedUse: 'therapeutic',
    evidenceBasis: 'established_classical',
  })
  expect(result.category).toBe('patent_or_proprietary_medicine')
})

test('new evidence needed -> new_or_non_classical_drug regardless of basis', () => {
  const result = classify({
    basis: 'classical',
    intendedUse: 'therapeutic',
    evidenceBasis: 'new_evidence_needed',
  })
  expect(result.category).toBe('new_or_non_classical_drug')
})

test('phytopharmaceutical evidence basis wins outright', () => {
  const result = classify({
    basis: 'new_or_proprietary',
    intendedUse: 'therapeutic',
    evidenceBasis: 'phytopharmaceutical',
  })
  expect(result.category).toBe('phytopharmaceutical')
})

test('therapeutic with not_sure evidence basis is unclear, low confidence', () => {
  const result = classify({
    basis: 'not_sure',
    intendedUse: 'therapeutic',
    evidenceBasis: 'not_sure',
  })
  expect(result.category).toBe('unclear')
  expect(result.confidence).toBe('low')
})

test('therapeutic with no evidenceBasis at all is unclear', () => {
  const result = classify({ basis: 'classical', intendedUse: 'therapeutic' })
  expect(result.category).toBe('unclear')
})
