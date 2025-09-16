from pathlib import Path
p=Path('app/core/qa_engine.py')
s=p.read_text(encoding='utf-8')
s2=s.replace('qa_chain({"query": question})','qa_chain.invoke({"query": question})')
if s2!=s:
    p.write_text(s2, encoding='utf-8')
    print('Replaced qa_chain call with invoke.')
else:
    print('No change needed.')
