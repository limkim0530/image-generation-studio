#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.52.0",
#     "pillow>=10.0.0",
# ]
# ///
"""Generate or edit images via one unified CLI across provider adapters:

- Google Gemini (Nano Banana Pro, Nano Banana 2) — via google-genai SDK.
- OpenAI Images-compatible endpoints such as xAI Grok Imagine — via stdlib urllib.
- OpenAI Responses image generation — via stdlib urllib.

Provider is selected from aliases, explicit provider config, or raw model inference.

Usage examples:
    uv run generate.py -p "prompt" -f out.png                         # Gemini (default)
    uv run generate.py -m nano-banana-2 -p "prompt" -f out.png -r 2K  # Gemini Flash
    uv run generate.py -p "combine" -f out.png -i a.png -i b.png      # Gemini multi-image
    uv run generate.py -m grok -p "prompt" -f out.jpg -r 2K           # xAI Grok Imagine
    uv run generate.py -m grok -p "edit it" -f out.png -i src.jpg     # OpenAI Images edit
    uv run generate.py -m gpt-image -p "prompt" -f out.png            # OpenAI Responses
"""

import argparse
import base64
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path


# ---------------- providers, adapters & aliases ----------------

BUILTIN_PROVIDER_DEFAULTS = {
    "gemini": {
        "adapter": "gemini",
        "default_model": "gemini-3-pro-image-preview",
    },
    "xai": {
        "adapter": "openai_images",
        "default_model": "grok-imagine-image",
    },
    "openai": {
        "adapter": "openai_responses",
        "default_model": "gpt-4.1-mini",
    },
}

BUILTIN_MODEL_ALIASES = {
    "nano-banana-pro": {"provider": "gemini", "model": "gemini-3-pro-image-preview"},
    "nano-banana-2": {"provider": "gemini", "model": "gemini-3.1-flash-image-preview"},
    "grok": {"provider": "xai", "model": "grok-imagine-image"},
    "grok-imagine": {"provider": "xai", "model": "grok-imagine-image"},
    "grok-pro": {"provider": "xai", "model": "grok-imagine-image-pro"},
    "grok-imagine-pro": {"provider": "xai", "model": "grok-imagine-image-pro"},
    "grok-lite": {"provider": "xai", "model": "grok-imagine-image-lite"},
    "grok-imagine-lite": {"provider": "xai", "model": "grok-imagine-image-lite"},
    "grok-2": {"provider": "xai", "model": "grok-2-image"},
    "openai": {"provider": "openai", "model": "gpt-4.1-mini"},
    "gpt-image": {"provider": "openai", "model": "gpt-4.1-mini"},
}

NANO2_ID = "gemini-3.1-flash-image-preview"

GEMINI_MODELS = {
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
}
XAI_MODELS = {
    "grok-imagine-image",
    "grok-imagine-image-pro",
    "grok-imagine-image-lite",
    "grok-2-image",
    "grok-2-image-1212",
}

ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
    "9:16", "16:9", "21:9",
    "2:1", "1:2", "20:9", "9:20", "19.5:9", "9:19.5",
]

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def merged_providers(cfg: dict) -> dict:
    providers = {name: dict(value) for name, value in BUILTIN_PROVIDER_DEFAULTS.items()}
    configured = cfg.get("providers")
    if isinstance(configured, dict):
        for name, value in configured.items():
            if isinstance(value, dict):
                base = providers.get(name, {})
                providers[name] = {**base, **value}
    return providers


def merged_model_aliases(cfg: dict) -> dict:
    aliases = {name: dict(value) for name, value in BUILTIN_MODEL_ALIASES.items()}
    configured = cfg.get("models")
    if isinstance(configured, dict):
        for name, value in configured.items():
            if isinstance(value, dict) and value.get("provider") and value.get("model"):
                aliases[name.lower()] = {
                    "provider": value["provider"],
                    "model": value["model"],
                }
    return aliases


def resolve_provider_adapter_model(args, cfg: dict) -> tuple[str, str, str]:
    providers = merged_providers(cfg)
    aliases = merged_model_aliases(cfg)

    if args.provider == "auto":
        explicit_provider = None
    elif args.provider:
        explicit_provider = args.provider
    else:
        die("--provider must not be empty.")

    def provider_config(name: str) -> dict:
        provider_cfg = providers.get(name)
        if not provider_cfg:
            die(f"Unknown provider {name!r}. Add it to providers in {CONFIG_PATH}.")
        return provider_cfg

    def provider_adapter(name: str) -> str:
        adapter_name = provider_config(name).get("adapter") or name
        if adapter_name not in {"gemini", "openai_images", "openai_responses"}:
            die(f"Provider {name!r} uses unsupported adapter {adapter_name!r}.")
        return adapter_name

    model_arg = args.model
    if model_arg:
        alias = aliases.get(model_arg.strip().lower())
        if alias:
            alias_provider = alias["provider"]
            model = alias["model"]
            if explicit_provider and explicit_provider != alias_provider:
                explicit_adapter = provider_adapter(explicit_provider)
                alias_adapter = provider_adapter(alias_provider)
                if explicit_adapter != alias_adapter:
                    die(
                        f"Alias {model_arg!r} maps to provider {alias_provider!r} "
                        f"using adapter {alias_adapter!r}, but --provider {explicit_provider!r} "
                        f"uses incompatible adapter {explicit_adapter!r}."
                    )
            provider = explicit_provider or alias_provider
        else:
            model = model_arg
            provider = (
                explicit_provider
                or known_provider_for(model)
                or cfg.get("default_provider")
                or "gemini"
            )
    else:
        provider = explicit_provider or cfg.get("default_provider") or "gemini"
        provider_cfg = provider_config(provider)
        model = provider_cfg.get("default_model")
        if not model:
            die(f"Provider {provider!r} has no default_model; pass --model.")

    adapter = provider_adapter(provider)
    return provider, adapter, model


def known_provider_for(model: str) -> str | None:
    if model in XAI_MODELS or model.startswith("grok"):
        return "xai"
    if model in GEMINI_MODELS or model.startswith("gemini"):
        return "gemini"
    if model.startswith("gpt-") or model.startswith("o"):
        return "openai"
    return None


# ---------------- config ----------------

def load_config() -> dict:
    """Read <skill>/config.json. Missing → {}. Unreadable → warn and {}."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Warning: cannot parse {CONFIG_PATH}: {e}", file=sys.stderr)
        return {}


def get_provider_config(cfg: dict, provider: str) -> dict:
    providers = merged_providers(cfg)
    provider_cfg = providers.get(provider, {})
    if provider == "gemini" and not provider_cfg.get("api_url") and cfg.get("api_url"):
        provider_cfg = {**provider_cfg, "api_url": cfg.get("api_url")}
    if provider == "gemini" and not provider_cfg.get("api_key") and cfg.get("api_key"):
        provider_cfg = {**provider_cfg, "api_key": cfg.get("api_key")}
    return provider_cfg


def resolve_credentials(args, cfg: dict, provider: str) -> tuple[str | None, str | None]:
    """Resolve (api_url, api_key) for the chosen provider with precedence:
    CLI flag → provider-specific env var → config.json."""
    env_prefix = {
        "gemini": "GEMINI",
        "xai": "XAI",
        "openai": "OPENAI",
    }.get(provider, provider.upper().replace("-", "_"))
    env_key = f"{env_prefix}_API_KEY"
    env_url = f"{env_prefix}_API_URL"
    key = args.api_key or os.environ.get(env_key)
    url = args.api_url or os.environ.get(env_url)
    provider_cfg = get_provider_config(cfg, provider)
    key = key or provider_cfg.get("api_key") or None
    url = url or provider_cfg.get("api_url") or None
    return url, key


BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
    ),
}


# ---------------- output helpers ----------------

def die(msg: str, code: int = 1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def save_image(img_bytes: bytes, out_path: Path, pil_module) -> None:
    """Save raw image bytes to out_path; format is picked from the file extension.
    RGBA is flattened onto white for formats that can't carry alpha."""
    img = pil_module.open(BytesIO(img_bytes))
    ext = out_path.suffix.lower().lstrip(".")
    fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}.get(ext, "PNG")
    has_alpha = img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info)
    if fmt == "JPEG":
        if has_alpha:
            rgba = img.convert("RGBA")
            bg = pil_module.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            bg.save(out_path, fmt)
        elif img.mode != "RGB":
            img.convert("RGB").save(out_path, fmt)
        else:
            img.save(out_path, fmt)
    elif fmt in {"PNG", "WEBP"} and has_alpha:
        img.convert("RGBA").save(out_path, fmt)
    elif fmt == "PNG" and img.mode not in {"RGB", "RGBA", "L", "LA", "P"}:
        img.convert("RGB").save(out_path, fmt)
    else:
        img.save(out_path, fmt)


# ---------------- CLI ----------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate / edit images with Gemini, OpenAI Images-compatible providers, or OpenAI Responses."
    )
    p.add_argument("-p", "--prompt", required=True, help="Prompt or edit instructions")
    p.add_argument("-f", "--filename", required=True,
                   help="Output path (.png/.jpg/.webp - extension picks the format)")
    p.add_argument("--provider", default="auto",
                   help="Provider config name to use, or auto. Auto uses model aliases, "
                        "then raw model-name inference, then config default_provider.")
    p.add_argument("-m", "--model",
                   help="Model alias from built-ins/config, or raw model ID. "
                        "Defaults to the selected provider's default_model.")
    p.add_argument("-i", "--input", dest="inputs", action="append", metavar="IMAGE",
                   help="Input image(s). Gemini: up to 14 for composition. "
                        "openai_images: sends repeated image[] fields. openai_responses: unsupported.")
    p.add_argument("-r", "--resolution", choices=["1K", "2K", "4K"], default="1K",
                   help="1K/2K/4K. Gemini uses native image_size; OpenAI adapters map "
                        "these to square sizes unless --size is provided.")
    p.add_argument("--aspect-ratio", choices=ASPECT_RATIOS,
                   help="Aspect ratio. Gemini and OpenAI Responses pass this through; "
                        "openai_images uses --size instead.")
    p.add_argument("--size",
                   help="OpenAI Images-compatible adapters: output size, e.g. auto, "
                        "1024x1024, 1536x1024, 1024x1536")
    p.add_argument("--quality", choices=["auto", "low", "medium", "high"], default="auto",
                   help="OpenAI Images-compatible adapters: output quality")
    p.add_argument("--output-format", choices=["png", "jpeg", "webp"],
                   help="OpenAI Images-compatible adapters: requested output format. "
                        "Defaults to the -f extension when possible, otherwise png.")
    p.add_argument("--output-compression", type=int,
                   help="OpenAI Images-compatible adapters: compression level for jpeg/webp outputs")
    p.add_argument("--moderation", choices=["auto", "low"], default="auto",
                   help="OpenAI Images-compatible adapters: moderation setting")
    p.add_argument("--response-format", choices=["url", "b64_json"],
                   help="OpenAI Images-compatible adapters: request url or b64_json responses when supported")
    p.add_argument("--api-key",
                   help="Override provider-specific *_API_KEY env and config 'api_key'")
    p.add_argument("--api-url",
                   help="Override provider base URL. Falls back to *_API_URL env, "
                        "then config 'api_url', then adapter default when available.")
    p.add_argument("--search", choices=["web", "image", "both"],
                   help="Nano 2 only: Google Search grounding (web / image / both)")
    p.add_argument("--thinking", choices=["minimal", "high"],
                   help="Nano 2 only: thinking level. minimal sends budget 0; high sends budget -1")
    p.add_argument("--stream", action="store_true",
                   help="Gemini only: stream text chunks live; image still writes at end")
    p.add_argument("--system-prompt", "--system", dest="system_prompt",
                   help="System instruction / global style prefix. Gemini sends it as "
                        "system_instruction; OpenAI-compatible adapters prepend it "
                        "to the user prompt. Overrides config.json 'system_prompt'.")
    return p.parse_args()


def iter_gemini_parts(response):
    parts = getattr(response, "parts", None)
    if parts:
        yield from parts
        return
    candidates = response.get("candidates") if isinstance(response, dict) else getattr(response, "candidates", None)
    for candidate in candidates or []:
        content = candidate.get("content") if isinstance(candidate, dict) else getattr(candidate, "content", None)
        if content is None:
            continue
        parts = content.get("parts") if isinstance(content, dict) else getattr(content, "parts", None)
        for part in parts or []:
            yield part


# ---------------- Gemini provider ----------------

def build_google_search(types_mod, mode: str):
    type_map = {"web": ["WEB"], "image": ["IMAGE"], "both": ["WEB", "IMAGE"]}
    try:
        return types_mod.GoogleSearch(search_types=type_map[mode])
    except TypeError:
        if mode != "web":
            print(f"Warning: SDK does not support search_types={mode!r}; "
                  "falling back to default web-only grounding.", file=sys.stderr)
        return types_mod.GoogleSearch()


def gemini_generate(args, model: str, api_url: str | None, api_key: str, out_path: Path):
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    is_nano2 = model == NANO2_ID

    client_kwargs = {"api_key": api_key}
    if api_url:
        client_kwargs["http_options"] = types.HttpOptions(
            base_url=api_url.rstrip("/"), api_version="v1beta"
        )
    client = genai.Client(**client_kwargs)

    input_imgs = []
    if args.inputs:
        if len(args.inputs) > 14:
            die(f"Too many input images ({len(args.inputs)}); max is 14 on Gemini.")
        for path in args.inputs:
            if not Path(path).exists():
                die(f"Input image not found: {path}")
            try:
                input_imgs.append(PILImage.open(path))
            except Exception as e:
                die(f"Cannot open {path}: {e}")

    contents = [*input_imgs, args.prompt] if input_imgs else args.prompt

    image_cfg = {"image_size": args.resolution}
    if args.aspect_ratio:
        image_cfg["aspect_ratio"] = args.aspect_ratio

    gen_cfg = {
        "response_modalities": ["TEXT", "IMAGE"],
        "image_config": types.ImageConfig(**image_cfg),
    }
    if args.system_prompt:
        gen_cfg["system_instruction"] = args.system_prompt
    if is_nano2:
        if args.search:
            gen_cfg["tools"] = [types.Tool(google_search=build_google_search(types, args.search))]
        if args.thinking:
            budget = -1 if args.thinking == "high" else 0
            gen_cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=budget)

    verb = "Streaming" if args.stream else ("Processing" if input_imgs else "Generating")
    suffix = f" {len(input_imgs)} input image(s)" if input_imgs else ""
    print(f"{verb}{suffix} with {model} @ {args.resolution}...")

    saved = False
    text_parts: list[str] = []

    def process_part(part):
        nonlocal saved
        if isinstance(part, dict):
            txt = part.get("text")
            inline = part.get("inline_data") or part.get("inlineData")
            data = inline.get("data") if isinstance(inline, dict) else None
        else:
            txt = getattr(part, "text", None)
            inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
            data = getattr(inline, "data", None) if inline else None
        if txt:
            text_parts.append(txt)
            if args.stream:
                print(txt, end="", flush=True)
        if data:
            if isinstance(data, str):
                data = base64.b64decode(data)
            save_image(data, out_path, PILImage)
            saved = True

    config = types.GenerateContentConfig(**gen_cfg)
    try:
        if args.stream:
            for chunk in client.models.generate_content_stream(
                model=model, contents=contents, config=config,
            ):
                for part in iter_gemini_parts(chunk):
                    process_part(part)
            if text_parts:
                print()
        else:
            response = client.models.generate_content(
                model=model, contents=contents, config=config,
            )
            for part in iter_gemini_parts(response):
                process_part(part)
            if text_parts:
                print(f"Model: {''.join(text_parts)}")
    except Exception as e:
        die(f"Gemini API call failed: {e}")

    if not saved:
        die("Gemini returned no image data.")
    print(f"Saved: {out_path.resolve()}")


# ---------------- OpenAI Images-compatible adapter ----------------

def _build_multipart(fields: dict, files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    """Return (body, boundary) for multipart/form-data.
    files is a list of (field_name, filename, content_bytes, content_type)."""
    boundary = "----nano-banana-" + secrets.token_hex(12)
    parts: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())
    for field_name, filename, content, content_type in files:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{filename}"\r\n'.encode()
        )
        parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        parts.append(content)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def _image_mime_type(path: Path) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "application/octet-stream")


def _openai_images_http(url: str, headers: dict, body: bytes, timeout: int = 300) -> dict:
    headers = {**BROWSER_HEADERS, **headers}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        die(f"OpenAI Images HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        die(f"OpenAI Images network error: {e.reason}")
    except Exception as e:
        die(f"OpenAI Images call failed: {e}")


def _download_image_url(url: str, api_key: str | None = None, timeout: int = 120) -> bytes:
    headers = {
        **BROWSER_HEADERS,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://x.ai/",
    }
    auth_error = None
    for include_auth in (False, True):
        request_headers = dict(headers)
        if include_auth and api_key:
            request_headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in {401, 403} and not include_auth and api_key:
                auth_error = e
                continue
            raise
    if auth_error:
        raise auth_error
    raise RuntimeError("image download failed")


def openai_images_size(args) -> str:
    if args.size:
        return args.size
    return {
        "1K": "1024x1024",
        "2K": "2048x2048",
        "4K": "4096x4096",
    }[args.resolution]


def output_format_for(args, out_path: Path) -> str:
    if args.output_format:
        return args.output_format
    ext = out_path.suffix.lower().lstrip(".")
    if ext == "jpg":
        return "jpeg"
    if ext in {"png", "jpeg", "webp"}:
        return ext
    return "png"


def add_openai_image_fields(target: dict, args, out_path: Path, stringify: bool = False) -> None:
    values = {
        "size": openai_images_size(args),
        "quality": args.quality,
        "output_format": output_format_for(args, out_path),
        "moderation": args.moderation,
    }
    if values["output_format"] != "png" and args.output_compression is not None:
        values["output_compression"] = args.output_compression
    if args.response_format:
        values["response_format"] = args.response_format
    for key, value in values.items():
        target[key] = str(value) if stringify else value


def openai_images_generate(args, model: str, api_url: str | None, api_key: str, out_path: Path):
    from PIL import Image as PILImage

    base = (api_url or "https://api.openai.com").rstrip("/")

    # OpenAI Images endpoints have no system role; prepend system prompt to the user prompt.
    effective_prompt = (
        f"{args.system_prompt}\n\n{args.prompt}"
        if args.system_prompt else args.prompt
    )

    if args.inputs:
        # --- image edit via /v1/images/edits (multipart) ---
        print(f"Editing with {model} @ {openai_images_size(args)} (OpenAI Images)...")

        fields = {
            "model": model,
            "prompt": effective_prompt,
        }
        add_openai_image_fields(fields, args, out_path, stringify=True)

        files = []
        for index, input_path in enumerate(args.inputs, start=1):
            in_path = Path(input_path)
            if not in_path.exists():
                die(f"Input image not found: {in_path}")
            files.append(("image[]", f"input-{index}{in_path.suffix}", in_path.read_bytes(), _image_mime_type(in_path)))

        body, boundary = _build_multipart(fields, files)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        }
        endpoint = f"{base}/v1/images/edits"
    else:
        # --- text-to-image via /v1/images/generations (JSON) ---
        print(f"Generating with {model} @ {openai_images_size(args)} (OpenAI Images)...")

        payload = {
            "model": model,
            "prompt": effective_prompt,
        }
        add_openai_image_fields(payload, args, out_path)

        body = json.dumps(payload).encode()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        endpoint = f"{base}/v1/images/generations"

    result = _openai_images_http(endpoint, headers, body)

    data = result.get("data") or []
    if not data:
        die(f"OpenAI Images returned no image data. Raw: {json.dumps(result)[:500]}")

    item = data[0]
    revised = item.get("revised_prompt")
    if revised:
        print(f"Revised prompt: {revised}")

    if item.get("b64_json"):
        img_bytes = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        try:
            img_bytes = _download_image_url(item["url"], api_key)
        except Exception as e:
            die(f"Cannot download image from {item['url']}: {e}")
    else:
        die(f"OpenAI Images response has no b64_json or url. Raw item: {json.dumps(item)[:300]}")

    save_image(img_bytes, out_path, PILImage)
    print(f"Saved: {out_path.resolve()}")


# ---------------- OpenAI Responses adapter ----------------

def _http_json(url: str, headers: dict, payload: dict, timeout: int = 300) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        die(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        die(f"Network error: {e.reason}")
    except Exception as e:
        die(f"HTTP call failed: {e}")


def _is_base64_image_data(value: str) -> bool:
    try:
        base64.b64decode(value, validate=True)
    except Exception:
        return False
    return True


def _find_openai_response_image(value):
    if isinstance(value, dict):
        output = value.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                result = item.get("result")
                if item.get("type") == "image_generation_call" and isinstance(result, str) and result:
                    return result

        for key in ("b64_json", "image_base64", "base64", "result"):
            data = value.get(key)
            if isinstance(data, str) and data:
                return data

        object_type = value.get("type") or value.get("object")
        if isinstance(object_type, str) and "image" in object_type:
            data = value.get("data")
            if isinstance(data, str) and data:
                return data
        data = value.get("data")
        if isinstance(data, str) and data and _is_base64_image_data(data):
            return data

        for child in value.values():
            found = _find_openai_response_image(child)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_openai_response_image(item)
            if found:
                return found
    return None


def openai_responses_generate(args, model: str, api_url: str | None, api_key: str, out_path: Path):
    from PIL import Image as PILImage

    if args.inputs:
        die("openai_responses adapter does not support input image editing yet.")
    if args.search or args.thinking or args.stream:
        print("Warning: --search, --thinking, and --stream are ignored by openai_responses.", file=sys.stderr)

    base = (api_url or "https://api.openai.com").rstrip("/")
    effective_prompt = (
        f"{args.system_prompt}\n\n{args.prompt}"
        if args.system_prompt else args.prompt
    )
    tool = {"type": "image_generation"}
    if args.resolution:
        size_map = {
            "1K": "1024x1024",
            "2K": "2048x2048",
            "4K": "4096x4096",
        }
        tool["size"] = size_map[args.resolution]
    if args.aspect_ratio:
        tool["aspect_ratio"] = args.aspect_ratio

    payload = {
        "model": model,
        "input": effective_prompt,
        "tools": [tool],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    endpoint = f"{base}/v1/responses"

    print(f"Generating with {model} via OpenAI Responses...")
    result = _http_json(endpoint, headers, payload)
    image_b64 = _find_openai_response_image(result)
    if not image_b64:
        die(f"OpenAI Responses returned no image data. Raw: {json.dumps(result)[:500]}")

    try:
        img_bytes = base64.b64decode(image_b64)
    except Exception as e:
        die(f"Cannot decode OpenAI Responses image data: {e}")

    save_image(img_bytes, out_path, PILImage)
    print(f"Saved: {out_path.resolve()}")


# ---------------- main ----------------

def main():
    args = parse_args()
    cfg = load_config()
    provider, adapter, model = resolve_provider_adapter_model(args, cfg)

    # Resolve system prompt: CLI > config.json top-level. Falsy strings ("") drop out naturally.
    args.system_prompt = args.system_prompt or cfg.get("system_prompt") or None

    # provider/adapter-mismatched flag warnings (non-fatal; help users catch typos fast)
    if adapter in {"openai_images", "openai_responses"}:
        bad = [f for f in ("search", "thinking", "stream") if getattr(args, f)]
        if bad:
            print("Warning: --" + ", --".join(bad) +
                  f" are Gemini-only; ignored for adapter {adapter!r}.", file=sys.stderr)
    else:
        is_nano2 = model == NANO2_ID
        if (args.search or args.thinking) and not is_nano2:
            print(f"Warning: --search / --thinking are Nano 2 only; "
                  f"ignoring them for {model!r}.", file=sys.stderr)

    api_url, api_key = resolve_credentials(args, cfg, provider)
    if not api_key:
        env_prefix = {
            "gemini": "GEMINI",
            "xai": "XAI",
            "openai": "OPENAI",
        }.get(provider, provider.upper().replace("-", "_"))
        env_name = f"{env_prefix}_API_KEY"
        die(f"No API key for provider {provider!r}. Pass --api-key, set {env_name}, "
            f"or add providers.{provider}.api_key to {CONFIG_PATH}.")

    out_path = Path(args.filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if adapter == "openai_images":
        openai_images_generate(args, model, api_url, api_key, out_path)
    elif adapter == "openai_responses":
        openai_responses_generate(args, model, api_url, api_key, out_path)
    else:
        gemini_generate(args, model, api_url, api_key, out_path)


if __name__ == "__main__":
    main()
