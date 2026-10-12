当前只维护 iPad Pro 键鼠版；触控开发暂停，已安装 Touch29.3 保留。两种版本已有的系统 Files/iCloud 手动导入导出保持可用；历史触控预览范围见 [TOUCH.txt](TOUCH.txt)。

# iPad Pro 迁移：开发者预览

本目录提供原创的平台适配、构建和验证工具。使用者必须自行准备已购买的 Windows 游戏、Unity 工具链和自己的 Apple 签名。仓库不包含游戏源码、资产、SDK 对象、App/IPA、测试存档或蓝图。

当前目标是 **iPad Pro + 实体键盘鼠标**。mini 支持已停止，不提供 mini 分辨率预设或低画质替代包。键鼠37.1已用公开工具独立重建并完成限定综合自动测试，最终设备保留42版，本次结果见 [验证记录](VALIDATION.md)。自动输入不能证明真实 Universal Control、USB 或蓝牙手感；也没有宣称 Windows 全功能/逐像素等价。

这是一套开发者复现入口，**不是向导式一键 iPad 安装器**。公开入口已在本机的全新工作区完成原始输入恢复、全新缓存构建、签名安装与 Pro 回归；尚未在另一台全新配置的 Mac 上复验。法线编码造成的地表暗区已在限定场景修复；低帧率尚未解决，项目现已阶段收尾。Mac 的 `start.command` 不会自动完成 iPad 部署。

## 架构

用户自己的 Windows 文件 → 本分支内的共用资源恢复工具 → iPad 平台适配 → ARM64 IL2CPP/AOT 游戏程序集 → 匹配版本的 iOS Unity 引擎和原生键鼠接口 → 用户签名的 iPad App。

iOS 原生引擎负责 Metal、窗口、音频和输入；游戏仍采用原按键、窗口关闭顺序与规则。AOT 桥接重写必要的加载命令并验证指令字节不变；不是远程串流，也不要求 JIT。BC 纹理适配保持原压缩块，不发布修改后的 Unity SDK。

## 固定输入与准备

- 游戏：Windows DSP **0.10.35.29104**。使用下述独立入口恢复资源；可以提供 AssetRipper 2.0 可执行文件，或它未修改的导出。
- Unity **2022.3.62f3c1**，Mac 和 iOS 构建支持，以及本人适用的 Unity 许可。
- Apple Silicon Mac、完整 Xcode、连接并开启开发者模式的 iPad Pro。需要自己的 Team ID、Bundle ID、签名 identity 和设备 ID；工具没有内置开发者账号。
- Python 3.12，主仓库依赖与 `ipad/requirements.txt`。
- 单独取得 [emu](https://github.com/brolnickij/emu) 的 `be2060bd1fbdf70545f954a3e4dc90c8f1a27cb0` 提交。这里只调用其 Mach-O 工具，不复制其项目或二进制；其许可与本项目分开。

所有工作目录放在云同步目录之外，且不要放在此仓库内。下面 `WORK` 应指向一个**包含 `local-private` 路径组件**的本地目录；资源改写工具会拒绝公开输出位置。准备较多空闲空间，Unity 的导出和缓存会产生多份大文件。

## 1. 准备独立源码副本

在本 iPad 分支中直接运行：

```sh
python3 ipad/source/prepare_from_windows.py \
  --game "$WINDOWS_GAME" --workspace "$WORK" \
  --assetripper "$ASSETRIPPER" \
  --spirv-cross "$SPIRV_CROSS" --vkd3d "$VKD3D"
```

`WORK` 必须是新的私有目录。若已有未修改的 AssetRipper 2.0 导出，可用 `--exported-project "$ORIGINAL_EXPORT"` 替代 `--assetripper`。入口调用同一分支内的 `tools/prepare_project.py`、`tools/recover_pipeline.py` 和 iPad 源码适配器；无需先构建 Mac 游戏，也无需切换 Mac 分支或借用开发者的已修工程。

生成的 `PROJECT` 为 `$WORK/work/dsp-runtime/port-project`，保留的原始导出为 `$WORK/work/dsp-runtime/recovered-project/ExportedProject`。不要复用其他工程的 `Library`。下述低层命令仅用于重试 iPad 适配阶段，完整入口已调用它：

```sh
python3 ipad/source/prepare_ipad_project.py \
  --project "$PROJECT" --original-export "$ORIGINAL_EXPORT" \
  --game-assembly "$WINDOWS_DATA/Managed/Assembly-CSharp.dll" \
  --report "$WORK/reports/source-preparation.json"
```

脚本校验游戏程序集版本，安装原生输入桥接的托管端、快速按键队列、窗口层级、HDR/DoF、文本流和电力提示着色器适配。键鼠版隐藏额外的屏幕 Esc，并常驻原版 FPS/UPS 与整个 App 的物理内存占用；触控预览保留其 Esc。所有游戏原方法仍从本人的导出读取；仓库不提供恢复后的方法或生成式源码配方。未知锚点、不同版本或已有其他修改必须先审查，不能直接删掉断言。

## 2. 导出两个平台

将 `UNITY` 设为 Unity 可执行文件，`UNITY_APP` 设为同一个 `Unity.app` 目录。 若本机许可有效但命令行报告 LicensingClient IPC 超时，可用 `TMPDIR=/tmp` 启动编辑器以对齐许可进程的本地 socket 路径；这不会激活或替代 Unity 许可。`ENGINE` 和 `MAC_AOT` 均为新私有输出目录。

```sh
DSP_MAC_AOT_OUTPUT="$MAC_AOT" "$UNITY" -batchmode -quit \
  -projectPath "$PROJECT" -buildTarget StandaloneOSX \
  -executeMethod DSPFullGameBridgeBuild.BuildMacAOT -logFile "$WORK/mac-export.log"

DSP_IOS_BRIDGE_OUTPUT="$ENGINE" DSP_IOS_BUNDLE_ID="$BUNDLE" \
DSP_IOS_BUILD_NUMBER=42 "$UNITY" -batchmode -quit \
  -projectPath "$PROJECT" -buildTarget iOS \
  -executeMethod DSPFullGameBridgeBuild.ExportIOS -logFile "$WORK/ios-export.log"
```

编辑器入口只放进 `Assets/Editor`。工程准备阶段已经设置 `DSP_EMU_IPAD`，确保首次 Unity 编译也能解析平台类型。两个导出产生的 Bee/ManagedStripped 输入供后续音频绑定与 AOT 重编译使用，不再从开发机的旧日志恢复命令。`MAC_AOT` 是 iPad 桥接所需的中间产物，使用 macOS ARM64 编译工具链；不需要启动它或验收 Mac 游戏。

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
  --version 37.0 --bc-archive "$WORK/bc-engine/libiPhone-bc-candidate.a" \
  --bc-probe-package
```

该包保留导出的纹理，尚不应用原始 BC 替换。使用 `xcrun devicectl device install app` 安装；把本地 `unity-bc-samples` 目录复制到该 App 的 `Documents/unity-bc-samples`，然后运行：

```sh
python3 ipad/source/run_bc_device_probe.py \
  --device "$DEVICE" --bundle "$BUNDLE" --version 37.0 --output "$WORK/bc-results"
```

必须两轮实际 Unity 采样通过，包含 12 组、233 个子资源、原生格式检查及独立颜色控制。退出码为零、Metal 硬件支持或旧 JSON 都不能代替这一步。

## 4. 完整签名包

沿用上面的构建参数，使用新的 `--work`、`--derived` 和正式测试版本（例如 `--version 37.1`），移除 `--bc-probe-package` 并添加：

```sh
--bc-manifest "$WORK/bc-manifest.json" --source-data "$WINDOWS_DATA" \
--bc-sample-report "$WORK/bc-results/report-0.json"
```

以采样工具实际输出的报告文件名为准。完整构建恢复原始压缩块、设置 HDR/阴影层级、使用游戏已有中文字体补齐 DIN 字形，并校验签名、资源、AOT 指令和 metadata。输出 App 在 `derived/Build/Products/Release-iphoneos/DSPemuiPad.app`。

脚本不会自动安装。先确认签名与报告成功，再用自己的设备和 Bundle ID 安装。手机上只出现图标不等于游戏运行成功。

### 图标、名称和增量资源

键鼠 App 的名称为“戴森球计划”。可向 `build_bridge.py` 添加 `--original-exe "$WINDOWS_EXE"`，从本人原始游戏可执行文件中提取默认图标；此可选步骤需 `pefile` 和 `Pillow`。图标仅写入私有 Xcode 资源目录，不进入工具仓库。

电力覆盖与建筑提示修复需要重新编译四个着色器。`prepare_ipad_project.py` 已添加对应 Metal 编译保护；之后执行正常 Unity iOS 导出。只替换托管 DLL、继续使用旧 shader 资源不会生效。不要将诊断纯色程序或实验绘制路径用于正式构建。

常驻 `App 内存` 使用 iPadOS `phys_footprint`，单位 GiB，每秒更新一次；它不是 Unity 托管堆，也不将 GPU/Unity 统计简单相加。FPS/UPS 使用游戏原有计算，不代表已完成性能优化。

## 5. 集中回归与试玩

键鼠电力/世界/文件/输入合并批次可向 `run_device_batch.py` 同时传入 `--world-audit --power-audit`。数据断言通过后仍需审阅本次电力阶段截图；不能将旧截图、仅菜单或正常退出视为视觉验收。

```sh
python3 ipad/source/run_device_batch.py \
  --device "$DEVICE" --bundle "$BUNDLE" --version 37.1 \
  --world-audit --power-audit --restart-existing --output-dir "$WORK/regression-37.1"
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

## 可选渲染诊断与收尾范围

普通准备流程不生成实验着色器。仅复查历史专项时，在导出前额外运行 `prepare_scene_shader_probe.py --project "$PROJECT" --report "$WORK/reports/scene-shader-probe.json"`，或在低层准备入口传 `--render-probes`；随后才可使用 `run_device_batch.py` 的 `--scene-audit` / `--performance-audit`。这些模式需要本人存档副本 `scene-audit-fixture.dsv`，会隔离保存目录、暂改测试场景，并在退出时恢复设置。测试执行成功不表示达到60FPS或画质等价。候选着色器仅限显式诊断，不替换普通游戏材质。

项目按用户要求在42版收尾；未验收的43版实验不纳入交付。清理时可删除Unity Library/Temp、AOT中间包、Xcode DerivedData、旧平台导出及旧测试包；应先归档最终签名App、源工程、存档和构建报告。不要删除自己的原始游戏、签名凭据或存档。
