# 离线输入法补丁实验

面向用户自行提供的搜狗 Android 20.17.0 ARM64 安装包，提供本地精简补丁与辅助界面代码。非官方项目，与原厂无隶属关系。

## 功能范围

- `lite/`：移除 INTERNET 权限，保留本地拼音、九宫格、候选与输入设置，关闭已识别的商业入口和统计任务。
- `offline-voice/`：在上述基础上接入本地普通话语音模型，固定使用 OFFLINE_ONLY，增加麦克风权限。
- 商业功能采用入口禁用和初始化裁剪；相关第三方类与资源未全部从最终 APK 物理删除。
- 语音资源使用原厂旧框架兼容包；不声称等同于新版应用下载的资源。

本仓库仅包含补丁脚本与辅助源码。原版或修改版 APK、厂商模型、词库、反编译结果、设备数据与签名私钥均不随源码分发。

## 状态

此前开发产物在单台 Android 13 ARM64 设备上通过了九宫格输入和人工离线语音上屏测试。未完成多机型、长句、噪声、方言或长期功耗验证。清理后的源码仓库移除了原始测试记录与历史产物；此记录不代表后续每个自行构建的 APK 均已实测。

## 本地构建

需要 Python 3.10+、JDK 17+、Android SDK（默认 Build Tools 36.1.0 与 android-36）和 apktool 3.0.3。可通过以下环境变量配置本机工具，不在源码中填写个人目录：

- `JAVA_HOME`
- `ANDROID_SDK_ROOT`（也支持 `ANDROID_HOME`）
- `APKTOOL_JAR`（默认 `tools/apktool_3.0.3.jar`）
- 可选：`ANDROID_BUILD_TOOLS`、`ANDROID_PLATFORM`

将自行取得的原始 APK 放在 `inputs/SogouInput_20.17.0_android_sweb.apk`。仅支持 SHA-256：

```text
3eb2612040fd7daefb7e92b9de5c1a715b03f272b644e0664948742df1c7a416
```

执行：

```sh
python prepare.py
python lite/build.py
```

输出位于 `dist/`，构建记录位于各自的 `build/` 与 `logs/`，首次构建会在 `.local/signing/` 创建项目独立密钥。两个构建变体共用该本地密钥。密钥、密码和输出文件被忽略规则及发布检查排除。

### 离线语音变体

在构建语音变体前，需要本地准备匹配 `offline-voice/resource-manifest.json` 的资源压缩包：

```text
audit/offline-voice/offline_zip_64_1.zip
```

可选的 `offline-voice/fetch_resources.py` 使用原 APK 的分发配置查询已知资源任务，不包含个人账号或设备标识。运行该脚本前，需自行用 JADX 将原 APK 反编译到 `audit/jadx/`，保持其默认 `sources/` 目录结构。脚本会校验官方 MD5 和固定 SHA-256；服务若已变更则停止，不自动改用未知资源。

```sh
python offline-voice/fetch_resources.py
python offline-voice/build.py
```

`offline-voice/probe/` 是可选的模型加载探针源码，依赖同一 JADX 输出；它不录音，也不替代完整应用测试。

### 签名与测试

自行构建使用新密钥，与原版以及此前本地产物的签名不同。切换签名通常需要卸载原应用，并会清除其私有数据。构建脚本不会操作手机或自动卸载应用。

安装后先验证普通输入，再手动授权麦克风、测试语音。请勿上传含输入内容、账号、设备信息的截图或日志。

## 发布前检查

仓库以新的匿名初始提交开始；没有继承开发阶段的分支、标签、提交记录或远程配置。
初始提交采用固定时间戳用于打包，不表示实际开发日期。

```sh
git add .
python scripts/publish_check.py
python scripts/publish_check.py --history
```

检查按源码路径白名单拒绝产物、二进制文件和常见敏感信息。第一次检查针对暂存区，第二次检查所有本地提交。不能代替对自由文本和图片的人工判断。

可选择为本仓库启用推送前检查：

```sh
git config --local core.hooksPath .githooks
```

发布前使用独立的发布账号和提交身份，并核对远程地址。文件清理无法消除托管账号、网络访问记录或已公开副本带来的关联；本仓库不自动登录或创建远程仓库。

## 许可

本仓库原创补丁脚本与辅助代码采用 MIT 许可，见 `LICENSE`。厂商 APK、模型、词库、商标及原有代码不属于该许可范围；见 `NOTICE.md`。
