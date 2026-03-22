# OpenClaw 一键回滚 + 一键验证

适用仓库：`HJN-Bot/openclaw-config-kit`（private）

## 1) 一键回滚
默认回滚到最新 `~/.openclaw/openclaw.json.bak-*`：

```bash
bash scripts/rollback-openclaw-config.sh
```

指定某个备份：

```bash
bash scripts/rollback-openclaw-config.sh ~/.openclaw/openclaw.json.bak-2026-03-19-pre-ab-hardening
```

回滚脚本会：
- 先备份当前配置为 `openclaw.json.pre-rollback-<UTC时间>`
- 覆盖 `~/.openclaw/openclaw.json`
- 尝试重启 gateway 并输出状态

---

## 2) 一键验证

```bash
bash scripts/verify-openclaw-health.sh
```

验证内容：
- `openclaw status --deep`
- `openclaw security audit --deep`
- `openclaw gateway status`
- 关键端口监听（8080 / 18789 / 18800 / 5678）

---

## 3) 推荐验证通过标准
- Gateway: running + RPC probe ok
- Discord: channel state OK
- Security audit: 不出现 `open groupPolicy with elevated/runtime/fs exposed`
- Dashboard: `:8080` 监听正常

---

## 4) 常见问题
- 若提示 `missing scope: operator.read`：
  - 属于 deep probe 权限提示，不影响主服务运行；可继续以 `openclaw gateway status` + Discord 冒烟为准。
- 若 dashboard-web.service fail：

```bash
systemctl --user reset-failed dashboard-web.service
systemctl --user restart dashboard-web.service
systemctl --user status dashboard-web.service --no-pager -l
```
