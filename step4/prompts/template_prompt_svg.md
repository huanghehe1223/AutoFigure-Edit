```
你是一个专业 SVG 重建助手。我要把一张科研示意图重建成可编辑 SVG 模板。

我会提供三类输入：
1. Image 1：原始目标图 figure.png
2. Image 2：SAM 标记图 samed.png，其中图标区域已经被灰色矩形覆盖，并标注了 <AF>01、<AF>02 等编号
3. boxlib.json：每个图标占位区域的精确坐标

你的任务：
请根据原始目标图和 SAM 标记图，生成一个完整的 template.svg 源码。

重要目标：
- 尽可能复现原图的整体布局、文字、箭头、连线、框、背景、颜色、层级关系和视觉风格
- 但是不要绘制真实图标
- 所有被 samed.png 灰色矩形覆盖的区域，都必须在 SVG 中生成为可替换的图标占位符
- 图标占位符必须严格使用 boxlib.json 中的坐标

SVG 尺寸要求：
- 必须使用 boxlib.json 里的 image_size 作为 SVG 尺寸
- 设置 width="{image_size.width}" height="{image_size.height}"
- 设置 viewBox="0 0 {image_size.width} {image_size.height}"
- 不要缩放，不要改变坐标系

图标占位符要求：
对于 boxlib.json 中的每一个 box，都必须生成一个占位符 group。

假设某个 box 是：
{
  "label": "<AF>01",
  "x1": 100,
  "y1": 200,
  "x2": 300,
  "y2": 420
}

则必须生成类似结构：

<g id="AF01">
  <rect x="100" y="200" width="200" height="220" fill="#808080" stroke="black" stroke-width="2"/>
  <text x="200" y="310" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="32" font-weight="bold">&lt;AF&gt;01</text>
</g>

注意：
- g 的 id 必须是去掉尖括号后的编号，例如 <AF>01 对应 id="AF01"
- text 里必须使用 XML 转义：&lt;AF&gt;01，不要直接写 <AF>01
- rect 的 x 必须等于 x1
- rect 的 y 必须等于 y1
- rect 的 width 必须等于 x2 - x1
- rect 的 height 必须等于 y2 - y1
- text 应该居中放在 rect 中心
- 占位符样式必须接近 samed.png：灰色填充 #808080，黑色边框，白色标签文字
- 不要把图标占位符替换为 image，也不要嵌入 base64 图片

非图标区域要求：
- 原图中的标题、说明文字、标签文字都尽量用 <text> 实现
- 原图中的矩形、圆角矩形、圆形、面板、背景块等用 SVG 基础元素实现
- 原图中的箭头、连接线、流程线尽量用 <path> 或 <line> + marker 实现
- 箭头样式、线条粗细、颜色、虚实线、圆角等尽量接近原图
- 可以使用 <defs> 定义 marker、渐变、滤镜、阴影等
- 文字不需要逐像素完全一致，但位置、字号、颜色、层级要尽量接近
- 不要把整张原图作为 <image> 嵌入 SVG
- 不要嵌入任何外部图片链接
- 不要使用 JavaScript
- SVG 必须是合法 XML

输出要求：
- 只输出完整 SVG 代码
- 使用 ```svg 代码块包裹
- 代码块里面必须从 <svg 开始，到 </svg> 结束
- 不要输出解释
- 不要省略任何内容
```

