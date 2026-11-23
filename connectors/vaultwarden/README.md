# Vaultwarden connector (shared copy)

Kit 的 Vaultwarden 连接器文件，只分享文件，不分享账号。

- `connector.yaml`、`CONNECTOR.md`、`bin/vaultwarden.py`、`bin/bw-auto.sh`
- 里面没有任何密钥、主密码、session，登录状态也不在里面。
- 用自己的 Vaultwarden 账号：账号由 ren 在网页 vault 里建，服务器已关注册。
- 服务器是 ren 自建在 lucas 上的 Vaultwarden，地址和证书见 CONNECTOR.md 和 bitwarden skill；`bw-auto.sh` / `vaultwarden.py` 里 `/home/hatch`、mihomo `127.0.0.1:7890`、证书路径是 Kit 沙盒的写法，用你自己的路径替换。
- 配套 skill：`skills/bitwarden/SKILL.md`（bw 安装、登录、解锁、全自动方案）。
