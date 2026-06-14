# Image Generation Studio

An **LLM skill repository** for generating, editing, composing, and restyling images through a unified CLI. It supports Google Gemini image models, OpenAI Images-compatible endpoints, and OpenAI Responses-compatible image generation providers.

## What this skill does

This repository lets an Agent call `scripts/generate.py` to create or edit images using user-configured providers, endpoints, models, and aliases. It is designed as a portable skill:
- `SKILL.md` contains the Agent-facing instructions and skill metadata (name, description, triggering criteria)
- `config.json` is local runtime configuration, created only when users configure custom providers or aliases
- `references/*.md` files provide adapter-specific documentation loaded on demand

Supported adapters:

| Adapter | Provider/API shape | Best for |
| --- | --- | --- |
| `gemini` | Google GenAI `models.generate_content` / streaming API | Gemini image generation, image editing, multi-image composition, aspect ratio control, search grounding, thinking |
| `openai_images` | OpenAI Images-compatible `/v1/images/generations` and `/v1/images/edits` | OpenAI Images-style providers, xAI/Grok Imagine, image edits through compatible endpoints |
| `openai_responses` | OpenAI Responses `/v1/responses` with `image_generation` tool | Text-to-image through Responses-compatible providers |

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) available in PATH
- Provider API credentials for the selected provider, supplied through environment variables, CLI flags, or `config.json`. Built-in providers use `GEMINI_API_KEY`, `XAI_API_KEY`, or `OPENAI_API_KEY`; only the key for the provider used by a command is needed.

The script declares its Python dependencies inline:

- `google-genai>=1.52.0`
- `pillow>=10.0.0`

`uv run` will install them into an isolated environment as needed.

## Quick start

Generate an image with the default provider/model resolution:

```bash
uv run scripts/generate.py -p "misty mountain at dawn, photorealistic" -f outputs/mountain.png
```

Use a Gemini-compatible provider with native size and aspect ratio controls:

```bash
uv run scripts/generate.py --provider my-gemini-provider -p "cyberpunk street at night" -f outputs/neon.png -r 2K --aspect-ratio 16:9
```

Edit or compose multiple images with Gemini:

```bash
uv run scripts/generate.py --provider my-gemini-provider -p "place the dog inside the castle courtyard" -f outputs/blend.png -i dog.jpg -i castle.jpg
```

Use an OpenAI Images-compatible provider:

```bash
uv run scripts/generate.py --provider my-images-provider -p "futuristic cafe product photo" -f outputs/cafe.png --size 1536x1024 --quality high
```

Use an OpenAI Images-compatible edit endpoint:

```bash
uv run scripts/generate.py --provider my-images-provider -p "add neon lights and heavy rain" -f outputs/edited.png -i outputs/cafe.png --response-format b64_json
```

Use an OpenAI Responses-compatible provider:

```bash
uv run scripts/generate.py --provider my-responses-provider -p "change the mug color to matte black" -f outputs/mug-edit.png -i outputs/mug.png --action edit --quality high
```

## Configuration

Local provider configuration lives in `config.json`. This file is user-specific runtime state and is not distributed with the skill; if it is missing, the CLI treats it as an empty config and falls back to built-in providers and aliases. When a user asks to configure providers or aliases, create `config.json` locally.

Minimal example:

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

### Model alias capabilities

The optional `capabilities` array enables advanced Gemini features:

- `"search"` - Enables `--search` flag for Google Search grounding (web/image/both)
- `"thinking"` - Enables `--thinking` flag for extended reasoning (minimal/high)

Without declared capabilities, `--search` and `--thinking` flags are warned and ignored by the Gemini adapter. Other adapters do not use this field.

Credentials are resolved with this precedence:

1. CLI flags: `--api-key`, `--api-url`
2. Provider-specific environment variables, for example `GEMINI_API_KEY`, `XAI_API_KEY`, `MY_IMAGES_PROVIDER_API_KEY`
3. Provider entries in `config.json`

Provider names are converted to environment variable prefixes by uppercasing and replacing `-` with `_`.

For detailed configuration guidance, see `references/configuration.md`.

## Common CLI options

| Option | Description |
| --- | --- |
| `--provider` | Provider config name, or `auto` for automatic resolution |
| `-m`, `--model` | Model alias or raw model ID |
| `-p`, `--prompt` | Prompt or edit instruction; required |
| `-f`, `--filename` | Output file path; required |
| `-i`, `--input` | Input image path; repeatable for supported adapters |
| `-n`, `--number` | OpenAI Images number of images to request; saved as `file`, `file-2`, `file-3`, etc. |
| `-r`, `--resolution` | `1K`, `2K`, or `4K` where supported; OpenAI-compatible adapters also accept `*-portrait` presets |
| `--aspect-ratio` | Gemini aspect ratio such as `1:1`, `16:9`, or `9:16`; OpenAI-compatible adapters use `--size` |
| `--size` | OpenAI-compatible size such as `1920x1088`, `1088x1920`, `2560x1440`, `1440x2560`, `3840x2160`, or `2160x3840` |
| `--quality` | OpenAI-compatible quality value |
| `--moderation` | OpenAI-compatible moderation setting |
| `--output-format` | OpenAI-compatible output format, such as `png`, `jpeg`, or `webp` |
| `--output-compression` | OpenAI Images upstream compression, or local saved-file quality for Responses, for `jpeg`/`webp` outputs |
| `--background` | OpenAI Responses image background: `auto`, `transparent`, or `opaque` |
| `--action` | OpenAI Responses image action: `auto`, `generate`, or `edit` |
| `--response-format` | OpenAI Images-style response format, such as `url` or `b64_json` |
| `--system-prompt`, `--system` | Per-call instruction/style prefix |
| `--search` | Gemini search grounding mode (requires `search` capability declared in model alias) |
| `--thinking` | Gemini thinking mode (requires `thinking` capability declared in model alias) |
| `--stream` | Gemini streaming text output |

Run with `-h` or `--help` to see all available options and their descriptions.

Adapter-specific support varies. Read the relevant reference before recommending provider-specific flags:

- `references/adapter-gemini.md`
- `references/adapter-openai-images.md`
- `references/adapter-openai-responses.md`

## Repository layout

This repository follows the standard skill structure:

```text
.
├── SKILL.md                         # Skill metadata (name, description, triggering) and Agent instructions
├── config.json                      # Local runtime config; created by users when needed and not distributed
├── scripts/
│   └── generate.py                  # Unified image generation/editing CLI
└── references/
    ├── configuration.md             # Provider/model/alias configuration guide
    ├── adapter-gemini.md            # Gemini adapter behavior
    ├── adapter-openai-images.md     # OpenAI Images-compatible adapter behavior
    └── adapter-openai-responses.md  # OpenAI Responses-compatible adapter behavior
```

**Skill loading behavior:**
1. **Metadata** (SKILL.md frontmatter: name + description) - Always in context for skill triggering
2. **SKILL.md body** - Loaded when skill is invoked
3. **Bundled resources** (references/, scripts/) - Loaded on demand as referenced by SKILL.md

## Notes for distribution

When distributing this skill:
- **Do not include `config.json`** - it contains user-specific runtime state and possibly API keys
- Include `SKILL.md`, `scripts/`, and `references/` directories
- Users create their own `config.json` locally when they configure providers
- Package using Claude Code's skill packaging system if available
