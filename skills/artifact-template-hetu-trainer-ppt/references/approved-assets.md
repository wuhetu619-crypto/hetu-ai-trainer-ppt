# 有效样页索引

路径相对skill根目录。`assets/manifest.json`记录包内文件校验值。先看预览再复制源PPT，保持原生对象、布局与品牌素材。

| 页型 | 源与有效页 | 预览 | 状态 |
| --- | --- | --- | --- |
| 封面 | assets/reference.pptx，第1页 | assets/preview.png | 已确认，按新主题换文案和背景 |
| 个人介绍 | assets/samples/profile-v6.pptx，第2页 | assets/previews/profile.png | 已锁定，完整课程第2页 |
| 鱼骨大纲 | assets/samples/outline-v2.pptx，第1页 | assets/previews/outline.png | 已确认；该文件第2页是旧章节 |
| 章节页 | assets/samples/chapter-v3.pptx，第1页 | assets/previews/chapter.png | 已锁定；新主题生成新功能关系图 |
| 内容背景 | assets/samples/content-circles-v1.pptx，第1页 | assets/previews/content.png | 已确认浅色圆形与留白 |
| 三图标几何 | assets/samples/three-icons-v3.pptx，第1页 | 沿用上行预览的三栏 | 已确认留白；背景以圆形版为准 |
| 流程知识/实操 | assets/samples/knowledge-practice-v2.pptx，第2、3页 | 需要时渲染源PPT | 教学参照；背景遵循最新圆形规则 |

## 固定资源

- assets/brand/logo-dark.png：深色字，浅底用。
- assets/brand/logo-light.png：浅色字，深底用。
- assets/brand/instructor.png：真实讲师原照。
- assets/brand/instructor.json：原文、照片SHA及固定页要求。
- assets/backgrounds/content-circles.png：当前内容背景。
- assets/backgrounds/cover-experience.png：经验主题封面示例，不用于所有新主题。
- assets/backgrounds/chapter-experience.png：书籍展开为步骤/判断的章节背景示例。
- assets/backgrounds/three-concepts-original.png：原手艺/办公/AI三图，不替代其他主题的小图。
- assets/prompts/cover.txt、chapter.txt、content.txt：历史生成提示词，按当前主题和规范改写，不直接复用主题名。

