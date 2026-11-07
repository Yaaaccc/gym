# 虾健健 24H · 实时人数记录

自动记录「虾健健24H共享自助健身」(南京仙林大学城店,门店号 SZY00087)的实时在店人数、温度、湿度:每 5 分钟一次,存入本仓库,并用 GitHub Pages 展示折线图。

## 网页图表

开启 Pages 后访问:`https://<你的用户名>.github.io/<仓库名>/`

## 工作原理

- GitHub Actions 定时器最快只能 5 分钟一次且经常不准时,所以 `.github/workflows/poll.yml` 每轮任务内由 `poll.py` **连续记录 8 条、每 30 秒一条**(约 4 分钟),结束时**自动触发下一轮**(定时器仅兜底),批与批之间因此偶尔有小空档。
- `poll.py` 请求公开接口 `https://xjj.cpc-api.fitron.vip/v1/user/stores/SZY00087/live-status`(无需登录),把 `{时间, 人数, 温度, 湿度}` 写入:
  - `data/history.jsonl` —— 全部历史(30 秒粒度)
  - `data/recent.json` —— 网页用:今天保留全量,更早的按 5 分钟抽稀,最多 30 天
- `index.html` 用 ECharts 画折线图

## 常见问题

- **手动跑一次**:仓库 → Actions → 记录实时人数 → Run workflow。
- **改记录条数/间隔**:编辑 `poll.py` 里的 `TICKS` 和 `INTERVAL`。
- **换门店**:改 `poll.py` 里的门店号 `SZY00087` 和 `index.html` 里的门店名。
- **数据量**:30 秒粒度一年约 85 万条(80 MB 上下);网页只加载抽稀后的 `recent.json`(约 1 MB),不用担心。

> 仅用于个人观察客流,请求频率很低(每天约 288 次);请勿公开传播数据或高频请求对方接口。
