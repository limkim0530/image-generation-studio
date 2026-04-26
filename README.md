# Image Generation Studio

A skill for generating, editing, composing, and restyling images through a unified CLI. It supports Google Gemini image models, OpenAI Images-compatible endpoints, and OpenAI Responses-compatible image generation providers.

## What this skill does

This repository lets an Agent call `scripts/generate.py` to create or edit images using user-configured providers, endpoints, models, and aliases. It is designed as a portable skill: `SKILL.md` documents the Agent-facing behavior, while `config.json` stores local runtime configuration and can stay empty in a distributed copy.

Supported adapters:

| Adapter | Provider/API shape | Best for |
| --- | --- | --- |
| `gemini` | Google GenAI `models.generate_content` / streaming API | Gemini image generation, image editing, multi-image composition, aspect ratio control, Nano Banana workflows |
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

Local provider configuration lives in `config.json`. The file can be empty (`{}`), omitted in a distributed skill, or filled with user-specific providers and aliases.

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
    }
  }
}
```

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
| `--search` | Gemini Nano 2 search grounding mode |
| `--thinking` | Gemini Nano 2 thinking mode |
| `--stream` | Gemini streaming text output |

Adapter-specific support varies. Read the relevant reference before recommending provider-specific flags:

- `references/adapter-gemini.md`
- `references/adapter-openai-images.md`
- `references/adapter-openai-responses.md`

## Repository layout

```text
.
├── SKILL.md                         # Claude Code skill metadata and Agent instructions
├── config.json                      # Local runtime config; may remain empty
├── scripts/
│   └── generate.py                  # Unified image generation/editing CLI
└── references/
    ├── configuration.md             # Provider/model/alias configuration guide
    ├── adapter-gemini.md            # Gemini adapter behavior
    ├── adapter-openai-images.md     # OpenAI Images-compatible adapter behavior
    └── adapter-openai-responses.md  # OpenAI Responses-compatible adapter behavior
```

## Notes for distribution

- Do not distribute real API keys in `config.json`.
- It is recommended to pass `--api-key` with each call or manage keys via environment variables; write to `config.json` only when the user explicitly accepts local key storage.
- Do not persist `system_prompt` in `config.json`; pass `--system-prompt` only for the current call.
- Keep `SKILL.md` generic; use `config.json` for local runtime state.
