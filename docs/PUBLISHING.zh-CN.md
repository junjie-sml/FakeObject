# 维护者发布教程：GitHub + 可选 Google Drive

目标仓库：<https://github.com/junjie-sml/FakeObject>。

## 分发结构

**GitHub 保存代码、配置、依赖版本、文档和测试；模型默认从官方来源下载。** 完整生成模型约 39 GiB，不需要塞进 Git。Google Drive 仅作为有必要且符合上游条款的团队离线镜像。

| 内容 | 位置 | 提交 Git？ |
|---|---|---|
| 自有源代码、模板、配置、文档、测试 | `src/`, `skills/`, `configs/`, `docs/`, `tests/` | 是 |
| 安装输入、测试版本约束 | `requirements/` | 是 |
| 固定上游代码/模型 revision | `configs/repositories.json`, `configs/models.yaml` | 是 |
| 实际上游仓库 | `third_party/` | 否，安装时获取 |
| 虚拟环境和本机 freeze 记录 | `envs/` | 否，每台机器重建 |
| 模型权重 | `models/` | 否，官方下载或受控离线包 |
| 上传照片、输出、缓存、诊断数据 | `data/`, `logs/` | 否 |
| 离线包、构建文件 | `dist/`, `build/` | 否 |
| Token、密码、本机环境变量 | `.env*` | 否，只有 `.env.example` 可提交 |

GitHub 普通 Git 文件有 100 MiB 上限，网页上传限制更小；这里额外将源仓库单文件上限定为 10 MiB，避免误提交。参见 [GitHub 大文件说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。不需要为官方可下载权重启用 Git LFS。

## 1. 发布前准备

安装 Git，确认在 GitHub 上拥有目标仓库写权限。可以用 Git Credential Manager 的正常浏览器登录流程或 GitHub CLI `gh auth login`；不要将 token 放到远程地址或 README。

```powershell
git --version
git config --global user.name
git config --global user.email
git ls-remote https://github.com/junjie-sml/FakeObject.git
```

若 name/email 尚未设置，在**当前仓库**执行 `git config user.name "你的名称"`、`git config user.email "你的 GitHub 提交邮箱"`。可使用 GitHub 提供的 noreply 邮箱。

目标为空仓库时，`ls-remote` 成功但不打印分支是正常的。如果已有提交，先 clone 并将源文件合并进去，不要用强制推送覆盖。

根 `LICENSE` 按维护者选择使用 MIT；它只覆盖项目自有代码。第三方代码、模型和照片保留各自条款，详见 [许可证说明](../LICENSE_NOTES.md)。

## 2. 初始化并审核待上传内容

首次在项目根目录执行；已经有 `.git` 时不用重复 init：

```powershell
git init -b main
git remote add origin https://github.com/junjie-sml/FakeObject.git
```

若 origin 已存在，先 `git remote -v` 核对，不要无条件覆盖。确保 `.gitignore` 已就位后再暂存：

```powershell
git add .
git status --short
envs\orchestrator\Scripts\python.exe scripts/check_release.py
git diff --cached --stat
```

`check_release.py` 审核的是 **Git index 中将被提交的内容**：禁止运行时目录、超大文件及常见凭据格式；不会扫描被忽略的私人照片或模型目录。它是辅助检查，发布前仍需检查自己新增的配置/文档。

已被 Git 跟踪的文件不会因新加 `.gitignore` 自动消失。误暂存但尚未提交的文件可用 `git rm --cached 路径` 从 index 移除，保留磁盘原文件；再次审核。若已推送真实凭据，应立即撤销该凭据，单纯删除最新文件不能使旧凭据失效。

## 3. 验证、提交和推送

```powershell
envs\orchestrator\Scripts\python.exe -m pytest -q
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py --ui-only
git commit -m "Prepare reproducible FakeObject workbench for collaborators"
git push -u origin main
```

首次可能触发 GitHub 登录。若收到仓库不存在/权限错误，核对 URL 和当前登录账号，并在 GitHub 接受邀请；不要反复覆盖 remote 或使用 `--force`。

推送后检查：

1. GitHub 首页能正确展示 README，安装教程、许可和架构链接可打开。
2. 仓库中没有 `models/`, `envs/`, `data/`, `logs/`，没有个人上传照片。
3. **Actions → CPU tests** 的 Windows/Linux CPU 检查结果；它不运行 GPU 模型，也不能证明 GPU 推理质量。
4. 在另一个目录 clone，一台新机器按 [安装教程](INSTALLATION.zh-CN.md) 配置并上传自己的图片测试。

可在 About 中填写：`Local fictional-object editing workbench with Grounded-SAM, BrushEdit and Qwen-Image.`；建议 topics：`computer-vision`, `image-editing`, `gradio`, `research`。是否公开仓库由维护者在 GitHub 设置，本流程不会自动改变可见性。

## 4. 邀请合作者与交付

私有仓库：Settings → Collaborators → 添加 GitHub 用户，让对方接受邀请。向合作者发送：

- 仓库地址和 `docs/INSTALLATION.zh-CN.md`。
- 推荐安装命令，如 `python scripts/bootstrap.py --backend qwen`。
- 已验证硬件、预览分辨率，以及没有验证的系统/显卡范围。
- 如果提供离线包，再附仅团队可读的 Drive 文件夹链接及 SHA256 文件。

共享仓库不会自动授予模型/照片的其他使用许可。优先让合作者各自从官方模型页下载，不把上游受限权重重新公开托管。

## 5. 可选：Google Drive 模型离线包

目前不必使用 Drive，安装器已经能从官方固定 revision 下载。仅在团队网络受限或重复下载困难时考虑镜像，并先核对具体上游条款是否允许该分发。这里的 MIT 不授权你再分发所有模型。

### 维护者制作包

确认 `models/` 中已有完整模型和下载回执。在项目根目录执行：

```powershell
envs\orchestrator\Scripts\python.exe scripts/package_models.py --model grounding_dino
envs\orchestrator\Scripts\python.exe scripts/package_models.py --model sam2
envs\orchestrator\Scripts\python.exe scripts/package_models.py --model qwen
# 按需制作：--model brushedit 或 --model clip
```

输出在 `dist/model-bundles/`：每个模型一个 `模型名-revision前12位.zip` 和同名 `.zip.sha256`。使用 ZIP64、不压缩权重，避免大量无效压缩开销；Qwen 包约 31 GiB，需要额外足够磁盘空间。

只打包下载回执中列出的文件、回执和许可说明，不包含环境、缓存、照片或推理记录。上游仓库内列出的许可证/模型卡随模型文件清单保留；包内的项目许可说明不能代替模型自身条款。若某模型条款需要额外文档，分发时一并提供。

在 Drive 网页中新建团队文件夹，上传所需 `.zip` 与 `.sha256`，按指定协作者邮箱授予只读访问。记录模型 source/revision、来源模型卡、制包日期和包大小。不要默认公开分享链接；Google 账号需要足够剩余存储空间。

### 合作者导入

先 clone GitHub，安装 UI 环境，再将模型包及 `.sha256` 下载到本机，例如项目根目录下已忽略的 `dist/incoming/`。

```powershell
python scripts/bootstrap.py --ui-only
# 将下列文件名替换为收到的实际名称
envs\orchestrator\Scripts\python.exe scripts/package_models.py --verify dist/incoming/qwen-REVISION.zip
python -m zipfile -e dist/incoming/qwen-REVISION.zip .
```

对检测模型/SAM 包同样操作。只解压来源可信、校验通过的团队包。归档内部已含 `models/...` 路径，解压到 **项目根目录**，不要解压到 `models/` 内造成双层目录。

然后正常安装环境：

```powershell
python scripts/bootstrap.py --backend qwen
python scripts/launch_app.py
```

下载器检查回执 revision 和全部文件存在后跳过这些权重；缺失文件会重新下载。包不包含 Python、Git 仓库和 pip wheel，因此这只解决模型下载，**不等于完全离线安装整套软件**。

## 6. 后续版本与发布

每次更新先停止相关任务，修改代码/文档，运行测试，`git add`，再执行 release audit 后提交：

```powershell
git add .
envs\orchestrator\Scripts\python.exe scripts/check_release.py
git diff --cached --stat
git commit -m "Describe the concrete change"
git push
```

准备正式版本时更新 CHANGELOG，待 CI 完成后可打 tag：

```powershell
git tag -a v0.2.0 -m "Collaborator setup and source release"
git push origin v0.2.0
```

在 GitHub Releases 页面选择这个 tag，写明变化、测试范围、兼容性和安装链接。不要把未经许可的模型包拖入公开 Release。需要修改上游模型/依赖版本时，应同步配置中的固定 revision、约束文件及实测记录。
