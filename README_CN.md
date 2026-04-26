# Image Generation Studio

这是一个图片生成 Skill 仓库，可以让 Agent 通过统一的 CLI 生成、编辑、合成和重绘图片。它支持 Google Gemini 图片模型、OpenAI Images 兼容接口，以及 OpenAI Responses 兼容的图片生成接口。

## 这个 Skill 能做什么

本仓库让 Agent 调用 `scripts/generate.py`，并根据用户配置的 provider、endpoint、model 和 alias 来生成或编辑图片。它适合作为可分发的 Skill：`SKILL.md` 负责描述 Agent 使用方式，`config.json` 负责保存本地运行配置，分发时可以保持为空。

支持的适配器：

| 适配器 | Provider/API 形态 | 适合场景 |
| --- | --- | --- |
| `gemini` | Google GenAI `models.generate_content` / streaming API | Gemini 图片生成、图片编辑、多图合成、比例控制、Nano Banana 工作流 |
| `openai_images` | OpenAI Images 兼容的 `/v1/images/generations` 和 `/v1/images/edits` | OpenAI Images 风格接口、xAI/Grok Imagine、兼容接口的图片编辑 |
| `openai_responses` | OpenAI Responses `/v1/responses` + `image_generation` tool | 通过 Responses 兼容接口进行文生图 |

## 环境要求

- Python 3.10+
- PATH 中可用的 [`uv`](https://docs.astral.sh/uv/)
- 图片 provider 的 API 凭据，可通过环境变量、CLI 参数或 `config.json` 提供

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
uv run scripts/generate.py --provider my-responses-provider -p "minimal product photo of a ceramic mug" -f outputs/mug.png --aspect-ratio 1:1
```

## 配置说明

本地 provider 配置位于 `config.json`。这个文件可以是空对象 `{}`，也可以在分发 Skill 时省略，或者填入用户自己的 provider 和模型别名。

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
    }
  }
}
```

凭据解析优先级：

1. CLI 参数：`--api-key`、`--api-url`
2. provider 对应的环境变量，例如 `GEMINI_API_KEY`、`XAI_API_KEY`、`MY_IMAGES_PROVIDER_API_KEY`
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
| `-r`, `--resolution` | 支持时可用 `1K`、`2K`、`4K` |
| `--aspect-ratio` | 宽高比，例如 `1:1`、`16:9`、`9:16` |
| `--size` | OpenAI Images 风格尺寸，例如 `1024x1024` 或 `1536x1024` |
| `--quality` | OpenAI Images 风格质量参数 |
| `--response-format` | OpenAI Images 风格返回格式，例如 `url` 或 `b64_json` |
| `--system-prompt`, `--system` | 本次调用的全局风格/系统指令 |
| `--search` | Gemini Nano 2 搜索 grounding 模式 |
| `--thinking` | Gemini Nano 2 thinking 模式 |
| `--stream` | Gemini 流式文本输出 |

不同适配器支持的参数不同。推荐 provider 专属参数前，请先阅读对应参考文档：

- `references/adapter-gemini.md`
- `references/adapter-openai-images.md`
- `references/adapter-openai-responses.md`

## 仓库结构

```text
.
├── SKILL.md                         # Claude Code Skill 元数据和 Agent 使用说明
├── config.json                      # 本地运行配置；可以保持为空
├── scripts/
│   └── generate.py                  # 统一的图片生成/编辑 CLI
└── references/
    ├── configuration.md             # provider/model/alias 配置指南
    ├── adapter-gemini.md            # Gemini 适配器行为说明
    ├── adapter-openai-images.md     # OpenAI Images 兼容适配器行为说明
    └── adapter-openai-responses.md  # OpenAI Responses 兼容适配器行为说明
```

## 分发注意事项

- 不要把真实 API Key 分发到 `config.json` 中。
- 推荐使用环境变量或每次调用时传入 `--api-key` 管理密钥。
- `SKILL.md` 保持通用说明，本地运行状态放在 `config.json`。
