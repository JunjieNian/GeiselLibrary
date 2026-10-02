# 交付验证

验证对象为 `D:\Projects\GeiselLibrary` 内的保存文件与实际 Unreal 游览程序。

## 已通过

- Blender 源文件重新打开并检查：48 个网格对象（文字保留为可编辑文字），约 209 万个三角形，所有网格均有有效纹理坐标。
- 最大楼板模型跨宽约 60.93 米；参考值为原报告的约 200 ft / 60.96 米。屋顶顶点标高约 43.51 米，论坛基准标高 10 米。
- Snake Path 生成中心线长度 170.688 米；宽度参考值 3.048 米。
- FBX 在 Unreal 成功导入 49 个网格（文字转网格），51 个材质，82 个材质槽；当前 FBX 的 SHA-256 与导入报告一致。
- Unreal C++ 构建成功。最终模型导入完成并保存关卡 `/Game/Geisel/Maps/L_GeiselLibrary`。
- 自动运行测试通过：初始镜头、实际飞行位移、视角切换、三种光照切换、地面射线、步行落地、步行位移、隐藏界面。
- 2026-10-01 的可见窗口核验：数字键切换 Snake Path 镜头、F 进入步行、鼠标环顾和 L 切换傍晚光照均在实际游览窗口中生效。
- 面向首次下载的 `build_and_setup.ps1 -SkipSceneImport` 分支执行成功，复用已保存关卡；全部 PowerShell 脚本语法检查通过。
- 运行截图逐项检查过：修正了导入镜头横滚、物理曝光范围、非灯具材质误发光、远处地面边界以及截图延迟造成的时段错配。

## 证据文件

- `GeometryValidation.json`：保存后的 Blender 文件回读结果。
- `SnakePathValidation.json`：保存后的蛇路网格检查，包含单块连续路面、一个花园开口、朝向、盘绕处重复面积和 62 个路面采样点。
- `RuntimeValidation.json`：公开保存的最终导入报告和自动运行断言摘要；完整本机日志不上传。
- `../UnrealProject/Saved/GeiselSetupReport.json`：模型导入数量、资源路径与 FBX 校验值。
- `../UnrealProject/Saved/Logs/GeiselSelfTest.log`：包含 `[GEISEL_SELFTEST] ALL_PASSED`。
- `../UnrealProject/Saved/Screenshots/Geisel/`：四个视角、日间/傍晚/暮色和步行界面的实际运行截图。
- `../Previews/`：Blender 静态预览与最终运行截图。

## Snake Path 盘绕修正（2026-10-01）

按 `References/smith-a-02.jpg` 的实景照片与 `smith-a-01.jpg` 的平面图修正花园盘绕段。原控制点顺序使蛇身在相接处两次急折回自身，导致路面翻折、断头和相互穿插。新的路径沿完整圆圈平顺绕行，相接处合并铺装轮廓、裁剪重叠鳞片；边线沿合并后的外周和花园内周生成。

保存后的 Blender 网格检查确认：一块连续的路面围合一个约 62.15 平方米的花园开口，路面三角形朝上，62 个盘绕中心线采样点均位于铺装内。Unreal 自测对同一组采样点做射线检测，要求命中蛇路铺装而不是下方裸土地形，并生成 `UE_08_Snake_Coil_Continuity.png` 近景。可编辑 Blender、FBX、GLB、Unreal 网格和关卡一起更新；详细运行结果见 `RuntimeValidation.json`。

## 当前边界

场景为公共参考资料支持的外景重建。细部构件、坡高、种植与周围远景采用目测估计；没有现场扫描或完整室内复原。地形外围是为了让环境连续而制作的简化背景，不是校园全景地理模型。Unreal 在大范围植被长阴影时可记录一次虚拟阴影任务队列性能警告；实际移动与截图测试仍通过。

## 改名清理状态

正确根目录为 `D:\Projects\GeiselLibrary`。旧拼写目录 `D:\Projects\GeiserLibrary` 已不存在；所有当前源码、启动器与说明中的名称已统一。

`Tools/Unreal/MigrationBackup` 内的 3 个旧迁移副本文件已逐项删除，目录层级为空。自动审批再次拒绝了移除旧编译缓存和空迁移目录的操作，原因仅为 `blocked by policy`，因此本机仍留有 `UnrealProject/Intermediate_PreRename`（6,283,513 字节）和空的 `Tools/Unreal/MigrationBackup`。这两处不是运行依赖，当前编译与运行使用新生成的 `UnrealProject/Intermediate` 与 `Binaries`。两处残留、当前编译缓存、日志和本地参考图片均通过 `.gitignore` 排除在公开仓库之外。
