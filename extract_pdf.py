import zlib
import re
import sys

# Ensure UTF-8 output even in Windows cmd/PowerShell with cp1252
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pdf_path = r"..\Food_Rescue_Waste_Reduction_Project_Synopsis.pdf"

try:
    with open(pdf_path, "rb") as f:
        data = f.read()

    streams = re.findall(rb"stream[\r\n]+(.*?)[\r\n]+endstream", data, re.DOTALL)
    text_parts = []
    for s in streams:
        try:
            dec = zlib.decompress(s)
            # Check text in TJ or Tj operators
            for match in re.findall(rb"\((.*?)\)", dec):
                try:
                    t = match.decode("utf-8")
                except UnicodeDecodeError:
                    t = match.decode("latin-1", "ignore")
                if len(t) > 2:
                    text_parts.append(t)
        except Exception:
            pass

    full_text = "\n".join(text_parts)
    print(full_text)

    # Also save to a clean text file for reference
    with open("synopsis_extracted.txt", "w", encoding="utf-8") as out:
        out.write(full_text)

except FileNotFoundError:
    print(f"File not found: {pdf_path}")
