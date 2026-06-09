"""Patch .do/app-spec.local.yaml with DATABASE_URL from temp file."""
import pathlib
import re
import sys

spec = pathlib.Path(__file__).resolve().parents[2] / ".do" / "app-spec.local.yaml"
uri = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").strip()
text = spec.read_text(encoding="utf-8")
text = re.sub(
    r"\ndatabases:\n  - name: pg\n    engine: PG\n    version: \"15\"\n    production: false\n",
    "\n",
    text,
)
if "${pg.DATABASE_URL}" in text:
    text = text.replace("value: ${pg.DATABASE_URL}", "value: " + repr(uri)[1:-1])
else:
    text = re.sub(
        r"(- key: DATABASE_URL\n        scope: RUN_TIME\n        type: SECRET\n        value: ).*?\n",
        r"\1" + repr(uri)[1:-1] + "\n",
        text,
        count=1,
    )
spec.write_text(text, encoding="utf-8")
print("patched")
