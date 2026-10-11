戴森球计划 Mac 版迁移工具（本轮已验证工具；新机器验收待进行）

本目录只包含作者编写的转换脚本和平台辅助代码。使用者须提供自己购买的 Windows 游戏；所有游戏代码、着色器、模型和纹理均在本机生成。公开时只分享本目录。仅对 port-tools 建仓库，不要添加上层的 local-private 或游戏 App。

支持的输入：DSP 0.10.35.29104，Steam Windows depot 1366541。
Assembly-CSharp.dll SHA256：6c122e5443e6843979b4064050dfcb5e0d75577a0b64f6ae4111290238b33c12
未知版本会被拒绝，不能靠删除校验来宣称兼容。当前目标是 Apple Silicon Mac / Metal / Mono。iPad/emu 仍需独立验证。

交互式入口：双击 start.command，或用 Python 3.12 运行 wizard.py。会提示依赖安装、路径选择和本人许可激活；输入 q 暂停，再次运行继续。完整说明见 docs/用户操作指南.txt。向导与恢复流程目前 79 项检查通过，尚未在新机器完成全流程。

自检修复：首轮普通 Release 的崩溃发生在新游戏截图后立即保存时，并非之前误判的菜单加载阶段。自检改为回到下一帧再保存，已通过新建、保存、重载和正常退出；没有修改游戏模型或渲染效果。新机器和完整功能验收仍未完成。

依赖：
• Apple Command Line Tools（含 xcrun/clang 与 macOS SDK），或已完成首次设置的 Xcode。
• 已自行安装并激活许可的 Unity 2022.3.62f3c1（需要 Mac 构建支持）。
• Python 3.12，建议在本地虚拟环境中运行 pip install -r requirements.txt。
• AssetRipper 2.0.0 的本机可执行文件，SPIRV-Cross 和 vkd3d-compiler。
具体版本和第三方来源见 docs/dependencies.txt；不捆绑这些第三方工具。

依次执行（替换示例路径；路径带空格时保留引号）：
  python3 port.py doctor --game '/path/to/owned/WindowsGame'
  python3 port.py prepare --game '/path/to/owned/WindowsGame' --workspace '/path/to/new/private-workspace' --assetripper '/path/to/AssetRipper.GUI.Free' --spirv-cross '/path/to/spirv-cross' --vkd3d '/path/to/vkd3d-compiler'
  python3 port.py recover-shaders --workspace '/path/to/new/private-workspace'
  python3 port.py build --project '/path/to/new/private-workspace/work/dsp-runtime/port-project' --output '/path/to/build/DSPMac.app' --release

安装好依赖后，也可用单一入口执行相同阶段：
  python3 port.py convert --game '/path/to/owned/WindowsGame' --workspace '/path/to/new/private-workspace' --assetripper '/path/to/AssetRipper.GUI.Free' --spirv-cross '/path/to/spirv-cross' --vkd3d '/path/to/vkd3d-compiler' --release
默认 App 位于私有工作目录的 build/DSPMac.app；可加 --output 指定新的输出路径。该入口组合了已测试的各阶段，仍需完成生成后的游戏运行验证。

Unity 不在默认位置时，doctor/build 可加 --unity '/path/to/Unity.app/Contents/MacOS/Unity'。
prepare 会通过仅监听本机的 AssetRipper API 导出原始工程，保留该导出并在副本上适配；也可用 --exported-project 指定自己从相同输入导出的、未经修改的 ExportedProject，替代 --assetripper。
prepare 拒绝覆盖已有工作目录；build 拒绝覆盖已有 App，检查脚本/着色器错误，并完成本机 ad-hoc 签名校验（不是 Apple 公证或公开分发签名）。恢复中断可重新执行 recover-shaders，它在核对生成产物哈希后复用已完成的纯提取阶段；产物丢失或改变时会重做对应阶段并使后续检查点失效。所选依赖二进制改变时拒绝混用旧产物。各阶段日志保存在 conversion-logs，转换状态保存在 conversion-state.json。请勿按文件名顺序手动运行 tools/runtime 下的脚本。
推荐把私有工作目录放在非 iCloud/OneDrive 的本地磁盘，以免云端占位文件和同步延迟影响构建。首次 Unity 导入、shader 编译和缓存需要较大磁盘空间。

可选实验：保持纹理尺寸、mipmap 和原版压缩数据的内存优化：
  python3 tools/restore_original_textures.py --help
该工具只写入新 App 副本，逐项验证原始压缩字节和未改动对象；不会重压缩或删除模型；完成后重新进行本机签名并验证。目前已完成 130MB 存档内存 A/B/A 测试，已追加通过两个旧存档、蓝图及菜单场景回归，仍作为明确选择的后处理步骤；不会自动改写已有试玩 App。

现有验证与限制：
• 已从当前本机购买的 Windows 文件重新完成 19539 个资源导出、6495 个 DXBC 转换、19 个 compute shader 和 143 个生产光照 shader 家族恢复。独立工程已完成构建（无脚本/着色器错误）、130MB/55MB 旧存档往返保存、蓝图预览与施工、十二个菜单镜头采样验证；新机器复现未验证。
• 先前工程的 Mac 试玩已验证部分旧存档、蓝图、生产链、五种 iPad 分辨率和 Mac 原生全屏，详见 docs/performance.txt。不能把这些结果自动视作本次全新转换的验证结果。
• Steam 平台服务未接入。独立沙盒已经验证生产链、研究、本地物流、两趟星际曲速物流及途中重载、戴森球设计/涂装/火箭/太阳帆吸收、两种地面炮塔战斗；大型网络、全武器/太空战斗和长时间稳定性尚未全面验证；不声称与 Windows 完全一致。
• 转换工具不接受账号密码，不替用户同意第三方许可，不上传游戏或个人数据。

发布前检查：
  python3 tools/check_release.py
检查文件边界和机器路径后，仍需人工核对来源及第三方许可。仅此目录可以作为未来公开项目；不附带恢复后的游戏 C#、HLSL、DXBC、SPIR-V、DLL、EXE、App、IPA、游戏资源、蓝图或存档。

生成 App 的可选本机自检：
  python3 port.py arm-smoke
随后打开刚生成的 App，它会静音新建独立测试世界、推进模拟，检查星图/戴森球/机甲编辑器及一次窗口分辨率切换，然后保存、重新加载并通过游戏正常退出。测试存档名带随机后缀，不覆盖手动存档；正常退出可能更新游戏自己的“最后退出”自动存档。结果写在本机应用数据目录的 converter-smoke-result.json，同时保存新游戏及界面截图。没有该一次性标记时不安装测试对象，普通启动保留正常声音和操作。这个基础自检不代替大存档、蓝图、画面及长期稳定性验证。

操作对齐：Caps Lock 通过 Apple GCKeyboard 实体按键接口接入原曲速逻辑；不更改 C、Esc、Tab 的原版规则。切出后再点击游戏窗口不会自动恢复航行鼠标锁定，按 Tab 恢复。差异与未验证范围见 docs/behavior-parity.txt。

小地图 Metal 缓冲区：Windows 原版在扩容/销毁时立即释放，Mac 会遇到队列中的绘制仍引用旧缓冲区的情况。适配层保留旧缓冲区到帧提交及 GPU 读回完成，保留原池内容、容量规则、绘制和战斗逻辑。三次战斗/保存重载、15页切换验证未再出现此前的缺缓冲区跳过绘制，28个待释放缓冲区全部回收。

编辑器预检：转换前读取Unity安装元数据，验证固定2022.3.62f3c1及MacStandaloneSupport。版本或组件错误时给出安装提示，可重新输入正确编辑器路径；不会先启动错误版本或自动接受许可。

UI 显存适配：Apple GPU 的 Mac Metal 路线对四个原版4×MSAA HDR界面目标采用临时多重采样存储；保留原尺寸、深度、抗锯齿、模型与逻辑。130MB/55MB真实存档一轮ABBA及多页面/保存重载通过，Metal分配分别减少约0.83/0.85GiB；最大RGBA差0.000488小于0.001阈值，并非逐位相同，不声称FPS或总物理内存改善。首次创建、尺寸切换、恢复和重载已在普通Release验证。主相机、银河界面、非AppleGPU与iPad不在该优化范围。详情见docs/performance.txt。

内存监测：tools/memory_monitor.py 在正式游戏外持续读取计费物理内存及CPU，定期保存系统区域分布，并生成本地曲线页面。不会切换或退出游戏。使用和分类限制见 docs/memory-monitor.txt。对象级分析仍需诊断版。

2026-10-11 最终 Mac 构建已采用传送带空预留延后分配和相机对称投影适配。
最大档有效数据保留，太空物理约25.7–26.6GB、繁忙地面约27.8GB（此前约40GB）；原版空尾部约13.01GB按需恢复。43组成对导出及真实游戏综合批次通过，不保证内存上限/FPS提升/iPad。
相机60矩阵/GPU矩阵配置与固定输入RGBA一致、实际FOV负对照能检出，真实蓝图偏轴分支保持；完整动态地面逐像素一致未建立。详情见docs/performance.txt及docs/behavior-parity.txt。
正式包已另行通过普通生产编译、严格签名、无私人诊断、四UI/尺寸恢复/保存重载/正常退出检查。工具79项自动检查和102文件边界检查通过；新机器全流程仍待实测。
start.command是准备好依赖后的统一向导入口，不会代替购买、依赖安装或本人同意Unity许可。建议保留默认y的原版纹理字节恢复，以获得本次验证的资源状态。

许可证：原创迁移工具采用MIT，见LICENSE；不授权分发原游戏或第三方依赖。启动按屏幕全屏已在Mac3840×2160验证，手动窗口/恢复/四UI/存读/正常退出通过；iPad原生横向分支已提供但未真机验证。分享与安装区别见docs/publishing.txt。79项测试、102文件边界通过，转换工具不上传用户数据。
