"""Lokalny eksport wyniku File Inspector bez nadpisywania raportów."""

import html
import json
from pathlib import Path
import uuid


def export_file_report(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    documents = {
        "json": text,
        "txt": "PRESTIGE TECH\nby Dominik Wasilak\n" + text,
        "html": ('<!doctype html><html lang="pl"><meta charset="utf-8">'
                 '<title>File Inspector — PRESTIGE TECH</title><h1>PRESTIGE TECH</h1>'
                 '<p>by Dominik Wasilak</p><pre>' + html.escape(text) + '</pre></html>'),
    }
    base = directory / ("report-" + uuid.uuid4().hex)
    created = []
    try:
        for extension, content in documents.items():
            path = base.with_suffix("." + extension)
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return [str(path) for path in created]
