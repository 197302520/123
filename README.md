# 社会网络教学平台

这是一个 Django/DRF + Vue 3 的单仓库教学平台基础。学生访问公开课程、案例和实验 API 无需登录；课程内容仅由 Django 管理后台中的教师（`is_staff=True`）维护。

## 本地开发

后端需要 Python 3.10+：

```powershell
python -m pip install -e "backend[dev]"
python backend/manage.py migrate
python backend/manage.py seed_learning_content
python backend/manage.py runserver
```

前端需要 Node 20+：

```powershell
cd frontend
npm install
npm run dev
```

Vite 将 `/api` 代理到 `http://localhost:8000`。复制根目录 `.env.example` 为 `.env` 后，可用 `docker compose up --build` 启动 PostgreSQL、Redis、Django web/worker 和 Vue 开发服务器。

生产 Compose、HTTPS、迁移/种子、14 天备份恢复、监控、两小时清理、可选 ML worker 与 90 人容量演练见 [`docs/deployment.md`](docs/deployment.md)。

## 验证

```powershell
python -m pytest backend/tests -q
python backend/manage.py check
cd frontend; npm run build
```

也可在仓库根目录运行 `python scripts/verify_release.py` 执行带超时的完整发布验证；本机没有 Docker 时，`python scripts/validate_compose.py` 会直接校验生产 Compose 合同。
