# PPT Issue #1：双平台获批视觉基线采用与复验

## 当前结论（2026-10-20）

**我跑过：本轮规定的 Windows 与独立 WSL2 本地检查均已通过，完整套件零失败、零跳过。尚未推送、创建 PR、合并或部署。Issue 仍待公开发布授权、远端 CI、Architect Review 和所有者审批。**

此前两平台各 166 passed / 1 failed 的记录完整保留在本文历史部分。本轮没有提高容差、删除测试或把未执行检查写成通过。

## 实际测试版本与审批来源

| 仓库 | 两平台实际执行完整验证的代码提交 |
| --- | --- |
| Python/HTML 内核 | `97482c889a9e196c56ff3cb64a4e711599577624` |
| Mini-App | `36f62fa7d5f4e78735dfe14d9cbaa192c9815116` |

本报告提交是上述代码提交的文档后继，不冒称其自身已经执行全部测试。两平台 SHA 完全一致；各自安装依赖，显式指定本平台的新内核克隆。
正式 `ENGINE_BASELINE.json` 仍锁 Public 冻结根提交，未提前更新为未合并候选；本次是实际双仓候选组合验证。

所有者已明确批准三组 Public 候选作为视觉目标：内核 Windows 九页、WSL2 九页、应用 Windows 软件渲染十二页，并批准本轮采用计划。获批渲染来源为内核 `f2c33fe124e864114020d15b66749025c8bb0046` 与应用 `d7508f77ed044ccc3ab9da40bf5a79076c33129e`；后续提交仅修改测试工具、基线资料与失败传递回归，不改产品渲染代码。

获批 `candidate-a` 原 PNG 按 SHA256 原样复制入库。应用 Linux 十二页复用原 Public PNG。两仓原目录的 **23 个 PNG/清单文件字节未变**；新增平台目录共 42 张 PNG，其中 12 张为原 Linux 图的逐字节复用。
Windows 应用几何数据经正式截图程序补采，只有全部 PNG 与获批图哈希相同时才登记；没有用补采图替换获批原件。

## 为什么此前像素失败现在可以通过

原九页 Golden 的完整环境无法核验，且第八页圆形修复有意改变画面。此前失败被保留为事实；原图作为历史档案，不再被冒称为本轮获批视觉目标。
原 `test_diagram_samples_match_baseline_zero_diff` 仍存在并要求零差异，当前参照按平台选择的获批目标。根目录旧图继续核验完整性。
应用 Windows 原参数重拍出现第 1、11、12 页 7、3、2 个像素波动。仅在 Windows 截图启动参数中增加 `--disable-gpu` 后重复截图和正式比较通过；Linux 参数不变，产品 HTML/CSS/JS 不变。
方案评估：保留存在波动的原参数 20/100；固定 Windows 软件渲染且保留严格断言 90/100；提高像素容差 0/100，拒绝。

## 环境与环境门禁

| 项目 | 原生 Windows | 独立 Ubuntu WSL2 |
| --- | --- | --- |
| 系统 | Windows 11 x64，build 26200 | Ubuntu 24.04.5 x64，WSL2 kernel 6.18.33.2 |
| Node / pnpm / uv | 22.23.3 / 9.0.0 / 0.13.1 | 22.23.3 / 9.0.0 / 0.13.1 |
| Python | 3.12.10 | 3.12.3 |
| Python Playwright / Pillow / pytest | 1.60.0 / 12.3.0 / 9.1.1 | 1.60.0 / 12.3.0 / 9.1.1 |
| 应用 playwright-core | 1.64.0 | 1.64.0 |
| Chrome for Testing | 152.0.7977.64 | 152.0.7977.64 |
| 视口 | 1920×1080 | 1920×1080 |

浏览器来自官方 CfT 下载，二进制与归档来源另有本地校验记录；未替换系统浏览器。
Windows 浏览器 SHA256：`79832d1e60cbad9323c07339f9608bc0ce93cb9242b9b5481c04a0c536720980`。
Linux 浏览器 SHA256：`3ed7df7904694145caf8da676d053f68300e8d2778a507e27b15f142c4efd0af`。
统一相对路径字体指纹：Windows `18e393e867896c06726b5cfe773c6b49c491970d81e0b9839c3292ac1ee23539`；Linux `2cbf96553560ba1d17405b92aeadee426f55d5e8b5ca6dd203abce2b2c773852`。它们由排序后的 UTF-8 相对路径、NUL、文件 SHA256、LF 计算，与原候选完整字体清单保留对应关系。
检查前核验平台、x64 架构、浏览器二进制及版本、Playwright、字体指纹、视口和启动参数。缺少平台清单、损坏图片、不支持平台或环境变化均明确失败；没有回退历史图、跨平台混比或跳过开关。
macOS 未实机验证。Docker 未代替独立 WSL2。测试使用无 pip 种子的隔离 uv 宿主；构建 Python、测试 overlay 与宿主实际路径分别审计。

## 本轮实际结果（我跑过）

| 项目 | Windows | 独立 WSL2 |
| --- | --- | --- |
| 内核完整 Python 套件 | 184 passed / 0 failed / 0 errors / 0 skipped | 184 passed / 0 failed / 0 errors / 0 skipped |
| 内核快测 | 73 passed / 111 deselected | 73 passed / 111 deselected |
| 内核行数门禁 | 通过 | 通过 |
| 内核平台九页严格比较 | 零差异 | 零差异 |
| 内核独立重拍及颜色变异 | 重拍零差异；变异仅第4、5页 | 同左 |
| 应用 TypeScript / ESLint | 通过 | 通过 |
| 应用可移植测试 | 10 项脚本 + 38 项 unit，通过 | 同左 |
| 应用完整跨仓集成 | 45 passed / 0 failed / 0 skipped | 同左 |
| 应用十二页几何与像素 | 通过，零像素差异 | 同左 |
| 应用反误通过检查 | 旋转、渐变两项变异均拒绝 | 同左 |
| 生产构建 | Next 16.4.2、tsup 9，通过 | 同左 |
| 冻结安装 | 通过 | 通过 |
| 完整、生产依赖审计 | 零告警，未忽略编号 | 同左 |
| Python 与隔离工具环境审计 | 无已知漏洞 | 同左 |

新增环境异常回归覆盖平台选择、缺失目标、图片丢失/损坏、错误浏览器或 Playwright、字体变化、参数/视口变化和不支持平台。完整套件数量与快测收集总数一致。
真实生产路径为 `DeckOutline → buildDeckHtml → Python builder → 单文件 HTML → 浏览器 QA`：合成中文、嵌入 PNG、十二页及语义动画通过；跨仓用例覆盖长中文和压缩后仍溢出的拒绝。新增持久回归复制真实 builder、故意缺失样式清单，验证 Python 实际退出 1 后包装层传递 `PPT builder failed (1):`；不使用 mock，并恢复环境变量及安全清理独立临时目录。

## 命令与证据

两平台使用上述固定工具，并显式配置各自 `PPT_ENGINE_ROOT`、`PPT_PYTHON_PATH`、`PPT_CHROME_PATH`。Windows 受控套件启用 UTF-8；另有强制关闭 Python UTF-8 模式的真实构建回归。

```bash
./tools/ci.sh --fast
uv run --no-project --python 3.12 --with playwright==1.60.0 --with pillow==12.3.0 --with pytest==9.1.1 python -m pytest tests -q --basetemp="$EVIDENCE_TMP" --junitxml="$EVIDENCE_XML"
pnpm install --frozen-lockfile --offline
pnpm validate
pnpm test:portable
pnpm test:ppt
pnpm test:ppt:golden:geometry
pnpm test:ppt:golden
pnpm build
pnpm audit --json
pnpm audit --prod --json
```

Windows 快测等价执行同一工具链的行数检查和 `pytest -q -m "not slow and not smoke"`。每次使用全新仓库外临时目录；完整测试不加筛选标记，所列最终验收命令退出码均为 0。
Python 审计命令为 `uv tool run --from pip-audit pip-audit --path <实际环境路径> --format json --progress-spinner off`，同时覆盖构建环境、实际测试 overlay 和隔离 uv 宿主。
本轮应用流程曾因记录器保护旧同名日志而中止，重复调用未执行测试；原退出记录保留，后续像素、生产形状和构建改用唯一日志名完成。没有覆盖失败日志或将记录器中止改写成测试通过。

## 安全、交付和回滚

完整 Public Git 历史秘密扫描无命中；已人工复核新增 PNG 来源、跟踪文件与待提交差异。未加入真实 env、凭据、客户资料、培训站点、个人联系方式、缓存或生成目录。历史上已由所有者批准公开的贡献者 Git 身份继续保留，不展示地址。
脚本测试中的临时数据为合成数据。二维码/联系方式相关命中为既有组件、占位符或审查文字；看似 IP 的内核版本号经过人工分类，未发现真实部署地址。
本轮基线采用没有新增依赖或继承旧告警例外，相对此前 Public 候选 d7508f7 未改锁文件；相对 Public main 已有的 Playwright 精确锁定仍保留。浏览器环境参数仅用于受控视觉 QA。
本地提交已按环境/测试修正、获批图片采用、复验报告分开。正式内核锁、历史标签、main、原工作树和 DVSK 均未改动。
本地技术门禁已满足，发布授权、远端 CI、Architect Review 与所有者审批仍待完成，不能据此宣布 Issue 已完成或可进入 M1。
若以后合并，使用新的 revert PR 回滚本轮环境选择和采用提交，保留历史与标签；恢复前一候选可能重新出现已记录的历史视觉失败，必须重跑并如实报告。

证据快照 `acceptance-evidence-index.json` SHA256：`af3ca5cde673eb94bd875ea742c70fc15f5541eae3cfb53d013fdb47f927cbf0`。原始路径、日志、截图和 XML 留在仓库外；公开报告仅提供安全文件标签与哈希。文档提交及其最终扫描另有本地交付记录，避免循环哈希。

| 本地证据标签 | SHA256 |
| --- | --- |
| `code-checkpoints.json` | `92e71e282f2c5170440e5e842230724b3d747ef27dbac58cb880a46e8a3a04bb` |
| `asset-review.json` | `b02ee5863c2ad652ae0ad21966a56c41aacd193e9d15793ed305c92a694d762f` |
| `adoption-source.json` | `ceed6b9ea8647ae061d0892ec90b7e5a4c6fe31b5cec7395ddde2db00775b3c2` |
| `windows-environment-detail.json` | `a846c6c31026db904d891de1c9ff698fc117d4d006e4d3bd70bd58915cd734f8` |
| `wsl/app/environment.json` | `8313cabf4f08ccdc9a92023f84982e2f20061bfa1e1dd279d1db01894e3f721f` |
| `windows-full.xml` | `11eeac3ec8dca36cb4aab22e15a983080eb7ccb904b024ab787ac80fff6794a7` |
| `windows-engine-full.log` | `c4e5bc0352a0ebf0ba9afea023ee5c92556e0dc11dcd6fbb46605ea5dc37ecc7` |
| `wsl/full.xml` | `e3c226de554d64280a4c5e83d829b9407e864c9894f4ae06a6d52af0d5ceccc6` |
| `wsl/full.log` | `101042a509f1994ea5dabd74ab99c30faf101a69e64e214875024d0c7313f875` |
| `engine-fast-final.log` | `165c77d36c54b3c774d80b24dd053d86caa1370f6718e3f51e58e9138da53c74` |
| `wsl/fast.log` | `144e9faa563ba6128fc0884cf0503243cef6c07d1a69882d93202a82745fe909` |
| `line-limits.log` | `be69cbae4de3bcfbb5d921250e8b5e9151698fec1cf0ee64938e542bd27dd0c8` |
| `windows-app-install.log` | `c9eb5c14d36455cbbfbfeb42526af5aadf3098b085d223bd6bd51ee72258ebfd` |
| `windows-app-validate.log` | `b2a3402d81012bd2f15521beeefa1814e119d1d4d00ada2ea463f82c474dd7af` |
| `windows-app-portable.log` | `379958cc75a1bbdcaa592fa0cc89d2f9f47c489b9b50de940bc34330f2b06a2c` |
| `windows-app-integration.log` | `552391fdbe8403095b56391b51b856267664cfca242547ea3ccec005409950be` |
| `windows-app-geometry.log` | `cf2e4712a433c14b7caa32960bf479136c61d47b9a13672603b301184186f079` |
| `windows-app-pixel-final.log` | `a0476ef73763739a18aef871013d771173760b0c5bb71dbb847fe958ad0d97c6` |
| `windows-app-production-final.log` | `66c7f7b9b957ae35f61a3baa334746776a53ecec7b40d76e8ab071dd18303266` |
| `windows-app-build-final.log` | `a9fda6655e96dc7531d74777bd1b058f607dde69d925fbe4c20079e6e7c181ee` |
| `wsl/app/validate.log` | `d58959e0d4c221c95ff63bf155798da61ac9b1362d61179ac17a92533ec630df` |
| `wsl/app/portable.log` | `7746971f55ab13504649a789b27ce5cbe229f8c948f8494bf69c2cd626d6a23a` |
| `wsl/app/integration.log` | `6dd55f71e6f98285fd452c58df9025859d4eac4595e4773520af79e890bf798d` |
| `wsl/app/geometry.log` | `ba449aa0db99fa89f5cdfdb36ff2be6e9f67fa5a83a866a7ddda7f36985067a3` |
| `wsl/app/pixel.log` | `741e1b9fa0908ad13215cb6e9d63b07d832609fce7da1b36157cf9c3b33f1051` |
| `wsl/app/production.log` | `91265fe259a13506dda7280aa3e0f4b1d41d50160db87b9b0e4ed67cb729fe01` |
| `wsl/app/build.log` | `37e08569177580bc922a6e1d22fec4e9b6309dd390060e482c4e9a24f0a10b2c` |
| `windows-app-audit-full.log` | `6cadcf2e93ca634e41afe74f167d3a4f653bef848f631edcb2b577d84b5870b9` |
| `windows-app-audit-prod.log` | `36872159045ec6e4454410c8f52e9219e00a49a67cc78a3a520e3a3744ac15bf` |
| `wsl/app/audit-full.log` | `6cadcf2e93ca634e41afe74f167d3a4f653bef848f631edcb2b577d84b5870b9` |
| `wsl/app/audit-prod.log` | `36872159045ec6e4454410c8f52e9219e00a49a67cc78a3a520e3a3744ac15bf` |
| `python-audit-windows.log` | `4dd340b571e44b9faf9f72edddb8b9888bf3f4fb8c86915e3767842b66bcd656` |
| `wsl/python-audit.log` | `5a3f6af3f16a44c3fb2f76cdaa252248b7f87a23d7fcf24c3c9ddd355e10388a` |
| `engine-secrets.log` | `ad0207fcabc97d0e8d82ec83fcc25e97bbd605a94d72cd14b26ef49efdee31d1` |
| `app-secrets.log` | `34ebe5ab94ce368770bc0e3a884248c3ac997aadb3ee520f80a8d75f73c1cb74` |
| `windows-app-orchestration-note.json` | `6e8e66d21628fdf144936c0523dfd65a83d2ac24a432eabb18ccfa7dcc22ee40` |
| `windows-executed-harness.txt` | `c2a27e12e893a4b7bc16472298f8f5bb0215b71cd2722683415c5f5e48b693c6` |
| `wsl-executed-harness.txt` | `90b01dd889b5fbe84ddcc6e0fb2aad8502c91b1b5efaacf12cbefa3f9706be05` |
| `wsl/production-harness.ts` | `4268403ecb3f8a7a05708a833078435425bc40f1039804d3232ba2abb5e16ed6` |
| `windows-pixel-evidence-index.json` | `1af88806c3eef6b78e8afa44e1c1837af0a0db426afbd1e92326e2163f28be31` |
| `wsl-pixel-evidence-index.json` | `4a43236a58231f2c036c4e1717a6968cf708a57e19b34cf630bf75d05ecaa858` |
| `windows-app-final-captures/capture-integrity.json` | `4af5b5ccb66eca39fe192757deda1f24718c447f83ab48dd8da68217c2367d08` |
| `wsl/app-final-captures/capture-integrity.json` | `c00f3c8b9b077baf1ccd33773e3f2c7489ede24d967ee9f0f556577f4809d95c` |

## 正式采用前的历史记录

以下原文保留此前状态与失败，不代表当前验收结论。

<details>
<summary>展开正式采用前的完整复现报告</summary>

# Public PPT Issue #1 独立复现报告

**状态：Blocked，本地候选待审，不是冻结或放行。**

## 本轮最小修复与原状证据

我跑过：原 Public 内核在 WSL2 快测 55 passed / 111 deselected；Windows 受控 UTF-8 快测 52 passed / 3 failed / 111 deselected。
Windows 初次未统一 UTF-8 的探索运行还出现大量编解码失败，日志原样保留为环境诊断，没有改写为正式复现结果。
两平台原状视觉选测均 2 passed / 3 failed：圆形宽高、历史 Golden、颜色变异参照误判。

- `dd0337f`：builder 文本文件显式 UTF-8；新增真实 builder 的中文、emoji、含空格中文路径及关闭 UTF-8 模式回归；修正测试夹具换行和路径分隔符。
- `6d821d7`：颜色变异使用同一环境刚拍的控制图，仍严格要求只改变第 4、5 页；独立原 Golden 零差异断言未动。
- `9483099`：只修正第 8 页 hub 坐标，保持中心和高度；同环境前后逐像素比较仅第 8 页变动 15436 像素，其余八页零差异。原尺寸、光晕等比、标签间距、连线及溢出检查保持不变。
- `f2c33fe`：WSL2 首次候选全测 162 passed / 5 failed，其中四项拖拽保存因 reload 后入口动画未结束而超时。只复用现有动画等待函数；两平台四项原断言通过。保留该失败运行及原样下载→应用→重建的验证。

方案审查：整体迁入旧分支会带入无关依赖及私有历史，10/100；先复现 Public 原状再逐项迁移可证必要修复，95/100。
拖拽测试保留原时序会继续误报，20/100；复用现有等待且保留原断言，95/100；改产品运行时扩大范围，40/100。
正式 Golden 的 9 张 PNG 与清单均未修改，旧候选图片未复制入库。

## 来源与实际验证组合

日期：2026-10-20。关联 [PPT Issue #1](https://github.com/YuLing-Ai-Tech/yuling-ai-ppt/issues/1)。
以下“我跑过”均指本轮从 Public 源独立克隆后执行；旧私有候选结果不作为通过证据。

| 层次 | Python/HTML 内核 | Mini-App |
| --- | --- | --- |
| 冻结标签 `public-baseline-2026-10-20` | `b1a96ad0c335316c9bb46e07ba77f62483a57e85` | `ed8cbb8b316e5b572f45a93faca550a41a3b265e` |
| 本轮克隆的 `main` | `067aed2802ef0633eba4578383033bc82d5d2990` | `ed8cbb8b316e5b572f45a93faca550a41a3b265e` |
| 实际测试的代码候选 | `f2c33fe124e864114020d15b66749025c8bb0046` | `d7508f77ed044ccc3ab9da40bf5a79076c33129e` |

内核 main 相比冻结根提交仅增加 setup-uv CI 修正。报告提交是上述代码候选的文档后继，不能把文档提交冒称为已执行全部测试的代码 SHA。
Windows 与 WSL2 各自 HTTPS 新克隆，再应用本轮 Public 修复提交，得到同一代码 SHA；未导入旧私有 Git 历史。
`ENGINE_BASELINE.json` 仍锁冻结内核 b1a96ad；本次验证使用显式指向各平台新内核克隆的 `PPT_ENGINE_ROOT`，因此结果是候选配对验证，不是冻结版本完整通过。

## 环境与平台边界

| 项目 | 原生 Windows | 独立 Ubuntu WSL2 |
| --- | --- | --- |
| 系统 | Windows 11 x64，build 26200 | Ubuntu 24.04.5 x64，WSL2 kernel 6.18.33.2 |
| Node / pnpm / uv | 22.23.3 / 9.0.0 / 0.13.1 | 22.23.3 / 9.0.0 / 0.13.1 |
| Python | 3.12.10 | 3.12.3 |
| Python Playwright / Pillow / pytest | 1.60.0 / 12.3.0 / 9.1.1 | 1.60.0 / 12.3.0 / 9.1.1 |
| 应用 Playwright | playwright-core 1.64.0 | playwright-core 1.64.0 |
| 实际浏览器 | Edge 155.0.4283.45 | 官方 Chrome for Testing 152.0.7977.64 |
| 视口 | 1920×1080 | 1920×1080 |

Windows 字体清单 SHA256：`f12570aff1d9833f59dc960bd63017bb603d5615cfd67f2601073fec31961f43`。
WSL2 的 242 个系统字体文件清单 SHA256：`69ddcb9591457e78db855ed14a56334d694a2778327701abb7d1658f31b718a4`。
文件逐项哈希保留在本地环境证据，不提交个人绝对路径。
这是独立 Ubuntu 发行版实测；Docker 发行版被保留，Docker 结果没有代替 WSL2。
macOS 路径候选只做代码审查，**未实机验证**。Linux Python、浏览器候选及原生 Windows 的显式路径均实测；不能据此宣称 macOS 兼容验收通过。

## 验证结果（我跑过）

| 检查 | Windows | 独立 WSL2 | 退出码 |
| --- | --- | --- | --- |
| 内核快测及行数门禁 | 56 passed / 111 deselected | 56 passed / 111 deselected | 0 / 0 |
| 内核全部 167 项 | 166 passed / 1 failed / 0 skipped | 166 passed / 1 failed / 0 skipped | 1 / 1 |
| 原 Golden 清单与 PNG 哈希 | 通过 | 通过 | 包含在上述套件 |
| 同环境九页独立截图两次 | 零像素差异，通过 | 零像素差异，通过 | 包含在上述套件 |
| 同环境颜色变异 | 仅第 4、5 页变化，通过 | 同左 | 包含在上述套件 |
| Mini-App 校验 | TypeScript、ESLint 通过 | 同左 | 0 / 0 |
| Mini-App 可移植测试 | 4 项 runner + 38 项 unit，通过 | 同左 | 0 / 0 |
| 候选配对集成测试 | 44 passed / 0 failed / 0 skipped | 同左 | 0 / 0 |
| Mini-App 黄金几何 | 12 pages，通过 | 同左 | 0 / 0 |
| Mini-App 严格像素 | 平台门禁拒绝，**未比较** | 12 页零差异，2 个变异均拒绝 | 1 / 0 |
| Mini-App 生产构建 | Next 16.4.2、tsup 9，通过 | 同左 | 0 / 0 |
| 合成生产形状调用 | 12 页 QA 通过，真实 Python 失败传递通过 | 同左 | 0 / 0 |

校验、可移植测试、构建在内核 `94830997b4e740f44c58622c421f39d5bfd136ca` 与应用上述候选上执行；此后的 f2c33fe 仅修正 Python 拖拽测试等待，不改运行时代码。
f2c33fe 最终配对重新执行了两平台 44 项集成和生产形状路径，以及 WSL2 的 12 页几何、像素检查。没有用旧候选的数量填充新基线结果。

### 唯一完整测试失败与视觉边界

失败：`tests/test_diagram_baseline.py::test_diagram_samples_match_baseline_zero_diff`。
两平台均实际比较并报九页差异，保留首拍、重拍和差异图；不是“未执行”。零像素断言和原 Golden 均保留。
原内核清单记录 Chrome 154.0.8037.58 / Playwright 1.60.0，但没有可核验的系统与字体记录，亦缺少截图 meta.json。
本轮查询并保存的 [官方 CfT 版本索引](https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json)未列出该版本；这不等于证明该浏览器不存在。
因此现有 Edge155 / Chrome152 结果不能宣称原内核黄金视觉通过。第 8 页坐标修复本身也是有意视觉改变，后续必须单独完成视觉治理决定；本任务不替换图片或清单。
Mini-App 的 Linux x64 / Chrome152 / Playwright1.64.0 与其门禁匹配，已实际完成比较；不将该通过结果套用到内核九页 Golden。

### 生产形状证据

使用合成 DeckOutline，经真实 TypeScript builder 包装层调用真实 Python builder，生成单文件 HTML，再由真实浏览器 QA 检查 12 页及语义动画。
验证中文、嵌入 PNG、无外部 HTTP script；现有 44 项集成同时覆盖长中文节点和压缩后仍溢出时的拒绝。
在隔离目录复制实际 builder 并故意缺失样式清单，让 Python 真实以 1 退出；包装层必须抛出 `PPT builder failed (1):`，未用 mock 替代。
Windows HTML SHA256：`94c0bc0e66d08e98941009bc08f2fec1ef1033442ca7c1ca4bff9fb16cb31d6b`。
WSL2 HTML SHA256：`92078ca46ed89373d045576337c457bfbaea0e01e7981d7e85d9c94a565fb23e`。
跨系统换行不同，未声称两者 HTML 字节相同。QA 均为 12 页 passed，motion passed。

## 可复现命令

各平台单独安装依赖，指向本平台新克隆；`PPT_PYTHON_PATH`、`PPT_CHROME_PATH` 显式设置为上述实测工具。
Windows 受控套件设置 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`；新增回归另以 `-X utf8=0` 强制验证文件编解码。
`EVIDENCE_TMP` 是仓库外、每次运行全新的目录；不复用系统历史 pytest 临时目录。

```bash
./tools/ci.sh --fast
uv run --no-project --python 3.12 --with playwright==1.60.0 --with pillow==12.3.0 --with pytest==9.1.1 python -m pytest tests -q --basetemp="$EVIDENCE_TMP" --junitxml="$EVIDENCE_XML"
```

原生 Windows 等价执行同一工具链的 `tools/check_line_limits.py` 及 `pytest -q -m "not slow and not smoke"`，快测也使用独立 `--basetemp`。

```bash
pnpm install --frozen-lockfile
pnpm validate
pnpm test:portable
PPT_ENGINE_ROOT=../yuling-ai-ppt pnpm test:ppt
PPT_ENGINE_ROOT=../yuling-ai-ppt pnpm test:ppt:golden:geometry
PPT_ENGINE_ROOT=../yuling-ai-ppt pnpm test:ppt:golden
pnpm build
pnpm audit --json
pnpm audit --prod --json
```

Windows 使用对应 PowerShell 环境赋值，pnpm 由已核验 Node CLI 启动，无 shell 参数拼接。
两个系统冻结安装通过；另外在仅含审核后 package.json 与锁文件的独立目录完成 Windows 离线冻结安装。
WSL 的官方 GNU SWC 下载曾超时，随后由官方 npm 源取得同一归档并核验锁文件 SHA512，再导入本地缓存冻结安装；未改 registry、依赖版本或锁文件。
生产形状补充检查执行 `pnpm exec tsx <仓库外的生产验证脚本>`；该脚本调用本仓实际 builder/QA，原始脚本及两平台执行版本哈希一并留存于本地证据索引。
Python 审计执行 `uv tool run --from pip-audit pip-audit --path <实际 site-packages> --format json --progress-spinner off`；对 builder、测试 overlay 和最终工具宿主分别传入实际路径。秘密扫描执行 `gitleaks git --redact --no-banner --log-opts=--all --report-format json --report-path <仓库外报告> .`，另外人工复核完整历史与待提交文件清单。
Windows 清理工具后的首次快测遇到系统旧 pytest 临时链接权限错误（退出 1），换用本轮独立临时目录后 56 项通过（退出 0）；失败日志保留，不删除历史临时目录或修改测试断言。

## 安全结论与人工复核

我跑过：本轮最终完整和生产 pnpm 审计均为零告警，muted 为空；WSL2 对应审计也为零。
构建 Python 环境及最终隔离 uv 宿主与实际测试 overlay 分别审计，均未发现已知漏洞。初次工具宿主审查发现的问题及处置细节只保留本地安全记录；已换成无 pip 种子的独立 uv 0.13.1 宿主，未修改旧档案。
完整套件是在该工具宿主清理前启动的诊断运行；清理后重新核对同版本测试包、执行快测，并在 Windows 重新运行四项真实拖拽保存测试。工具宿主变更不修改代码候选或构建用 Python 环境，不将前后环境混称同一执行记录。
最终锁文件核验：sharp 0.35.5、PostCSS 8.5.31、esbuild 0.28.2。没有沿用旧私有候选的告警例外。
完整 Public 历史秘密扫描无命中；路径与内容审查未发现真实 env、私钥、CSV、客户资料、真实联系方式、培训站点或缓存/生成物被提交。
二维码相关 CSS、样板占位文字和测试语境经过人工复核，未发现实际联系方式或二维码数据；官方文档/包仓库、本地回环链接按用途保留。
唯一需确认的上游 Git 作者身份，仓库所有者已于本轮明确批准公开保留；本报告不展示其地址，新候选提交仅用 GitHub 匿名身份。
新增资产仅为 UTF-8 回归中的合成文字；没有提交旧私有图片、客户资产或生成截图。
上述是扫描覆盖范围内的结论，不是安全绝对保证，也不替代 Architect、所有者和远端 CI 的审查。

## 回滚与后续门禁

提交按兼容修复、测试修正、样板坐标、应用版本锁及报告拆分，可分别审查；若以后合并，使用新的 revert 分支和 PR，依赖清单/锁文件同步恢复后重跑配对验证。
不改写 main、不移动标签、不删除工作树，不创建稳定标签。本轮没有推送、发布 PR、合并或部署。
内核原 Golden 与环境来源仍阻塞验收；还需公开材料发布批准、两仓 Draft PR、远端 CI、Architect Review 和所有者审批。
最终内核合并 SHA 确定后，再通过单独审查更新应用正式内核锁并重跑配对验证。DVSK 不在本轮修改范围。

## 本地证据索引

原始失败、截图、XML、命令/退出码、工具来源与字体清单均保存在仓库外；公开报告只保留无个人路径的文件标签及 SHA256。
`review-evidence-index.json` SHA256：`22e7400f63d0574e76a88fe654d6b91b6602ee52b62b7e0db78210a5c432a805`。该索引是下表所列验证材料的不可变快照，不是之后文档提交和最终秘密扫描的循环哈希。

| 本地证据标签 | SHA256 |
| --- | --- |
| `final-windows-fast.log` | `07eedb3238f02f40a3ecd5dc398af3bb6c1559c063836a8bcad9368045ad3b75` |
| `final-windows-full.log` | `269414fe192720e1c66dbf12b4f69d49ec01430e148b36809085afbab78f6c13` |
| `final-windows-full.xml` | `b68f0ab117dea013e67dfe05b0cd5aeea2bd8919d7515e4f124ae993f18d1b22` |
| `wsl/final-wsl-fast.log` | `69197a4dc24163bdaf82f6e01ad16e6da27e9a62b4f33696a887597bde2f7a1a` |
| `wsl/final-wsl-full.log` | `1ff45620823331e7e8ade5642fc057e2c36f89862d9c7aaf0b01cdbfedc04eac` |
| `wsl/final-wsl-full.xml` | `8efcf2e9e303066cd6f0be2711080dd42a57ea6e26ab37a64a3b01ab9245b644` |
| `final-windows-integration.log` | `2a0ddccb27017fcec406b7ebf6dc23382eb6303c8a2596914f08ae4ce181df97` |
| `final-windows-production.log` | `66c7f7b9b957ae35f61a3baa334746776a53ecec7b40d76e8ab071dd18303266` |
| `wsl/final-app/integration.log` | `4d4331ff54cd39c5752ea7e0168884d46de6933303f122eb8b8385e0766c5235` |
| `wsl/final-app/geometry.log` | `ba449aa0db99fa89f5cdfdb36ff2be6e9f67fa5a83a866a7ddda7f36985067a3` |
| `wsl/final-app/pixel.log` | `741e1b9fa0908ad13215cb6e9d63b07d832609fce7da1b36157cf9c3b33f1051` |
| `wsl/final-app/production.log` | `91265fe259a13506dda7280aa3e0f4b1d41d50160db87b9b0e4ed67cb729fe01` |
| `fixed-windows-validate.log` | `b2a3402d81012bd2f15521beeefa1814e119d1d4d00ada2ea463f82c474dd7af` |
| `fixed-windows-portable.log` | `89929eb62a9e5e8a4dcafbdc3d901ba3c26c9629ead9ca2eae35e84ccf0da011` |
| `fixed-windows-geometry.log` | `cf2e4712a433c14b7caa32960bf479136c61d47b9a13672603b301184186f079` |
| `fixed-windows-pixel.log` | `b5e4349eadfd6424b273451ddcb7d5d05ba44246208a7fe9fdb9d033ad2c63b6` |
| `fixed-windows-build.log` | `509fd0dbee789b301b01343bacd307b3961423841d7240366a9cff4fb6e7fe9b` |
| `wsl/app/validate.log` | `d58959e0d4c221c95ff63bf155798da61ac9b1362d61179ac17a92533ec630df` |
| `wsl/app/portable.log` | `0fde28a950998e6697ccc36539abbbaf1050056671da343bcbfae054fd3ebb42` |
| `wsl/app/build.log` | `face444047ac725c3e13da7882652a04dcbc104514de68cd7a679e16158a2598` |
| `final-audit-full.log` | `6cadcf2e93ca634e41afe74f167d3a4f653bef848f631edcb2b577d84b5870b9` |
| `final-audit-prod.log` | `36872159045ec6e4454410c8f52e9219e00a49a67cc78a3a520e3a3744ac15bf` |
| `clean-python-audit.log` | `a4769d0e9fa915bda036748abf8b0d59290560c944e6dc731272d4252b91c195` |
| `wsl/clean-python-audit.log` | `5a3f6af3f16a44c3fb2f76cdaa252248b7f87a23d7fcf24c3c9ddd355e10388a` |
| `clean-windows-fast-retry.log` | `8bcd8d59d438ab8ece7285cd383084443a4e873a9db5db71abc9839e8ae4d87b` |
| `clean-windows-drag.log` | `e7efc761b687f7bbd1df5c8270cb323152a213587640b8ad0f768cb955004f21` |
| `wsl/clean-wsl-fast.log` | `4524df33187664177fb5da7edea041120734aa30d6bf411660c9e10da52fff90` |
| `hub-only-comparison.log` | `632b5468fc04a6b997c00df943aceaf956f2d038194019a0919f37fcc241f156` |
| `final-source-review.json` | `73a279ca6251f3b18bac5c6d7b45758a7fb6d1298fec99c7a12ebe3b6012fa86` |
| `git-identity-review.json` | `6f046f05d944c335511d892bd0c7e20671bfa857cc2bbb4e7d90346c613867c2` |
| `environment-windows-detail.json` | `23c767e4ff22072d2100fcbec938889339dc1ae8d9edec9c9762cf8a293e2eae` |
| `wsl/final-app/environment.json` | `41535b8d8889229388d9533e24756d71a4519474ad1889e9785f8481e002b620` |
| `browser-official-index.json` | `ccdf97a1a3319ea32687bee6ea08229cc5bc428b2dec49cc86c09831ae716e4b` |
| `windows-pixel-evidence-index.json` | `ff1811c7030affea7b4766fb9b1595bd04dfa20b454e92b44eee4172ba05a0f4` |
| `wsl-pixel-evidence-index.json` | `b22fba808f7ba7082c489761e71aa7498d9d8fa5beffdac45a5bc794734ad313` |
| `production-harness-final-windows.ts` | `6cda81947b1faa7d71b56c4c18bd877d85dfa94ace05c9bda44c5a0dbb42eca9` |
| `wsl/production-harness-final-wsl.ts` | `57738646d63e398b678a0d5f78130a3a267df98e8b53d747067eecdc1a7a9ea0` |


</details>
