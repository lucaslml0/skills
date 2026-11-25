# 新 Agent 签到工作台（xinwen-workbench）标准流程

给一个新子 Agent 接入 luo 的工作台用。四段提示词全文照抄可用，全部已参数化。不要把真实密钥、口令、指纹写进 skill、工单、记忆或聊天记录以外的任何文件。

适用范围：主调度 Rumi + xinwen-workbench（Docker 版）+ 工单池 agent-bus。只做入职，不做业务派单。

## 变量（发提示词前先填好）

| 变量 | 说明 | 例子 |
| --- | --- | --- |
| `<AGENT_ID>` | 工单池、聊天、ROSTER、工位目录统一认的名字，不可改 | `muse-5` |
| `<DISPLAY_NAME>` | 工作台显示名，可与 ID 不同 | `muse-5` |
| `<BOX_HOST>` | 盒子地址，主调度 Rumi 所在的服务器 | `1.94.177.113` |
| `<TAILNET_IP>` | 新人 Tailscale IP，`100.x` | `100.x.x.x` |
| `<SSH_FINGERPRINT>` | 新人公钥 SHA256 指纹 | `SHA256:<...>` |
| `<AVATAR>` | 新人默认形象，当前工作台默认是 Jolly | `Jolly` |

约定：时间一律北京时间（Asia/Shanghai）。工作日指周一至周五。

## 占位符确认规则（每填一个停一次）

六个占位符，一个一个确认，不批量、不猜、不跳过：

1. 每填一个占位符就停下来，把拟用的值、来源、会用在哪里报给 luo，等他确认（或改成另一个值）后再填下一个。
2. 表里的例子（`muse-5`、`1.94.177.113`、`Jolly` 等）只是例子，不是默认值，照样要逐个确认，不能直接当真值用。
3. 顺序：先 `<AGENT_ID>`，再 `<DISPLAY_NAME>`，再 `<BOX_HOST>`；`<TAILNET_IP>` 和 `<SSH_FINGERPRINT>` 是新人发回来的，收到后先报给 luo 确认，再写进 ROSTER / `authorized_keys`；`<AVATAR>` 最后确认。
4. luo 改了某个值，全文统一改成新值，不要留旧值。没确认的占位符不发、不写、不建：提示词、ROSTER、工位、容器里都不许出现未确认的 `<...>`。
5. 一次只问一个占位符，不要一次列六个让 luo 一起确认。

## 分工

- **luo（主人）**：批 Tailscale 设备、把公钥加进盒子 `authorized_keys`、确认入职完成。只在下面标出的点介入。
- **Rumi（主调度，盒子侧）**：建名册行、建工位、把新人加进工作台三处、发四段提示词、逐项验收。没验过不报完成。
- **新人（它自己的设备）**：装 Tailscale、生成自己的密钥对、搭两个轮询、报额度。私钥绝不离开它自己的机器。

三条红线，全程不破：一，不发布、不代发消息、不花钱；二，没有工单，不动仓库；三，账号、密钥、口令绝不写进文件。

## 第 0 步：Rumi 先准备（发提示词 1 之前）

1. 定 `<AGENT_ID>`：先报拟用值给 luo 确认，确认后再定 `<DISPLAY_NAME>`，同样停下来等确认。查 ROSTER 和 `agents/`，确认不重名、不重复。
2. ROSTER 加一行：`<AGENT_ID>`、尾网地址先写 `待补充`、角色 `子 Agent`、状态 `待签到`。
3. 建工位 `agent-bus/agents/<AGENT_ID>/`，放三个文件，初始值照下面写：
   - `status.json`：`{"agent": "<AGENT_ID>", "status": "待签到", "role": "子 Agent", "tailnet": null, "last_seen": null}`
   - `quota.json`：`{"as_of": null, "note": "待签到后填写", "pct": null, "reset": null}`（签到后按固定格式覆盖写，字段不变）
   - `heartbeat.json`：`{"agent": "<AGENT_ID>", "status": "待签到", "last_seen": null}`
4. 把新人加进工作台三处：聊天列表、指挥中心、原理页。三处已动态化（2026-11-25 14:23 落地，`app.py` 的 `chat_agent_list()`）：rumi + muse-1 固定，子 Agent 从 `agents/` 下的工位子文件夹按目录创建时间排，新成员排最后，API 输出加 tailnet；不要手改“5 个 / 6 个”“三位 / 四位”这种硬编码数字。没有工位目录的 Agent 不进聊天列表（muse-2 就是这么退出的）。加完重建容器，验收必须用 `docker exec` 查容器内的文件，宿主机源文件不算数。
5. 本地与盒子同步：本地实际落盘 `~/workspace/shared/agent-bus/`，`/opt/shared` 是软链；盒子同一路径 `/opt/shared/agent-bus/`。两边 ROSTER、工位 md5 对上才算完。

## 提示词 1：加入子 Agent 池（发给新人）

> 请加入主 Muse 的子 Agent 池。先做两件事：
>
> 1. 在你这台设备上装 Tailscale，登录 tailnet，等主人去后台批设备；
> 2. 在你这台设备上生成一对专用的 SSH 密钥（不要复用别人的密钥，私钥不要发出来、不要离开这台机器），把公钥指纹（SHA256）和你的 Tailscale IP（100.x）发给主人。
>
> 做完回一句：Tailscale 已装、指纹和 IP 是什么。

Rumi 收到后做：luo 在 Tailscale 后台批设备；luo 把新人公钥加进盒子 `/root/.ssh/authorized_keys`（新人只发指纹和公钥，私钥不经手）。然后核对：指纹对得上、钥匙没重复、`authorized_keys` 行数对（加一行只多一行）。对不上就停，不要往下走。

## 提示词 2：测 SSH、搭工单轮询（发给新人）

> 盒子这边已接好：钥匙已加、名册已入行、工位已建。现在做两件事：
>
> 1. 测 SSH：`ssh root@<BOX_HOST> 'echo HI'`，能回 `HI` 就是通了；
> 2. 搭每 30 分钟轮询工单箱的定时任务（盒子 `/opt/shared/agent-bus/tasks/`），按调度协议领单、干活、回单；搭好后告诉主人你已就绪。
>
> 调度协议：工单一单一目录 `TYYYYMMDD-NNN`，内含 `task.md`（任务、要求、验收标准）+ `result.md`（结果）。领单时在 `task.md` 写认领者 + 时间，状态改 `doing`；做完把结果写回 `result.md`，状态改 `done`。

验收：新人回 `HI` 的实测结果 + 定时任务已建的证据（任务名、周期、最近一次跑的时间），不是口头说“搭好了”。SSH 不通先查密钥路径：盒子侧 ssh 默认找 `/root/.ssh/`，重建后那里可能没 key 文件，带 `-i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes` 再试一次；仍不通就停下来报 luo，不要反复重试同一条路。

## 提示词 3：搭聊天轮询、报额度（发给新人）

> 盒子这边已接好：钥匙已加、名册已入行、工位已建，工作台聊天列表、指挥中心、原理页也都加上你了，头像先用默认的。
>
> 现在搭两样东西：
>
> 1. 轮询网页消息：只在工作日 09:30–23:00，每 1 分钟读一次工作台网页聊天（`/chat`），看到发给 `<AGENT_ID>` 的消息就回，像其他子 Agent 那样；午休 12:00–13:00 暂停，非工作时段的消息等下一时段处理，不要 24 小时轮询。任务名叫 `<AGENT_ID>-chat-poll-1min`；
> 2. 上报免费额度：每 30 分钟把免费额度剩余百分比和重置时间写到盒子 `/opt/shared/agent-bus/agents/<AGENT_ID>/quota.json`，格式固定如下，不要自创别的字段：`{"as_of": "YYYY-MM-DD HH:MM", "note": "免费额度已用 X%，MM-DD HH:MM重置；附加词元剩 Y", "pct": 剩余百分比, "reset": "MM-DD HH:MM"}`。`pct` 是剩余百分比，`note` 里的已用 X% = 100 - `pct`。
>
> 搭好后告诉主人你已就绪。

额度文件格式（固定这一种，不要自创别的字段）：

```json
{"as_of": "2026-11-22 12:00", "note": "免费额度已用 X%，MM-DD HH:MM重置；附加词元剩 Y", "pct": 剩余百分比, "reset": "MM-DD HH:MM"}
```

- `as_of`：这次上报时间，`YYYY-MM-DD HH:MM`，北京时间。
- `pct`：剩余百分比，数字。`note` 里的已用 X% = 100 - `pct`，别写反。
- `reset`：额度重置时间，`MM-DD HH:MM`。
- `note`：照模板填，已用百分比和重置时间与 `pct` / `reset` 对得上；附加词元没有就写 0。
- 每 30 分钟覆盖写一次到盒子 `/opt/shared/agent-bus/agents/<AGENT_ID>/quota.json`，不要追加。

聊天页额度卡有数才算报上去了，文件写了但页面没数等于没报。

验收：工作日 09:30–23:00 内发一条测试消息给 `<AGENT_ID>`，1 分钟内回上来；午休 12:00–13:00 和非工作时段不轮询、不回（等下一时段）；`quota.json` 30 分钟内有一次新鲜上报，`as_of` 是最近 30 分钟内，`pct` / `reset` / `note` 都不是空，且 `note` 里的已用百分比 = 100 - `pct`。

## 提示词 4：头像（发给新人 / Rumi 自己做）

> 工作台中的 `<AGENT_ID>` 用你的默认形象。

当前工作台默认形象是 Jolly：换成 Jolly，缓存版本号同步升了，页面刷新后头像变了才算完。同样规则：改完重建容器，用容器内文件验收，不要只看宿主机。

## 入职检查清单（缺一项都不算完）

- [ ] 每个占位符都已逐个经 luo 确认，无未确认的 `<...>` 残留
- [ ] 新号改名完成，工单池里认这个名（ID、显示名、ROSTER、工位、聊天三处一致）
- [ ] Tailscale 进网，后台已批，尾网地址已分（ROSTER 和 `status.json` 里不再是 `待补充` / `null`）
- [ ] SSH 密钥是专用的，私钥没离开它自己的机器
- [ ] 指纹对得上，钥匙没重复，`authorized_keys` 行数对
- [ ] 名册 ROSTER 有一行，状态改成 `已签到`
- [ ] 工位目录已建，额度和状态有地方写（`status.json` / `quota.json` / `heartbeat.json` 三个都在）
- [ ] 工作台三处都加上了：聊天列表、指挥中心、原理页（动态取数，不手改总数）
- [ ] 头像换成默认形象（当前为 Jolly），缓存版本号同步升了
- [ ] 聊天轮询只在工作日 09:30–23:00 跑，午休 12:00–13:00 暂停
- [ ] 额度每 30 分钟上报，格式是 `{"as_of", "note", "pct", "reset"}`，聊天页额度卡有数

全部打勾后，Rumi 把 ROSTER 状态改成 `已签到`，`status.json` / `heartbeat.json` 的 `last_seen` 写上首次心跳时间，再向 luo 汇报：谁入职了、每项怎么验的、证据是什么。

## 常见失败

| 现象 | 先查什么 |
| --- | --- |
| SSH 被拒，密钥没变 | 盒子 `authorized_keys` 是否还有这把 key；本机 ssh 默认密钥路径（重建后 `/root/.ssh/` 可能为空），改带 `-i ~/.ssh/id_ed25519` |
| 改名 / 加人后页面还是旧的 | 只改了宿主机源文件、容器没重建；用 `docker exec` 查容器内文件 |
| 总数还是 5 个 / 名单缺人 | 某处还是硬编码数字，改成从 `agents/` 子文件夹动态取 |
| 额度卡没数 | `quota.json` 字段名 / 路径是否照已有那份；上报时间是否在 30 分钟内 |
| 聊天半夜还在回 | 轮询没加工作日 09:30–23:00 + 午休暂停的时间判断 |

## 相关位置

- 工单池：`/opt/shared/agent-bus/`（本地 `~/workspace/shared/agent-bus/`），规则 `DISPATCH.md`，名册 `ROSTER.md`
- 工作台：盒子 `/opt/xinwen-workbench`，Docker 容器，端口只发布到宿主机 `127.0.0.1:18080`
- 主调度规则：Rumi 唯一主调度，luo 只跟 Rumi 对话；先拆工单再派活，验收通过再汇报。
