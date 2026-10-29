"""Execute the public research notebook in this interpreter and render offline HTML."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

from denguepharma_analytics.storage import require_published


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    project = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--data-dir', type=Path, default=project / 'analytics/data')
    parser.add_argument('--output', type=Path, required=True,
                        help='New output directory; existing directories are refused.')
    parser.add_argument('--quarto', type=Path, default=project / 'analytics/.tools/bin/quarto.cmd')
    args = parser.parse_args()
    root, output = args.data_dir.resolve(), args.output.resolve()
    manifest = require_published(root, args.run)
    source = project / 'notebooks/03_pesquisa_reprodutivel.ipynb'
    notebook = nbformat.read(source, as_version=4)
    nbformat.validate(notebook)
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ANALYTICS_DATA_DIR=str(root), DENGUEPHARMA_RUN_ID=args.run)
    with tempfile.TemporaryDirectory(prefix='analytics-notebook-') as temporary:
        kernel = Path(temporary) / 'analytics-research'
        kernel.mkdir()
        (kernel / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'Analytics research', 'language': 'python',
        }), encoding='utf-8')
        manager = KernelManager(kernel_name='analytics-research',
            kernel_spec_manager=KernelSpecManager(kernel_dirs=[temporary]))
        try:
            NotebookClient(notebook, km=manager, timeout=180,
                resources={'metadata': {'path': str(project)}}).execute(env=env)
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    nbformat.validate(notebook)
    executed = output / 'pesquisa.ipynb'
    nbformat.write(notebook, executed)
    subprocess.run([str(args.quarto.resolve()), 'render', str(executed),
        '--to', 'html', '--no-execute', '--embed-resources',
        '--metadata', 'title:DenguePharma Analytics - pesquisa reproduzivel'], check=True)
    assert require_published(root, args.run) == manifest, 'Published run changed'
    html = output / 'pesquisa.html'
    if not html.is_file():
        raise RuntimeError('HTML_NOT_RENDERED')
    record = {
        'schema_version': 1, 'run_id': args.run,
        'input_hash': manifest['input_hash'], 'analysis_code_hash': manifest['code_hash'],
        'source_notebook_sha256': sha(source), 'runner_sha256': sha(Path(__file__)),
        'published_manifest_sha256': sha(root / 'runs' / args.run / 'manifest.json'),
        'python_version': sys.version.split()[0],
        'dependencies': {name: importlib.metadata.version(name) for name in
            ['denguepharma-analytics', 'nbclient', 'nbformat', 'ipykernel', 'pandas', 'duckdb']},
        'quarto_version': subprocess.check_output([str(args.quarto.resolve()), '--version'], text=True).strip(),
        'tables': {name: {'rows': meta['rows'], 'logical_hash': meta['logical_hash']}
            for name, meta in manifest['tables'].items() if meta['public']},
        'artifacts': {path.name: sha(path) for path in [executed, html]},
        'notice': 'Public metadata only. No collection, curation or clinical inference.',
    }
    (output / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run_id': args.run, 'output': str(output), 'status': 'verified'}))


if __name__ == '__main__':
    main()
