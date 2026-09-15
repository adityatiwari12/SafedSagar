/**
 * Deterministic product-classification decision logic - the "Product
 * Classification Wizard" from docs/product/rbac-architecture-and-ux-spec.md
 * Section 4. Deliberately NOT an LLM call: the six categories map to a
 * small, explainable decision tree, so the wizard gives a precise,
 * reproducible answer instead of a model guess. The category keys match
 * the backend's PRODUCT_CATEGORIES (app/graph/state.py) so a value here
 * renders identically to what classify_product would later produce in
 * the chat's ClassificationBadges.
 */

export type ProductCategory =
  | 'classical_or_generic_medicine'
  | 'patent_or_proprietary_medicine'
  | 'new_or_non_classical_drug'
  | 'phytopharmaceutical'
  | 'ayurveda_aahara_or_nutraceutical'
  | 'cosmetic'
  | 'unclear'

export type Basis = 'classical' | 'new_or_proprietary' | 'not_sure'
export type IntendedUse = 'therapeutic' | 'food' | 'cosmetic'
export type EvidenceBasis = 'established_classical' | 'new_evidence_needed' | 'phytopharmaceutical' | 'not_sure'

export interface WizardAnswers {
  basis: Basis
  intendedUse: IntendedUse
  evidenceBasis?: EvidenceBasis // only asked when intendedUse === 'therapeutic'
}

export interface ClassificationResult {
  category: ProductCategory
  confidence: 'high' | 'medium' | 'low'
  rationale: string
  implication: string
}

const IMPLICATIONS: Record<ProductCategory, string> = {
  classical_or_generic_medicine:
    'Largely traditional knowledge - faces the Section 3(p) patenting bar. Defended through TKDL awareness (prior-art pointer), not patents. Focus IP strategy on trademark/GI/trade-secret instead.',
  patent_or_proprietary_medicine:
    'Genuine patent potential if it demonstrates novelty and inventive step beyond known/classical compositions. Document what is actually new before filing.',
  new_or_non_classical_drug:
    'Strongest patent potential, but requires clinical/scientific evidence of safety and effectiveness under the applicable new-drug regulatory pathway - a longer, more evidence-heavy route.',
  phytopharmaceutical:
    'Falls under the phytopharmaceutical drug framework (standardized plant-derived, defined pharmacological action) - a distinct regulatory pathway from classical or new-drug routes.',
  ayurveda_aahara_or_nutraceutical:
    'Regulated as food under the FSSAI Ayurveda-Aahara Regulations, 2022 - no disease-treatment claims permitted. IP strategy centers on trademark/packaging/design, not patent.',
  cosmetic:
    'Regulated under the cosmetic framework (Drugs and Cosmetics Act) - claims must stay cosmetic (appearance), never therapeutic. Trademark/design are the primary IP levers.',
  unclear:
    'Not enough information to classify confidently from these answers. Describe the product in your own words in the chat instead - the assistant will ask targeted follow-up questions.',
}

export function classify(answers: WizardAnswers): ClassificationResult {
  if (answers.intendedUse === 'food') {
    return {
      category: 'ayurveda_aahara_or_nutraceutical',
      confidence: 'high',
      rationale: 'Intended use is food/nutraceutical (Ayurveda Aahara), not therapeutic.',
      implication: IMPLICATIONS.ayurveda_aahara_or_nutraceutical,
    }
  }

  if (answers.intendedUse === 'cosmetic') {
    return {
      category: 'cosmetic',
      confidence: 'high',
      rationale: 'Intended use is cosmetic (external, appearance-related), not therapeutic.',
      implication: IMPLICATIONS.cosmetic,
    }
  }

  // intendedUse === 'therapeutic' from here on
  const { basis, evidenceBasis } = answers

  if (evidenceBasis === 'phytopharmaceutical') {
    return {
      category: 'phytopharmaceutical',
      confidence: 'high',
      rationale: 'Standardized plant-extract-based drug with a defined pharmacological action.',
      implication: IMPLICATIONS.phytopharmaceutical,
    }
  }

  if (evidenceBasis === 'new_evidence_needed') {
    return {
      category: 'new_or_non_classical_drug',
      confidence: 'high',
      rationale: 'Therapeutic use requiring new safety/effectiveness evidence, not relying on established/classical use.',
      implication: IMPLICATIONS.new_or_non_classical_drug,
    }
  }

  if (evidenceBasis === 'established_classical') {
    if (basis === 'classical') {
      return {
        category: 'classical_or_generic_medicine',
        confidence: 'high',
        rationale: 'Formulation and method drawn from an authoritative classical text, with established use.',
        implication: IMPLICATIONS.classical_or_generic_medicine,
      }
    }
    if (basis === 'new_or_proprietary') {
      return {
        category: 'patent_or_proprietary_medicine',
        confidence: 'high',
        rationale: 'A new or proprietary formulation, but relying on established/classical-use evidence rather than new clinical data.',
        implication: IMPLICATIONS.patent_or_proprietary_medicine,
      }
    }
  }

  return {
    category: 'unclear',
    confidence: 'low',
    rationale: "The answers given don't map cleanly to one category (e.g. 'not sure' on a key question).",
    implication: IMPLICATIONS.unclear,
  }
}

export function describeAnswersForChat(productDescription: string, result: ClassificationResult): string {
  return (
    `${productDescription.trim()}\n\n` +
    `[Product Classification Wizard result: ${result.category.replace(/_/g, ' ')} ` +
    `(${result.confidence} confidence) - ${result.rationale}]`
  )
}
