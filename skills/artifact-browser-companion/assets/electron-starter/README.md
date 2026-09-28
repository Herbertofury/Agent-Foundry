# __APP_NAME__

Generated from the Artifact Browser Companion starter.

This starter proves the local catalog plus real Chromium browser-shell architecture. Replace the sample catalog and tailor the catalog/gallery UI before release.

## Development

```bash
npm install
npm run check
npm start
```

## Standalone packages

```bash
npm run package
npm run make
```

Electron Forge creates platform-appropriate packaged output/distributables. After the first successful install, pin the exact tested dependency versions in `package-lock.json`; do not ship a floating `latest` dependency set.
