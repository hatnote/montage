![Logo](https://i.imgur.com/EZD3p9r.png)

## Montage

[![CI](https://github.com/hatnote/montage/actions/workflows/pr.yml/badge.svg)](https://github.com/hatnote/montage/actions/workflows/pr.yml)

_Photo evaluation tool for and by Wiki Loves competitions_

Round-based photo evaluation is a crucial step in the "Wiki Loves"
series of photography competitions. Montage provides a configurable
workflow that adapts to the conventions of all groups.

- [montage on Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Montage)
- [montage on Phabricator](https://phabricator.wikimedia.org/project/view/2287/)

## Development

See [dev.md](dev.md) for full setup instructions, including OAuth configuration and pre-commit hooks.

Quick start:

```bash
git clone git@github.com:hatnote/montage.git && cd montage
make start                                        # backend (Docker)
cd frontend && npm install && npm run dev          # frontend (new terminal)
```

## Testing

```bash
docker build -t montage-ci -f dockerfile .
docker run --rm -v $(pwd):/app -e PYTHONPATH=/app montage-ci \
  python -m pytest montage/tests/test_web_basic.py -v --tb=short
```

## Deployment

See [deployment.md](deployment.md) for Toolforge deployment instructions.