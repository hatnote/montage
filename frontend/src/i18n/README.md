# Internationalisation

Montage is translated into 20+ languages via [TranslateWiki](https://translatewiki.net).

## How it works

- `en.json` is the source of truth — every new key goes here first
- `qqq.json` contains documentation strings for translators (see [Localisation for developers](https://translatewiki.net/wiki/Translating:Localisation_for_developers) for the convention)
- All other locale files are managed by TranslateWiki and should not be edited manually — TranslateWiki picks up new keys from `en.json` automatically after merge

## When adding a new string

1. Add the key and English text to `en.json`
2. Add a short translator note to `qqq.json` explaining context, parameters, and where the string appears
3. Use `t('yourKey')` in the component — never hardcode English text

Do not edit any locale file other than `en.json` and `qqq.json`.

## For translators

To translate Montage into your language, visit the [Montage project on TranslateWiki](https://translatewiki.net/wiki/Translating:Montage). No GitHub account needed — TranslateWiki handles everything and submits translations back automatically.
Did you find a mistake in the English string? You can propose an improvement on GitHub. Create an issue or submit a PR for simple straightforward fixes. Did you find a mistake in any other language? Please submit the improvement through Translatewiki. 
