from pathlib import Path
from docling.document_converter import DocumentConverter

converter = DocumentConverter()

result = converter.convert(Path("./sample.pdf"))

doc = result.document

print(type(doc))
print("=" * 80)
print(dir(doc))
print("=" * 80)

print("Pages:", len(doc.pages))

print("=" * 80)
print("Document metadata:")
print(getattr(doc, "metadata", None))

print("=" * 80)
print("Tables:")
print(getattr(doc, "tables", None))

print("=" * 80)
print("Pictures:")
print(getattr(doc, "pictures", None))

print("=" * 80)
print("Texts:")
print(getattr(doc, "texts", None))