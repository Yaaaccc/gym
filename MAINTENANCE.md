# 维护手册(给维护者和 AI Agent)

> **新 Agent 接手必读**:先完整读完本文件再动手。
> **最重要的一条:`data/history.jsonl` 是唯一完整档案,任何操作不得覆盖/清空/重写它,只允许追加。** 网页用的 `data/recent.json` 是派生物,坏了随时能从档案重建,不用慌。

## 项目是什么

自动记录「虾健健24H共享自助健身」南京仙林大学城店(门店号 SZY00087)的实时在店人数/温度/湿度,30 秒粒度,网页折线图展示。仓库公开,纯免费方案(GitHub Actions + GitHub Pages)。

- 网页:<https://yaaaccc.github.io/gym/>
- 仓库:<https://github.com/Yaaaccc/gym>
- 数据源(公开接口,**无需登录**):
  `GET https://xjj.cpc-api.fitron.vip/v1/user/stores/SZY00087/live-status`
  返回:`{"code":0,"data":{"occupancyCount":43,"environment":{"temperature":19.4,"humidity":64.4,"pressure":0}}}`
- 本机 gh CLI 已登录 GitHub 账号 **Yaaaccc**(repo + workflow 权限)

## 架构 / 数据流

```
GitHub Actions 每 ~4.5 分钟一轮(poll.yml):
  1. 任务内连续记录 8 条、每 30 秒一条(GitHub 定时器最快 5 分钟,靠任务内循环实现 30 秒粒度)
  2. 追加写入 data/history.jsonl(完整档案,只追加)
  3. 从 history.jsonl 重建 data/recent.json(幂等:今天全量;更早的按 5 分钟时间桶抽稀;保留 30 天)
  4. 提交推送(GITHUB_TOKEN;⚠️ 这种推送不会触发 deploy.yml)
  5. 结束时自动触发下一轮 poll(链条自续)+ 显式触发 deploy.yml 刷新网页
deploy.yml:部署网页到 GitHub Pages + 自检(超 20 分钟无新记录 → 自动重新点燃链条)
```

## 文件一览

| 文件 | 作用 |
|---|---|
| `poll.py` | 采集脚本(任务内 8 条 × 30 秒;`TICKS`/`INTERVAL` 可调;`build_recent()` 负责重建 recent.json) |
| `.github/workflows/poll.yml` | 记录链条(自续 + 触发重试 3 次 + schedule 兜底) |
| `.github/workflows/deploy.yml` | 网页部署(每 30 分钟兜底)+ 断链自愈检查 |
| `index.html` | 网页(ECharts;拥挤度阈值在 `CROWD` 数组;<30 舒适 / 30-50 轻微 / 50-80 中等 / 80+ 极度) |
| `data/history.jsonl` | **完整档案,只追加,勿覆盖** |
| `data/recent.json` | 派生摘要(每次运行自动重建,可随时手动重建) |
| `README.md` | 使用说明 |

## 常见故障与处理(按症状查)

### 症状 1:数据停更新(最常见)
99% 是链条断了。已见过的断因(均为 GitHub 平台偶发,与代码无关):触发接口偶发 HTTP 500(已内置重试 3 次)、运行器被平台回收取消。

诊断:
```bash
gh run list --repo Yaaaccc/gym --workflow poll.yml --limit 5
```
(最近 1 小时应有约 13 轮,绝大多数 success;有 failure 或长时间无新轮 = 断链)

修复(重新点燃链条,约 5 分钟后数据恢复):
```bash
gh workflow run poll.yml --repo Yaaaccc/gym --ref main
```

### 症状 2:网页数据滞后于仓库
原理:网页是静态快照,**只有部署成功才更新**;机器人的提交不会触发部署(见已知坑 1),靠 poll 结束时显式触发部署 + deploy 每 30 分钟兜底。

手动刷新部署:
```bash
gh workflow run deploy.yml --repo Yaaaccc/gym --ref main
```

### 症状 3:recent.json 数据异常/丢失
它是派生物,**链条正常运行时每轮自动重建**(从 history.jsonl),一般等 5 分钟自愈。需立即手动重建时:
```bash
curl -s "https://yaaaccc.github.io/gym/data/history.jsonl" -o data/history.jsonl
python -c "import sys; sys.path.insert(0,'.'); import poll, json; json.dump(poll.build_recent(), open('data/recent.json','w',encoding='utf-8'), ensure_ascii=False)"
```
然后按下方流程上传 `data/recent.json`。若 history.jsonl 本身缺数据:无法补录(过去的时刻采不回来),空档属正常。

### 症状 4:GitHub 定时器(schedule)不触发
cron 是"尽力而为",可能延迟几十分钟甚至不触发——**这是已知且无法修复的**,链条自续才是主要机制,schedule 仅为兜底。deploy 的 */30 同理。

## 上传代码的标准流程

本地直连 github.com 时断时续(国内网络),两种方式按序尝试:

**A. git 正常推送(优先):**
```bash
git pull --rebase origin main
# ⚠️ 机器人会不断提交 data/,变基时切勿用旧 data/ 覆盖远端新数据;
# 如提示冲突/落后,先 git fetch 再 git reset --soft origin/main,
# 然后 git checkout HEAD -- data/ (保留远端新数据),重新提交
git add -A && git commit -m "..." && git push
```

**B. 直连失败,用 API 逐文件上传(用户令牌的提交会正常触发 deploy):**
```bash
SHA=$(gh api "repos/Yaaaccc/gym/contents/<路径>" --jq .sha)
gh api -X PUT "repos/Yaaaccc/gym/contents/<路径>" -f message="说明" -f content=$(base64 -w0 <文件>) -f branch=main -f sha=$SHA
```
⚠️ 文件较大时 `-f content=...` 会报 `Argument list too long`,改用 stdin:
```bash
python -c "import base64,json; body={'message':'说明','content':base64.b64encode(open('<文件>','rb').read()).decode(),'branch':'main','sha':'<SHA>'}; open('_body.json','w').write(json.dumps(body))"
gh api -X PUT "repos/Yaaaccc/gym/contents/<路径>" --input _body.json
rm _body.json
```

## 已知坑(前人踩过,勿重蹈)

1. **GITHUB_TOKEN 的 push 不会触发 on:push 工作流**(workflow_dispatch 例外)——所以数据提交后,poll.yml 会显式 `gh workflow run deploy.yml`。若删掉该步骤,网页将不再自动更新。
2. **recent.json 的抽稀必须"每次从档案重建"**,绝不能在上一次输出上继续抽稀——会叠加衰减(2000→200→20→1,2026-11-08 踩过,当天网页多日对比失效)。
3. **抽稀规则用时间桶**(`(t-dayStart)//300` 每桶留第一条),不要用"分钟数字 %5"——30 秒批次落点漂移,会保留稀疏不均的点(同日踩过)。
4. `gh api -X PUT -f content=<大base64>` 超 argv 上限 → 用 `--input _body.json`(见上)。
5. GitHub 免费运行器偶发被回收/取消(shutdown signal)——链条断了直接重新点燃,无需排查代码。
6. 所有 ts 均为北京时间(+08:00)字符串;跨时区环境判断"今天"用 `ts[:10]` 与北京日期比较,或用 `Date('YYYY-MM-DDT00:00:00+08:00')`。
7. index.html 的 ECharts 从 CDN(bootcdn)加载,若线上图表空白先查 CDN 是否可达。
8. 改完 index.html 部署后,务必验证线上生效:
   `curl -s https://yaaaccc.github.io/gym/ | grep -c <新代码特征词>`

## 数据现状备注

- 已知空档(断链导致,**无法补录**):2026-11-07 08:01–09:52;2026-11-08 18:44–21:00。
- 拥挤度阈值(用户定义):<30 舒适;30-50 轻微拥挤;50-80 中等拥挤;80+ 极度拥挤。改 `index.html` 的 `CROWD` 数组生效。
- 多日对比视图最多显示最近 7 天(改 `index.html` 的 `buildMultiSeries` 里 `slice(-7)`)。
- 历史平均·预测线:需至少 1 个既往日数据;数据越多越准。

## 给 Agent 的维护检查清单

1. `gh run list --repo Yaaaccc/gym --workflow poll.yml --limit 5` — 链条活着吗?
2. 断了 → `gh workflow run poll.yml --repo Yaaaccc/gym --ref main`
3. 网页落后 → `gh workflow run deploy.yml --repo Yaaaccc/gym --ref main`
4. 改完代码 → 按"上传代码的标准流程"发布,并验证线上生效(见已知坑 8)
5. 检查数据健康:`curl -s https://yaaaccc.github.io/gym/data/recent.json | tail -c 300` — 最新 ts 距现在应在 10 分钟内
