# 11. Cloud OCR APIs

[Back to README](../README.md) | Prev: [Training and fine-tuning](10-training-finetuning.md) | Next: [Glossary](12-glossary.md)

When you should not run it yourself: no GPU, spiky volume, standard forms (invoices, IDs, receipts, W-2s)
where a prebuilt model exists, or compliance that wants a vendor SLA. When you should: privacy, cost at
steady volume, unusual documents, offline.

Prices are list prices from 2026 pricing roundups and vendor pages; verify before budgeting. All vendors
have free tiers or monthly free pages.

---

## Price table (per 1,000 pages, list)

| Service | Plain OCR / Read | Layout (tables, paragraphs) | Prebuilt (invoice, receipt, ID) | Custom / trained extraction | Notes |
|:--------|:----------------:|:---------------------------:|:-------------------------------:|:---------------------------:|:------|
| **Azure AI Document Intelligence** | $1.50 | $10 | $10 | $30 | Commitment tiers cut it further; best prebuilt catalog |
| **Google Document AI** | $1.50 (Enterprise OCR) | $10 (Form Parser / Layout Parser) | $10 to $30 (specialized processors) | $30 (custom extractor) | Layout Parser is what feeds Vertex RAG |
| **Google Cloud Vision** | $1.50 (`TEXT_DETECTION`, `DOCUMENT_TEXT_DETECTION`) | n/a | n/a | n/a | 1,000 units/month free; scene text |
| **AWS Textract** | $1.50 (DetectDocumentText) | $15 (Tables) + $50 (Forms) = $65 for both | $10 (AnalyzeExpense), $25+ (AnalyzeID) | Queries add-on | Most expensive for structure |
| **Mistral OCR 3** | ~$1 to $2 flat | included | included (Markdown + images + bboxes) | n/a | Cheapest full-document parse; batch discounts |
| **Datalab (Marker/Chandra API)** | per page, tiered | included | n/a | n/a | Same models as the open repos, hosted |
| **OCR.space** | free tier (25k/month), then $ | n/a | n/a | n/a | Tesseract-class quality |
| **Frontier multimodal LLMs** (Claude, GPT, Gemini) | token priced: roughly $1 to $10 per 1,000 pages depending on model and resolution | prompt-defined | prompt-defined | prompt-defined | Best reasoning, worst determinism, watch hallucination |

Worked example from a 2026 roundup: 50,000 invoices a month with tables and forms costs about $3,250 on Textract
Forms + Tables versus about $50 on Mistral OCR batch. Plain Read OCR is the same $1.50 everywhere except Mistral.

---

## Azure AI Document Intelligence

Models: `prebuilt-read` (OCR + language + handwriting flag), `prebuilt-layout` (paragraphs, tables, selection marks,
figures, Markdown output), `prebuilt-invoice`, `prebuilt-receipt`, `prebuilt-idDocument`, `prebuilt-tax.us.w2`,
`prebuilt-contract`, `prebuilt-healthInsuranceCard`, plus custom extraction/classification trained in Document
Intelligence Studio on 5+ labeled samples.

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
client = DocumentIntelligenceClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))
with open("scan.pdf", "rb") as f:
    poller = client.begin_analyze_document("prebuilt-layout", body=f, output_content_format="markdown")
result = poller.result()
print(result.content)                       # markdown
for t in result.tables: print(t.row_count, t.column_count)
```

Strengths: the prebuilt catalog, Markdown output from layout, handwriting, 300+ languages in Read. Weakness:
per-page pricing on multi-page PDFs adds up; the Studio UI is the only sane way to train custom models.

---

## Google Document AI and Cloud Vision

Document AI processors: Enterprise Document OCR, Form Parser, Layout Parser (chunks for RAG), Invoice, Expense,
Identity, Custom Extractor (Gemini-backed since 2025). Cloud Vision is the older, cheaper image API.

```python
from google.cloud import documentai
client = documentai.DocumentProcessorServiceClient()
name = client.processor_path(PROJECT, "us", PROCESSOR_ID)
raw = documentai.RawDocument(content=open("scan.pdf", "rb").read(), mime_type="application/pdf")
doc = client.process_document(request=documentai.ProcessRequest(name=name, raw_document=raw)).document
print(doc.text)
for page in doc.pages:
    for table in page.tables: print(len(table.header_rows), len(table.body_rows))
```

Strengths: OCR quality on photos, 200+ languages, Vertex integration, Gemini-backed custom extraction.
Weakness: processor sprawl, regional endpoints, quotas.

---

## AWS Textract

APIs: `DetectDocumentText` (lines/words), `AnalyzeDocument` with `FeatureTypes` `TABLES`, `FORMS`, `QUERIES`,
`SIGNATURES`, `LAYOUT`; `AnalyzeExpense`; `AnalyzeID`. Async variants for multi-page PDFs in S3.

```python
import boto3
tx = boto3.client("textract", region_name="us-east-1")
r = tx.analyze_document(Document={"Bytes": open("scan.png", "rb").read()},
                        FeatureTypes=["TABLES", "FORMS", "LAYOUT"],
                        QueriesConfig={"Queries": [{"Text": "What is the invoice total?"}]})
for b in r["Blocks"]:
    if b["BlockType"] == "LINE": print(b["Text"], round(b["Confidence"], 1))
```

Strengths: Queries (ask natural-language questions per page), calibrated confidences, S3-native batch.
Weakness: cost for Forms + Tables, weaker handwriting than Azure.

---

## Mistral OCR 3

Flat-rate document understanding: upload a PDF or image, get Markdown with images extracted and positioned,
tables, and optional structured JSON via annotations. Multilingual, fast, cheap. Batch API halves the price.

```python
from mistralai import Mistral
client = Mistral(api_key=KEY)
r = client.ocr.process(model="mistral-ocr-latest",
                       document={"type": "document_url", "document_url": "https://example.com/paper.pdf"},
                       include_image_base64=False)
for p in r.pages: print(p.markdown)
```

---

## Frontier multimodal LLMs as OCR

Claude, GPT, and Gemini read pages well and are the only cloud option that can *reason* while transcribing
("this is a two-column layout; the footnote belongs to column 1"). They are also the only option that will
confidently fabricate a row. Use them for:

- Extraction from already-OCRed text (cheap, no images)
- Hard pages a dedicated parser garbled
- Structured output with a JSON schema

Not for: bulk plain OCR (10 to 50x the price of Read APIs), archival transcription (normalization), anything you
cannot diff against a second source.

Cost math: a 1,000 x 1,400 px page is roughly 1,000 to 1,800 input tokens on current tokenizers plus the output
tokens; at 2026 list prices that is fractions of a cent to a few cents per page depending on the model. Check the
current price table before assuming.

---

## Privacy and compliance notes

- All three hyperscalers offer regional processing, no-training clauses, and BAAs (Azure, Google, AWS all sign
  HIPAA BAAs for these services). Mistral offers EU hosting. Read the data retention section of each.
- If the documents cannot leave the building, the open models in [07](07-vlm-document-parsers.md) match or beat
  the cloud Read APIs on accuracy in 2026; what you lose is the prebuilt form models and the SLA.
- Hybrid: local RapidOCR/PaddleOCR-VL for everything, cloud prebuilt for the 5 percent of documents that are
  standard forms and need field-level accuracy.

---

## Choosing

| Priority | Pick |
|:---------|:-----|
| Cheapest full parse to Markdown | Mistral OCR 3 |
| Standard business forms with fields | Azure prebuilt |
| Already on GCP / need RAG chunks | Google Document AI Layout Parser |
| Already on AWS / need per-page questions | Textract with Queries |
| Photos, signs, scene text | Google Cloud Vision |
| Reasoning over the page | A frontier LLM with a diff against a Read API |
| None of the above leaves the LAN | [07](07-vlm-document-parsers.md) |
