---
name: image-generation-studio
description: Generate or edit images with the image-generation-studio CLI through supported adapters (`gemini`, `openai_images`, `openai_responses`) and user-configured providers, endpoints, models, and aliases. Use this skill whenever the user wants to create, edit, compose, or restyle images — including prompts like "make an image", "generate a picture", "edit this photo", "combine these images", "4K poster", or mentions of configured image providers/models such as "nano banana", "Gemini image", "Grok image", "xAI image", "OpenAI image", "OpenAI Responses", "custom image provider", or "gpt-image".
version: 1.0.2
metadata:
  requires:
    bins: ["uv"]
---

# Image Generation (Gemini, OpenAI Images-compatible, OpenAI Responses)

Use this skill by running `uv run {baseDir}/scripts/generate.py`. Treat `{baseDir}/config.json` as a local runtime config: it may be empty or omitted in a distributed skill, and users can add their own provider names, API endpoints, default models, and aliases without changing this document.

Model aliases resolve to `{provider, model}`, and each provider declares an adapter that controls the request format (`gemini`, `openai_images`, or `openai_responses`). Built-in aliases are convenience shortcuts; prefer user-defined aliases from `config.json` or explicit `--provider <name>` when the user has a custom provider/proxy. Alias overrides are allowed only when the alias provider and explicit provider use the same adapter.

## Model and provider resolution

The script chooses a provider/model at runtime from CLI flags and the user's local config:

1. `-m / --model` can be a built-in alias, a user-defined alias from `config.json`, or a raw model ID.
2. `--provider` can force a provider config by name. If both an alias and explicit provider are used, their adapters must be compatible.
3. When no provider/model is specified, the script uses the runtime config's `default_provider` and that provider's `default_model`; if the config is empty, the script falls back to its built-in defaults.

For repeatable results, prefer passing `-m <alias>` or `--provider <name>` explicitly instead of relying on implicit defaults.

## Quick start by adapter

Use examples by adapter capability, then replace provider/model names with the user's configured names when needed.

```bash
# Any adapter: text-to-image with runtime default provider/model resolution
uv run {baseDir}/scripts/generate.py -p "misty mountain at dawn, photorealistic" -f mountain.png

# Gemini adapter: aspect ratio + native 1K/2K/4K image_size
uv run {baseDir}/scripts/generate.py --provider my-gemini-provider -p "cyberpunk street at night" -f neon.png -r 2K --aspect-ratio 16:9

# Gemini adapter: edit / compose with multiple input images
uv run {baseDir}/scripts/generate.py --provider my-gemini-provider -p "place the dog inside the castle courtyard" -f blend.png -i dog.jpg -i castle.jpg

# Gemini adapter on a Nano 2-compatible model: search grounding, thinking, and streaming text
uv run {baseDir}/scripts/generate.py -m my-nano2-alias -p "art nouveau jazz festival poster" -f poster.png --search web --thinking high --stream

# openai_images adapter: text-to-image through /v1/images/generations
uv run {baseDir}/scripts/generate.py --provider my-images-provider -p "futuristic cafe product photo" -f cafe.png --size 1536x1024 --quality high

# openai_images adapter: edit through /v1/images/edits when the provider/model supports it
uv run {baseDir}/scripts/generate.py --provider my-images-provider -p "add neon lights and heavy rain" -f edited.png -i cafe.png --response-format b64_json

# openai_responses adapter: text-to-image through /v1/responses with the image_generation tool
uv run {baseDir}/scripts/generate.py --provider my-responses-provider -p "minimal product photo of a ceramic mug" -f mug.png --aspect-ratio 1:1

# Temporary per-call endpoint/key override, without editing config.json
uv run {baseDir}/scripts/generate.py --provider my-images-provider -p "..." -f out.png --api-url https://provider.example --api-key "$MY_IMAGES_PROVIDER_API_KEY"
```

## Configuration

Credentials are resolved per provider with precedence **CLI flag → env var → `<skill>/config.json`**. Prefer environment variables or per-call `--api-key` for secrets; store `api_key` in `config.json` only when the user explicitly accepts local secret storage. Provider names are converted to env var prefixes by uppercasing and replacing `-` with `_`: provider `my-images-provider` reads `MY_IMAGES_PROVIDER_API_KEY` and `MY_IMAGES_PROVIDER_API_URL`. Built-in provider names follow the same pattern, e.g. `gemini` → `GEMINI_API_KEY` / `GEMINI_API_URL`.

Providers own credentials and default models; their `adapter` controls the request format. Model aliases are optional shortcuts to `{provider, model}`. Raw model IDs infer a known built-in provider from the model name when possible, otherwise they use the selected/default provider.

When the user asks to configure providers, models, aliases, API endpoints, API keys, or a blank `config.json`, read `references/configuration.md` and convert the user's natural-language description into a `{baseDir}/config.json` update. Ask only for missing required fields, preserve existing config entries, and do not invent credentials or model IDs.

### Minimal config.json

The file lives at `{baseDir}/config.json`. It may be empty, omitted, or as small as one provider plus one alias:

```json
{
  "default_provider": "my-images-provider",
  "providers": {
    "my-images-provider": {
      "adapter": "openai_images",
      "api_url": "https://provider.example",
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

Persistent `system_prompt` entries in `config.json` are intentionally ignored because they can become hidden global instructions for future calls. Use `--system-prompt` / `--system` only for instructions that should apply to the current invocation. Gemini sends the per-call value as native `system_instruction`; `openai_images` and `openai_responses` prepend it to the user prompt with a blank line separator.

Supported adapters:

| Adapter | Request format | Use when | Details |
|---------|----------------|----------|---------|
| `gemini` | Google GenAI `models.generate_content` / `generate_content_stream` with native `system_instruction` | Provider exposes Gemini image models through the Google GenAI API shape | `references/adapter-gemini.md` |
| `openai_images` | OpenAI Images-compatible `/v1/images/generations` JSON and `/v1/images/edits` multipart requests | Provider/proxy exposes OpenAI Images-style generation or edit endpoints | `references/adapter-openai-images.md` |
| `openai_responses` | OpenAI Responses API `/v1/responses` with the `image_generation` tool | Provider/proxy exposes Responses API image generation and the selected model supports the `image_generation` tool | `references/adapter-openai-responses.md` |

Before choosing flags:

| Need | Use | Avoid |
| --- | --- | --- |
| Input-image edit or composition | `gemini` for multi-image composition, or `openai_images` when the provider/model supports edits | `openai_responses` with `-i` |
| Shape control on `openai_images` | `--size` | `--aspect-ratio` |
| Shape control on `gemini` or `openai_responses` | `-r / --resolution` and optional `--aspect-ratio` | OpenAI Images-only fields unless the adapter reference says they are sent |
| Search, thinking, or streaming | Gemini Nano 2 / Gemini streaming rules in `references/adapter-gemini.md` | Any OpenAI-compatible adapter |

After resolving or choosing an adapter, read the matching adapter reference before recommending adapter-specific flags, debugging provider errors, or deciding whether image editing/composition is supported.

`config.json` contains secrets if `api_key` is stored there. Do not distribute real local config files; ship an empty or sanitized config, or rely on env vars / CLI flags. Do not accept or persist `system_prompt` values from untrusted sources; the CLI ignores persisted `system_prompt` and only honors per-call `--system-prompt`.

## Common options

These options are shared by the CLI, though adapter references define which ones are actually sent to each provider:

- `--provider` — provider config name, or `auto` (default). Auto first uses model aliases, then raw model-name inference, then `default_provider`, then the script's built-in fallback. Explicit providers can override aliases only when their adapters are compatible.
- `-m / --model` — alias from config `models`, a built-in alias, or a raw model ID.
- `-p / --prompt` — prompt or edit instructions (required).
- `-f / --filename` — output path (required). Parent directories are created automatically. Extension picks the final saved format: `.png`, `.jpg`, `.jpeg`, `.webp`; unknown extensions save as PNG. All adapters save through Pillow, so provider bytes may be re-encoded to match the extension.
- `--api-key` / `--api-url` — temporary per-call credential or endpoint override.
- `--system-prompt` / `--system` — per-call style/instruction prefix. Gemini sends it natively; OpenAI-compatible adapters prepend it to the prompt.

## Adapter-specific options

Read only the relevant reference once the adapter is known:

- `references/adapter-gemini.md` — Gemini image generation, image editing/composition with up to 14 inputs, `1K`/`2K`/`4K` native image size, aspect ratio, Nano 2 search/thinking, and streaming behavior.
- `references/adapter-openai-images.md` — OpenAI Images-compatible generation and edits, `size`, `quality`, `output_format`, `output_compression`, `moderation`, `response_format`, URL download behavior, and provider-dependent edit support.
- `references/adapter-openai-responses.md` — OpenAI Responses `/v1/responses` image generation tool, resolution/aspect-ratio mapping, response image extraction, and current lack of input-image editing.

## Notes

- Prefer timestamped filenames to avoid clobbering: `2026-04-18-<name>.png`.
- On failure the script prints the raw provider error and exits non-zero — read it before retrying.
- Don't read the output image back into your context unless the user asks — just report the saved path.
- Some providers add watermark or provenance metadata to generated images.
