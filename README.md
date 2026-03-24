![Logo](https://i.imgur.com/EZD3p9r.png)

## Montage

_Photo evaluation tool for and by Wiki Loves competitions_

Round-based photo evaluation is a crucial step in the "Wiki Loves"
series of photography competitions. Montage provides a configurable
workflow that adapts to the conventions of all groups.

- [montage on Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Montage)
- [montage on Phabricator](https://phabricator.wikimedia.org/project/view/2287/)

## Testing

`pip install tox` into your virtualenv, then `tox`.

## Local Setup Troubleshooting

If you run into issues setting up the project locally, here are some common fixes:

### Python version
- Use Python 3.10 (newer versions like 3.14 may cause dependency issues)

### pkg_resources error
If you see:
ModuleNotFoundError: No module named 'pkg_resources'

Run:
pip install "setuptools<82"

### Missing config file
If you see an error about config.dev.yaml:

Run:
cp config.default.yaml config.dev.yaml

### Database not initialized
If you see errors about missing tables:

- The database has not been initialized yet
- Check project setup steps or scripts to initialize the database

### General tip
- Always activate your virtual environment before running the app:
  source venv/bin/activate