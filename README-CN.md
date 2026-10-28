# Guxiang 的运动主页

使用 Strava 同步跑步、骑行、徒步和训练记录，只保留新版仪表盘。

## 本地预览

需要 Node.js 20.19+（推荐 22+）、pnpm 8.9 和 Python 3.12。

```powershell
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

默认打开 http://127.0.0.1:5173/，代码修改会自动刷新。首页 `/`、汇总页 `/summary`；旧链接会跳转到新版，经典页面和版本切换已移除。

## 修改个人信息

- `src/static/site-metadata.ts`：昵称、标题、头像、GitHub / Strava 链接。
- `src/components/Dashboard/config.ts`：年、月、周目标（当前是模板参考目标，按自己的计划修改）。
- `src/utils/const.ts`：地图外观；可以通过 `VITE_MAPBOX_TOKEN` 使用自己的 Mapbox 公开访问令牌。

## Strava 本地同步

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-strava.txt
Copy-Item .env.example .env  # 已有 .env 时跳过，避免覆盖凭据
# 在 .env 中填写客户端信息
.\.venv\Scripts\python.exe authorize-strava.py --github-repo g1653/Gux_Worksout
.\sync-strava-local.ps1
```

授权脚本会打开浏览器，请允许读取运动记录（`activity:read_all`）。它将凭据保存在被 Git 忽略的 `.env`，并可同步到指定仓库的 Actions Secrets。同步脚本会自动刷新访问令牌，并保存最新刷新令牌。

`--force` 重新读取全部历史记录；`--timeline-limit 0` 跳过详细时间线；`--skip-temperature-backfill` 跳过天气补全。初次导入可能受 Strava API 速率限制，失败后可再次运行。

## GitHub 自动更新

仓库 Secrets：`STRAVA_CLIENT_ID`、`STRAVA_CLIENT_SECRET`、`STRAVA_CLIENT_REFRESH_TOKEN`，以及已保存的 `STRAVA_ACCESS_TOKEN`。自动同步使用刷新令牌取得有效的访问令牌。

`Sync Strava` 工作流在 `main` 分支每天北京时间 00:00 运行，也可在 Actions 中手动运行。更新数据会提交回仓库。GitHub 的计划任务可能延迟，长期无活动的公开仓库可能暂停计划任务。

Strava 刷新令牌会轮换。工作流将最新令牌以 AES-GCM 加密保存在 `.github/strava-token.enc`，密钥来自 Actions Secret 中的客户端密钥；仓库中没有明文凭据，也不需要额外的 GitHub 管理令牌。重新授权并更新初始刷新令牌 Secret 后，会自动开始新的令牌链。同步失败时也会先保留已轮换的加密令牌。

本地 PowerShell 同步脚本在检测到 GitHub CLI 时，也会自动更新云端 Secrets。若直接运行 Python 同步脚本，请随后执行 `gh secret set --repo g1653/Gux_Worksout --env-file .env`。本地同步前先 `git pull`，以读取云端最新的加密刷新令牌；不要同时运行本地和云端同步。云端更新后的运动数据也会随 `git pull` 出现在本地预览中。

网页部署可使用现有 Vercel 配置或手动运行 `Publish GitHub Pages` 工作流。GitHub Pages 需先在仓库 Settings → Pages 中选择 GitHub Actions；当前本地预览不依赖网站部署。

## 验证

```powershell
pnpm run typecheck
pnpm run test:dashboard
pnpm run build
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_strava*.py'
```

## 致谢与许可

基于 [Neewii_Worksout](https://github.com/Niewei-Yang/Neewii_Worksout)、[workouts_page](https://github.com/ben-29/workouts_page) 和 [running_page](https://github.com/yihong0618/running_page)。保留上游 MIT 许可及 `src/components/Dashboard/LICENSE`。
