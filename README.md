# Guxiang Workouts

A personal Strava activity dashboard for Guxiang. This fork keeps the modern dashboard only, with activity history, maps, summary charts, training goals and detailed timelines.

See [中文使用说明](README-CN.md) for local preview, profile customization, Strava authorization and daily GitHub Actions sync.

- Home: `/`
- Summary: `/summary`
- Local preview: `pnpm dev --host 127.0.0.1`
- Sync: `python run_page/strava_sync.py` (credentials from ignored `.env` or environment variables)
- Scheduled sync: daily at 16:00 UTC, on `main`.

Credentials are stored in GitHub Actions Secrets and local `.env`, never frontend code. Refreshed tokens in CI are persisted using AES-GCM encryption keyed by the client secret.

Built on [Neewii_Worksout](https://github.com/Niewei-Yang/Neewii_Worksout), [workouts_page](https://github.com/ben-29/workouts_page) and [running_page](https://github.com/yihong0618/running_page). Original MIT licenses are retained.
