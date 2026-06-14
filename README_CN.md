# Image Generation Studio

这是一个 **LLM Skill 仓库**，可以让 Agent 通过统一的 CLI 生成、编辑、合成和重绘图片。它支持 Google Gemini 图片模型、OpenAI Images 兼容接口，以及 OpenAI Responses 兼容的图片生成接口。

## 这个 Skill 能做什么

本仓库让 Agent 调用 `scripts/generate.py`，并根据用户配置的 provider、endpoint、model 和 alias 来生成或编辑图片。它设计为可移植的 Skill：
- `SKILL.md` 包含 Agent 使用说明和 Skill 元数据（名称、描述、触发条件）
- `config.json` 是本地运行配置，仅在用户配置自定义 provider 或 alias 时创建
- `references/*.md` 文件提供适配器专属文档，按需加载

支持的适配器：

| 适配器 | Provider/API 形态 | 适合场景 |
| --- | --- | --- |
| `gemini` | Google GenAI `models.generate_content` / streaming API | Gemini 图片生成、图片编辑、多图合成、比例控制、Nano Banana 工作流 |
| `openai_images` | OpenAI Images 兼容的 `/v1/images/generations` 和 `/v1/images/edits` | OpenAI Images 风格接口、xAI/Grok Imagine、兼容接口的图片编辑 |
| `openai_responses` | OpenAI Responses `/v1/responses` + `image_generation` tool | 通过 Responses 兼容接口进行文生图 |

## 环境要求

- Python 3.10+
- PATH 中可用的 [`uv`](https://docs.astral.sh/uv/)
- 所选图片 provider 的 API 凭据，可通过 CLI 参数、环境变量或 `config.json` 提供。内置 provider 可使用 `GEMINI_API_KEY`、`XAI_API_KEY` 或 `OPENAI_API_KEY`，但只需要当前命令所用 provider 的 key，环境变量不是必须的。

脚本在文件头部声明了 Python 依赖：

- `google-genai>=1.52.0`
- `pillow>=10.0.0`

使用 `uv run` 运行时会按需安装到隔离环境中。

## 快速开始

使用默认 provider/model 解析生成图片：

```bash
uv run scripts/generate.py -p "misty mountain at dawn, photorealistic" -f outputs/mountain.png
```

使用 Gemini 兼容 provider，并指定原生分辨率和宽高比：

```bash
uv run scripts/generate.py --provider my-gemini-provider -p "cyberpunk street at night" -f outputs/neon.png -r 2K --aspect-ratio 16:9
```

使用 Gemini 编辑或合成多张图片：

```bash
uv run scripts/generate.py --provider my-gemini-provider -p "place the dog inside the castle courtyard" -f outputs/blend.png -i dog.jpg -i castle.jpg
```

使用 OpenAI Images 兼容 provider：

```bash
uv run scripts/generate.py --provider my-images-provider -p "futuristic cafe product photo" -f outputs/cafe.png --size 1536x1024 --quality high
```

使用 OpenAI Images 兼容的图片编辑接口：

```bash
uv run scripts/generate.py --provider my-images-provider -p "add neon lights and heavy rain" -f outputs/edited.png -i outputs/cafe.png --response-format b64_json
```

使用 OpenAI Responses 兼容 provider：

```bash
uv run scripts/generate.py --provider my-responses-provider -p "change the mug color to matte black" -f outputs/mug-edit.png -i outputs/mug.png --action edit --quality high
```

## 配置说明

本地 provider 配置位于 `config.json`。这个文件是用户专属的运行状态，不随 Skill 分发；如果文件不存在，CLI 会把它当作空配置，并回退到内置 provider 和 alias。用户要求配置 provider 或 alias 时，再在本地创建 `config.json`。

最小配置示例：

```json
{
  "default_provider": "my-images-provider",
  "providers": {
    "my-images-provider": {
      "adapter": "openai_images",
      "api_url": "https://provider.example",
      "api_key": "sk-...",
      "default_model": "image-model-id"
    }
  },
  "models": {
    "fast-image": {
      "provider": "my-images-provider",
      "model": "image-model-id"
    },
    "gemini-nano2-full": {
      "provider": "gemini",
      "model": "gemini-3.1-flash-image-preview",
      "capabilities": ["search", "thinking"]
    }
  }
}
```

### 模型别名的 capabilities 字段

可选的 `capabilities` 数组用于启用 Gemini 高级功能：

- `"search"` - 启用 `--search` 参数进行 Google 搜索 grounding（web/image/both）
- `"thinking"` - 启用 `--thinking` 参数进行扩展推理（minimal/high）

如果未声明 capabilities，Gemini 适配器会警告并忽略 `--search` 和 `--thinking` 参数。其他适配器不使用此字段。

凭据解析优先级：

1. CLI 参数：`--api-key`、`--api-url`
2. provider 对应的可选环境变量，例如 `GEMINI_API_KEY`、`XAI_API_KEY`、`MY_IMAGES_PROVIDER_API_KEY`
3. `config.json` 中的 provider 配置

provider 名称会转换为环境变量前缀：转为大写，并把 `-` 替换为 `_`。

更详细的配置规则见 `references/configuration.md`。

## 常用 CLI 参数

| 参数 | 说明 |
| --- | --- |
| `--provider` | provider 配置名称，或使用 `auto` 自动解析 |
| `-m`, `--model` | 模型别名或原始模型 ID |
| `-p`, `--prompt` | 提示词或编辑指令；必填 |
| `-f`, `--filename` | 输出文件路径；必填 |
| `-i`, `--input` | 输入图片路径；可重复传入，取决于适配器是否支持 |
| `-n`, `--number` | OpenAI Images 请求图片数量；保存为 `file`、`file-2`、`file-3` 等 |
| `-r`, `--resolution` | 支持时可用 `1K`、`2K`、`4K`；OpenAI 兼容适配器还支持 `*-portrait` 竖屏预设 |
| `--aspect-ratio` | Gemini 宽高比，例如 `1:1`、`16:9`、`9:16`；OpenAI 兼容适配器使用 `--size` |
| `--size` | OpenAI 兼容尺寸，例如 `1920x1088`、`1088x1920`、`2560x1440`、`1440x2560`、`3840x2160` 或 `2160x3840` |
| `--quality` | OpenAI 兼容质量参数 |
| `--moderation` | OpenAI 兼容审核参数 |
| `--output-format` | OpenAI 兼容输出格式，例如 `png`、`jpeg` 或 `webp` |
| `--output-compression` | OpenAI Images 上游压缩参数，或 Responses 本地保存质量参数，仅用于 `jpeg`/`webp` 输出 |
| `--background` | OpenAI Responses 图片背景：`auto`、`transparent` 或 `opaque` |
| `--action` | OpenAI Responses 图片动作：`auto`、`generate` 或 `edit` |
| `--response-format` | OpenAI Images 风格返回格式，例如 `url` 或 `b64_json` |
| `--system-prompt`, `--system` | 本次调用的风格/系统指令 |
| `--search` | Gemini 搜索 grounding 模式（需要在 model alias 中声明 `capabilities`） |
| `--thinking` | Gemini thinking 模式（需要在 model alias 中声明 `capabilities`） |
| `--stream` | Gemini 流式文本输出 |

运行 `-h` 或 `--help` 查看所有可用参数及说明。

不同适配器支持的参数不同。推荐 provider 专属参数前，请先阅读对应参考文档：

- `references/adapter-gemini.md`
- `references/adapter-openai-images.md`
- `references/adapter-openai-responses.md`

## 仓库结构

这个仓库遵循标准的 Skill 结构：

```text
.
├── SKILL.md                         # Skill 元数据（名称、描述、触发条件）和 Agent 使用说明
├── config.json                      # 本地运行配置；用户需要时创建，不随 Skill 分发
├── scripts/
│   └── generate.py                  # 统一的图片生成/编辑 CLI
└── references/
    ├── configuration.md             # provider/model/alias 配置指南
    ├── adapter-gemini.md            # Gemini 适配器行为说明
    ├── adapter-openai-images.md     # OpenAI Images 兼容适配器行为说明
    └── adapter-openai-responses.md  # OpenAI Responses 兼容适配器行为说明
```

**Skill 加载机制：**
1. **元数据**（SKILL.md frontmatter：name + description）- 始终在上下文中，用于 Skill 触发判断
2. **SKILL.md 主体** - 当 Skill 被调用时加载
3. **打包资源**（references/、scripts/）- 根据 SKILL.md 引用按需加载

## 分发注意事项

分发此 Skill 时：
- **不要包含 `config.json`** - 它包含用户专属的运行状态，可能含有 API 密钥
- 包含 `SKILL.md`、`scripts/` 和 `references/` 目录
- 用户在本地配置 provider 时会自行创建 `config.json`
- 如果可用，使用 Claude Code 的 skill 打包系统进行打包
