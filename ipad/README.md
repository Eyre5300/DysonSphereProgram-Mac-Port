触控开发分支：Pro27 键鼠基线保留；独立 DSP Touch 首期的操作、构建与测试范围见 [TOUCH.txt](TOUCH.txt)。

# iPad Pro 迁移：开发者预览

本目录提供原创的平台适配、构建和验证工具。使用者必须自行准备已购买的 Windows 游戏、Unity 工具链和自己的 Apple 签名。仓库不包含游戏源码、资产、SDK 对象、App/IPA、测试存档或蓝图。

当前目标是 **iPad Pro + 实体键盘鼠标**。mini 支持已停止，不提供 mini 分辨率预设或低画质替代包。Pro27 已完成限定综合自动测试，本次结果见 [验证记录](VALIDATION.md)。自动输入不能证明真实 Universal Control、USB 或蓝牙手感；也没有宣称 Windows 全功能/逐像素等价。

这是一套开发者复现入口，**不是向导式一键 iPad 安装器**。公开入口已做源码准备、编译和本地资源检查；从空白新机器到最终安装的全过程仍需验证。Mac 的 `start.command` 不会自动完成 iPad 部署。

## 架构

用户自己的 Windows 文件 → 本仓库的 Mac 资源恢复项目 → iPad 平台适配 → Mac ARM64 IL2CPP/AOT 游戏程序集 → 匹配版本的 iOS Unity 引擎和原生键鼠接口 → 用户签名的 iPad App。

iOS 原生引擎负责 Metal、窗口、音频和输入；游戏仍采用原按键、窗口关闭顺序与规则。AOT 桥接重写必要的加载命令并验证指令字节不变；不是远程串流，也不要求 JIT。BC 纹理适配保持原压缩块，不发布修改后的 Unity SDK。

## 固定输入与准备

- 游戏：Windows DSP **0.10.35.29104**。先按主仓库指南完成 Mac 项目的资源/着色器恢复，保留未修改的 AssetRipper 2.0 导出。
- Unity **2022.3.62f3c1**，Mac 和 iOS 构建支持，以及本人适用的 Unity 许可。
- Apple Silicon Mac、完整 Xcode、连接并开启开发者模式的 iPad Pro。需要自己的 Team ID、Bundle ID、签名 identity 和设备 ID；工具没有内置开发者账号。
- Python 3.12，主仓库依赖与 `ipad/requirements.txt`。
- 单独取得 [emu](https://github.com/brolnickij/emu) 的 `be2060bd1fbdf70545f954a3e4dc90c8f1a27cb0` 提交。这里只调用其 Mach-O 工具，不复制其项目或二进制；其许可与本项目分开。

所有工作目录放在云同步目录之外，且不要放在此仓库内。下面 `WORK` 应指向一个**包含 `local-private` 路径组件**的本地目录；资源改写工具会拒绝公开输出位置。准备较多空闲空间，Unity 的导出和缓存会产生多份大文件。

## 1. 准备独立源码副本

复制已经完成 Mac 资源恢复的 Unity 项目到 `PROJECT`；不要指向原始游戏、未修改导出或正式 Mac 项目。保留 `Assets`、`Packages`、`ProjectSettings`，不要复用不同平台的旧 `Library`。

```sh
python3 ipad/source/prepare_ipad_project.py \
  --project "$PROJECT" --original-export "$ORIGINAL_EXPORT" \
  --game-assembly "$WINDOWS_DATA/Managed/Assembly-CSharp.dll" \
  --report "$WORK/reports/source-preparation.json"
```

脚本校验游戏程序集版本，安装原生输入桥接的托管端、快速按键队列、右上角 Esc、窗口层级、HDR/DoF 和文本流适配。所有游戏原方法仍从本人的导出读取；仓库不提供恢复后的方法或生成式源码配方。未知锚点、不同版本或已有其他修改必须先审查，不能直接删掉断言。

## 2. 导出两个平台

将 `UNITY` 设为 Unity 可执行文件，`UNITY_APP` 设为同一个 `Unity.app` 目录。`ENGINE` 和 `MAC_AOT` 均为新私有输出目录。

```sh
DSP_MAC_AOT_OUTPUT="$MAC_AOT" "$UNITY" -batchmode -quit \
  -projectPath "$PROJECT" -buildTarget StandaloneOSX \
  -executeMethod DSPFullGameBridgeBuild.BuildMacAOT -logFile "$WORK/mac-export.log"

DSP_IOS_BRIDGE_OUTPUT="$ENGINE" DSP_IOS_BUNDLE_ID="$BUNDLE" \
DSP_IOS_BUILD_NUMBER=27 "$UNITY" -batchmode -quit \
  -projectPath "$PROJECT" -buildTarget iOS \
  -executeMethod DSPFullGameBridgeBuild.ExportIOS -logFile "$WORK/ios-export.log"
```

编辑器入口只放进 `Assets/Editor`。两个导出产生的 Bee/ManagedStripped 输入供后续音频绑定与 AOT 重编译使用，不再从开发机的旧日志恢复命令。

## 3. 原始 BC 支持与实际采样门槛

```sh
python3 ipad/source/prepare_bc_archive.py \
  --archive "$ENGINE/Libraries/libiPhone-lib.a" --output "$WORK/bc-engine"
python3 ipad/source/create_bc_manifest.py \
  --source-data "$WINDOWS_DATA" --target-data "$ENGINE/Data" \
  --output "$WORK/bc-manifest.json"
python3 ipad/source/prepare_unity_bc_samples.py \
  --manifest "$WORK/bc-manifest.json" --source-data "$WINDOWS_DATA" \
  --output "$WORK/unity-bc-samples"
```

对象脚本锁定原始 SDK 对象 SHA，检查七处符号/调用重定位并验证指令不变。资源脚本要求 2234 个唯一、元数据一致、不膨胀的匹配对象；不同法线编码和 CPU 可读纹理不混用。生成的 archive、manifest、样本全是私人构建产物，不能提交仓库。

先构建只做 BC 验证的包：

```sh
python3 ipad/source/build_bridge.py \
  --project "$PROJECT" --engine "$ENGINE" --unity "$UNITY_APP" --upstream "$EMU" \
  --work "$WORK/probe-build" --derived "$WORK/probe-derived" \
  --team "$TEAM" --bundle "$BUNDLE" --device "$DEVICE" --identity "$IDENTITY" \
  --version 27-probe --bc-archive "$WORK/bc-engine/libiPhone-bc-candidate.a" \
  --bc-probe-package
```

该包保留导出的纹理，尚不应用原始 BC 替换。使用 `xcrun devicectl device install app` 安装；把本地 `unity-bc-samples` 目录复制到该 App 的 `Documents/unity-bc-samples`，然后运行：

```sh
python3 ipad/source/run_bc_device_probe.py \
  --device "$DEVICE" --bundle "$BUNDLE" --version 27-probe --output "$WORK/bc-results"
```

必须两轮实际 Unity 采样通过，包含 12 组、233 个子资源、原生格式检查及独立颜色控制。退出码为零、Metal 硬件支持或旧 JSON 都不能代替这一步。

## 4. 完整签名包

沿用上面的构建参数，使用新的 `--work`、`--derived` 和正式测试版本，移除 `--bc-probe-package` 并添加：

```sh
--bc-manifest "$WORK/bc-manifest.json" --source-data "$WINDOWS_DATA" \
--bc-sample-report "$WORK/bc-results/report-0.json"
```

以采样工具实际输出的报告文件名为准。完整构建恢复原始压缩块、设置 HDR/阴影层级、使用游戏已有中文字体补齐 DIN 字形，并校验签名、资源、AOT 指令和 metadata。输出 App 在 `derived/Build/Products/Release-iphoneos/DSPemuiPad.app`。

脚本不会自动安装。先确认签名与报告成功，再用自己的设备和 Bundle ID 安装。手机上只出现图标不等于游戏运行成功。

## 5. 集中回归与试玩

```sh
python3 ipad/source/run_device_batch.py \
  --device "$DEVICE" --bundle "$BUNDLE" --version 27 \
  --restart-existing --output-dir "$WORK/regression-27"
```

`--restart-existing` 会结束该 Bundle 的现有进程，只有明确允许中断游戏时使用。普通启动不启用测试；测试启动会静音、准备测试资源并修改独立测试存档，因此不要拿唯一存档测试。

批次检查本次版本/进程/随机批次标识，确认进入真实世界，再测试界面、键鼠、保存重载和综合功能。大存档与蓝图需要提供自己的副本和配置；没有这些输入就不能声称相关阶段通过。配置结构见 `DSPPadMatchedRenderRegression.Config` 与 `DSPPadFunctionalBatch`，示例要求见 [验证记录](VALIDATION.md)。

回归通过后正常退出，再普通启动试玩。需额外检查实体键鼠、不同连接方式、长时间运行、所有战斗场景及未覆盖画面。没有这些证据就不要宣传“完整 Windows 等价”。

## 文件与边界

- `source/`：原创 C#/Objective-C/C++ 适配和参数化 Python 工具。
- `source-origin.json`：公开文件来源、用途和哈希。
- `VALIDATION.md`：开发机验证范围与公开入口的复现边界。
- 主目录 MIT 只涵盖原创工具；游戏、Unity 和上游依赖各自保留原权利与许可。

没有提供 mini 的内存实验、动画分块上传实现、降纹理配置或任何游戏/SDK 二进制。
