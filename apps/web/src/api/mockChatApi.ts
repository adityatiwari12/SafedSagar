import { ChatApi, ChatTurnInput, ChatTurnResponse, Citation } from './chatApi'

let counter = 0
function nextId(prefix: string): string {
  counter += 1
  return `${prefix}-${counter}`
}

const PATENT_ACT_CITATION: Citation = {
  doc_id: 'ipindia-patents-act-1970',
  title: 'The Patents Act, 1970',
  section_or_article: 'Section 3(p)',
  source_url: 'https://ipindia.gov.in/',
  last_verified_date: '2026-09-15',
}

const BIODIVERSITY_ACT_CITATION: Citation = {
  doc_id: 'india-biological-diversity-act-2002',
  title: 'The Biological Diversity Act, 2002',
  section_or_article: 'Section 6',
  source_url: 'https://nbaindia.org/',
  last_verified_date: '2026-09-15',
}

const TRIPS_CITATION: Citation = {
  doc_id: 'wto-trips-1994',
  title: 'TRIPS Agreement',
  section_or_article: 'Article 27',
  source_url: 'https://www.wto.org/english/docs_e/legal_e/27-trips.pdf',
  last_verified_date: '2026-09-15',
}

const FSSAI_CITATION: Citation = {
  doc_id: 'fssai-ayurveda-aahara-regulations-2022',
  title: 'Food Safety and Standards (Ayurveda Aahara) Regulations, 2022',
  section_or_article: 'Regulation 3',
  source_url: 'https://www.fssai.gov.in/',
  last_verified_date: '2026-09-15',
}

function buildResponse(
  conversationId: string,
  overrides: Partial<ChatTurnResponse>,
): ChatTurnResponse {
  return {
    conversationId,
    classification: { product_type: 'unknown', ip_type: 'unknown' },
    jurisdiction: 'india',
    answer: '',
    citations: [],
    confidence: 0.5,
    confidence_band: 'medium',
    escalate_recommended: false,
    ...overrides,
  }
}

const clarifyingMemory = new Map<string, boolean>()

export const mockChatApi: ChatApi = {
  async sendTurn(input: ChatTurnInput): Promise<ChatTurnResponse> {
    const conversationId = input.conversationId ?? nextId('conv')
    const text = input.text.toLowerCase()
    const answered = Boolean(input.answers && Object.keys(input.answers).length > 0)

    // First vague turn → ask clarifying questions (guided intake)
    if (
      !answered &&
      !clarifyingMemory.get(conversationId) &&
      (text.includes('formulate') || text.includes('product') || text.includes('medicine')) &&
      !text.includes('ashwagandha') &&
      !text.includes('abs') &&
      !text.includes('biodiversity')
    ) {
      clarifyingMemory.set(conversationId, true)
      return buildResponse(conversationId, {
        clarifying_questions: [
          'Is this a classical Ayurvedic formulation, a proprietary Ayurvedic medicine, or a new composition?',
          'Is the intended use primarily as a drug/medicine, food (Ayurveda Aahara), or cosmetic?',
          'What do you mainly need help with — patent, trademark, GI, ABS/biodiversity, or regulatory compliance?',
        ],
        classification: { product_type: 'unknown', ip_type: 'unknown' },
        jurisdiction: input.jurisdiction,
        confidence: 0.35,
        confidence_band: 'low',
      })
    }

    if (text.includes('ashwagandha') && (text.includes('patent') || answered)) {
      return buildResponse(conversationId, {
        classification: { product_type: 'ayurvedic_formulation', ip_type: 'patent' },
        jurisdiction: input.jurisdiction,
        answer:
          'A formulation using a known medicinal plant like Ashwagandha is patentable in India only if it demonstrates a novel, non-obvious inventive step beyond the known traditional use. Section 3(p) of the Patents Act bars claims over traditional knowledge as such. Before filing, treat TKDL as a likely prior-art pointer and contact CSIR-TKDL for a formal search — this assistant cannot retrieve TKDL contents.',
        citations: [PATENT_ACT_CITATION, BIODIVERSITY_ACT_CITATION],
        confidence: 0.72,
        confidence_band: 'medium',
        escalate_recommended: false,
        abs_tk_flags: {
          biological_resource_likely: true,
          traditional_knowledge_likely: true,
          note: 'Biological resource + traditional knowledge indicators present. Consider NBA ABS approval and TKDL prior-art awareness.',
        },
        next_steps: [
          'Document inventive step vs classical texts and known compositions',
          'Request TKDL prior-art awareness check via CSIR-TKDL unit',
          'Assess NBA Form I / ABS approval if Indian biological resources are used commercially',
          'Review Patents Act Section 3 exclusions with a registered patent agent before filing',
        ],
      })
    }

    if (text.includes('biodiversity') || text.includes('abs') || text.includes('nagoya')) {
      const international = input.jurisdiction === 'international'
      return buildResponse(conversationId, {
        classification: { product_type: 'ayurvedic_formulation', ip_type: 'abs' },
        jurisdiction: input.jurisdiction,
        answer: international
          ? 'Cross-border access and benefit-sharing is framed by the CBD and Nagoya Protocol. The WIPO GRATK Treaty (May 2024) is signed but NOT YET IN FORCE — it is not binding law until enough ratifications are deposited. Map obligations for source and user countries separately from India domestic NBA rules.'
          : 'Commercial use of biological resources sourced from India generally requires prior approval from the National Biodiversity Authority under the Biological Diversity Act and related ABS rules. Landmark guidance includes Divya Pharmacy v. Union of India on FEBS obligations.',
        citations: international
          ? [TRIPS_CITATION, BIODIVERSITY_ACT_CITATION]
          : [BIODIVERSITY_ACT_CITATION],
        confidence: 0.68,
        confidence_band: 'medium',
        escalate_recommended: false,
        abs_tk_flags: {
          biological_resource_likely: true,
          traditional_knowledge_likely: false,
          note: 'ABS pathway likely applicable.',
        },
        next_steps: [
          'Identify whether the resource is accessed from India and for commercial use',
          'Prepare NBA application materials (Form I / relevant ABS pathway)',
          'Keep India domestic ABS and international Nagoya/GRATK analysis in separate tracks',
        ],
      })
    }

    if (text.includes('aahara') || text.includes('fssai') || text.includes('food')) {
      return buildResponse(conversationId, {
        classification: { product_type: 'ayurveda_aahara', ip_type: 'regulatory' },
        jurisdiction: input.jurisdiction,
        answer:
          'Ayurveda Aahara products fall under the Food Safety and Standards (Ayurveda Aahara) Regulations, 2022. Classification as food vs drug changes labelling, claims, and licensing — avoid therapeutic claims that push the product into drug regulation.',
        citations: [FSSAI_CITATION],
        confidence: 0.7,
        confidence_band: 'medium',
        next_steps: [
          'Confirm Category-A / permitted ingredient lists under Ayurveda Aahara regulations',
          'Align labelling and claims with FSSAI food rules (not drug claims)',
          'Check whether any IP filing (mark / patent) should proceed in parallel',
        ],
      })
    }

    return buildResponse(conversationId, {
      answer:
        "I couldn't confidently classify this question against the current corpus. Please rephrase with product type, intended use, and whether you need patent, trademark, ABS, or regulatory guidance — or talk to a human IP facilitator.",
      confidence: 0.2,
      confidence_band: 'low',
      escalate_recommended: true,
      next_steps: [
        'Add product category and intended market (India / export)',
        'Specify whether biological resources or classical texts are involved',
        'Escalate to a human facilitator if the matter is time-sensitive',
      ],
    })
  },

  async escalate(_conversationId: string) {
    return { escalation_id: nextId('escalation') }
  },
}
