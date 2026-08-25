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

## 验证

```powershell
python -m pytest backend/tests -q
python backend/manage.py check
cd frontend; npm run build
```
