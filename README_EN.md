# 🧰 comfyui-Ultra-Tools

**English | [한국어](README.md)**

[![Version](https://img.shields.io/badge/version-2.0.9-blue)](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/tag/v2.0.9)
[![Comfy Registry](https://img.shields.io/badge/Comfy%20Registry-Ultra%20Tools-6f42c1)](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools)
[![License: GPL v3](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)
![UI](https://img.shields.io/badge/UI-English%20%2F%20Korean-orange)

**Twelve practical ComfyUI nodes that take the busywork out of everyday generation.**

Picking, styling and translating prompts; finding and loading images; stamping a watermark on the result; checking model sizes and run times; cleaning up pops in generated audio — each node grew out of a real annoyance in day-to-day ComfyUI work and was refined until it stopped being one. Every node is independent, so you can drop in only the ones you need.

## ✨ Highlights

| | |
|---|---|
| 📦 **Zero extra dependencies** | No pip packages to install. Only libraries that already ship with ComfyUI are used. |
| 🌐 **English / Korean UI** | Node names, menus and help text follow your ComfyUI language setting automatically. |
| 🖥️ **Both canvases** | Built and tested for the new **Nodes 2.0 (Vue)** frontend and the classic LiteGraph canvas. |
| 🔒 **Safe by default** | File browsing stays inside folders ComfyUI manages, and API keys are never written into workflows. |
| 📖 **Per-node manuals** | Detailed manuals for every node are included in the `메뉴얼` (Manuals) folder (Korean). |
| 🔁 **Workflow-stable** | Node IDs and inputs/outputs are kept stable, so your saved workflows keep opening after updates. |

---

## 🗂️ Node Overview

| Group | Node | What it does for you |
|---|---|---|
| ✍️ Prompt | [Prompt Composer](#prompt-composer) | Build a **complete scene prompt from menus** — output tuned for 9 model families |
| ✍️ Prompt | [Prompt Styler](#prompt-styler) | **Keep your prompt as written** and add mood/style in each model's syntax |
| ✍️ Prompt | [Textbox](#textbox) | Up to **32 text slots** in one node, each with its own input and output |
| ✍️ Prompt | [Translator](#translator) | **Translate inside the workflow** — works without an API key, 20 languages |
| ✍️ Prompt | [Wildcard Browser](#wildcard-browser) | Browse wildcard folders and **copy `__folder/file__` with one click** |
| 📁 Image | [Image Load](#image-load) | Core Load Image plus a **thumbnail browser and in-place loading from output folders** |
| 🏷️ Finishing | [Text Watermark](#text-watermark) | Two-block **text watermark** with outline, glow and rotation — 15 fonts bundled |
| 🏷️ Finishing | [Image Watermark](#image-watermark) | **Logo/signature watermark** with tiling, blend modes, shadow and a MASK output |
| 🔊 Audio | [Audio Fade](#audio-fade) | **Removes start-of-clip pops** from generated audio without touching sync |
| 📊 Utility | [Model Viewer](#model-viewer) | Lists the **models the current workflow actually uses**, with file sizes |
| 📊 Utility | [Model Viewer (All)](#model-viewer) | **Scans all model folders by type** to find what's eating your disk |
| ⏱️ Utility | [Workflow Timer](#workflow-timer) | **Live run timer** plus a 100-run history and average |

Search for **`Ultra Tools`** in the node search; all nodes are grouped under the `Ultra Tools` category.

---

## 📦 Installation

### ① ComfyUI Manager (easiest)

Open ComfyUI Manager → **Custom Nodes Manager**, search for **`Ultra Tools`** and install. ([Comfy Registry page](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools))

### ② Git

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git
```

To update, run `git pull` inside the `comfyui-Ultra-Tools` folder.

### ③ Release ZIP

Download the [**v2.0.9 install ZIP**](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.9/comfyui-Ultra-Tools-v2.0.9.zip). It contains a single `comfyui-Ultra-Tools` folder — place that folder inside `ComfyUI/custom_nodes/`. The archive is packed so Korean file names extract correctly.

> ⚠️ When upgrading from an older ZIP, **back up and delete the old folder first**, then add the new one. Extracting on top of an old copy can leave behind files that were removed in newer versions.

After installing or updating, **fully restart ComfyUI** and **hard-refresh the browser (Ctrl+F5)**.

---

## 🚀 Quick Start

- **Example workflow:** drag `이미지 워크플로우/Ultra_Tools_Image_Load_Preview.json` onto the ComfyUI canvas, pick an image in Image Load, and queue it.
- **Handy combinations**

| You want to… | Wire it like this |
|---|---|
| Write prompts in your own language for an English-trained model | Textbox → **Translator** (english) → **Prompt Styler** → CLIP Text Encode |
| Build a prompt just by choosing from menus | **Prompt Composer** (positive / negative) → two CLIP Text Encode nodes |
| Brand your images with a logo and a credit line | Generated image → **Image Watermark** → **Text Watermark** → Save Image |
| Clean the audio pop on MiniMax H3 videos | H3 AUDIO → **Audio Fade** → Create Video |
| Compare generation speed across settings | Drop a **Workflow Timer** anywhere on the canvas (no wires needed) |
| Check which models a workflow needs before sharing it | Drop a **Model Viewer** on the canvas |

---

<a id="prompt-composer"></a>

## 🎨 Ultra Tools Prompt Composer

A prompt builder that **assembles a full scene prompt from menus**, with no external input required. It can also restyle a prompt you already have.

**Great if you…**
- would rather choose *who, where, how it's framed and in what art style* than type a prompt from scratch;
- need the same scene for both natural-language models and tag-based models;
- want to try many art styles quickly with random picks.

**Features**
- **9 model formats**: natural-language models (Z-Image, Krea2, Qwen, Flux), tag-based models (SDXL, Illustrious, Pony, SD 1.5) and the hybrid Anima format. The same choices are rewritten in the syntax each model understands best.
- **22 moods (+3 random modes) × 34 styles**: moods such as noir, gothic romance, cyberpunk, golden hour and vintage film; styles such as watercolor, oil painting, charcoal, pencil, ink wash, pixel art, miniature diorama, 3D figure and chibi. Choose `Auto by Mood` and the node picks a style that suits the mood.
- **15 framings · 17 lens looks** to control shot size and camera feel.
- **Scene builder**: combine subject (person, couple, group, scenery only, product/object), location, time of day, weather, props and lighting. Turn on scene detail enrichment for a fuller scene.
- Menu depth (basic / detailed / full) lets beginners start simple and power users see everything.
- **Conflict cleanup**: words like "photorealistic, DSLR" weaken a watercolor style — the node softens such conflicting terms for you.
- Your own `custom_text` is **never reworded into a different meaning**.
- Outputs a model-appropriate **negative prompt** alongside the positive.

**Tips**
- To style an existing prompt, connect it to `external_positive_in` and start with `balanced`. If the style is too weak, step up to `strong`.
- Random moods (e.g. `🎲 Random All`, `🎲 Random Traditional Media Style`) are seed-driven, so a combination you like can be reproduced.

---

<a id="prompt-styler"></a>

## 🖌️ Ultra Tools Prompt Styler

A styler that **keeps your prompt as intact as possible** and layers mood, style, framing and lens feel on top in the right syntax for each model. Its menus are simpler than Composer's, so it slots straight into an existing prompt pipeline.

**Great if you…**
- want to restyle prompts coming from a text node or another prompt generator;
- have seen odd results from clashing Pony / Illustrious / Anima rating and source tags.

**Features**
- Uses the same model formats, moods, styles, framings and lens looks as Composer.
- **Three style strengths** (`subtle` / `balanced` / `strong`) decide how much of your original wording to protect.
- **Merge position**: append after your prompt (recommended), prepend, or output the style phrase only — handy for mixing with other prompt builders.
- **Preserves weighted syntax** such as `(watercolor wash:1.3)` and repairs broken brackets and stray commas safely.
- Keeps **camera, lens and photorealism terms out of non-photographic styles** like watercolor, pencil and ink wash.
- **Resolves Pony / ILXL / Anima rating and source tag conflicts** automatically — e.g. `rating_safe` and `rating_explicit` never end up together.
- Merges your external negative with the model's default negative **without duplicates**, and avoids negatives that would erase light sources (lamps, candles, neon signs) present in your prompt.

**Tips**
- If a style doesn't take on Anima-family models, try disabling quality, speed or style LoRAs first — they often lock the art style. The manual walks through the checks in order.

---

<a id="textbox"></a>

## 📝 Ultra Tools Textbox

A text node that **manages many independent texts in a single node**.

**Great if you…**
- keep positive prompt, negative prompt, filename prefix and notes in a pile of separate text nodes;
- want to see — and edit — the string another node sends in.

**Features**
- **＋ Add text** grows the node up to **32 slots**. `Text N` is always paired as `IN N → OUT N`; slots never mix.
- **Connecting an input does not grey the slot out.** After a run the slot shows the string it actually received, so you can inspect, copy and edit it.
- **× Delete** any slot in the middle; connections on later slots stay intact.
- **Reorder with ⋀ ⋁** — content, name and wires all move together.
- **Rename** a slot ("action", "background", …) and the output socket is renamed too.
- A **Copy button** on every slot.
- Slot count and contents are saved in the workflow and restored exactly. JSON-looking strings are safely treated as plain text.

---

<a id="translator"></a>

## 🌐 Ultra Tools Translator

A lightweight node that translates text right inside your workflow. Defaults: **translate to Korean**, **auto-detect source language** — just change `target_language` to `english` (or any of the 20 languages). The output is a `STRING`, so it connects to any text or prompt node.

**Features**
- **Works without an API key** using the public MyMemory translation API.
- Free translation can hit `HTTP 429` (too many requests) under heavy use. Save an official **Google Cloud Translation API key** via the node's **Google Translate API settings** button (labelled `Google 번역 API 설정`): the official API is then tried first, with automatic fallback to MyMemory.
- The key is stored **only in this PC's ComfyUI user settings — never in the workflow file**. Sharing a workflow never shares your key, and a saved key is never shown again in the browser.
- **Shares the same key with Ultra MiniMax H3 Prompt** — save it in one node and the other uses it too.
- **Preserve line breaks** keeps line-based prompts structured.
- **Return original text on failure** keeps the workflow running even if translation fails.
- **20 languages**: English, Korean, Japanese, Chinese (Simplified / Traditional), Spanish, French, German, Italian, Portuguese, Russian, Ukrainian, Vietnamese, Thai, Indonesian, Hindi, Arabic, Turkish, Dutch, Polish.

---

<a id="wildcard-browser"></a>

## 🃏 Ultra Tools Wildcard Browser

Walk through your wildcard folders **one level at a time**; click a file and its wildcard call (e.g. `__01_Natural/K-Pop/female_singer__`) is **copied to the clipboard instantly**.

**Great if you…**
- use Impact Pack's wildcard processor and its **"add wildcard" list is empty or clicking does nothing** — copy here and paste there instead;
- have thousands of wildcard files and can never remember the exact path.

**Features**
- **Step-by-step navigation**: click into folders, `📁 ..` to go back. Large folders stay tidy because sub-files aren't dumped all at once.
- Shows only `.txt` `.yaml` `.yml` `.json`; files with the same name and different extensions are grouped.
- Supports symlinks and Windows junctions, and **blocks circular links** automatically.
- Remembers the last sub-folder you were viewing when the workflow is reopened.
- For safety, browsing is limited to **ComfyUI model folders (including `extra_model_paths.yaml`) and `wildcards` / `custom_wildcards` folders inside ComfyUI** (e.g. Impact Pack). The default path is `models/wildcards`.
- It takes no part in generation, so **a missing wildcard drive never breaks image generation**.

---

<a id="image-load"></a>

## 📁 Ultra Tools Image Load

Built **directly on ComfyUI's core Load Image**, with a far better way to pick images. Outputs (IMAGE / MASK) and the upload button match the core node, so it's a **drop-in replacement** for any existing Load Image.

**Great if you…**
- have hundreds of images in `input` and can't find anything from a file-name list;
- keep copying fresh results from `output` into `input` just to reuse them.

**Features**
- **Thumbnail browser** (the *View Input Thumbnails* button)
  - Switch between thumbnail and list views; file-name search; folder filter; thumbnail size slider.
  - Window size and view settings are remembered for next time.
  - Shows each image's resolution, and images with any aspect ratio are shown whole, never cropped.
  - Loads what's on screen first, so even large libraries scroll quickly.
- **Load from output folders in place**: register folders inside ComfyUI `output` and images load from where they are — **no copying into `input`**. Register as many as you like; sub-folders are included, and you see a live preview of a folder's images while browsing for it.
- Click to choose a candidate and press **Select**, or **double-click to apply instantly**. Closing with `Esc` leaves the node's current image unchanged.
- Ctrl/Shift-click to select several images and **delete them in one go**.
- Right-click *Open in new tab*, *Save as* and *Copy image* work on the **original full-resolution file**, not the thumbnail.

> ⚠️ Delete permanently removes the original files. Always check the file list shown before confirming.
>
> ℹ️ Since v2.0.2, to comply with Comfy Registry security policy, folders **outside** ComfyUI can no longer be registered. Upload such images with *choose file to upload*, or move them into the `output` folder.

---

<a id="text-watermark"></a>

## ✒️ Ultra Tools Text Watermark

Adds a **two-block, paragraph-style text watermark** — for example your name on top and your site address below.

**Features**
- Text 1 and Text 2 each get their own **font, size, color, alignment and style**, and both can span multiple lines.
- Per-text **outline**, and **glow** that can be switched on per text.
- Vertical or horizontal layout, block spacing, overall opacity, 9 anchor positions, fine X/Y offsets and **rotation**.
- **15 fonts bundled**, including Korean handwriting fonts and English script fonts (Happy Goheung, Nanum Pen/Brush Script, Binggrae Samanco, Pretendard, Great Vibes and more).
- Drop your own fonts (`.ttf` `.otf` `.ttc` `.otc`) into the `fonts` folder to add them to the list. For safety, system font folders are not read.

---

<a id="image-watermark"></a>

## 🖼️ Ultra Tools Image Watermark

Composites a logo, signature or icon image as a watermark.

**Features**
- Pick the watermark file with the node's **upload/select button**, or connect a Load Image as before. Transparency in PNG / WebP files is applied automatically.
- **Sizes by the visible logo, ignoring transparent padding** (percentage or pixel mode), so a small logo on a large transparent canvas doesn't end up tiny.
- Color invert, solid tint, outline, drop shadow and edge softening.
- 5 blend modes: normal / multiply / screen / overlay / soft light.
- **Tiling**: *full* grid or staggered *diagonal*, with adjustable spacing and rotation — ideal for copy-protection patterns.
- Also **outputs a MASK** of the watermarked area.
- Extreme settings that would blow up memory are **reported clearly before running**, never silently scaled down.

> 💡 Recommended order: original → **Image Watermark** (repeating logo) → **Text Watermark** (credit line) → Save Image

---

<a id="audio-fade"></a>

## 🔊 Ultra Tools Audio Fade

Applies **fade-in / fade-out** to generated audio. Made for models such as MiniMax H3 that can produce a **pop or crackle at the very start** of the audio.

- Just insert it in the AUDIO line. The default is a 0.15 s fade-in; if a pop remains, nudge it up to 0.18–0.20 s.
- 4 curves: smooth / linear / equal_power / exponential.
- **Never changes length, sample rate or audio/video sync**, and never overwrites the source data.
- On very short clips where fade-in + fade-out exceed the clip length, both fades are scaled down proportionally so they don't overlap.

---

<a id="model-viewer"></a>

## 📊 Ultra Tools Model Viewer / Model Viewer (All)

Two **read-only information nodes** for your model files. They never move or delete anything.

- **Model Viewer**: finds the models **the open workflow actually uses** and lists file names and sizes by type. It refreshes automatically when the graph changes — perfect for checking what someone needs before you share a workflow.
- **Model Viewer (All)**: **scans every model folder by type** — Checkpoint, UNET, LoRA, VAE, Text Encoder, CLIP, ControlNet, Upscale and more — showing counts, total size and a ranking of the largest files (top 5–100). Great for disk cleanup.
- Recognizes safetensors, ckpt, pt, gguf, onnx, nunchaku and other model formats.

---

<a id="workflow-timer"></a>

## ⏱️ Ultra Tools Workflow Timer

A **run timer** you simply place on the canvas — no wires required.

- Shows elapsed time **live** while a run is in progress.
- On completion, adds to a **history of the last 100 runs** with **total count and average time**.
- History is kept separately for each workflow tab.
- Perfect for **before/after speed comparisons** when you change models, samplers, resolution or optimization settings.

---

## ❓ FAQ / Troubleshooting

**I installed it but the nodes don't show up.**
Fully restart ComfyUI and hard-refresh the browser (Ctrl+F5). For ZIP installs, make sure the layout is `custom_nodes/comfyui-Ultra-Tools/__init__.py` — not nested one folder deeper.

**Translation suddenly stopped working (HTTP 429).**
That's the free API's rate limit. Wait a little, or save an official API key under *Google Translate API settings*. With *return original text on failure* enabled, your workflow keeps running either way.

**Image Load won't let me register a folder on another drive.**
Since v2.0.2, registration is limited to ComfyUI `input` / `output` for Comfy Registry security policy. Move the images into `output`, or upload them.

**Wildcard Browser doesn't show my wildcard folder.**
Place it in `ComfyUI/models/wildcards`, or in a `wildcards` / `custom_wildcards` folder inside ComfyUI (e.g. Impact Pack). Model paths registered in `extra_model_paths.yaml` can be browsed too.

**How do I use my own font in Text Watermark?**
Copy the font file into `comfyui-Ultra-Tools/fonts/` and restart ComfyUI.

**Where can I find more detail?**
Per-node manuals are in the `메뉴얼` folder (Korean). Bug reports and suggestions are welcome in [Issues](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/issues) — English is fine.

---

## 🧩 Where did Ultra Image + PiD go?

Since v2.0.0, the image-generation and PiD (PixelDiT) upscaling node lives in its own pack, **[Ultra Image + PiD](https://github.com/Yamoon-jjang/comfyui-Ultra-Image-PiD)** — it was moved, not discontinued. Its model dependencies and update cycle differ from the utility nodes, so splitting it keeps Ultra Tools light and stable.

- Only that one node left Ultra Tools; the other 12 nodes keep the same IDs and behavior.
- Old workflows containing `UltraImagePiD` are **not** converted to the new `UltraStandaloneImagePiD` automatically. Install the standalone pack, swap the node in and reconnect it.

---

## 🔗 Companion Nodes

- [**Ultra Image + PiD**](https://github.com/Yamoon-jjang/comfyui-Ultra-Image-PiD) — generate with several image model families from one node, with per-model settings memory and optional PiD upscaling
- [**Ultra Qwen Image Editor**](https://github.com/Yamoon-jjang/comfyui-Ultra-Qwen-Image-Editor) — all-in-one image editing node for the Qwen Image Edit family
- [**Ultra MiniMax H3 Prompt**](https://github.com/Yamoon-jjang/comfyui-Ultra-MiniMax-H3-Prompt) — prompt builder for MiniMax H3 video (T2V / I2V / R2V); shares its API key with Translator

---

## 📝 Recent Changes

| Version | Changes |
|---|---|
| **2.0.9** | Local path privacy — Wildcard Browser and Image Load show ComfyUI-relative paths instead of real disk paths; Text Watermark uses bundled fonts only. Inputs/outputs and workflow compatibility unchanged. ([release notes](RELEASE_NOTES_v2.0.9.md)) |
| 2.0.2 | Image Load external folders limited to ComfyUI input / output (Registry security policy) |
| 2.0.0 | Image + PiD moved to a standalone pack (13 → 12 nodes) |

See [Releases](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases) for the full history.

---

## 🔞 Adult Content Notice

Prompt Composer and Prompt Styler include optional adult (18+) prompt options. They are **off by default** and apply only when you select them. They are intended for adult subjects only and must not be used to depict minors. Users are responsible for what they generate.

---

## 📄 License

- Code, manuals, example workflows and data files: **GNU GPL v3.0** (`LICENSE`)
- Fonts in the `fonts` folder are not covered by the GPL; each keeps its original license → [`fonts/FONTS_LICENSE.md`](fonts/FONTS_LICENSE.md)

Copyright (C) 2026 Yamoon-jjang
