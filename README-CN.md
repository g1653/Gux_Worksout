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

每次同步都会补齐带轨迹活动的行政区信息：以轨迹起点反查国家、省份和城市，保存到 SQLite 和 `activities.json`。优先采用行政区编码，兼容直辖市及香港；省份地图不再从街道名称猜测省份。查询失败或结果不完整时保留原地点，下次继续补齐。没有定位/轨迹的活动保留未知地点。省份统计表示活动起点所属省级地区，不表示跨省路线途经的全部地区。

单独重试地点补齐：`.\.venv\Scripts\python.exe run_page/backfill_locations.py`。查看详情时间线待拉取数量：`.\.venv\Scripts\python.exe run_page/strava_timeline_sync.py --dry-run`。已获取的时间线按活动 ID 单独保存，后续批次会跳过完成项；缺失的数据不会编造。

## GitHub 自动更新

Garmin Personal API 也在此工作流中同步，密钥放入 `GARMIN_PERSONAL_API_KEY` Secret，区域配置为中国区。缺少 Garmin Secret 时跳过 Garmin，继续更新 Strava。

本地 Garmin 同步：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-garmin.txt
# 在 .env 中设置 GARMIN_PERSONAL_API_KEY 和 GARMIN_REGION=CN
.\.venv\Scripts\python.exe run_page/garmin_personal_sync.py
```

使用 [Garmin 官方 Personal API 客户端](https://github.com/garmin/connect-personal-api-python) 自动换取访问令牌，令牌和原始 FIT 文件仅保存在被 Git 忽略的 `.cache-garmin/`。个人密钥到期后，需在 Garmin Connect 重新生成并更新 `.env` 和 GitHub Secret。

主页使用 **Garmin 为主、Strava 补充**：同一活动的名称、类型、日期、距离、时长、心率和爬升以中国区 Garmin 为准，记录 `metrics_source=garmin`；路线和时间条优先使用原始 FIT。Strava 保留活动身份关联、官方最佳成绩及已有爬坡分段，独有活动也会收录。后续 Strava 刷新不会覆盖 Garmin 指标。FIT 无路线时保留已有可用路线，地点和天气信息持续保存。

跨来源去重要求类型兼容、开始时间相差不超过 90 秒、距离差不超过 5%（短活动允许 100 米），且只有一个匹配项。重复活动记录 `garmin_id`；Garmin 独有活动使用负数内部 ID。以后 Strava 补到同一活动时，会合并为 Strava ID 并保留 Garmin 数据。`source` 表示活动身份来源，`metrics_source` 表示指标来源，两者可能不同。驾驶归为交通，事故检测事件不作为独立运动计数。

Garmin 同步读取全部活动分页，补齐缺失路线的 FIT 文件，并反查保存省份。已完成的 FIT 查询记录在数据库中，避免反复下载无轨迹活动。失败后可重试，已保存的进度不会丢失。同步范围是运动活动，不向主页发布睡眠、体重等健康数据。

Garmin FIT 中记录的速度、心率、功率和海拔会转换为主页时间条，保留暂停和缺失区间；原文件没有的传感器数据不会补造。每次 Garmin 同步后也会补齐符合条件的户外活动天气，兼容小数秒时长，近期活动使用 Open-Meteo 的近期天气接口。天气查询发送起点坐标与日期；室内或缺少定位的活动可能没有天气。

缺失日期或使用 1970 年占位日期的 Garmin 记录会保留在数据库中并标记 `garmin_invalid_date`，暂不导出到主页，以免污染年度统计；在 Garmin 修正日期后再次同步即可恢复显示。

仓库 Secrets：`STRAVA_CLIENT_ID`、`STRAVA_CLIENT_SECRET`、`STRAVA_CLIENT_REFRESH_TOKEN`，以及已保存的 `STRAVA_ACCESS_TOKEN`。自动同步使用刷新令牌取得有效的访问令牌。

`Sync Strava and Garmin` 工作流在 `main` 分支每天北京时间 00:00 运行，也可在 Actions 中手动运行。先读取 Strava 补充数据，再读取 Garmin 并更新主数据；Strava 拉取失败仍继续 Garmin，同步成功的数据会提交回仓库，失败来源仍会在任务中报错。GitHub 的计划任务可能延迟，长期无活动的公开仓库可能暂停计划任务。

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
