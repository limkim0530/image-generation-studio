---
name: image-generation-studio
description: Generate or edit images with the image-generation-studio CLI through supported adapters (`gemini`, `openai_images`, `openai_responses`) and user-configured providers, endpoints, models, and aliases. Use this skill whenever the user wants to create, edit, compose, or restyle images — including prompts like "make an image", "generate a picture", "edit this photo", "combine these images", "4K poster", or mentions of configured image providers/models such as "nano banana", "Gemini image", "Grok image", "xAI image", "OpenAI image", "OpenAI Responses", "custom image provider", or "gpt-image".
version: 1.1.1
requires:
  bins: ["uv"]
---

# Image Generation Studio

Use this skill by running `uv run {baseDir}/scripts/generate.py`. Treat `{baseDir}/config.json` as local runtime state: it may be empty or omitted in a distributed skill, and users can add their own provider names, API endpoints, default models, and aliases without changing this document.

## Prerequisites

- Python 3.10+
- `uv` available in PATH
- Python dependencies declared in `scripts/generate.py` and installed by `uv run` as needed:
  - `google-genai>=1.52.0`
  - `pillow>=10.0.0`

## Credentials

This skill needs an API key for the provider selected at runtime, but environment variables are optional. The key can come from per-call `--api-key`, a provider-specific environment variable, or `config.json` if the user explicitly accepts local secret storage.

Built-in provider environment variables are `GEMINI_API_KEY` for `gemini`, `XAI_API_KEY` for `xai`, and `OPENAI_API_KEY` for `openai`. Custom providers use `<PROVIDER_NAME>_API_KEY` after uppercasing the provider name and replacing `-` with `_`, they are all optional.

## First step

Choose the relevant reference, then follow that reference for adapter-specific flags, payload behavior, supported operations, and failure handling:

| Situation | Read |
| --- | --- |
| Configure providers, models, aliases, API endpoints, API keys, or defaults | `references/configuration.md` |
| Gemini, Google GenAI, Nano Banana, Gemini image models, multi-image composition, search, thinking, or streaming | `references/adapter-gemini.md` |
| OpenAI Images API, `/v1/images/generations`, `/v1/images/edits`, Grok/xAI image endpoints, `gpt-image-*`, `response_format`, or temporary image URLs | `references/adapter-openai-images.md` |
| OpenAI Responses API, `/v1/responses`, or the `image_generation` tool | `references/adapter-openai-responses.md` |

If the user says only "OpenAI compatible" and does not identify the endpoint shape, ask whether their provider exposes OpenAI Images endpoints or the Responses API before choosing an adapter.

## Generic command shape

```bash
uv run {baseDir}/scripts/generate.py --provider <provider-name> -p "<prompt>" -f <output-file>
```

Common CLI fields are `--provider`, `-m / --model`, `-p / --prompt`, `-f / --filename`, `--api-key`, `--api-url`, and `--system-prompt / --system`. Adapter references define which image-specific flags are sent to each provider.

## Operating rules

- Prefer user-defined aliases and providers from `config.json` over built-in aliases when the user has configured a custom provider or proxy.
- Read the matching adapter reference before recommending provider-specific flags, debugging provider errors, or deciding whether editing/composition, shape control, streaming, search, response format, or other adapter-specific behavior is supported.
- Keep `config.json` sanitized for distribution. Do not invent credentials, endpoints, or model IDs.
- Prefer timestamped filenames to avoid clobbering existing outputs.
- On failure, read the provider error before retrying.
- Do not read generated images back into context unless the user asks; report the saved path instead.
