# Document AI Analyzer — Frontend

A minimal, monochrome document-chat interface built with React + Vite.
Consumes an existing backend at `/documents/upload` and `/documents/{id}/query`.

## Setup

```bash
npm install
cp .env.example .env   # set VITE_API_URL to your backend
npm run dev
```

## Build

```bash
npm run build
```

## Structure

- `src/components/` — Header, UploadButton, UploadState, DocumentInfo,
  ChatWindow, ChatMessage, ChatInput, LoadingIndicator, MarkdownRenderer
- `src/services/api.js` — all backend calls (upload, query)
- Markdown responses are rendered with `react-markdown` + `remark-gfm`
  (headings, bold/italic, lists, code blocks, tables, blockquotes).

## Behavior notes

- Selecting a file immediately switches to the chat shell; the document
  status area shows "Processing document…" while upload is in flight.
- The chat input stays typable during upload; Send is disabled until the
  backend returns `status: "ready"`.
- While a query is in flight, a second submission is blocked and a
  typing-dots indicator stands in for the assistant reply.
- Errors from either endpoint are shown as short, human-readable messages
  — no raw stack traces.
