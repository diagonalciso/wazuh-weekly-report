#!/bin/bash
# Render HTML -> PDF using whatever engine is present.
# Usage: render_pdf.sh <input.html> <output.pdf>
# Exit 0 = PDF produced; exit 2 = no engine found (caller may fall back to HTML).
set -uo pipefail
HTML="$1"; PDF="$2"

try() { command -v "$1" >/dev/null 2>&1; }

# 1. Chromium / Chrome family (--print-to-pdf). NOTE: snap chromium can only
#    write under $HOME, so PDF path must be in the home dir on those systems.
for bin in chromium chromium-browser google-chrome google-chrome-stable chrome; do
    if try "$bin"; then
        "$bin" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
            --print-to-pdf="$PDF" "file://$HTML" >/dev/null 2>&1
        [ -s "$PDF" ] && { echo "rendered via $bin"; exit 0; }
    fi
done

# 2. wkhtmltopdf
if try wkhtmltopdf; then
    wkhtmltopdf --quiet "$HTML" "$PDF" >/dev/null 2>&1
    [ -s "$PDF" ] && { echo "rendered via wkhtmltopdf"; exit 0; }
fi

# 3. weasyprint (python)
if try weasyprint; then
    weasyprint "$HTML" "$PDF" >/dev/null 2>&1
    [ -s "$PDF" ] && { echo "rendered via weasyprint"; exit 0; }
fi

# 4. libreoffice headless
if try libreoffice || try soffice; then
    SOFF=$(command -v libreoffice || command -v soffice)
    "$SOFF" --headless --convert-to pdf --outdir "$(dirname "$PDF")" "$HTML" >/dev/null 2>&1
    OUT="$(dirname "$PDF")/$(basename "${HTML%.html}").pdf"
    [ -s "$OUT" ] && { mv -f "$OUT" "$PDF"; echo "rendered via libreoffice"; exit 0; }
fi

echo "no PDF engine found" >&2
exit 2
