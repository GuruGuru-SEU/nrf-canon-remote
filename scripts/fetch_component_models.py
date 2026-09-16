"""Verify archived JLC assets, downloading only missing files with pinned hashes."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

folder = Path(__file__).resolve().parent.parent / 'reference/component-models'
sources = json.loads((folder / 'sources.json').read_text())
for code, source in sources.items():
    for suffix, record in source['files'].items():
        path = folder / f'{code}.{suffix}'
        data = path.read_bytes() if path.exists() else urlopen(
            Request(record['url'], headers={'User-Agent': 'nrf-canon-remote-model-fetcher/1.0'}),
            timeout=30,
        ).read()
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise RuntimeError(f'{path.name}: source checksum changed; inspect before replacing')
        if not path.exists():
            path.write_bytes(data)
        print(f'OK {path.name}')
