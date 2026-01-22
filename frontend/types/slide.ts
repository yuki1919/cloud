export type EnrichmentItem = {
  summary: string;
  expansions: string[];
  references: string[];
  search_snippets: string[];
};

export type SlideEnrichment = {
  slide_number: number;
  title?: string | null;
  raw_text: string;
  section?: string | null;
  enrichment: EnrichmentItem;
};

export type GlobalNotes = {
  overview: string;
  knowledge_points: string[];
  related_refs: string[];
};

export type TopicNote = {
  title: string;
  slide_numbers: number[];
  section?: string | null;
  raw_text: string;
  enrichment: EnrichmentItem;
};
