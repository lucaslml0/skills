# skills

ren 的 Muse skills 库：可复用的 agent 技能，每个 skill 一个目录，装好就能用。

## Skills

- **opencli-x-post**：用 OpenCLI 驱动已登录 X 的 Chrome 发帖和回复，覆盖单条、多条 thread 和回复，含 Browser Bridge 掉线唤醒办法。
- **bitwarden**：用 Bitwarden CLI（bw）登自建 Vaultwarden，查密码、存密码，含自签证书和沙盒代理的走法。

## 目录结构

```
.
├── README.md
└── skills/
    ├── opencli-x-post/
    │   └── SKILL.md
    └── bitwarden/
        └── SKILL.md
```

## 安装

```sh
npx skills add lucaslml0/skills --skill opencli-x-post
npx skills add lucaslml0/skills --skill bitwarden
```

也可以直接把 `skills/<名字>/` 目录复制到 agent 的 skills 目录下使用。
