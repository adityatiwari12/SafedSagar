/** Standard, generic descriptions of each IP regime the assistant can
 * detect (app.graph.state.IP_TYPES) - explainer copy only, not legal
 * advice about any specific product. Every regime named here already has
 * primary source text in the ingested corpus (Patents Act, Trade Marks
 * Act, GI Act, Copyright Act, Designs Act, PPV&FR Act, Biological
 * Diversity Act, Drugs and Cosmetics Act / FSSAI regs). */
export interface IpTypeInfo {
  label: string
  protects: string
}

export const IP_TYPE_INFO: Record<string, IpTypeInfo> = {
  patent: {
    label: 'Patent',
    protects:
      'A new, useful and non-obvious invention - formulation, process or device - for a limited term. Does not protect the underlying traditional knowledge itself.',
  },
  trademark: {
    label: 'Trademark',
    protects: 'A brand name, logo or other identifier used to distinguish goods in trade.',
  },
  geographical_indication: {
    label: 'Geographical Indication',
    protects: 'A name tied to a specific geographic origin and the qualities that origin gives the product.',
  },
  copyright: {
    label: 'Copyright',
    protects: 'Original documentation, research write-ups, artwork or other literary/creative expression.',
  },
  design: {
    label: 'Design',
    protects: 'The visual appearance - shape, packaging, container - of an article, not how it functions.',
  },
  trade_secret: {
    label: 'Trade Secret',
    protects: 'A confidential formulation or process kept secret rather than disclosed through a patent filing.',
  },
  plant_variety: {
    label: 'Plant Variety',
    protects: 'A new plant variety, under the PPV&FR Act - relevant to cultivators and plant-derived formulations.',
  },
  access_and_benefit_sharing: {
    label: 'Access & Benefit Sharing',
    protects:
      'Not an IP right itself - a compliance gate under the Biological Diversity Act governing use of biological resources and associated traditional knowledge.',
  },
  drug_regulatory: {
    label: 'Regulatory Pathway',
    protects:
      'Not an IP right - the AYUSH/FSSAI approval pathway required before commercialization, regardless of IP status.',
  },
}

export function ipTypeInfo(ipType: string): IpTypeInfo {
  return (
    IP_TYPE_INFO[ipType] ?? {
      label: ipType.replace(/_/g, ' '),
      protects: '',
    }
  )
}
