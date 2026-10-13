"""Explicit non-kernel fallback for trusted S01 Python-only notebooks.

The normal runner remains run_s01_notebooks.py. This fallback does not validate
Jupyter startup, magics, widgets or kernel isolation, and labels its outputs so.
"""
import argparse
import ast
import contextlib
import io
import os
from pathlib import Path

import IPython.display
from IPython.core.formatters import DisplayFormatter
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def execute(path):
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    namespace = {'__name__': '__main__'}
    formatter = DisplayFormatter()
    count = 0
    for cell in notebook.cells:
        if cell.cell_type != 'code':
            continue
        count += 1
        print(f'Executing {path.name}: cell {count}', flush=True)
        cell.outputs = []
        cell.metadata.pop('execution', None)
        output = io.StringIO()

        def display(*values, **kwargs):
            for value in values:
                data, metadata = formatter.format(value)
                cell.outputs.append(nbformat.v4.new_output('display_data', data=data, metadata=metadata))

        original_display = IPython.display.display
        IPython.display.display = display
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                tree = ast.parse(cell.source)
                expression = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
                exec(compile(tree, '<S01 sequential notebook cell>', 'exec'), namespace)
                if expression is not None:
                    value = eval(compile(ast.Expression(expression.value), '<S01 sequential expression>', 'eval'), namespace)
                    if value is not None:
                        data, metadata = formatter.format(value)
                        cell.outputs.append(nbformat.v4.new_output('execute_result', data=data,
                                            metadata=metadata, execution_count=count))
        finally:
            IPython.display.display = original_display
        if output.getvalue():
            cell.outputs.append(nbformat.v4.new_output('stream', name='stdout', text=output.getvalue()))
        cell.execution_count = count
    notebook.metadata.execution_method = (
        'Explicit sequential Python AST/exec/eval in project environment; NOT a Jupyter-kernel run. '
        'Rich display captured with IPython DisplayFormatter; no kernel isolation/magic/widget validation.')
    notebook.metadata.kernelspec = {'name': 'python3', 'display_name': 'Python 3 (non-kernel fallback)', 'language': 'python'}
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    print(f'Passed {path.name}: {count} code cells; explicit non-kernel execution', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notebooks', nargs='+', choices=['00', '01', '02', '03', '04'], default=['00', '01', '02', '03', '04'])
    args = parser.parse_args()
    os.chdir(ROOT)
    for number in sorted(set(args.notebooks)):
        paths = list((ROOT / 'notebooks').glob(f'{number}_S01_*.ipynb'))
        assert len(paths) == 1, f'Expected exactly one notebook {number}'
        execute(paths[0])
