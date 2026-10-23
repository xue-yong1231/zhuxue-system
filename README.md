# 助学题库

公开可访问的题目学习网站：访客可浏览题目；管理员登录后可在后台录入、编辑、删除题目。

> **异地访问**：本机 `python run.py` 只能自己或局域网访问。  
> 要让「地球另一边」的同学也能用，请按下方 **「公网部署（推荐）」** 把网站发布到云上，会得到一个 `https://...` 链接，发给任何人即可。

## 功能概览

- **科目首页**：语文、数学、英文、物理、化学、生物、电脑、地理、历史
- **学习**：科目内分类（如名句、文学常识）→ 一页一条，含翻译与解释，可翻页
- **练习**：四选一选择题（房主出题：正确答案 + 三个干扰项）
- **登录与权限**：管理员（房主）可进后台；可修改自己的用户名/密码
- **后台管理**：按科目管理学习分类、学习内容、练习题
- **公网可部署**：Gunicorn / Render / Procfile

## 环境要求

- Python 3.10+（推荐 3.11 / 3.12 / 3.13）

## 本地快速启动（仅本机 / 同局域网）

在项目根目录执行：

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python run.py
```

浏览器打开：<http://127.0.0.1:5000>

同局域网访问：`http://你的电脑IP:5000`（需放行防火墙）。  
**不同城市 / 海外用户无法通过局域网 IP 访问**，请使用下面的公网部署。

## 公网部署（推荐）——使用者不在同一局域网也能用

### 方式 A：Render 一键部署（适合长期给二三十人用）

1. 把本项目上传到 **GitHub**（新建仓库 → 上传代码；不要上传 `.env`、`.venv`、`data.db`）
2. 打开 [https://render.com](https://render.com) 注册并登录（可用 GitHub 账号）
3. 选择 **New → Blueprint**，连接刚才的仓库（项目里已有 `render.yaml`）
4. 确认创建 Web Service 后点击应用，等待 Build 完成
5. 部署成功后，控制台会给出公网地址，例如：  
   `https://zhuxue-system.onrender.com`
6. 把该链接发给同学即可（地球另一边也能打开）
7. 使用管理员登录：用户名 `admin`，密码 `admin123`（可在 Render 的 Environment 里改 `ADMIN_PASSWORD`）

**说明：**

- 免费套餐首次打开可能要等十几秒唤醒，属正常现象
- 默认用 SQLite：免费实例重启后数据可能清空。若要长期存题，请在 Render 环境变量中增加 `DATABASE_URL`（可用 [Neon](https://neon.tech) 等免费 PostgreSQL，复制连接串即可）
- 生产环境建议设置 `FORCE_HTTPS=true`（`render.yaml` 已默认开启）

手动创建服务时（不用 Blueprint）也可：

| 项 | 值 |
|----|----|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn "run:app" --bind 0.0.0.0:$PORT` |
| 环境变量 | `SECRET_KEY`、`ADMIN_USERNAME`、`ADMIN_PASSWORD` |

### 方式 B：临时公网隧道（电脑必须一直开着）

适合先快速演示，不适合长期给班级用：

1. 本机先 `python run.py` 跑起来
2. 安装并登录 [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) 或使用 ngrok
3. 把本地 `5000` 端口映射成一个 `https://...` 临时域名发给同学  
4. 你的电脑关机或断网后，外网立刻无法访问

## 默认管理员账号

| 项目 | 默认值 |
|------|--------|
| 用户名 | `admin` |
| 密码 | `admin123` |

本地可在 `.env` 中修改（参考 `.env.example`）。云上请在托管平台的 **Environment Variables** 里配置同名变量。

## 使用说明

1. 打开网站首页「题目广场」公开浏览题目  
2. 点击「登录」，使用管理员账号进入  
3. 「管理后台」→「新建题目」完成录入  
4. 可在后台列表中编辑或删除题目  

## 项目结构

```
助学系统/
├── app/                 # Flask 应用与路由
├── templates/           # 页面模板
├── static/css/          # 样式
├── run.py               # 本地 / WSGI 入口（gunicorn 使用 run:app）
├── Procfile             # Railway 等平台启动命令
├── render.yaml          # Render 一键部署蓝图
├── runtime.txt          # Python 版本提示
├── requirements.txt
├── .env.example
└── README.md
```

## 技术栈

- 后端：Flask + Flask-Login + Flask-SQLAlchemy
- 数据库：本地 SQLite；云上可接 PostgreSQL（`DATABASE_URL`）
- 生产服务：Gunicorn
- 前端：Jinja2 模板 + 自定义 CSS
