# AI Auto Trading Bot

Rule-based Upbit trading bot with a static realized-performance dashboard.

## Dashboard

`generate_dashboard.py` reads `trade_history.json` and writes a single static page to `docs/index.html`.

```bash
python3 generate_dashboard.py
```

The dashboard intentionally shows only completed sell-side trades. Open positions, balances, and secrets are not published.

To expose the page through GitHub Pages:

1. Open the repository settings in GitHub.
2. Go to `Pages`.
3. Set the source to `Deploy from a branch`.
4. Select branch `main` and folder `/docs`.

The bot regenerates `docs/index.html` after each completed sell. Publishing updates to GitHub Pages still requires pushing the changed `docs/index.html` file to the repository.

## Local test

```bash
docker compose run --rm coin-bot python -m unittest test_logic.py
```
