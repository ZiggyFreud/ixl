# IXL Public Adjuster Chatbot

RAG-based customer support chatbot for [IXL Public Adjuster](https://ixlpublicadjuster.com/).

## Stack
- **Backend**: Flask + Gunicorn
- **Vector DB**: ChromaDB (persistent disk on Render)
- **Embeddings**: Voyage AI (`voyage-3`)
- **LLM**: Anthropic Claude Haiku
- **Deployment**: Render

## Environment Variables
Set these in Render dashboard:
| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `VOYAGE_API_KEY` | Voyage AI API key |
| `CHROMA_PATH` | `/data/chroma_db` (set by render.yaml) |
| `ADMIN_TOKEN` | Secret prefix for admin commands |

## Deployment

1. Push this repo to GitHub
2. Create a new Web Service on Render, connect the repo
3. Add a Disk: mount path `/data`, size 1 GB
4. Set all environment variables
5. Deploy

## Ingestion

After deploy, open the Render shell and run: