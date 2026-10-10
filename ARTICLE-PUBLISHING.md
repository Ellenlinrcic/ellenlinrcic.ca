# 文章发布标准流程

## 一次设置后的单一检查命令

在网站项目目录运行 `npm run check:publish`。需要已安装的 Node、npm 与 Python 3；首次获取项目时使用现有锁文件安装依赖 (`npm ci`)。检查自动清空并重建 `_site`，不会提交、推送、部署或发送表单。

## 每次发表文章

1. 确认正文、政策来源、日期、中英文标题及摘要。参考最新 Markdown 文章完整 front matter；使用现有 `article.njk` 与分类（policy-updates、case-strategy-notes、client-reminders）。填写唯一英文 permalink `articles/<slug>.html`，`tags: articles`；中文正文和标题可以保留。
2. 只新增文章及所需图片；图片及内部链接以 `/` 开头。模板负责 canonical、分类列表与首页链接，sitemap 自动加入 Markdown 文章。不要改旧文章、旧网址、模板、表单或设计。
3. 运行 `npm run check:publish`。确认所有文章路由、HTML 输出、canonical、sitemap、静态入口链接、资源、robots 与 404 检查通过；阅读警告。70 是当前基线，新增文章后数量应增加，不固定锁死为70。
4. 查看变更清单，核对只包含获准的文件。报告文章地址、检查结果与例外，等待用户确认提交、推送和部署。
5. 获准后执行发布，等待 Cloudflare Pages 部署完成，再运行 `npm run check:publish -- --live`。该命令同时重新检查本地构建，再检查线上200、404和308、Location、canonical、sitemap与 robots。失败时不得宣称上线检查通过。不会请求 Google 收录。
6. 发布确认后，将新增源文件和图片的 SHA-256 加入 `scripts/seo-baseline.json` 的 protected；不得删除或批量刷新旧指纹。已有源文件变更会失败，只有获准的具体改动经审查后才能更新对应指纹。检查器没有自动绕过选项。

## 当前已知例外

严格按页面、属性和原始链接列入警告，新增其他位置仍报错：
- 首页 `/visitor-visas.html`（2处）：目标不存在。
- `/provincial-nominee-programs` 的 `/ontario-oinp.html`：目标不存在。
- `/image-test` 的 `/images/%20work-permit-pr-banner.jpg`（2处）：诊断页图片路径多了空格。
- `/articles/pgwp-student-hunger-strike-2026`：没有非文章页面静态入口链接。保留旧页面，不擅自补改。

## 结构与部署记录

`src` 混合旧 HTML、Markdown 与一个独立 Nunjucks 文章。Eleventy 的现有 passthrough 复制旧页面/图片，生成新文章及列表。构建命令 `npm run build`，输出 `_site`。现有 sitemap 使用旧页面条目加 `collections.articles`，canonicalUrl 处理 `.html` 到无扩展名网址；保留这些机制，无新增生成器或部署依赖。

Git origin 为 Ellenlinrcic/ellenlinrcic.ca，已知 main 通过 Cloudflare Pages 发布。仓库没有 wrangler 配置、部署工作流或现有测试；Cloudflare 控制台的当前构建设置未在本次独立核实。308 是托管端行为，本地文件存在不证明线上返回308或404。指纹保护整个现有 src，包括内容、表单脚本、设计、图片、robots、headers和模板。

维护检查程序后运行 `npm run test:seo`；测试使用隔离副本注入错误，不修改文章。不测试表单实际送达，也不判断政策内容或 Google 最终收录。
