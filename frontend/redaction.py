"""Best-effort display masking; stored evidence and evaluation outputs stay raw."""
import csv
import io
import json
import re

from app.defenses.output_screening import mask_unverified_cards


# Match complete tokens, never leave a usable suffix in the rendered preview.
PROVIDER_KEY = re.compile(
    r'(?<![\w-])(?:nvapi-|sk-or-v1-|sk-proj-|sk-ant-api\d*-|sk-|'
    r'gh[pousr]_|github_pat_|xox[baprs]-|AIza)[A-Za-z0-9_-]{8,}'
)
LABELED_SECRET = re.compile(
    r'(?P<label>\b(?:api[ _-]?key|access[ _-]?token|auth[ _-]?token|'
    r'client[ _-]?secret|password)\b[\"\']?\s*[:=]\s*)'
    r'(?P<value>"[^"\r\n]+"|\'[^\'\r\n]+\'|\[credential hidden\]|[^\s,;<>]+)', re.IGNORECASE
)
EMAIL = re.compile(r'(?<![\w.+-])[A-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@'
                   r'[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,}(?![\w.-])', re.IGNORECASE)
CANARY = re.compile(r'\b(?:[A-Z0-9]+[-_])*CANARY(?:[-_][A-Z0-9]+)+\b', re.IGNORECASE)
SECRET_FIELD = re.compile(r'(?:[a-z0-9]+[ _-])*(?:api[ _-]?key|access[ _-]?token|'
                          r'auth[ _-]?token|client[ _-]?secret|password)', re.IGNORECASE)


def mask_text(text):
    def labeled(match):
        value = match['value']
        quote = value[0] if value[0] in {'"', "'"} else ''
        return match['label'] + quote + '[credential hidden]' + quote
    text = LABELED_SECRET.sub(labeled, text)
    text = PROVIDER_KEY.sub('[credential hidden]', text)
    text = EMAIL.sub('[email hidden]', text)
    text = CANARY.sub('[internal test marker hidden]', text)
    return mask_unverified_cards(text)


def artifact_preview(content, *, filename=''):
    """Mask only text downloads; callers leave binary charts untouched."""
    from frontend.presentation import answer_preview
    text = content.decode('utf-8')
    if filename.endswith('.csv'):
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerows([mask_text(cell) for cell in row] for row in csv.reader(io.StringIO(text)))
        return output.getvalue().encode('utf-8')
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return mask_text(text).encode('utf-8')
    return json.dumps(answer_preview(value), indent=2, ensure_ascii=False).encode('utf-8')
