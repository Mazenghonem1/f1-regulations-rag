"""pdftotext -layout wrapper. Verified present at /usr/local/bin/pdftotext
(docs/RECON.md) -- layout mode is what keeps label columns and Article
numbering parseable."""
import subprocess


def extract_text(pdf_path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
