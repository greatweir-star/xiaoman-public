# xiaoman-change Skill

## 能力描述
基于单张素材图，自动分析人物特征，生成小满所需的完整形象素材包。

## 使用场景
- 用户想要自定义小满形象
- 替换小满的头像、引导页、风格预览图
- 批量生成不同风格/场景的形象变体

## 工作流程

### 1. 接收素材图
用户上传一张参考图（真人照片、插画、AI生成图均可）。

### 2. 分析特征
观察并记录图中人物的关键特征：
- 发型、发色、长度
- 五官特点（眼睛、鼻子、嘴型）
- 服装风格、颜色
- 整体气质（清新、成熟、可爱、酷等）
- 年龄段感

### 3. 构建提示词
基于分析的特征，为每个生成任务构建提示词：

| 任务 | 提示词要点 |
|------|-----------|
| avatar | 头像构图、圆形裁切、温柔微笑、匹配参考特征 |
| onboarding | 全身/半身、欢迎姿态、梦幻背景 |
| fresh | 新海诚风格、柔和光线、天空背景 |
| korean | 韩系时尚插画、干净线条、现代感 |
| watercolor | 手绘水彩质感、柔和色调、艺术感 |

### 4. 调用生图
使用 image_gen 工具，传入 ref_image_path（垫图），生成各场景图片。

### 5. 保存到目录
```
web/public/assets/xiaoman/
├── avatar.jpg
├── onboarding.png
└── styles/
    ├── fresh.png
    ├── korean.png
    └── watercolor.png
```

## 小满侧集成（预留）

后端 API 设计：
```python
@app.post("/api/generate-avatar")
async def generate_avatar(file: UploadFile):
    """上传素材图，自动生成全套形象"""
    # 1. 保存上传的图片
    # 2. 调用图像生成服务（GPT Image 2 / 豆包等）
    # 3. 生成全套图片
    # 4. 保存到 assets/xiaoman/
    # 5. 返回生成结果
```

前端集成：
- Onboarding 第三步"选择画风"改为"上传你的形象"或"选择默认形象"
- 设置页增加"更换形象"按钮
- 支持实时预览生成进度

## 示例

**输入：** 一张短发女孩的照片

**输出：**
- avatar.jpg: 温柔微笑的圆形头像
- onboarding.png: 全身站立姿态的插画
- styles/fresh.png: 新海诚风格的清新插画
- styles/korean.png: 韩系时尚插画
- styles/watercolor.png: 温柔水彩手绘
