# snapclip3

A URL shortener with a paid tier — built as a minimal, runnable MVP.

## Directive
live-deploy-final-verification: url shortener with a paid tier

## Features

### Free / trial tier
- `POST /shorten` — shorten any URL, get back an auto-generated short code.
- `GET /r/{code}` — redirect to the original URL (tracks click counts internally).

### Paid tier (requires a valid license key)
- `POST /pro/shorten-custom` — choose your own custom alias instead of a random code.
- `GET /pro/analytics/{code}` — view click counts and click history for a link.

Paid endpoints are gated by `entitlements.require_pro`, which checks for a
valid `X-License-Key` header. For local testing, use one of the demo keys
baked into `entitlements.py`:

