# 食品经营许可管理系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-brightgreen.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v0.26.10.10-orange.svg)]()

基于 Flask + Docker 的食品经营许可管理系统，支持多品类证件的集中管理和批量下载。

---

## ✨ 功能特性

### 📋 品类管理
- **品类拓扑浏览** - 以商品品类为顶层结构组织所有证件信息
- **模糊搜索** - 支持按商品名、规格、厂家、证件编号、批次号等维度搜索
- **一键打包下载** - 搜索商品后批量下载该商品的全套4种证件（营业执照、食品经营许可证、第三方检验报告、厂检报告）

### 📄 证件管理
| 证件类型 | 功能说明 |
|---------|---------|
| 营业执照 | 厂家级证件，支持模糊搜索和有效期预警 |
| 食品经营许可证 | 厂家级证件，支持模糊搜索和有效期预警 |
| 第三方检验报告 | 支持PDF/图片上传，自动计算365天有效期 |
| 厂检报告 | 简化录入流程，仅需生产日期（无需保质期） |

### 🔍 智能预警
- 证书到期前 30 天自动预警
- 支持自定义预警阈值
- 预警看板实时展示过期风险

### 👥 权限控制
- 5 级细粒度权限管理
- 支持编辑、删除、导入、查看用户等独立控制

### 📅 日期输入优化
- 三段式日期输入（年/月/日），提升录入效率
- 输入4位年份后自动跳转到月份字段
- 第三方检验报告默认日期智能填充

---

## 🚀 快速开始

### 环境要求
- Docker & Docker Compose
- 或 Python 3.10+ 本地运行

### Docker 一键部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/mobinewan/file-manager.git
cd file-manager

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

访问 http://localhost:12321

### 本地开发部署

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python run.py init-db

# 启动服务
python run.py run
```

### 首次登录
- 默认账号：`admin`
- 默认密码：`admin123`

---

## 📁 项目结构

```
file-manager/
├── app/                      # 应用主目录
│   ├── auth/                 # 认证模块（登录、权限）
│   ├── bulk_import/          # 批量导入功能
│   ├── bundle_download/      # 打包下载功能
│   ├── category/             # 品类管理
│   ├── certificate/          # 证书编辑
│   ├── excel_import/         # Excel 导入
│   ├── manufacturer/         # 厂家管理
│   ├── models/               # 数据模型
│   ├── product/              # 商品管理
│   ├── reminder/             # 到期预警
│   ├── search/               # 全局搜索
│   ├── static/               # 静态资源（CSS/JS）
│   ├── templates/            # 前端模板
│   └── utils/                # 工具函数
├── instance/                 # 数据库文件（自动创建）
├── uploads/                  # 文件上传目录（自动创建）
├── docker-compose.yml        # Docker 编排配置
├── Dockerfile                # Docker 镜像构建
├── requirements.txt          # Python 依赖
└── run.py                    # 应用入口
```

---

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SECRET_KEY` | `dev-secret-key-change-me` | Flask 密钥 |
| `PORT` | `12321` | 服务端口 |
| `DB_PATH` | `instance/app.db` | 数据库路径 |
| `UPLOAD_FOLDER` | `uploads` | 文件上传目录 |
| `DEFAULT_THRESHOLD_DAYS` | `30` | 到期预警天数 |
| `ADMIN_USERNAME` | `admin` | 管理员账号 |
| `ADMIN_PASSWORD` | `admin123` | 管理员密码 |

---

## 📖 使用说明

### 添加厂家
1. 导航到 **厂家管理** 页面
2. 点击 **新建厂家**，填写厂家名称、统一社会信用代码等信息
3. 厂家创建后可添加营业执照和食品经营许可证

### 添加商品
1. 进入具体厂家详情页
2. 点击 **新建商品**，填写商品名称、品类、规格型号等
3. 商品创建后可上传：
   - 营业执照（系统自动关联）
   - 食品经营许可证（系统自动关联）
   - 第三方检验报告（支持 PDF/图片）
   - 厂检报告（仅需生产日期）

### 品类浏览
1. 导航到 **品类** 页面查看所有品类
2. 进入具体品类可查看该品类下所有商品的证件信息
3. 支持模糊搜索，可跨商品、厂家、证件编号搜索

### 打包下载
1. 导航到 **打包下载** 页面
2. 输入商品名称进行搜索
3. 勾选需要下载的证件（可筛选特定生产日期）
4. 点击 **生成 ZIP 打包下载** 一键导出全套证件

### 到期预警
1. 导航到 **预警中心** 查看所有即将过期的证件
2. 可自定义预警阈值（默认30天）
3. 点击跳转到具体证书详情页进行更新

---

## 📝 版本历史

### v0.26.10.10（当前版本）
- ✅ 新增品类拓扑结构浏览
- ✅ 新增打包下载功能（支持批量导出4种证件）
- ✅ 品类详情页增加模糊搜索
- ✅ 日期输入改为三段式（年/月/日）自动跳转
- ✅ 厂检报告简化（无需保质期和有效期）
- ✅ 第三方检验报告默认日期智能填充
- ✅ 厂检报告不在预警系统中显示
- ✅ 用户权限细化为5个独立控制点
- ✅ 新增证书编辑功能

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📬 联系方式

- GitHub: [@mobinewan](https://github.com/mobinewan)
- 项目地址: https://github.com/mobinewan/file-manager

---

<div align="center">

Made with ❤️ by [mobinewan](https://github.com/mobinewan)

</div>
