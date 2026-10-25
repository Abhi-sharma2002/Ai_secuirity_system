"""Bounded extraction in a terminable child process. Never execute document content."""
import io
import multiprocessing as mp
import os
import zipfile
from pathlib import PurePosixPath

PARSER_VERSION = 'bounded-v2.1'
MAX_TEXT = 1_000_000
MAX_PAGES = 200


def _extract(raw, suffix):
    blocks, warnings = [], []
    if suffix in {'.txt', '.md'}:
        text = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
        if any((ord(c) < 32 and c not in '\n\t') or 127 <= ord(c) <= 159 for c in text):
            raise ValueError('binary_or_control_content')
        if text.lstrip().startswith(('%PDF-', 'PK\x03\x04', '{\\rtf')):
            raise ValueError('format_mismatch')
        blocks = [{'text': text, 'page': 0, 'section': 'text'}]
    elif suffix == '.pdf':
        from pypdf import PdfReader
        if not raw.startswith(b'%PDF-'):
            raise ValueError('format_mismatch')
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError('encrypted')
        if len(reader.pages) > MAX_PAGES:
            raise ValueError('page_limit')
        total = 0
        for number, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ''
            except Exception:
                text = ''
                warnings.append(f'Page {number}: extraction failed')
            total += len(text)
            if total > MAX_TEXT:
                raise ValueError('text_limit')
            blocks.append({'text': text, 'page': number, 'section': f'page {number}'})
            if not text.strip():
                warnings.append(f'Page {number}: no text extracted; blank or OCR may be required')
    elif suffix == '.docx':
        from docx import Document
        from docx.text.paragraph import Paragraph
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if len(members) > 1000 or sum(i.file_size for i in members) > 30_000_000:
                raise ValueError('docx_expansion_limit')
            for info in members:
                path = PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in info.filename:
                    raise ValueError('unsafe_package_path')
                if info.flag_bits & 1:
                    raise ValueError('encrypted')
                if info.file_size > 5_000_000 or info.file_size / max(info.compress_size, 1) > 200:
                    raise ValueError('docx_expansion_limit')
                if any(x in info.filename.lower() for x in ('vbaproject', 'embeddings/', 'activex/')):
                    raise ValueError('unsupported_embedded_content')
            if 'word/document.xml' not in archive.namelist():
                raise ValueError('format_mismatch')
            xml = archive.read('word/document.xml')
            if any(x in xml for x in (b'<w:ins ', b'<w:del ', b'<w:altChunk', b'<w:object', b'<w:drawing')):
                raise ValueError('unsupported_revisions_or_embedded_content')
        doc = Document(io.BytesIO(raw))
        for i, item in enumerate(doc.iter_inner_content(), 1):
            text = item.text if isinstance(item, Paragraph) else '\n'.join('\t'.join(c.text for c in row.cells) for row in item.rows)
            blocks.append({'text': text, 'page': 0, 'section': f'body {i}'})
        for i, section in enumerate(doc.sections, 1):
            for label, part in [('header', section.header), ('footer', section.footer)]:
                for item in part.iter_inner_content():
                    text = item.text if isinstance(item, Paragraph) else '\n'.join('\t'.join(c.text for c in row.cells) for row in item.rows)
                    blocks.append({'text': text, 'page': 0, 'section': f'{label} {i}'})
    else:
        raise ValueError('unsupported_format')
    if sum(len(b['text']) for b in blocks) > MAX_TEXT:
        raise ValueError('text_limit')
    usable = [b for b in blocks if b['text'].strip()]
    state = 'needs_ocr' if not usable and suffix == '.pdf' else 'needs_review' if warnings else 'parsed'
    if not usable and suffix != '.pdf':
        raise ValueError('empty_document')
    return {'blocks': usable, 'warnings': warnings, 'status': state, 'parser_version': PARSER_VERSION}


def _worker(conn, raw, suffix):
    try:
        if os.name == 'posix':
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
            resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        conn.send({'ok': _extract(raw, suffix)})
    except BaseException as exc:
        safe = str(exc) if isinstance(exc, (ValueError, UnicodeError)) else 'corrupt_or_unsupported'
        conn.send({'error': safe[:160]})
    finally:
        conn.close()


def parse(raw: bytes, suffix: str, timeout=20):
    context = mp.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, raw, suffix), daemon=True)
    process.start()
    child.close()
    try:
        if not parent.poll(timeout):
            raise ValueError('parser_timeout')
        try:
            result = parent.recv()
        except EOFError:
            raise ValueError('parser_process_failed') from None
        if 'error' in result:
            raise ValueError(result['error'])
        from app.models.contracts import ParsedDocument
        return ParsedDocument.model_validate(result['ok']).model_dump()
    finally:
        if process.is_alive():
            process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join()
        parent.close()
