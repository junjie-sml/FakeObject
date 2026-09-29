# 协作者安装与操作教程

从一台没有本项目的新电脑开始。首页见 [README](../README.md)，维护者上传仓库及制作 Google Drive 模型包见 [发布教程](PUBLISHING.zh-CN.md)。

## 1. 准备机器

- 安装 64 位 **Python 3.11** 和 Git，重新打开终端。脚本创建独立 venv，不修改全局 Conda/CUDA 环境。
- 实测平台：Windows、RTX 4070 12 GB 显存、32 GB 内存。完整安装建议预留 100 GB，环境、下载缓存和输出也占空间。
- 生成需要 NVIDIA GPU 和兼容驱动，`nvidia-smi` 应能列出 GPU。PyTorch wheel 自带 CUDA runtime，一般无需另装 CUDA Toolkit。
- 检测/Qwen：Torch 2.6.0 + CUDA 12.4；BrushEdit：Torch 2.0.1 + CUDA 11.8。`nvidia-smi` 的 CUDA 数字代表驱动能力，不必与所有 worker 的 CUDA 版本相同。
- Linux/WSL2 提供安装路径，但未做 GPU 端到端验证。macOS/AMD GPU 不支持本配置；需要新版 CUDA 的新架构显卡也不保证兼容。

```powershell
python --version
git --version
nvidia-smi
```

Windows 的 `python` 若不是 3.11，可用 `py -3.11` 代替初始安装/启动命令里的 `python`。Conda 用户可先执行 `conda create -n fakeobject-bootstrap python=3.11` 和 `conda activate fakeobject-bootstrap`，再创建项目环境。

## 2. 克隆项目

```powershell
git clone https://github.com/junjie-sml/FakeObject.git
cd FakeObject
```

任意可写目录均可，不需要维护者的盘符/用户名。私有仓库先邀请 Collaborator，再用 Git Credential Manager 登录；不要把 token 写进 clone URL。

## 3. 选择安装范围

首次建议只装一个后端，确认正常后再添加另一个。

| 命令 | 功能 | 模型下载量约 |
|---|---|---:|
| `python scripts/bootstrap.py --ui-only` | UI、概念设计；无检测/生成 | 0 |
| `python scripts/bootstrap.py` | UI、检测分割；无生成 | 0.79 GiB |
| `python scripts/bootstrap.py --backend brushedit` | UI、检测、BrushEdit | 8.20 GiB |
| `python scripts/bootstrap.py --backend qwen` | UI、检测、Qwen | 31.65 GiB |
| `python scripts/bootstrap.py --full` | 两个编辑后端及检测 | 39.06 GiB |

依赖包、环境和缓存体积另计。第一次安装可能较久，不要同时运行多个安装进程。

```powershell
python scripts/bootstrap.py --backend qwen
```

安装器依次创建 UI 环境、获取固定 commit 的上游代码、安装检测及所选编辑环境、下载固定 revision 的模型、执行依赖/基本功能检查。

**不要从别的电脑复制 `envs/`。** `requirements/constraints/` 保存测试过的依赖版本；`configs/repositories.json` 和 `configs/models.yaml` 分别固定上游代码/模型版本。GPU 环境互相隔离，不要合并。

中断后可重跑同一命令；同 revision 且文件清单齐全的模型会跳过下载。上游 checkout 存在不同 commit 或本地修改时，安装器会停止并保留内容，建议另建项目副本安装，不强制重置。

### 可选：演示照片和类别诊断

上传自己的照片即可使用，不必下载 COCO。需要演示下拉框及 scripted demo 时：

```powershell
envs\orchestrator\Scripts\python.exe scripts/collect_test_images.py --count 50
```

也可安装时加 `--dataset`。它会额外下载 COCO annotation archive，不只有 50 张照片。来源/许可记录在本地 `data/metadata/image_manifest.jsonl`，照片不随 Git 分发。

可选 CLIP 相似度诊断增加约 0.57 GiB，不影响基础生成：

```powershell
envs\orchestrator\Scripts\python.exe scripts/download_models.py --model clip
```

### Linux / WSL2

使用独立 Linux checkout，例如 `~/projects/FakeObject`。解释器需要 Python 3.11、venv 和 pip；不要复用 Windows 虚拟环境目录。

```bash
git clone https://github.com/junjie-sml/FakeObject.git
cd FakeObject
python3.11 scripts/bootstrap.py --backend qwen
python3.11 scripts/launch_app.py
```

默认 `SAM2_BUILD_CUDA=0`，不编译可选 SAM 扩展。远程服务器仍只监听 localhost，可从本机建立 SSH 隧道：

```bash
ssh -L 7860:127.0.0.1:7860 your-user@your-server
```

然后访问本机 `http://127.0.0.1:7860`，无需开放公网端口。

## 4. 启动与关闭

```powershell
python scripts/launch_app.py
```

访问 **http://127.0.0.1:7860**。启动器自动使用 orchestrator 环境。保持终端运行，Ctrl+C 关闭；电脑重启后需重新启动，它不是常驻系统服务。

端口冲突时：

```powershell
$env:FAKE_OBJECT_PORT="7861"
python scripts/launch_app.py
```

Linux：`FAKE_OBJECT_PORT=7861 python3.11 scripts/launch_app.py`。`.env.example` 只是参考，程序不会自动读取 `.env`。

## 5. 完成一次编辑

1. 在 **单图编辑** 上传照片，优先选目标清晰、无遮挡的图片。
2. **目标物体** 输入短名称，如 `杯子` / `cup`、`建筑` / `building`。常见中文词会本地映射成检测词；复杂目标可填英文短语。
3. **编辑要求** 输入完整需求，例如 `把选中的建筑换成风格相近的水晶建筑，修改全部可见立面，保持周围环境。`
4. 选择已安装的 **编辑方案**。界面默认 A；只装 Qwen 时应切到 **B · Grounded-SAM-2 + Qwen 2.1**。
5. 点击 **检测目标**。默认“尽量找全”、置信度 0.15、最多 50 个候选。整座建筑和其中的塔楼属于不同范围，不一定是重复检测。可以补充名称、调低阈值或调整数量；不保证找到全部物体。
6. 点击候选缩略图或使用下拉框选择一个。核对 **当前编辑目标：候选 N** 和绿色蒙版；多候选必须明确选择，每次生成只编辑一个选区。
7. 必要时 **预览蒙版**，在高级设置调整扩张/羽化。内部孔洞默认填充；保留窗洞等真实孔洞时可关闭。前景保护蒙版中的白色区域会保留。
8. 默认 **沿用用户构想**：Qwen 保留原始要求，不强加模板材质。要探索虚构造型，切到 **自主创作/概念探索**，再点击 **生成三个概念** 并选 A/B/C。切换模式会清除旧概念。
9. 首次保持 **预览（已验证）**、seed 42、**严格保持场景** 开启，点击 **开始生成**。Qwen 实测约两分钟，包含模型加载；不要重复提交。
10. 向下滚动至提示词字段下的 **模型原始生成结果** 和 **严格保持场景的结果**。也可在 **结果与历史 → 刷新** 找到保存记录。

BrushEdit 的英文文本编码器对复杂中文理解有限，推荐英文设计及目标描述。当前 BrushEdit 适配器从结构化概念编译目标描述，不等同于 Qwen 直接遵从原始中文编辑要求。

切换候选会清空上一目标的结果。READY 表示计算和保存成功，不保证视觉质量；即使选了完整建筑，模型仍可能只充分改造中央立面，两侧墙面改变不足。

## 6. 输出与复现

输出目录：`data/outputs/YYYY-MM-DD/RUN_ID/`，日期按 UTC。

| 文件 | 内容 |
|---|---|
| `original.png`, `raw_mask.png` | 原图、所选原始蒙版 |
| `processed_mask.png`, `alpha_mask.png`, `mask_overlay.png` | 处理后范围、透明度和预览 |
| `raw_output.png` | 模型原始图 |
| `strict_output.png` | 严格合成图 |
| `final_output.png` | 按严格保持开关选出的最终图 |
| `prompt.txt`, `conditioning_prompt.txt` | 编排提示词及 Qwen 最终输入提示词 |
| `metadata.json`, `logs.txt` | 参数、版本、选区、耗时、诊断/错误 |

`selected_region` 包含编号、类别、边界、像素数和蒙版哈希；Python/JSON index 从 0 开始，界面从 1 开始。同 seed 不保证跨设备、驱动或不同后端逐像素复现。

严格合成保证 **alpha 为 0 的像素** 保持原值。扩张会增加可编辑范围，羽化边界会混合；不能强迫模型充分改造所有内部部分，也不会自动改变选区外的反射和影子。

推理 worker 使用离线模型加载，不调用外部图像 API；安装和数据下载需要联网。私人照片、运行日志、缓存均不应提交到 GitHub。

## 验证与排错

Windows 在仓库根目录执行；Linux 将解释器替换为 `envs/orchestrator/bin/python`。

```powershell
envs\orchestrator\Scripts\python.exe -m pytest -q
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py
envs\orchestrator\Scripts\python.exe scripts/verify_installation.py
```

仅 UI 测试用 `scripts/run_smoke_tests.py --ui-only`。未安装的可选 worker 显示 SKIPPED。

下载演示照片后可执行真实推理检查，会占用 GPU：

```powershell
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py --inference
envs\orchestrator\Scripts\python.exe scripts/first_demo.py --pipeline qwen_image
```

`--inference` 只做真实检测/分割；`first_demo.py` 才生成图片。脚本 demo 明确选择最大框，交互 UI 不会替用户选框。Qwen 尺寸回归需要其环境和 processor 文件：

```powershell
envs\qwen_image\Scripts\python.exe -m unittest discover -s tests -p test_qwen_preprocessing.py -v
```

| 问题 | 处理 |
|---|---|
| 网页打不开 | 检查启动终端；重新运行 launcher，等待显示 URL；检查端口占用 |
| Python 版本不对 | 使用 `py -3.11` / `python3.11`，不要用 3.12+ 构建旧 Torch 环境 |
| `git` 找不到 | 安装 Git，重新打开终端，验证 `git --version` |
| HF 下载 401/403 | 查看对应模型访问条款；有授权后在当前 shell 设置 `HF_TOKEN`，不要写入 Git |
| 下载中断/缺少模型 | 重跑所选 backend 安装，或 `scripts/download_models.py --model qwen` |
| UI 能开，生成不可用 | 是否只装了 UI/检测？或选了没装的后端？补装并切到对应方案 |
| Torch CUDA unavailable | 用相应 worker 的 Python 检查 CUDA，核对驱动和官方 CUDA wheel |
| CUDA OOM | 使用预览、关闭其它 GPU 任务；一次自动降低分辨率重试仍失败则检查 worker 日志 |
| 只改变一部分 | 核对蒙版，简化要求，使用“沿用用户构想”；模型仍有遵从性局限 |
| 概念后修改了目标/提示词 | 重新检测/生成概念，不复用旧 JSON 或蒙版 |
| 高分辨率不稳定 | 768/1024 属实验设置，先用 512 预览 |

报告问题时提供系统、GPU、Python、后端、run ID 和日志末尾；检查日志路径和照片是否包含私人信息。

## 更新项目

停止 GPU 任务/UI，保存本地修改后：

```powershell
git pull --ff-only
python scripts/bootstrap.py --backend qwen
python scripts/launch_app.py
```

若固定上游 commit 变化而旧 checkout 不匹配，保留旧环境并在新的项目目录安装更稳妥。不要随意升级单个 Transformers/Diffusers 包后沿用旧测试结论。

官方参考：[PyTorch CUDA wheel](https://pytorch.org/get-started/previous-versions/)、[Hugging Face 下载](https://huggingface.co/docs/huggingface_hub/guides/download)、[许可证说明](../LICENSE_NOTES.md)。
