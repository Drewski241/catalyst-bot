# Changelog

All notable changes to CATalyst are recorded here.

This changelog was added during public-readiness work. Earlier release notes may
be reconstructed from GitHub Releases and tag history where available.

## v1.2.5

- Fixed offer replacement after sweep fills so confirmed fills clear stale DB-only
  retry backoff before rebuilding the ladder.
- Reduced noisy proactive coin top-up attempts when a low-spare tier has no
  usable split source.
- Stabilized startup inner spread display while market data and dynamic spread
  inputs are still calibrating.
- Fixed the CAT deposit baseline timestamp path flagged by Code Quality.

## v1.2.4

- Current public-readiness baseline.
- Source version metadata aligned with the latest tagged release.

## v1.2.1

- Desktop application baseline with Flask, PyWebView, SQLite WAL, and Sage wallet integration.
