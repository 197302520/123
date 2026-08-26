# 生产部署与运维

## 上线前

复制 `.env.production.example` 为仅部署主机可读的环境文件，替换数据库密码、Django 密钥、域名与 CSRF HTTPS 来源。教师密码应使用密码管理器生成的长随机口令；Django 已默认使用内存硬化的 scrypt 哈希，并启用 12 位最低长度、常见密码、纯数字和用户属性相似度校验，同时按来源 IP 限制后台登录尝试。

在受控发布窗口执行：

```sh
docker compose --env-file .env.production -f compose.prod.yaml build
docker compose --env-file .env.production -f compose.prod.yaml run --rm web python manage.py migrate --noinput
docker compose --env-file .env.production -f compose.prod.yaml run --rm web python manage.py seed_learning_content
docker compose --env-file .env.production -f compose.prod.yaml up -d postgres redis web worker beat frontend
```

生产 Web 使用 Gunicorn；Celery worker 与 beat 分离，避免重复执行两小时清理任务。测试环境默认同步执行，生产 Compose 明确关闭 eager 模式并使用 Redis 队列。Web 镜像构建时已执行 `collectstatic`，WhiteNoise 提供带哈希的 Django Admin 静态资源，内层 Nginx 将 `/static/` 与 `/admin/` 一并转发到 Web 容器。可选 GCN/GAT 镜像使用 `--profile ml` 构建；未启用时相关算法明确返回能力不可用，不伪造结果。

运行中任务持有可续约租约：worker 每 `RUN_HEARTBEAT_SECONDS` 续约，beat 只回收已过 `RUN_LEASE_SECONDS` 的租约。丢失的 pending 投递在 `PENDING_DELIVERY_SECONDS` 后以原 task ID 有界重投，worker 的原子状态声明阻止重复执行。公开取消对 pending 任务只撤销投递；对 running 任务使用 Celery `terminate=True` 与 `SIGTERM`，让 worker 子进程可被安全替换。不要配置 `SIGKILL`；无论终止与完成如何竞争，数据库只允许 `running`→终态的条件写入，已取消/已失败不会被迟到结果覆盖。

## HTTPS、域名与境内部署

只在反向代理或负载均衡器终止 TLS 后开放服务，将公网 443 转发到本机 `127.0.0.1:8080`。外层代理必须删除客户端自带的转发头，并写入经验证的 `Host`、`X-Forwarded-Proto=https`、单一合法 IP 的 `X-Real-IP` 和规范化的 `X-Forwarded-For`；内层 Nginx 原样传递这些值，不用容器间 HTTP 或代理容器 IP 覆盖它们。Compose 的 frontend 只绑定 loopback，web 仅 expose 而不映射端口；不得让客户端或同机不可信服务绕过外层代理。若改变代理层数，必须同步调整 `DJANGO_NUM_PROXIES`。确认域名、证书自动续期、HSTS、可信来源与安全 Cookie 后再开放教师后台。若服务器或 CDN 节点位于中国境内，应在上线前向服务提供商确认 ICP 备案/公安备案及单位数据合规要求；境外部署仍需核对学校的数据分类与跨境政策。

## 数据保留、备份与恢复

匿名运行输入、参数与结果的 `expires_at` 固定为创建后两小时，Celery beat 每分钟删除到期记录。浏览器实验历史只在 IndexedDB 中，不创建学生账户或持久画像。

数据库备份使用 `ops` profile：

```sh
docker compose --env-file .env.production -f compose.prod.yaml run --rm backup
```

脚本生成 PostgreSQL custom-format dump，并删除 14 天前的同类备份。应将 `/backups` 对应卷复制到加密的异机存储，每季度抽样恢复。恢复前先停止 web/worker/beat、另做一次当前库备份并确认目标文件。恢复脚本只接受规范路径仍位于 `/backups` 且名称匹配的普通 dump 文件，并以 PostgreSQL 单事务执行 clean/restore；任一步失败会整体回滚：

```sh
docker compose --env-file .env.production -f compose.prod.yaml stop web worker beat
docker compose --env-file .env.production -f compose.prod.yaml run --rm --entrypoint /bin/sh backup /ops/restore.sh /backups/social-network-YYYYMMDDTHHMMSSZ.dump
docker compose --env-file .env.production -f compose.prod.yaml up -d web worker beat
```

## 监控与故障处置

监控容器健康、HTTP 5xx/429、P95 请求时间、Celery pending/running/failed/cancelled 数、租约过期和 pending 重投次数、Redis 内存、PostgreSQL 连接/磁盘、备份时间与两小时清理滞后。日志只记录请求元数据、运行 ID、算法和状态，不记录上传内容、图正文或企业文本。告警后按运行 ID 排查；失败结果只暴露结构化安全错误。

## 验证与容量演练

无 Docker 的开发机运行 `python scripts/verify_release.py`；每条命令有独立超时，Compose 由 YAML 合同脚本验证。上线到隔离环境后执行 90 名匿名学生、最多 30 个并发作业的有界演练：

```sh
python scripts/load_test.py --base-url https://sna.example.edu.cn --students 90 --max-jobs 30 --deadline 120
```

演练前临时配置足以容纳 90 次标准算法请求的限额；完成后恢复课堂策略。验收条件是 90 个真实度中心性任务均得到非空表格，队列并发不超过 30，且无 5xx、无到期数据残留。
