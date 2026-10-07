# Yeonghun Park — Portfolio

Independent copy of the existing portfolio website.

- Original: https://yh-pa-rk.github.io/
- Project site: https://yh-pa-rk.github.io/portfolio/
- Edit `index.html`, `activities/index.html`, and `cv/index.html` independently after the initial import.
- Photos, styles, scripts, and PDF documents are stored in this repository under `assets/`.

## Publish

In **Settings → Pages**, select **GitHub Actions** as the source. The **Import and deploy portfolio** workflow publishes the site.

The import runs only while `index.html` is absent. It downloads the existing public site, verifies every file against its recorded Git blob hash, changes local URLs to `/portfolio/`, and commits the copied files. Subsequent deployments use this repository's own files.
