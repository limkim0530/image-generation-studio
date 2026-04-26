# Configuration assistant

Use this reference when the user wants to configure image-generation-studio providers, models, aliases, API endpoints, API keys, or defaults. This includes casual requests like "Configure this interface for me.", "Add this API address.", "I want to use Grok for visualization.", "config.json is empty, how do I fill it in?."

The goal is to convert the user's natural-language description into a valid `{baseDir}/config.json` update. Keep `SKILL.md` generic for distribution; local `config.json` is user-specific runtime state.

## Configuration shape

`{baseDir}/config.json` may be missing, empty, or `{}`. Treat all of those as an empty config and write a normalized object like:

```json
{
  "default_provider": "my-provider",
  "system_prompt": "",
  "providers": {
    "my-provider": {
      "adapter": "openai_images",
      "api_url": "https://provider.example",
      "api_key": "sk-...",
      "default_model": "image-model-id"
    }
  },
  "models": {
    "friendly-alias": {
      "provider": "my-provider",
      "model": "image-model-id"
    }
  }
}
```

Keep existing providers, aliases, and `system_prompt` unless the user asks to replace or remove them.

## Adapter selection

Choose exactly one adapter for each provider:

| User description | adapter | Read next |
| --- | --- | --- |
| Gemini, Google GenAI, Nano Banana, `gemini-*` models, Google-compatible `generate_content` API | `gemini` | `references/adapter-gemini.md` |
| OpenAI Images API, `/v1/images/generations`, `/v1/images/edits`, `gpt-image-*`, Grok Imagine, xAI image endpoints, most OpenAI-image-compatible proxies | `openai_images` | `references/adapter-openai-images.md` |
| OpenAI Responses API, `/v1/responses` with `image_generation` tool | `openai_responses` | `references/adapter-openai-responses.md` |

If the user says "OpenAI compatible" but does not specify Images vs Responses, ask which endpoint shape their provider exposes. If they mention `/v1/images/generations` or image edits, use `openai_images`. If they mention `/v1/responses`, use `openai_responses`.

After selecting an adapter, read the matching adapter reference before recommending adapter-specific command flags or deciding whether requested features such as editing, multi-image composition, aspect ratio, streaming, search, or response format are supported.

## Natural-language extraction

Extract these fields when present:

- provider name: a short config key such as `gemini`, `xai`, `openai`, `codex`, `newapi`, or a user-provided name. Normalize to lowercase kebab-case.
- adapter: infer from endpoint/model/provider wording using the table above.
- api_url: provider base URL that the CLI can append endpoint suffixes to. For example, convert `https://host/v1/images/generations` to `https://host` only when that base path really exposes `/v1/images/generations`; keep any required proxy prefix in the base URL.
- api_key: secret token. Store it only if the user explicitly gives it for config; otherwise suggest using the provider-specific environment variable.
- default_model: the model ID to use by default for that provider.
- alias: a friendly name under `models`, often the same as the model ID or user phrase like `fast-image`.
- default_provider: set it when the user says this should be the default, or when configuring the first provider in an empty config.
- system_prompt: only set when the user asks for a global style/instruction applied to every image call.

Ask only for missing required information. Required fields for default/no-`--model` use are `provider name`, `adapter`, `default_model`, and either `api_key` in config, a matching environment variable, or user intent to pass `--api-key` per call. If the user will always pass `--model`, `default_model` can be omitted. `api_url` can be omitted for official endpoints, but custom/proxy providers usually need it.

## Updating config.json

When enough information is available:

1. Read `{baseDir}/config.json` if it exists.
2. If it is missing, empty, or invalid JSON, start from `{}`. If invalid JSON has user content, tell the user before overwriting.
3. Ensure top-level `providers` and `models` are objects.
4. Merge the provider entry instead of replacing unrelated providers.
5. Add or update aliases requested by the user.
6. Set `default_provider` only when requested or when the config has no default yet.
7. Write pretty JSON with two-space indentation.

Do not remove existing keys unless the user asks. Do not invent API keys, endpoints, or model IDs.

## Provider-specific environment variables

Provider names map to environment variables by uppercasing and replacing `-` with `_`:

- `gemini` → `GEMINI_API_KEY`, `GEMINI_API_URL`
- `my-images-provider` → `MY_IMAGES_PROVIDER_API_KEY`, `MY_IMAGES_PROVIDER_API_URL`

If the user is uncomfortable storing secrets in `config.json`, write config without `api_key` and tell them which env var to set.

## Confirmation style

After writing config, briefly report:

- provider name and adapter
- default model
- aliases added
- whether it is now the default provider
- where credentials are expected from: config or env var

Then give one concrete test command using `{baseDir}/scripts/generate.py`, `--provider`, and a small output filename.

## Examples

### OpenAI Images-compatible proxy

User: "Please configure `newapi` with the address `https://newapi.example`, key `sk-abc`, and model `gpt-image-2`. Name it `codex` and use it as the default from now on."

Config update:

```json
{
  "default_provider": "codex",
  "providers": {
    "codex": {
      "adapter": "openai_images",
      "api_url": "https://newapi.example",
      "api_key": "sk-abc",
      "default_model": "gpt-image-2"
    }
  },
  "models": {
    "gpt-image-2": {
      "provider": "codex",
      "model": "gpt-image-2"
    }
  }
}
```

### Gemini-compatible provider without storing key

User: "I have the Gemini key, don't want to write it in a file, use gemini-3-pro-image-preview, don't store the key."

Config update:

```json
{
  "default_provider": "gemini",
  "providers": {
    "gemini": {
      "adapter": "gemini",
      "default_model": "gemini-3-pro-image-preview"
    }
  },
  "models": {
    "nano-banana-pro": {
      "provider": "gemini",
      "model": "gemini-3-pro-image-preview"
    }
  }
}
```

Tell the user to set `GEMINI_API_KEY`.
