# 当前状态

> **最高优先级要求：绝对不要再出现 Linux GUI 启动路径引用未导入名称而崩溃的问题。** 本次问题是 `../ok-script/ok/gui/start/StartTab.py` 使用 `sys.platform` 却遗漏 `import sys`；今后新增或解决冲突后的平台分支必须检查其全部名称导入，并实际验证 Linux GUI 能完成主窗口初始化。

本文是 `ok-wuthering-waves` 与 `../ok-script` 自有改动的唯一当前状态说明。

我们的目的，是在尽量不改动上游原始项目的前提下实现自有 Feature。上游原始代码、业务流程和文档默认保持不变；只有 Feature 无法实现时才做最小必要代码适配。上游原始文档不属于整理范围，不应修改；只整理我们新增的文档，无用内容直接删除，仍有价值的内容合并到本文。

## 需求与实现

- [x] Linux wlroots 支持
  - [x] 发现并选择可用 Wayland socket，捕获完整 `wl_output`
  - [x] 支持鼠标、键盘、点击、长按、滚动和滑动
  - [x] 保留 Windows 原有实现；Linux 隔离 Windows 依赖并可正常关闭
  - [x] Linux 隐藏或禁用管理员启动、EXE/进程/HWND、计划任务、全局热键、录制、静音和系统主题等 Windows 专属能力
- [x] 低频重要操作记录
  - [x] 按任务会话写入 JSONL，并为重要节点保存必要的前后截图
  - [x] 普通高频操作只写轻量元数据，不保存截图
- [x] 非 PyAppify 启动时不做更新检查
  - [x] 源码直接启动（Linux 常规用法）没有启动器，`PYAPPIFY_VERSION` 为空
  - [x] 此时隐藏更新控件并只留一条 INFO/WARNING，不再抛 `get_version_list` RuntimeError
- [x] 本地只使用 uv
  - [x] 当前目录以 `pyproject.toml` 和 `uv.lock` 统一管理环境与命令
  - [x] `../ok-script` 作为 editable 本地依赖
  - [x] editable 构建访问 pypi.org 必须成功（见下方「本地 uv / ok-script editable」）

## 上游同步原则

当前已同步到（2026-09-07）：`ok-wuthering-waves` v3.6.7、`ok-script` v2.0.6。

```text
同步目标
├─ 使用两个项目各自权威 upstream 的最新稳定标签
├─ 排除 alpha、beta、rc 等预发布版本
└─ 将本地 Feature 提交 rebase 到稳定标签，不跟随未发布开发提交

处理原则
├─ 每次 rebase 前，先将我们的全部自有改动 squash 成尽量少的提交
├─ 先完整保护已提交、已暂存、未暂存和未跟踪内容
├─ 冲突优先保留上游当前实现，只合入 Linux 与重要操作记录所需改动
├─ 同步后检查提交范围、残留冲突并运行相关验证
└─ 未经明确要求不 push；需要改写远端时只使用 force-with-lease
```

## 本地 uv / ok-script editable

> **最高优先级要求：editable `ok-script` 构建访问 `https://pypi.org` 必须成功，不得用跳过 PyPI / 写死版本掩盖网络或 SSL 故障。**

```text
原因
├─ 上游 ok-script/setup.py 会请求 https://pypi.org/pypi/ok-script/json 读取最新版本并自增
└─ uv editable 构建在隔离环境执行该逻辑；HTTPS/SSL 失败会直接让 uv run/sync 失败

固定做法
├─ 本机到 pypi.org:443 的 HTTPS 必须可用（curl / python requests 均 200）
├─ pyproject.toml: [tool.uv.extra-build-dependencies] ok-script = ["requests", "packaging"]
│  （隔离 build 环境缺包会导致 import 失败，看起来像构建坏了）
├─ ../ok-script/get_pypi_latest_version.py: 对 SSLError/ConnectionError/Timeout 重试
│  （处理偶发 SSLEOFError: UNEXPECTED_EOF_WHILE_READING，而不是跳过 PyPI）
└─ 验证：uv cache clean ok-script 后 uv sync / uv run 仍能完成 metadata 构建

故障排查（access 失败时先修网络，禁止改成离线假版本）
├─ curl -I https://pypi.org/pypi/ok-script/json
├─ .venv/bin/python -c "import requests; print(requests.get('https://pypi.org/pypi/ok-script/json',timeout=30).status_code)"
├─ 检查代理/MITM/防火墙/DNS；必要时修复系统 CA，而不是绕过 PyPI
└─ 禁止再用 OK_SCRIPT_BUILD_VERSION 或 0.0.0.dev0 作为本地开发的默认逃逸路径
```

```text
pyproject.toml 只在上游文件基础上追加两段
├─ [tool.uv.sources] ok-script = { path = "../ok-script", editable = true }
├─ [tool.uv.extra-build-dependencies] ok-script = ["requests", "packaging"]
└─ 其余（name/version/build-system/optional-dependencies/依赖列表）保持上游原样
   不要再自行加 onnxocr-ppocrv4、gitpython 等依赖：
   ok-script[ocr] 已经带 onnxocr-ppocrv5，两者装进同一个 onnxocr/ 目录，
   卸载 ppocrv4 会顺手删掉 ppocrv5 的文件，表现为
   ModuleNotFoundError: No module named 'onnxocr.onnx_paddleocr'
   修复：uv sync --reinstall-package onnxocr-ppocrv5
```

## PyAppify 更新检查

```text
问题
├─ pyappify.get_version_list 永远可 import，但只有 PyAppify 启动器启动时才可用
├─ 启动器通过 PYAPPIFY_VERSION 环境变量声明自己；源码启动时为 None
└─ 旧的判断只看 callable(get_version_list)，于是 About 页开机自动检查必然报
   RuntimeError: PyAppify does not support checking for updates for pyappify_version: None

做法
├─ ../ok-script/ok/util/pyappify_support.py: supports_update_check(module)
│  ├─ 无 get_version_list -> False
│  ├─ 模块没有 pyappify_version 属性（测试替身）-> True，保持上游旧行为
│  └─ 有该属性则解析版本，低于 1.2.2 或为空 -> False
├─ 调用方：ok/ui/qt/about/AboutTab.py 与 ok/ui/web/app.py 的 update_supported
├─ update_card 为 None 时 MainWindow._schedule_update_check 自然不再排期
└─ 回归测试：../ok-script/tests/test_pyappify_support.py
```

## Linux 不支持且不计划实现

```text
非 wlroots Linux
├─ GNOME Mutter、KDE KWin 等不提供所需 wlroots 协议的环境
└─ Portal、PipeWire 或其他替代捕获后端

窗口级能力
├─ 单窗口捕获、裁剪、前置和尺寸管理
└─ 多显示器输出选择
```
