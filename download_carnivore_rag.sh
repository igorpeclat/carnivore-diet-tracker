#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Carnivore RAG Downloader (direct sources only)
# - Downloads public PDFs (curl/wget friendly)
# - Organizes into rag/ folders
# - Generates manifest.json
# - Writes MANUAL_SOURCES.md for paywalled/login sources (Scribd)
# ============================================================

ROOT_DIR="${1:-rag}"
mkdir -p "$ROOT_DIR"
cd "$ROOT_DIR"

mkdir -p science recipes manual

# Prefer curl; fallback to wget
download() {
  local url="$1"
  local out="$2"

  echo "==> Downloading: $url"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --retry 3 --retry-delay 2 -o "$out" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$out" "$url"
  else
    echo "ERROR: Need curl or wget installed." >&2
    exit 1
  fi
}

# --------------------------
# Direct-download sources
# --------------------------

# 1) MDPI: Assessing the Nutrient Composition of a Carnivore Diet (PDF)
MDPI_URL="https://www.mdpi.com/2072-6643/17/1/140/pdf"
MDPI_OUT="science/carnivore_nutrient_composition_mdpi.pdf"
download "$MDPI_URL" "$MDPI_OUT"

# 2) Bookey CDN: The Carnivore Code Cookbook (PDF) - mixed content, needs filtering
BOOKEY_URL="https://cdn.bookey.app/files/pdf/book/en/the-carnivore-code-cookbook.pdf"
BOOKEY_OUT="recipes/carnivore_code_cookbook_bookey.pdf"
download "$BOOKEY_URL" "$BOOKEY_OUT"

# --------------------------
# Manual sources (login / paywall)
# --------------------------
cat > manual/MANUAL_SOURCES.md <<'MD'
# Manual sources (login / paywall)

Essas fontes foram mencionadas antes, mas **não têm download direto via curl/wget**
sem autenticação/sessão e/ou permissões de download.

Use **download manual** (se você tiver direito/acesso) e coloque os PDFs baixados aqui em `rag/manual/`.

## Links
- SAMPLE Carnivore Diet Meal Plan (Scribd):
  https://pt.scribd.com/document/737678415/SAMPLE-Carnivore-Diet-Meal-Plan-pdf

- Carnivore Diet PDF (Scribd):
  https://www.scribd.com/document/887599259/Carnivore-Diet-PDF

- Dieta Carnívora Fácil — Dr. Jon Marins (Scribd):
  https://pt.scribd.com/document/927129489/Dieta-Carni-Vora-Fa-Cil-Dr-Jon-Marins
MD

cd ..

# --------------------------
# manifest.json (simple, RAG-friendly)
# --------------------------
cat > rag_manifest.json <<'JSON'
{
  "corpus_name": "carnivore_rag",
  "version": "1.0",
  "files": [
    {
      "path": "rag/science/carnivore_nutrient_composition_mdpi.pdf",
      "type": "science",
      "topic": ["micronutrients", "nutrition"],
      "strictness": "neutral",
      "source": "MDPI (direct PDF)",
      "requires_filtering": false,
      "notes": "Paper-style technical reference; good for nutrient-related responses."
    },
    {
      "path": "rag/recipes/carnivore_code_cookbook_bookey.pdf",
      "type": "recipes",
      "topic": ["cooking", "recipes"],
      "strictness": "mixed",
      "source": "Bookey CDN (direct PDF)",
      "requires_filtering": true,
      "notes": "May contain non-strict ingredients; apply carnivore rules filtering at ingestion time."
    }
  ],
  "manual_sources": [
    {
      "path": "rag/manual/",
      "file": "MANUAL_SOURCES.md",
      "notes": "Contains sources that require login/paywall; download manually if you have access."
    }
  ]
}
JSON

echo ""
echo "✅ Done."
echo "Folder: $(pwd)/rag"
echo "Direct PDFs downloaded:"
echo " - rag/$MDPI_OUT"
echo " - rag/$BOOKEY_OUT"
echo ""
echo "Manual sources list:"
echo " - rag/manual/MANUAL_SOURCES.md"
echo ""
echo "Manifest:"
echo " - rag_manifest.json"
