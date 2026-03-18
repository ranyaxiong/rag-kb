from pathlib import Path
p = Path('app/core/qa_engine.py')
s = p.read_text(encoding='utf-8')
pattern_r = (
    "[\n                                f\"(doc_id={d.metadata.get('document_id')[:8]}, file={d.metadata.get('filename')}, dist={s:.4f})\"\n                                for d, s in top_r\n                            ]"
)
pattern_g = (
    "[\n                                f\"(doc_id={d.metadata.get('document_id')[:8]}, file={d.metadata.get('filename')}, dist={s:.4f})\"\n                                for d, s in top_g\n                            ]"
)
safe_snippet = (
    "[\n                                (lambda _d,_s: f\"(doc_id={{{{(((_d.metadata.get('document_id'))[:8]) if isinstance(_d.metadata.get('document_id'), str) else 'unknown')}}}}, "
    "file={{{{_d.metadata.get('filename', 'Unknown')}}}}, dist={{{{_s:.4f}}}})\")(_d=d, _s=s)\n                                for d, s in top_{which}\n                            ]"
)
changed = False
if pattern_r in s:
    s = s.replace(pattern_r, safe_snippet.format(which='r'))
    changed = True
if pattern_g in s:
    s = s.replace(pattern_g, safe_snippet.format(which='g'))
    changed = True
if changed:
    p.write_text(s, encoding='utf-8')
    print('Patched qa_engine.py safe logging.')
else:
    print('Patterns not found; no changes made.')
