import ast, pathlib
code = pathlib.Path('app/core/qa_engine.py').read_text(encoding='utf-8')
ast.parse(code)
print('syntax ok')
