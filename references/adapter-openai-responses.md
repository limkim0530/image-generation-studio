# OpenAI Responses adapter

Use this reference when the selected provider uses `adapter: "openai_responses"`, or when the user mentions OpenAI Responses, `/v1/responses`, the `image_generation` tool, or image generation through a Responses-compatible proxy.

The implementation lives in `{baseDir}/scripts/generate.py` under `openai_responses_generate`.

## Request shape

The adapter uses stdlib HTTP JSON calls:

- endpoint: `POST {base}/v1/responses`
- base URL: `--api-url` / provider `api_url`, defaulting to `https://api.openai.com`
- authorization: `Authorization: Bearer <api_key>`
- payload includes `model`, `input`, and `tools: [{"type": "image_generation", ...}]`

The prompt is sent as the top-level `input` string. If a system prompt is configured, it is prepended to the user prompt with a blank line.

## Supported operations

- Text-to-image generation through the Responses API image generation tool.
- Resolution mapping to tool `size`.
- Aspect ratio passthrough to the image generation tool.
- Flexible image extraction from several possible response shapes.

## Unsupported operations in this wrapper

- Input image editing/composition is not implemented. If `-i / --input` is provided, the script exits with `openai_responses adapter does not support input image editing yet.`
- Streaming is not implemented for this adapter.
- Search grounding and thinking flags are not implemented for this adapter.
- OpenAI Images-specific fields are not sent.

## Relevant CLI options

| Option | Behavior |
| --- | --- |
| `--provider` | Selects a config provider whose adapter is `openai_responses`. |
| `-m`, `--model` | Model ID or alias for the Responses-compatible provider. |
| `-p`, `--prompt` | Required prompt. |
| `-f`, `--filename` | Required output path. Extension controls final saved format; parent directories are created automatically. |
| `-r`, `--resolution` | Maps to tool `size`: `1K` → `1024x1024`, `2K` → `2048x2048`, `4K` → `4096x4096`. |
| `--aspect-ratio` | Passed into the `image_generation` tool as `aspect_ratio`. |
| `--system-prompt`, `--system` | Prepended to the prompt with a blank line. |

## Ignored or irrelevant options

The script warns and ignores these for this adapter:

- `--search`
- `--thinking`
- `--stream`

These OpenAI Images-style options are accepted by the common CLI but are silently omitted from the Responses payload:

- `--size`
- `--quality`
- `--output-format`
- `--output-compression`
- `--moderation`
- `--response-format`

Use `-r / --resolution` and `--aspect-ratio` instead of `--size` for this adapter.

## Response handling

The adapter searches the JSON response recursively for image data. It first looks for an output item like:

```json
{
  "type": "image_generation_call",
  "result": "<base64 image>"
}
```

It also accepts common keys such as `b64_json`, `image_base64`, `base64`, `result`, or image-like objects with base64 `data`.

If no image data is found, the script exits with `OpenAI Responses returned no image data` and includes the first part of the raw response.

## Good command patterns

Text-to-image:

```bash
uv run {baseDir}/scripts/generate.py --provider my-responses -p "minimal product photo of a matte black lamp" -f outputs/lamp.png -r 1K --aspect-ratio 1:1
```

With a model alias:

```bash
uv run {baseDir}/scripts/generate.py -m my-responses-image -p "wide cinematic desert road at night" -f outputs/road.webp --aspect-ratio 16:9
```

## Common failure causes

- Provider/proxy exposes OpenAI Images endpoints but not `/v1/responses`.
- Selected model does not support the Responses `image_generation` tool.
- User tries to edit an input image with `-i`; use `gemini` or `openai_images` instead.
- Provider ignores or rejects `size` or `aspect_ratio` inside the tool object.
- Response shape lacks extractable base64 image data.
