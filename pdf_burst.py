import sys
from pypdf import PdfReader, PdfWriter
from pathlib import Path

def pdf_burst(input_path):
    reader = PdfReader(input_path)
    stem = Path(input_path).stem
    out_dir = Path(input_path).parent / "burst"
    out_dir.mkdir(exist_ok=True)

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        out_path = out_dir / f"{stem}_page_{i:03d}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"Wrote {out_path}")

    print(f"Successfully burst {input_path} into {len(reader.pages)} pages!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: pdf_burst.py <input.pdf>")
        sys.exit(1)
    pdf_burst(sys.argv[1])