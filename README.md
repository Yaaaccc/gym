# 虾健健 24H · 实时人数记录

自动记录「虾健健24H共享自助健身」(南京仙林大学城店,门店号 SZY00087)的实时在店人数、温度、湿度:每 5 分钟一次,存入本仓库,并用 GitHub Pages 展示折线图。

## 网页图表

开启 Pages 后访问:`https://<你的用户名>.github.io/<仓库名>/`

## 工作原理

- `.github/workflows/poll.yml` 每 5 分钟运行一次 `poll.py`
- `poll.py` 请求公开接口 `https://xjj.cpc-api.fitron.vip/v1/user/stores/SZY00087/live-status`(无需登录),把 `{时间, 人数, 温度, 湿度}` 写入:
  - `data/history.jsonl` —— 全部历史
  - `data/recent.json` —— 最近 30 天,网页默认读这个
- `index.html` 用 ECharts 画折线图

## 常见问题

- **更新间隔**:GitHub Actions 定时任务是"尽力而为",实际 5~15 分钟浮动、偶尔跳过一次,不影响看趋势。
- **手动跑一次**:仓库 → Actions → 记录实时人数 → Run workflow。
- **改频率**:编辑 `.github/workflows/poll.yml` 里的 `*/5`(如改成 `*/15`)。
- **换门店**:改 `poll.py` 里的门店号 `SZY00087` 和 `index.html` 里的门店名。
- **数据量**:一年约 10 万条(10 MB 上下),网页默认只加载最近 30 天,不用担心。

> 仅用于个人观察客流,请求频率很低(每天约 288 次);请勿公开传播数据或高频请求对方接口。
