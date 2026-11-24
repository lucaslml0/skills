# skills

ren 的 Muse skills 库：可复用的 agent 技能，每个 skill 一个目录，装好就能用。

## Skills

- **opencli-x-post**：用 OpenCLI 驱动已登录 X 的 Chrome 发帖和回复，覆盖单条、多条 thread 和回复，含 Browser Bridge 掉线唤醒办法。
- **bitwarden**：用 Bitwarden CLI（bw）登自建 Vaultwarden，查密码、存密码，含自签证书和沙盒代理的走法。
- **cloud-mail**：用 Cloud Mail REST API 读写 ren 的 mail.520141025.xyz 邮箱、管 @520141025.xyz 地址，账号密码从 Vaultwarden lucas 组织 mail 集合读，含 token 401 抖动重试和浏览器 UA 的走法。附 `bin/cloud-mail.py` helper。

## Connectors

- **vaultwarden**（`connectors/vaultwarden/`）：Kit 的 Vaultwarden 连接器文件（connector 文档 + `vaultwarden.py` + `bw-auto.sh` 全自动解锁包装器）。只分享文件，不分享账号：用自己的 Vaultwarden 账号登录，账号由 ren 在网页 vault 里建；`/home/hatch`、mihomo 代理、自签证书路径是 Kit 沙盒的写法，按自己的环境替换。配套 skill 是 `skills/bitwarden/`。

## 目录结构

```
.
├── README.md
└── skills/
    ├── opencli-x-post/
    │   └── SKILL.md
    ├── bitwarden/
    │   └── SKILL.md
    └── cloud-mail/
        ├── SKILL.md
        └── bin/
            └── cloud-mail.py
```

## 安装

```sh
npx skills add lucaslml0/skills --skill opencli-x-post
npx skills add lucaslml0/skills --skill bitwarden
npx skills add lucaslml0/skills --skill cloud-mail
```

也可以直接把 `skills/<名字>/` 目录复制到 agent 的 skills 目录下使用。
