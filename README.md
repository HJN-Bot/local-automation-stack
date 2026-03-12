# Local Automation Stack (Dify + n8n)

本仓库用于本地部署：
- Dify（LLM 应用编排）
- n8n（自动化工作流编排）

## 快速启动
```bash
cp .env.example .env
# 按需修改密码和密钥

docker compose up -d
```

- n8n: http://localhost:5678
- Dify: http://localhost:8081

## 停止
```bash
docker compose down
```

## 目录
- `docker-compose.yml`：主编排
- `.env.example`：环境变量模板
- `docs/`：部署/安全/联调说明

## 安全建议
- 修改默认密码
- 不对公网暴露端口（先本机 loopback）
- 将密钥放入 `.env`，不要提交到 git
