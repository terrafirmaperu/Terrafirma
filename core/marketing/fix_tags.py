from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'templates' / 'marketing'
TAG_OPEN = chr(60) + 'div'
TAG_CLOSE = chr(60) + '/' + 'motion'
TAG_CLOSE2 = chr(60) + '/' + 'div'
BAD_OPEN = chr(60) + 'motion'

for path in ROOT.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    if BAD_OPEN not in text and TAG_CLOSE not in text:
        continue
    text = text.replace(BAD_OPEN, TAG_OPEN)
    text = text.replace(TAG_CLOSE, TAG_CLOSE2)
    path.write_text(text, encoding='utf-8')
    print('fixed', path.name)
