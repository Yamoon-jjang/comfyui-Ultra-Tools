# -*- coding: utf-8 -*-
"""
comfyui-Ultra-Prompt_Styler
A deterministic ComfyUI prompt style node that adapts prompt wording to model-specific rules.

Design goals:
- Build a structured prompt-style blueprint first.
- Render that blueprint differently for tag / natural-language / instruction-following models.
- Keep adult sensuality non-explicit and clearly adult.
- Use director-inspired visual grammar without relying on director names in the final prompt.
- Output a compact prompt text pair: positive_prompt and negative_prompt.
"""

from __future__ import annotations

import copy
import json
import os
import random
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple


NODE_CATEGORY = "Ultra Tools"


MOOD_FAMILIES: Dict[str, Dict[str, Any]] = {
    "Default / None": {
        "anchor": "",
        "emotion": [],
        "avoid": [],
    },
    "Erotic / Sensual": {
        "anchor": "cinematic restrained sensual tension",
        "emotion": ["adult intimacy", "quiet desire", "elegant restraint", "private emotional charge"],
        "avoid": ["explicit sexual act", "pornographic staging", "juvenile styling"],
    },
    "Lyrical / Poetic": {
        "anchor": "lyrical cinematic melancholy",
        "emotion": ["quiet longing", "soft emotional distance", "delicate silence", "lingering tenderness"],
        "avoid": ["overly dramatic posing", "abstract color noise"],
    },
    "Classical / Golden Age": {
        "anchor": "classical studio glamour",
        "emotion": ["timeless elegance", "refined poise", "controlled romance", "graceful stillness"],
        "avoid": ["modern casual clutter", "random streetwear"],
    },
    "Noir / Neo-noir": {
        "anchor": "adult cinematic noir tension",
        "emotion": ["dangerous intimacy", "silent suspicion", "nocturnal desire", "private unease"],
        "avoid": ["flat daylight", "comedy tone"],
    },
    "Dreamlike / Surreal": {
        "anchor": "dreamlike sensual atmosphere",
        "emotion": ["ambiguous emotion", "soft unreality", "subconscious intimacy", "floating calm"],
        "avoid": ["random abstract pattern replacing the subject", "unreadable subject"],
    },
    "Gothic Romance": {
        "anchor": "gothic romantic darkness",
        "emotion": ["romantic unease", "low amber longing", "velvet tension", "haunted elegance"],
        "avoid": ["cartoon horror", "cheap monster props"],
    },
    "Melodrama": {
        "anchor": "lush cinematic melodrama",
        "emotion": ["heightened emotion", "romantic conflict", "expressive stillness", "fragile intensity"],
        "avoid": ["neutral documentary tone"],
    },
    "Fashion Editorial": {
        "anchor": "high-end cinematic fashion editorial",
        "emotion": ["controlled sensuality", "luxury calm", "confident elegance", "gallery-like poise"],
        "avoid": ["messy amateur snapshot", "cheap costume look"],
    },
    "Arthouse Realism": {
        "anchor": "intimate arthouse realism",
        "emotion": ["ordinary private moment", "unposed emotional realism", "quiet sensuality", "natural vulnerability"],
        "avoid": ["over-polished fantasy", "exaggerated glamour"],
    },
    "Pop Neon": {
        "anchor": "stylized pop neon cinema",
        "emotion": ["electric attraction", "modern nightlife energy", "glossy desire", "color-driven tension"],
        "avoid": ["muddy lighting", "desaturated dullness"],
    },
    "Baroque / Operatic": {
        "anchor": "baroque theatrical grandeur with dramatic chiaroscuro and velvet-lit opulence",
        "emotion": ["theatrical intensity", "operatic elegance", "ceremonial drama", "deep chiaroscuro tension"],
        "avoid": ["minimal empty background", "literal picture frame", "decorative outer frame", "ornate border", "gilded border", "framed portrait on wall", "museum frame", "letterbox border", "image border"],
    },
    "Minimalist Psychological": {
        "anchor": "minimalist psychological intimacy",
        "emotion": ["controlled distance", "cold stillness", "subtle pressure", "restrained vulnerability"],
        "avoid": ["busy decoration", "chaotic color palette"],
    },
    "Dark Fantasy Romance": {
        "anchor": "dark fantasy romantic unease",
        "emotion": ["shadowy attraction", "ominous elegance", "mythic sensuality", "chased by darkness atmosphere"],
        "avoid": ["literal skull props", "generic Halloween costume"],
    },
    "Black & White Film": {
        "anchor": "black and white, high contrast monochrome",
        "emotion": ["monochrome drama", "timeless contrast", "classic film mood", "tonal depth"],
        "avoid": ["color", "vibrant color", "saturated color palette"],
    },
    "Golden Hour Warmth": {
        "anchor": "golden hour warm light",
        "emotion": ["warm intimacy", "soft radiance", "sunlit tenderness", "gentle glow"],
        "avoid": ["cold tones", "harsh shadows", "dark mood"],
    },
    "Vintage / Retro": {
        "anchor": "vintage retro photograph",
        "emotion": ["nostalgic warmth", "faded memory", "retro charm", "nostalgic beauty"],
        "avoid": ["modern clean look", "digital sharpness", "ultra-realistic"],
    },
    "Cyberpunk / Sci-fi": {
        "anchor": "cyberpunk neon sci-fi",
        "emotion": ["futuristic tension", "digital edge", "neon isolation", "synthetic atmosphere"],
        "avoid": ["natural landscape", "pastoral calm", "vintage look"],
    },
    "Watercolor / Painterly": {
        "anchor": "watercolor painterly style",
        "emotion": ["soft artistic beauty", "gentle impression", "painted serenity", "delicate color blending"],
        "avoid": ["photorealistic", "sharp detail", "hard edges"],
    },
    "Bright / High-key": {
        "anchor": "bright high-key illumination",
        "emotion": ["cheerful lightness", "clean radiance", "fresh energy", "airy calm"],
        "avoid": ["dark shadows", "moody darkness", "low-key illumination"],
    },
    "Cinematic Widescreen": {
        "anchor": "cinematic widescreen anamorphic",
        "emotion": ["epic scale", "cinematic grandeur", "dramatic scope", "visual storytelling"],
        "avoid": ["snapshot look", "amateur composition", "flat lighting"],
    },
    "Romantic / Soft Focus": {
        "anchor": "romantic soft focus",
        "emotion": ["tender romance", "gentle warmth", "soft intimacy", "dreamy closeness"],
        "avoid": ["harsh light", "cold tone", "sharp clinical look"],
    },
    "Horror / Unsettling": {
        "anchor": "horror dark unsettling mood",
        "emotion": ["creeping dread", "ominous tension", "psychological horror", "eerie silence"],
        "avoid": ["cheerful mood", "bright colors", "comedy tone"],
    },
}

STYLE_DNA: Dict[str, Dict[str, Any]] = {
    "Auto by Mood": {},
    "Neutral / Minimal Carryover": {
        "anchor": "natural visual continuity",
        "lighting": ["controlled natural lighting", "clean readable light"],
        "color": ["balanced color", "natural color balance"],
        "composition": ["clean readable composition", "natural framing"],
        "texture": ["subtle natural texture"],
    },
    "Neon Melancholy / Rain Glass": {
        "anchor": "neon melancholy through rain-soaked glass",
        "lighting": ["warm off-camera interior glow", "neon spill through wet windows", "dim ambient shadows"],
        "color": ["amber", "deep red", "muted cyan", "green neon trace"],
        "composition": ["framing through glass", "mirror reflection", "urban intimacy", "isolated close framing"],
        "texture": ["rain-soaked reflections", "humid haze", "soft motion blur"],
    },
    "Classical Studio Glamour": {
        "anchor": "golden-age studio glamour",
        "lighting": ["broad soft key illumination", "soft shadow lift", "subtle edge highlight", "velvety shadow falloff"],
        "color": ["ivory", "warm gold", "deep brown", "soft champagne"],
        "composition": ["balanced portrait composition", "elegant negative space", "graceful posture"],
        "texture": ["satin fabric", "polished wood", "soft tonal grain"],
    },
    "Baroque Operatic Atmosphere": {
        "anchor": "baroque operatic atmosphere",
        "lighting": ["dramatic chiaroscuro", "warm theatrical spotlight glow", "deep velvet shadow", "candlelit stage glow"],
        "color": ["antique gold tones", "burgundy velvet", "ivory highlights", "deep umber shadows"],
        "composition": ["grand theatrical staging", "opulent interior depth", "ceremonial pose rhythm", "opera-house atmosphere"],
        "texture": ["velvet drapery richness", "painted tonal depth", "polished ornamental surfaces", "rich classical texture"],
    },
    "Noir Chiaroscuro": {
        "anchor": "sharp noir chiaroscuro",
        "lighting": ["hard side light", "venetian blind shadows", "deep black background", "silver edge highlights"],
        "color": ["black", "silver", "smoky gray", "muted burgundy"],
        "composition": ["diagonal shadow bands", "doorway framing", "compressed interior space"],
        "texture": ["smoky air", "wet pavement reflections", "grainy darkness"],
    },
    "Symmetric Psychological Coldness": {
        "anchor": "cold symmetrical psychological cinema",
        "lighting": ["controlled overhead illumination", "cold indirect illumination", "precise shadow geometry"],
        "color": ["cold white", "steel blue", "muted beige", "desaturated red accent"],
        "composition": ["strict symmetry", "architectural framing", "static distance", "centered subject"],
        "texture": ["polished reflective finish", "clean minimal geometry", "sterile interior silence"],
    },
    "Swedish Face Silence": {
        "anchor": "quiet face-centered chamber drama",
        "lighting": ["soft window illumination", "pale diffused illumination", "gentle facial shadow"],
        "color": ["chalk white", "pale gray", "muted skin tones", "dry earth brown"],
        "composition": ["intimate close-up", "still face emphasis", "spare background"],
        "texture": ["linen", "matte skin", "quiet empty wall"],
    },
    "Mediterranean Sunlight": {
        "anchor": "warm mediterranean sensual sunlight",
        "lighting": ["sun-warmed side illumination", "reflected sea light", "late afternoon glow"],
        "color": ["terracotta", "sunlit cream", "sea blue", "olive green"],
        "composition": ["open veranda framing", "wind in fabric", "relaxed diagonal pose"],
        "texture": ["linen-soft texture", "sun-warmed stone texture", "sunlit dust"],
    },
    "French Natural Light New Wave": {
        "anchor": "natural-light nouvelle-vague intimacy",
        "lighting": ["available window light", "soft outdoor bounce", "unpolished daylight"],
        "color": ["muted cream", "faded blue", "soft gray", "natural skin tone"],
        "composition": ["casual off-center framing", "unposed body language", "documentary-like stillness"],
        "texture": ["soft tonal texture", "ordinary apartment details", "creased fabric"],
    },
    "Gothic Candle Velvet": {
        "anchor": "low amber gothic velvet romance",
        "lighting": ["low amber gothic darkness", "low amber glow", "heavy background shadows"],
        "color": ["deep burgundy", "black velvet", "aged gold", "dark wine red"],
        "composition": ["arched doorway framing", "old mansion depth", "romantic negative space"],
        "texture": ["velvet", "lace", "aged wood", "dust in warm low light"],
    },
    "Dream Pastel Diffusion": {
        "anchor": "soft surreal pastel diffusion",
        "lighting": ["diffused glow", "soft rear glow", "gentle bloom around edges"],
        "color": ["misty pink", "lavender", "pearl white", "soft cyan"],
        "composition": ["floating composition", "ambiguous room geometry", "soft-focus depth"],
        "texture": ["gauze", "haze", "glowing fabric"],
    },
    "Fashion Editorial Studio Cinema": {
        "anchor": "studio-cinematic fashion editorial",
        "lighting": ["broad diffused studio illumination", "crisp edge highlights", "controlled glossy highlights"],
        "color": ["black", "cream", "deep red", "metallic accent"],
        "composition": ["magazine cover composition", "controlled pose", "polished editorial finish"],
        "texture": ["silk", "latex-like shine without explicitness", "polished reflective finish", "high-end fabric"],
    },
    "Dark Fantasy Shadow Mass": {
        "anchor": "ominous dark fantasy romance",
        "lighting": ["low warm side illumination", "encroaching darkness", "faint edge glow through mist"],
        "color": ["blackened purple", "deep crimson", "cold blue shadow", "ashen gold"],
        "composition": ["the subject held against a mass of darkness", "large shadow shape in the background", "mythic interior depth"],
        "texture": ["heavy cloak fabric", "mist", "aged stone", "smoky air"],
    },
    "Black & White Classic": {
        "anchor": "black and white, high contrast monochrome",
        "lighting": ["high contrast lighting", "dramatic side light", "sharp highlight", "deep shadow"],
        "color": ["monochrome", "grayscale tones", "silver highlights", "deep blacks"],
        "composition": ["strong tonal contrast", "classic composition", "dramatic framing"],
        "texture": ["tonal grain", "monochrome print texture", "classic tonal feel"],
    },
    "Golden Hour Glow": {
        "anchor": "golden hour warm glow",
        "lighting": ["golden hour illumination", "warm rear glow", "soft radiant halo", "edge highlight glow"],
        "color": ["warm amber tones", "golden highlights", "soft orange", "warm shadows"],
        "composition": ["backlit composition", "natural framing", "open airy feel"],
        "texture": ["soft bloom", "warm haze", "soft tonal grain"],
    },
    "Vintage Film Look": {
        "anchor": "vintage retro aesthetic",
        "lighting": ["soft vintage illumination", "warm shadow lift", "faded highlights"],
        "color": ["faded warm tones", "retro color palette", "desaturated pastels", "aged color shift"],
        "composition": ["casual vintage framing", "relaxed composition", "snapshot feel"],
        "texture": ["aged surface texture", "faded edge glow", "worn material texture", "soft vignette"],
    },
    "Cyberpunk Neon": {
        "anchor": "cyberpunk neon atmosphere",
        "lighting": ["neon glow", "holographic glow", "electric blue glow", "pink magenta edge glow"],
        "color": ["electric cyan", "hot magenta", "neon purple", "dark background"],
        "composition": ["dynamic angle", "futuristic framing", "layered depth"],
        "texture": ["glossy surface", "wet reflections", "digital noise"],
    },
    "Soft Romantic Glow": {
        "anchor": "romantic soft focus glow",
        "lighting": ["soft warm illumination", "gentle rear glow", "diffused glow", "warm edge glow"],
        "color": ["warm pink tones", "soft peach", "creamy highlights", "gentle warmth"],
        "composition": ["close intimate framing", "soft focus depth", "gently blurred background"],
        "texture": ["soft bloom", "dreamy haze", "smooth skin texture"],
    },
}

AUTO_STYLE_BY_MOOD = {
    "Default / None": "Neutral / Minimal Carryover",
    "Erotic / Sensual": "Neon Melancholy / Rain Glass",
    "Lyrical / Poetic": "Soft Romantic Glow",
    "Classical / Golden Age": "Classical Studio Glamour",
    "Noir / Neo-noir": "Noir Chiaroscuro",
    "Dreamlike / Surreal": "Dream Pastel Diffusion",
    "Gothic Romance": "Gothic Candle Velvet",
    "Melodrama": "Classical Studio Glamour",
    "Fashion Editorial": "Fashion Editorial Studio Cinema",
    "Arthouse Realism": "Neutral / Minimal Carryover",
    "Pop Neon": "Cyberpunk Neon",
    "Baroque / Operatic": "Baroque Operatic Atmosphere",
    "Minimalist Psychological": "Symmetric Psychological Coldness",
    "Dark Fantasy Romance": "Dark Fantasy Shadow Mass",
    "Black & White Film": "Black & White Classic",
    "Golden Hour Warmth": "Golden Hour Glow",
    "Vintage / Retro": "Vintage Film Look",
    "Cyberpunk / Sci-fi": "Cyberpunk Neon",
    "Watercolor / Painterly": "Watercolor / Painterly",
    "Bright / High-key": "High-key Clean Light",
    "Cinematic Widescreen": "Neutral / Minimal Carryover",
    "Romantic / Soft Focus": "Soft Romantic Glow",
    "Horror / Unsettling": "Dark Fantasy Shadow Mass",
}

ADULT_WARDROBE = {
    "auto": "",
    "nude": "nude",
    "topless": "topless",
    "lingerie": "lingerie",
    "bikini": "bikini",
    "one-piece swimsuit": "one-piece swimsuit",
    "sheer nightgown": "sheer nightgown",
    "silk slip dress": "silk slip dress",
    "corset": "corset",
    "bodysuit": "bodysuit",
    "latex outfit": "latex outfit",
    "leather outfit": "leather outfit",
    "evening dress": "evening dress",
    "tailored suit": "tailored suit",
    "bathrobe": "bathrobe",
    "lace lingerie set": "lace lingerie set",
    "sheer robe": "sheer robe",
    "satin robe": "glossy satin robe",
    "silk camisole": "silk camisole",
    "bralette": "bralette",
    "lace bodysuit": "lace bodysuit",
    "sheer bodysuit": "sheer bodysuit",
    "garter belt": "garter belt",
    "thigh-high stockings": "thigh-high stockings",
    "pantyhose": "pantyhose",
    "open shirt": "open shirt",
    "oversized shirt": "oversized button-down shirt",
    "mini dress": "mini dress",
    "off-shoulder dress": "off-shoulder dress",
    "halter dress": "halter dress",
    "fishnet outfit": "fishnet outfit",
    "vinyl outfit": "vinyl outfit",
    "mesh top": "mesh top",
}

SCENE_FRAMING = {
    "auto": [],
    "headshot (face-focused)": ["headshot", "face-focused framing"],
    "close-up": ["close-up", "tight portrait framing"],
    "upper body": ["upper body shot", "upper body framing"],
    "waist-up": ["waist-up shot", "mid portrait framing"],
    "three-quarter body": ["three-quarter body shot", "knee-up framing"],
    "full body (head to toe)": ["full body shot", "head-to-toe framing"],
    "full shot (full body + extra space)": ["full shot", "full body with extra negative space"],
    "wide shot": ["wide shot", "subject small within the frame"],
    "high-angle portrait": ["high-angle portrait", "slightly elevated viewpoint", "gentle downward framing"],
    "overhead portrait": ["overhead portrait view", "downward portrait framing", "top-down portrait perspective"],
    "over-the-shoulder": ["over-the-shoulder framing", "partial back view", "shoulder-led composition"],
    "profile portrait": ["profile portrait", "side-profile framing"],
    "back view": ["back-facing framing", "rear-view composition"],
    "environmental portrait": ["environmental portrait", "subject integrated with surroundings"],
    "seated full body": ["seated full body shot", "full figure seated framing"],
}

LENS_PRESETS = {
    "auto": [],
    "18mm ultra-wide dramatic": ["18mm ultra-wide lens", "expansive perspective", "dramatic spatial depth"],
    "24mm wide cinematic": ["24mm wide-angle lens", "wide compositional framing", "deep spatial perspective"],
    "28mm documentary wide": ["28mm lens", "documentary wide framing", "natural spatial context"],
    "35mm environmental": ["35mm lens", "environmental framing", "natural perspective"],
    "40mm cinematic natural": ["40mm lens", "natural balanced perspective", "balanced medium framing"],
    "50mm intimate natural": ["50mm lens", "medium shot", "natural perspective"],
    "58mm vintage character": ["58mm lens", "vintage optical character", "gentle falloff"],
    "85mm portrait shallow DOF": ["85mm lens", "close framing", "soft focus depth"],
    "100mm macro detail": ["100mm macro lens", "close detail framing", "compressed depth"],
    "135mm compressed portrait": ["135mm telephoto lens", "tight compressed framing", "soft background separation"],
    "long lens compression": ["telephoto look", "compressed perspective", "distant observational framing"],
    "anamorphic widescreen": ["anamorphic widescreen character", "widescreen aspect framing", "horizontal highlight streak tendency"],
    "wide architectural": ["wide-angle composition", "symmetrical framing", "strong architectural lines"],
    "overhead top-down": ["top-down overhead view", "graphic spatial layout", "flattened perspective"],
    "low angle dramatic": ["low-angle shot", "dramatic upward perspective", "strong visual presence"],
    "dutch angle tension": ["dutch angle", "tilted composition", "psychological tension"],
    "handheld documentary": ["handheld observational feel", "candid framing", "immediate documentary energy"],
}

EXPLICITNESS = {
    "default": "",
    "safe": "tasteful adult presentation",
    "suggestive": "suggestive adult restraint",
    "sensual": "restrained adult sensuality",
    "bold sensual": "bold adult sensual mood with elegant restraint",
    "nsfw": "adult erotic tone",
    "explicit nsfw": "explicit adult erotic presentation",
    "romantic non-explicit": "romantic adult intimacy",
}


NONPHYSICAL_STYLE_CUES: Dict[str, Dict[str, Any]] = {
    "Neutral / Minimal Carryover": {
        "anchor": "natural visual continuity",
        "lighting": ["controlled ambient lighting", "clean readable light"],
        "color": ["coherent natural color grade", "balanced color"],
        "composition": ["balanced visual composition", "natural framing"],
        "texture": ["subtle tonal grain"],
    },
    "Neon Melancholy / Rain Glass": {
        "anchor": "neon atmospheric mood",
        "lighting": ["moody illumination", "neon glow", "soft edge highlight"],
        "color": ["warm cool contrast", "amber cyan tones", "deep saturated color"],
        "composition": ["reflective composition", "intimate framing", "compositional framing"],
        "texture": ["glossy highlights", "soft bloom", "tonal grain"],
    },
    "Classical Studio Glamour": {
        "anchor": "classic glamour",
        "lighting": ["broad soft key illumination", "subtle edge highlight", "warm shadow lift"],
        "color": ["warm golden tones", "ivory champagne palette", "rich contrast"],
        "composition": ["balanced composition", "elegant framing", "negative space"],
        "texture": ["tonal grain", "smooth tonal finish", "velvety shadows"],
    },
    "Baroque Operatic Atmosphere": {
        "anchor": "baroque operatic atmosphere",
        "lighting": ["dramatic chiaroscuro", "warm theatrical glow", "deep velvet shadow"],
        "color": ["antique gold tones", "burgundy ivory contrast", "deep umber shadows"],
        "composition": ["grand theatrical staging", "opulent classical framing", "ceremonial visual rhythm"],
        "texture": ["painted tonal depth", "rich classical texture", "velvety tonal finish"],
    },
    "High-key Clean Light": {
        "anchor": "high-key clean light",
        "lighting": ["bright even illumination", "soft shadowless light", "clean airy glow"],
        "color": ["fresh neutral palette", "bright clean tones", "soft pale highlights"],
        "composition": ["minimal clean composition", "open airy framing", "clear readable spacing"],
        "texture": ["smooth clean finish", "soft polished texture", "light tonal clarity"],
    },
    "Cinematic Widescreen Scope": {
        "anchor": "cinematic widescreen scope",
        "lighting": ["controlled cinematic lighting", "wide tonal contrast", "filmic edge illumination"],
        "color": ["filmic color grade", "balanced cinematic palette", "subtle teal amber contrast"],
        "composition": ["widescreen composition", "panoramic framing", "horizontal cinematic staging"],
        "texture": ["filmic grain", "cinematic tonal finish", "polished motion-picture texture"],
    },
    "Noir Chiaroscuro": {
        "anchor": "film noir, chiaroscuro",
        "lighting": ["low-key illumination", "high contrast", "deep shadows"],
        "color": ["monochrome", "smoky grayscale", "muted burgundy"],
        "composition": ["dramatic framing", "shadow composition", "visual tension"],
        "texture": ["tonal grain", "matte darkness", "crisp shadows"],
    },
    "Symmetric Psychological Coldness": {
        "anchor": "cold symmetrical cinema",
        "lighting": ["cold overhead light", "controlled lighting", "clean edges"],
        "color": ["desaturated palette", "cold blue-gray", "restrained red"],
        "composition": ["symmetrical framing", "centered framing", "static composition"],
        "texture": ["clean surface", "matte finish", "minimal texture"],
    },
    "Swedish Face Silence": {
        "anchor": "intimate closeup drama",
        "lighting": ["soft diffused illumination", "gentle shadow lift", "quiet illumination"],
        "color": ["pale neutral palette", "warm flesh tones", "muted earth tones"],
        "composition": ["close framing", "minimal composition", "still framing"],
        "texture": ["matte texture", "fine tonal grain", "soft tonal blend"],
    },
    "Mediterranean Sunlight": {
        "anchor": "warm golden light",
        "lighting": ["warm side light", "luminous glow", "bright natural light"],
        "color": ["terracotta cream tones", "golden warm palette", "olive blue accent"],
        "composition": ["open composition", "relaxed framing", "airy spacing"],
        "texture": ["highlight bloom", "warm matte finish", "soft tonal grain"],
    },
    "French Natural Light New Wave": {
        "anchor": "natural light realism",
        "lighting": ["natural light", "available light", "soft ambient light"],
        "color": ["faded blue cream", "muted natural color", "soft gray tones"],
        "composition": ["off-center framing", "casual framing", "candid composition"],
        "texture": ["tonal grain", "natural texture", "unpolished finish"],
    },
    "Gothic Candle Velvet": {
        "anchor": "gothic romantic mood",
        "lighting": ["low amber gothic mood", "low warm illumination", "heavy shadows"],
        "color": ["burgundy gold palette", "dark romantic tones", "deep warm contrast"],
        "composition": ["ornate composition", "romantic framing", "dramatic negative space"],
        "texture": ["rich shadows", "soft grain", "deep tonal depth"],
    },
    "Dream Pastel Diffusion": {
        "anchor": "dreamlike pastel mood",
        "lighting": ["diffused glow", "soft rear glow", "ethereal illumination"],
        "color": ["pastel palette", "pink lavender tones", "soft cyan accent"],
        "composition": ["soft focus", "floating composition", "gentle framing"],
        "texture": ["soft bloom", "hazy texture", "silky tonal blend"],
    },
    "Fashion Editorial Studio Cinema": {
        "anchor": "fashion editorial",
        "lighting": ["clean studio-style illumination", "clean highlights", "controlled contrast"],
        "color": ["luxury color palette", "black cream contrast", "deep red accent"],
        "composition": ["editorial composition", "graphic framing", "polished framing"],
        "texture": ["glossy finish", "smooth texture", "clean polish"],
    },
    "Dark Fantasy Shadow Mass": {
        "anchor": "dark fantasy mood",
        "lighting": ["dramatic low light", "ominous glow", "heavy shadow contrast"],
        "color": ["deep crimson black", "ashen blue accent", "dark mythic tones"],
        "composition": ["silhouette composition", "dramatic framing", "epic composition"],
        "texture": ["smoky atmosphere", "dense shadows", "gritty atmospheric texture"],
    },
    "Black & White Classic": {
        "anchor": "monochrome, high contrast tonal rendering",
        "lighting": ["high contrast", "dramatic side light", "sharp highlight"],
        "color": ["monochrome", "grayscale", "deep blacks"],
        "composition": ["strong tonal contrast", "classic framing", "dramatic composition"],
        "texture": ["tonal grain", "monochrome print texture", "classic tonal feel"],
    },
    "Golden Hour Glow": {
        "anchor": "golden hour, warm glow",
        "lighting": ["golden hour illumination", "warm rear glow", "soft radiant halo"],
        "color": ["warm amber tones", "golden highlight", "soft orange"],
        "composition": ["backlit composition", "natural framing", "airy spacing"],
        "texture": ["soft bloom", "warm haze", "soft tonal grain"],
    },
    "Vintage Film Look": {
        "anchor": "vintage, retro aesthetic",
        "lighting": ["soft vintage illumination", "warm shadow lift", "faded highlight"],
        "color": ["faded warm tones", "retro palette", "aged color shift"],
        "composition": ["casual framing", "relaxed composition", "snapshot feel"],
        "texture": ["aged surface texture", "faded edge glow", "soft vignette"],
    },
    "Cyberpunk Neon": {
        "anchor": "cyberpunk, neon glow",
        "lighting": ["neon glow", "holographic glow", "electric blue glow"],
        "color": ["electric cyan", "hot magenta", "neon purple"],
        "composition": ["dynamic angle", "layered depth", "futuristic framing"],
        "texture": ["glossy highlight", "digital noise", "reflective neon sheen"],
    },
    "Soft Romantic Glow": {
        "anchor": "romantic, soft focus",
        "lighting": ["soft warm illumination", "gentle rear glow", "diffused glow"],
        "color": ["warm pink tones", "soft peach", "creamy highlight"],
        "composition": ["intimate framing", "soft focus depth", "gently blurred background"],
        "texture": ["soft bloom", "dreamy haze", "smooth tonal blend"],
    },
    "Watercolor / Painterly": {
        "anchor": "watercolor illustration, painterly",
        "lighting": ["soft ambient wash", "gentle diffused light", "even tonal fill"],
        "color": ["translucent pigment", "soft color wash", "muted natural palette"],
        "composition": ["loose painterly framing", "soft edge treatment"],
        "texture": ["brushstroke texture", "wet pigment bleed", "paper grain"],
    },
}

SAFE_CAMERA_TERM_REPLACEMENTS: Dict[str, str] = {
    "18mm ultra-wide lens": "18mm ultra-wide lens",
    "24mm wide-angle lens": "24mm wide-angle lens",
    "28mm lens": "28mm lens",
    "35mm lens": "35mm lens",
    "40mm lens": "40mm lens",
    "50mm lens": "50mm lens",
    "58mm lens": "58mm lens",
    "85mm lens": "85mm lens",
    "100mm macro lens": "100mm macro lens",
    "135mm telephoto lens": "135mm telephoto lens",
    "anamorphic widescreen character": "anamorphic widescreen character",
    "wide shot": "wide shot",
    "environmental framing": "environmental framing",
    "medium shot": "medium shot",
    "natural perspective": "natural perspective",
    "portrait framing": "close framing",
    "close framing": "close framing",
    "soft focus depth": "soft focus depth",
    "telephoto look": "telephoto look",
    "compressed perspective": "compressed perspective",
    "wide-angle composition": "wide-angle composition",
    "symmetrical framing": "symmetrical framing",
    "expansive perspective": "expansive perspective",
    "dramatic spatial depth": "dramatic spatial depth",
    "wide compositional framing": "wide compositional framing",
    "deep spatial perspective": "deep spatial perspective",
    "documentary wide framing": "documentary wide framing",
    "natural spatial context": "natural spatial context",
    "natural balanced perspective": "natural balanced perspective",
    "balanced medium framing": "balanced medium framing",
    "vintage optical character": "vintage optical character",
    "gentle falloff": "gentle falloff",
    "close detail framing": "close detail framing",
    "compressed depth": "compressed depth",
    "tight compressed framing": "tight compressed framing",
    "soft background separation": "soft background separation",
    "distant observational framing": "distant observational framing",
    "widescreen aspect framing": "widescreen aspect framing",
    "horizontal highlight streak tendency": "horizontal highlight streak tendency",
    "strong architectural lines": "strong architectural lines",
    "top-down overhead view": "top-down overhead view",
    "graphic spatial layout": "graphic spatial layout",
    "flattened perspective": "flattened perspective",
    "low-angle shot": "low-angle shot",
    "dramatic upward perspective": "dramatic upward perspective",
    "strong visual presence": "strong visual presence",
    "dutch angle": "dutch angle",
    "tilted composition": "tilted composition",
    "psychological tension": "psychological tension",
    "handheld observational feel": "handheld observational feel",
    "candid framing": "candid framing",
    "immediate documentary energy": "immediate documentary energy",
}

SAFE_CAMERA_TERM_ALLOWLIST = frozenset(
    value.lower() for value in SAFE_CAMERA_TERM_REPLACEMENTS.values()
) | frozenset({
    "natural full-body perspective",
})


# Mood families and style names where automatic lens/camera boilerplate should be suppressed.
# This set is intentionally broader than painterly media: some photographic-looking moods
# still should not receive automatic physical lens terms unless the user explicitly selects a lens.
CAMERA_SUPPRESS_MOOD_FAMILIES: frozenset = frozenset({
    "Watercolor / Painterly",
    "Dreamlike / Surreal",
    "Romantic / Soft Focus",
    "Bright / High-key",
    "Lyrical / Poetic",
    "Gothic Romance",
    "Golden Hour Warmth",
    "Dark Fantasy Romance",
    "Horror / Unsettling",
})

CAMERA_SUPPRESS_STYLE_NAMES: frozenset = frozenset({
    "Watercolor / Painterly",
    "Dream Pastel Diffusion",
    "Soft Romantic Glow",
    "High-key Clean Light",
    "Gothic Candle Velvet",
    "Golden Hour Glow",
    "Dark Fantasy Shadow Mass",
    "Charcoal Drawing",
    "Graphite Pencil Sketch",
    "Pen and Ink Sketch",
    "Ink Wash / Sumi-e",
    "Colored Pencil Illustration",
    "Pastel Chalk Drawing",
    "Gouache Storybook Illustration",
    "Hand-Painted Storybook Animation",
    "Clean Cel Animation",
})

_CAMERA_SUPPRESS_KW_RE = re.compile(
    r"\b(?:watercolor|painterly|painting|gouache|illustration|"
    r"hand[-\s]?drawn|oil[-\s]?paint|sketch|ink[-\s]?wash|anime|manga|cel[-\s]?shad(?:e|ed|ing)?)\b",
    re.IGNORECASE,
)


NONPHOTOGRAPHIC_STYLE_NAMES: frozenset = frozenset({
    "Watercolor / Painterly",
    "Dream Pastel Diffusion",
    "Charcoal Drawing",
    "Graphite Pencil Sketch",
    "Pen and Ink Sketch",
    "Ink Wash / Sumi-e",
    "Colored Pencil Illustration",
    "Pastel Chalk Drawing",
    "Gouache Storybook Illustration",
    "Hand-Painted Storybook Animation",
    "Clean Cel Animation",
})

_NONPHOTO_STYLE_BLOCK_RE = re.compile(
    r"\b(?:cinematic|filmic|lens|camera|anamorphic|dof|photographic|photoreal(?:istic)?)\b|"
    r"\b(?:medium|wide|full|close|close-up|low-angle|high-angle|overhead|tracking|dolly|handheld)\s+shot\b|"
    r"\b(?:camera|lens|natural)\s+perspective\b",
    re.IGNORECASE,
)

def _is_nonphotographic_style_context(style_name: str) -> bool:
    style_key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    if style_key in NONPHOTOGRAPHIC_STYLE_NAMES:
        return True
    return bool(_CAMERA_SUPPRESS_KW_RE.search(style_key))


def _filter_nonphoto_style_terms(parts: List[str], style_name: str) -> List[str]:
    if not _is_nonphotographic_style_context(style_name):
        return [_clean_text(x) for x in parts if _clean_text(x)]
    out: List[str] = []
    for part in parts:
        cleaned = _clean_text(part)
        if not cleaned:
            continue
        if _NONPHOTO_STYLE_BLOCK_RE.search(cleaned):
            continue
        out.append(cleaned)
    return out


_NATURAL_QUALITY_BLOCK_FOR_NONPHOTO_RE = re.compile(
    r"\b(?:cinematic|filmic|lens|camera|anamorphic|dof|photographic|photorealistic|"
    r"realistic|controlled\s+lighting|highly\s+detailed)\b|"
    r"\b(?:medium|wide|full|close|close-up|low-angle|high-angle|overhead|tracking|dolly|handheld)\s+shot\b|"
    r"\b(?:camera|lens|natural)\s+perspective\b",
    re.IGNORECASE,
)


def _natural_quality_for_prompt(bp: "Blueprint") -> str:
    """Return natural-model quality hints without weakening non-photographic styles."""
    quality = _tag_quality_for_model(bp.model_profile, bp.adult_tone)
    parts = [_clean_text(x) for x in _split_prompt_tags(quality) if _clean_text(x)]
    if _is_nonphotographic_style_context(bp.style_name):
        parts = [part for part in parts if not _NATURAL_QUALITY_BLOCK_FOR_NONPHOTO_RE.search(part)]
    return _join_comma(parts)




STYLE_AUTO_CAMERA_HINTS_2026_05_31_C: Dict[str, List[str]] = {
    "Miniature Diorama": ["macro lens look", "shallow depth of field", "tilt-shift miniature scale"],
    "3D Collectible Figure": ["product-display close framing", "controlled studio depth", "clean showcase lighting perspective"],
}

def _style_allows_auto_camera(style_name: str) -> bool:
    key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    return key in STYLE_AUTO_CAMERA_HINTS_2026_05_31_C

def _style_auto_camera_terms(style_name: str, lens_preset: str = "auto") -> List[str]:
    lens_key = _canonical_ui_value(lens_preset, "lens_preset") or str(lens_preset or "auto")
    if lens_key not in ("", "auto"):
        return []
    key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    return list(STYLE_AUTO_CAMERA_HINTS_2026_05_31_C.get(key, []))

def _is_camera_suppressed_context(style_name: str, mood_family: str) -> bool:
    """Return True when automatic lens/camera terms should be suppressed."""
    if mood_family in CAMERA_SUPPRESS_MOOD_FAMILIES:
        return True
    if style_name in CAMERA_SUPPRESS_STYLE_NAMES:
        return True
    return bool(_CAMERA_SUPPRESS_KW_RE.search(style_name))


def _suppress_auto_camera_for_prompt(style_name: str, mood_family: str, lens_preset: str = "auto") -> bool:
    """Suppress automatically generated camera/lens phrasing unless the user explicitly asked for it.

    This node's primary goal is to preserve the chosen mood/style. Auto-injected lens or
    framing phrases can pull the model toward a photographic interpretation and weaken the
    selected visual style. Therefore, when lens_preset is auto, suppress camera phrasing for
    any non-default mood/style selection, while still honoring an explicit user lens choice.
    """
    lens_key = _canonical_ui_value(lens_preset, "lens_preset") or str(lens_preset or "auto")
    if lens_key not in ("", "auto"):
        return False
    if _style_allows_auto_camera(style_name):
        return False
    if _is_camera_suppressed_context(style_name, mood_family):
        return True
    if mood_family != "Default / None":
        return True
    return style_name not in ("Auto by Mood", "Neutral / Minimal Carryover", "")

PHYSICAL_STYLE_CUE_PATTERN = re.compile(
    r"\b("
    r"rain|rainy|storm|snow|fog|mist|weather|wet|humid|sun|sunlit|daylight|afternoon|window|glass|room|hotel|"
    r"apartment|mansion|veranda|street|city|urban|background|backdrop|subject|"
    r"person|woman|man|couple|people|girl|boy|portrait|face|body|skin|pose|posing|"
    r"wardrobe|dress|suit|robe|outfit|fabric|linen|silk|velvet|lace|wood|"
    r"stone|curtain|curtains|wall|walls|floor|doorway|mirror|vanity|candle|torch|pavement|"
    r"studio\s+set|editorial\s+set|luxury\s+set|interior|exterior|sea|school|uniform|cityscape"
    r")\b",
    re.IGNORECASE,
)

MODEL_PROFILES: Dict[str, Dict[str, Any]] = {
    "Z-Image Natural": {
        "family": "natural",
        "model_key": "zimage",
        "quality": "clear subject, coherent image, well-defined scene, consistent details",
        "negative": "Avoid making the style replace the subject. Avoid underage cues, school styling, explicit sexual action, bad anatomy, and random decorative noise.",
    },
    "Qwen Natural": {
        "family": "natural",
        "model_key": "qwen",
        "quality": "coherent image, visually refined, consistent details",
        "negative": "Avoid underage appearance, school uniform implications, explicit sexual action, pornographic staging, unreadable faces, and abstract color noise replacing the subject.",
    },
    "Flux Natural": {
        "family": "natural",
        "model_key": "flux",
        "quality": "coherent image, visually refined, strong scene cohesion, consistent details",
        "negative": "Avoid underage appearance, school uniform implications, explicit sexual action, pornographic staging, unreadable faces, and abstract color noise replacing the subject.",
    },
    "Anima Mixed": {
        "family": "mixed",
        "model_key": "anima",
        "quality": "masterpiece, best quality, score_7, safe, highres, absurdres",
        "negative": "low quality, worst quality, bad anatomy, deformed hands, childish appearance, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic staging, photorealistic skin texture, realistic pores, style overpowering the subject",
    },
    "SDXL Tag": {
        "family": "tag",
        "model_key": "sdxl",
        "quality": "masterpiece, best quality, highres, detailed",
        "negative": "low quality, worst quality, bad anatomy, deformed hands, childish, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic, messy composition",
    },
    "ILXL / Illustrious Tag": {
        "family": "tag",
        "model_key": "ilxl",
        "quality": "masterpiece, best quality, amazing quality, very aesthetic, newest, absurdres, highres, safe",
        "negative": "low quality, worst quality, bad anatomy, extra fingers, bad hands, childish, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic, messy composition",
    },
    "Pony Tag": {
        "family": "tag",
        "model_key": "pony",
        "quality": "score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up, source_anime, rating_safe",
        "negative": "score_4, score_5, score_6, low quality, worst quality, bad anatomy, extra fingers, childish, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic",
    },
    "SD 1.5 Tag": {
        "family": "tag",
        "model_key": "sd",
        "quality": "masterpiece, best quality, highres, detailed",
        "negative": "low quality, worst quality, bad anatomy, bad hands, childish, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic, messy composition",
    },
    "Universal Natural Language": {
        "family": "natural",
        "model_key": "universal",
        "quality": "detailed subject, coherent image, visually refined, consistent details",
        "negative": "low quality, bad anatomy, childish appearance, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic staging, random abstract color noise, unreadable subject",
    },

    "SDXL / Anima Natural": {
        "family": "mixed",
        "model_key": "anima",
        "quality": "masterpiece, best quality, score_7, safe, highres, absurdres",
        "negative": "low quality, worst quality, bad anatomy, deformed hands, childish appearance, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic staging, photorealistic skin texture, realistic pores, style overpowering the subject",
    },
    "Pony / Illustrious Tag": {
        "family": "tag",
        "model_key": "ilxl",
        "quality": "masterpiece, best quality, amazing quality, very aesthetic, newest, absurdres, highres, safe",
        "negative": "low quality, worst quality, bad anatomy, extra fingers, bad hands, childish, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic, messy composition",
    },
    "Anime Tag General": {
        "family": "tag",
        "model_key": "ilxl",
        "quality": "masterpiece, best quality, amazing quality, very aesthetic, newest, absurdres, highres, safe",
        "negative": "low quality, worst quality, bad anatomy, childish, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic, messy composition",
    },
    "Flux / Qwen Instruction": {
        "family": "natural",
        "model_key": "qwen",
        "quality": "coherent image, visually refined, consistent details",
        "negative": "Avoid underage appearance, school uniform implications, explicit sexual action, pornographic staging, unreadable faces, and abstract color noise replacing the subject.",
    },
}

VISIBLE_MODEL_PROFILES: List[str] = [
    "Z-Image Natural",
    "Qwen Natural",
    "Flux Natural",
    "Anima Mixed",
    "SDXL Tag",
    "ILXL / Illustrious Tag",
    "Pony Tag",
    "SD 1.5 Tag",
    "Universal Natural Language",
]


UI_LABELS_KO: Dict[str, Dict[str, str]] = {
    "model_profile": {
        "Z-Image Natural": "Z-Image 자연어",
        "Qwen Natural": "Qwen 자연어",
        "Flux Natural": "Flux 자연어",
        "Anima Mixed": "Anima 태그+문장",
        "SDXL Tag": "SDXL 태그형",
        "ILXL / Illustrious Tag": "ILXL / Illustrious 태그형",
        "Pony Tag": "Pony 태그형",
        "SD 1.5 Tag": "SD 1.5 태그형",
        "Universal Natural Language": "범용 자연어",
        "SDXL / Anima Natural": "SDXL / Anima 자연어",
        "Pony / Illustrious Tag": "Pony / Illustrious 태그형",
        "Anime Tag General": "애니메이션 범용 태그형",
        "Flux / Qwen Instruction": "Flux / Qwen 지시문형"
    },
    "mood_family": {
        "Default / None": "기본",
        "🎲 Random All": "🎲 랜덤 전체",
        "🎲 Random Transformative Style": "🎲 랜덤 변환 스타일",
        "🎲 Random Traditional Media Style": "🎲 랜덤 전통 매체 화풍",
        "Erotic / Sensual": "관능적인 분위기",
        "Lyrical / Poetic": "서정적인 분위기",
        "Classical / Golden Age": "클래식 영화 분위기",
        "Noir / Neo-noir": "어두운 영화 분위기",
        "Dreamlike / Surreal": "몽환적인 분위기",
        "Gothic Romance": "고딕 로맨스 분위기",
        "Melodrama": "감정적인 드라마 분위기",
        "Fashion Editorial": "고급 화보 분위기",
        "Arthouse Realism": "차분한 예술영화 분위기",
        "Pop Neon": "선명한 네온 분위기",
        "Baroque / Operatic": "화려하고 웅장한 분위기",
        "Minimalist Psychological": "절제된 심리극 분위기",
        "Dark Fantasy Romance": "어두운 판타지 로맨스",
        "Black & White Film": "흑백 영화 분위기",
        "Golden Hour Warmth": "따뜻한 노을빛 분위기",
        "Vintage / Retro": "빈티지 감성",
        "Cyberpunk / Sci-fi": "미래적인 네온 분위기",
        "Watercolor / Painterly": "수채화처럼 부드러운 분위기",
        "Bright / High-key": "밝고 깨끗한 분위기",
        "Cinematic Widescreen": "넓고 장대한 분위기",
        "Romantic / Soft Focus": "부드러운 로맨틱 분위기",
        "Horror / Unsettling": "불안하고 어두운 분위기"
    },
    "style_dna": {
        "Auto by Mood": "분위기에 맞춰 자동",
        "Neutral / Minimal Carryover": "중립 / 거의 추가 안 함",
        "Neon Melancholy / Rain Glass": "빗속 네온 감성",
        "Classical Studio Glamour": "클래식 스튜디오 화보",
        "Noir Chiaroscuro": "어두운 영화 명암",
        "Symmetric Psychological Coldness": "차갑고 대칭적인 화면",
        "Swedish Face Silence": "고요한 클로즈업 초상",
        "Mediterranean Sunlight": "따뜻한 지중해 햇빛",
        "French Natural Light New Wave": "자연광 거리 영화 느낌",
        "Gothic Candle Velvet": "고딕 촛불과 벨벳",
        "Dream Pastel Diffusion": "몽환적인 파스텔 빛",
        "Fashion Editorial Studio Cinema": "스튜디오 화보 영화감",
        "High-key Clean Light": "밝고 깨끗한 조명",
        "Cinematic Widescreen Scope": "넓은 영화 화면",
        "Baroque Operatic Atmosphere": "화려하고 웅장한 무대감",
        "Dark Fantasy Shadow Mass": "어두운 판타지 그림자",
        "Black & White Classic": "클래식 흑백",
        "Golden Hour Glow": "따뜻한 노을빛",
        "Vintage Film Look": "빈티지 필름 느낌",
        "Cyberpunk Neon": "사이버펑크 네온",
        "Soft Romantic Glow": "부드러운 로맨틱 빛",
        "Watercolor / Painterly": "수채화 회화 느낌",
        "Charcoal Drawing": "목탄 드로잉",
        "Graphite Pencil Sketch": "연필 스케치",
        "Pen and Ink Sketch": "펜화 스케치",
        "Ink Wash / Sumi-e": "수묵화",
        "Colored Pencil Illustration": "색연필 일러스트",
        "Pastel Chalk Drawing": "파스텔 드로잉",
        "Gouache Storybook Illustration": "불투명 물감 동화풍",
        "Hand-Painted Storybook Animation": "손그림 동화 애니풍",
        "Volumetric Dust Light": "공기 중 먼지 빛",
        "Long Exposure Light Trails": "긴 노출 빛 궤적",
        "Oil Painting": "유화 느낌",
        "Miniature Diorama": "미니어처 디오라마",
        "Pixel Art": "픽셀 아트",
        "3D Collectible Figure": "3D 피규어 느낌",
        "Apocalyptic Wasteland": "폐허 세계 분위기",
        "Chibi Style": "치비 스타일",
        "Clean Cel Animation": "깔끔한 셀 애니풍"
    },
    "lens_preset": {
        "auto": "자동",
        "18mm ultra-wide dramatic": "18mm 초광각 / 공간 강조",
        "24mm wide cinematic": "24mm 넓은 영화 화면",
        "28mm documentary wide": "28mm 넓은 현장감",
        "35mm environmental": "35mm 배경이 보이는 인물",
        "40mm cinematic natural": "40mm 자연스러운 화면",
        "50mm intimate natural": "50mm 자연스러운 인물",
        "58mm vintage character": "58mm 빈티지 인물",
        "85mm portrait shallow DOF": "85mm 인물 / 배경 흐림",
        "100mm macro detail": "100mm 가까운 디테일",
        "135mm compressed portrait": "135mm 망원 인물",
        "long lens compression": "망원 압축감",
        "anamorphic widescreen": "와이드 영화 화면",
        "wide architectural": "넓은 건축 공간",
        "overhead top-down": "위에서 내려다봄",
        "low angle dramatic": "아래에서 올려다봄",
        "dutch angle tension": "기울어진 긴장감",
        "handheld documentary": "핸드헬드 현장감"
    },
    "style_strength": {
        "subtle": "원본 보존",
        "balanced": "균형 적용",
        "strong": "스타일 우선"
    },
    "style_conflict_cleanup": {
        "off": "끔",
        "soft": "부드럽게 완화",
        "strong": "강하게 완화"
    },
    "adult_tone": {
        "default": "기본",
        "safe": "안전한 표현",
        "suggestive": "살짝 암시적",
        "sensual": "부드러운 관능",
        "bold sensual": "강한 관능",
        "nsfw": "성인 NSFW",
        "explicit nsfw": "강한 성인 NSFW",
        "romantic non-explicit": "노골적이지 않은 로맨스"
    },
    "adult_wardrobe": {
        "auto": "자동 / 미지정",
        "nude": "누드",
        "topless": "상의 탈의",
        "lingerie": "란제리",
        "bikini": "비키니",
        "one-piece swimsuit": "원피스 수영복",
        "sheer nightgown": "시스루 나이트가운",
        "silk slip dress": "실크 슬립 드레스",
        "corset": "코르셋",
        "bodysuit": "바디수트",
        "latex outfit": "라텍스 의상",
        "leather outfit": "가죽 의상",
        "evening dress": "이브닝 드레스",
        "tailored suit": "테일러드 수트",
        "bathrobe": "목욕 가운",
        "lace lingerie set": "레이스 란제리 세트",
        "sheer robe": "시스루 로브",
        "satin robe": "새틴 로브",
        "silk camisole": "실크 캐미솔",
        "bralette": "브라렛",
        "lace bodysuit": "레이스 바디수트",
        "sheer bodysuit": "시스루 바디수트",
        "garter belt": "가터 벨트",
        "thigh-high stockings": "허벅지 스타킹",
        "pantyhose": "팬티스타킹",
        "open shirt": "오픈 셔츠",
        "oversized shirt": "오버사이즈 셔츠",
        "mini dress": "미니 드레스",
        "off-shoulder dress": "오프숄더 드레스",
        "halter dress": "홀터넥 드레스",
        "fishnet outfit": "그물망 의상",
        "vinyl outfit": "글로시 비닐 의상",
        "mesh top": "메시 탑"
    },
    "scene_framing": {
        "auto": "자동 / 미지정",
        "headshot (face-focused)": "얼굴 중심",
        "close-up": "가까운 인물",
        "upper body": "상반신",
        "waist-up": "허리 위",
        "three-quarter body": "무릎 위 정도",
        "full body (head to toe)": "전신",
        "full shot (full body + extra space)": "전신 + 주변 여백",
        "wide shot": "넓은 배경 포함",
        "high-angle portrait": "위쪽 시점 인물",
        "overhead portrait": "위에서 내려다본 인물",
        "over-the-shoulder": "어깨 너머 시점",
        "profile portrait": "옆모습",
        "back view": "뒷모습",
        "environmental portrait": "배경이 보이는 인물",
        "seated full body": "앉은 전신"
    },
    "external_prompt_mode": {
        "Append style after external prompt": "원본 뒤에 스타일 문구 추가",
        "Prepend style before external prompt": "스타일 문구를 앞에 먼저 배치",
        "Output style only": "스타일 문구만 출력"
    }
}

UI_LABELS_KO_REVERSE_BY_WIDGET: Dict[str, Dict[str, str]] = {
    widget_name: {ko: canonical for canonical, ko in mapping.items()}
    for widget_name, mapping in UI_LABELS_KO.items()
}


_UI_LABELS_KO_REVERSE_COUNTS: Dict[str, int] = {}
for _mapping in UI_LABELS_KO.values():
    for _ko in _mapping.values():
        _UI_LABELS_KO_REVERSE_COUNTS[_ko] = _UI_LABELS_KO_REVERSE_COUNTS.get(_ko, 0) + 1

UI_LABELS_KO_REVERSE_UNAMBIGUOUS: Dict[str, str] = {
    ko: canonical
    for mapping in UI_LABELS_KO.values()
    for canonical, ko in mapping.items()
    if _UI_LABELS_KO_REVERSE_COUNTS.get(ko, 0) == 1
}

UI_VALUE_ALIASES: Dict[str, Dict[str, str]] = {
    "external_prompt_mode": {
        "External prompt + style only": "Output style only",
    },
}

# Legacy Korean display labels kept for old workflow compatibility after the UI wording cleanup.
UI_VALUE_ALIASES.update({
    "mood_family": {
        "누아르 / 현대 누아르": "Noir / Neo-noir",
        "고전 영화 / 황금기": "Classical / Golden Age",
        "서정적 / 시적": "Lyrical / Poetic",
        "관능적 / 감각적": "Erotic / Sensual",
        "몽환적 / 초현실적": "Dreamlike / Surreal",
        "패션 화보풍": "Fashion Editorial",
        "예술영화 리얼리즘": "Arthouse Realism",
        "팝 네온 감성": "Pop Neon",
        "바로크풍 / 오페라적 웅장함": "Baroque / Operatic",
        "미니멀 심리극": "Minimalist Psychological",
        "따뜻한 노스탤지어": "Golden Hour Warmth",
        "사이버펑크 / SF 정서": "Cyberpunk / Sci-fi",
        "수채화 / 회화풍": "Watercolor / Painterly",
        "수채화적 서정감": "Watercolor / Painterly",
        "밝고 경쾌한 정서": "Bright / High-key",
        "장대한 서사감": "Cinematic Widescreen",
        "로맨틱한 친밀감": "Romantic / Soft Focus",
        "호러 / 불안한 분위기": "Horror / Unsettling",
        "🎲 Random Mood": "🎲 Random All",
        "🎲 랜덤 분위기": "🎲 Random All",
        "랜덤 분위기": "🎲 Random All",
        "🎲 랜덤 전체": "🎲 Random All",
        "랜덤 전체": "🎲 Random All",
        "🎲 랜덤 변환 스타일": "🎲 Random Transformative Style",
        "🎲 랜덤 전통 매체 화풍": "🎲 Random Traditional Media Style"
    },
    "style_dna": {
        "정서에 맞춰 자동": "Auto by Mood",
        "중립 / 최소 개입": "Neutral / Minimal Carryover",
        "네온 멜랑콜리 / 빗물 유리": "Neon Melancholy / Rain Glass",
        "클래식 스튜디오 글래머": "Classical Studio Glamour",
        "누아르 키아로스쿠로": "Noir Chiaroscuro",
        "대칭적 심리적 냉기": "Symmetric Psychological Coldness",
        "스웨덴식 정적 초상": "Swedish Face Silence",
        "지중해 햇빛": "Mediterranean Sunlight",
        "프랑스 자연광 누벨바그": "French Natural Light New Wave",
        "고딕 촛불 벨벳": "Gothic Candle Velvet",
        "몽환 파스텔 확산광": "Dream Pastel Diffusion",
        "패션 에디토리얼 스튜디오 시네마": "Fashion Editorial Studio Cinema",
        "하이키 클린 라이트": "High-key Clean Light",
        "시네마틱 와이드스크린 스코프": "Cinematic Widescreen Scope",
        "바로크 오페라틱 분위기": "Baroque Operatic Atmosphere",
        "다크 판타지 그림자 덩어리": "Dark Fantasy Shadow Mass",
        "흑백 클래식": "Black & White Classic",
        "골든아워 빛감": "Golden Hour Glow",
        "빈티지 필름": "Vintage Film Look",
        "사이버펑크 네온": "Cyberpunk Neon",
        "부드러운 로맨틱 광채": "Soft Romantic Glow",
        "수채화 / 회화풍": "Watercolor / Painterly",
        "흑연 연필 스케치": "Graphite Pencil Sketch",
        "펜 앤 잉크 스케치": "Pen and Ink Sketch",
        "먹그림 / 수묵화": "Ink Wash / Sumi-e",
        "파스텔 초크 드로잉": "Pastel Chalk Drawing",
        "구아슈 동화책 일러스트": "Gouache Storybook Illustration",
        "손그림 동화풍": "Hand-Painted Storybook Animation",
        "손그림 동화풍 애니메이션": "Hand-Painted Storybook Animation",
        "먼지 / 빛 산란(볼류메트릭)": "Volumetric Dust Light",
        "먼지 / 볼류메트릭 빛 산란": "Volumetric Dust Light",
        "롱 익스포저 / 빛 궤적": "Long Exposure Light Trails",
        "아포칼립스": "Apocalyptic Wasteland",
        "아포칼립스 / 폐허 세계": "Apocalyptic Wasteland",
        "치비 스타일": "Chibi Style",
        "클린 셀 애니메이션": "Clean Cel Animation"
    },
    "lens_preset": {
        "18mm 초광각 드라마틱": "18mm ultra-wide dramatic",
        "24mm 와이드 시네마틱": "24mm wide cinematic",
        "28mm 다큐멘터리 와이드": "28mm documentary wide",
        "35mm 환경형": "35mm environmental",
        "40mm 시네마틱 자연형": "40mm cinematic natural",
        "50mm 자연스러운 친밀감": "50mm intimate natural",
        "58mm 빈티지 캐릭터": "58mm vintage character",
        "85mm 얕은 심도 인물형": "85mm portrait shallow DOF",
        "100mm 매크로 디테일": "100mm macro detail",
        "135mm 압축 인물형": "135mm compressed portrait",
        "아나모픽 와이드스크린": "anamorphic widescreen",
        "광각 건축적 구도": "wide architectural",
        "오버헤드 탑다운": "overhead top-down",
        "로우앵글 드라마틱": "low angle dramatic",
        "더치앵글 긴장감": "dutch angle tension",
        "핸드헬드 다큐멘터리": "handheld documentary"
    },
    "style_strength": {
        "원본 보존": "subtle",
        "균형 적용": "balanced",
        "스타일 우선": "strong",
        "절제": "subtle",
        "균형": "balanced",
        "강함": "strong"
    },
    "style_conflict_cleanup": {
        "끔": "off",
        "사용 안 함": "off",
        "부드럽게 완화": "soft",
        "약하게 완화": "soft",
        "강하게 완화": "strong",
        "강함": "strong"
    },
    "adult_tone": {
        "세이프": "safe",
        "암시적": "suggestive",
        "센슈얼": "sensual",
        "대담한 센슈얼": "bold sensual",
        "강한 NSFW": "explicit nsfw",
        "로맨틱 비노골적": "romantic non-explicit"
    },
    "scene_framing": {
        "헤드샷 (얼굴 중심)": "headshot (face-focused)",
        "클로즈업": "close-up",
        "3/4 바디": "three-quarter body",
        "전신 (머리~발끝)": "full body (head to toe)",
        "풀샷 (전신+여백)": "full shot (full body + extra space)",
        "와이드샷": "wide shot",
        "하이앵글 인물샷": "high-angle portrait",
        "오버헤드 인물샷": "overhead portrait",
        "오버더숄더": "over-the-shoulder",
        "프로필 인물샷": "profile portrait",
        "환경 인물샷": "environmental portrait"
    },
    "external_prompt_mode": {
        "외부 프롬프트 뒤에 스타일 추가": "Append style after external prompt",
        "외부 프롬프트 앞에 스타일 추가": "Prepend style before external prompt",
        "스타일만 출력": "Output style only"
    }
})


def _canonical_ui_value(value: Any, widget_name: str = "") -> str:
    s = _normalize_text(value)
    if not s:
        return s
    if widget_name:
        s = UI_VALUE_ALIASES.get(widget_name, {}).get(s, s)
        return UI_LABELS_KO_REVERSE_BY_WIDGET.get(widget_name, {}).get(s, s)
    return UI_LABELS_KO_REVERSE_UNAMBIGUOUS.get(s, s)


def _ui_options(widget_name: str, canonical_values: List[str]) -> List[str]:
    """Return canonical dropdown choices only.

    The frontend localizes display labels and serializes canonical values, while
    backend normalization still accepts legacy Korean labels if an old workflow
    sends them directly. Keeping the server-side combo list canonical prevents
    duplicate-looking English/Korean/legacy choices from appearing in ComfyUI.
    """
    out: List[str] = []
    seen = set()
    for value in canonical_values:
        canonical = _canonical_ui_value(value, widget_name)
        candidate = _normalize_text(canonical)
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def _merge_data_dict(fallback: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge external JSON data over embedded defaults.

    External ./data/*.json files may contain only additions or partial overrides.
    Keeping fallback entries prevents UI option loss and ComfyUI validation errors
    when users customize a single entry instead of copying the whole data file.
    """
    merged: Dict[str, Any] = copy.deepcopy(fallback)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_data_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _load_data_dict(filename: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Load a JSON dictionary from ./data, merging it over embedded defaults.

    Keeping embedded defaults allows the node to run even if a user deletes the
    data folder, while the data folder keeps style/model expansion maintainable.
    """
    path = os.path.join(DATA_DIR, filename)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data:
                return _merge_data_dict(fallback, data)
            print(f"[Ultra-PromptStyler] Ignoring empty/non-dict data file: {filename}")
    except Exception as e:
        print(f"[Ultra-PromptStyler] Failed to load data/{filename}: {e}")
    return copy.deepcopy(fallback)

# Keep embedded fallback data synchronized with the external JSON data files.
# Normal runtime still prefers ./data/*.json. These updates preserve the
# role-separated mood/style behavior if a data file is missing.
MOOD_FAMILIES.update({'Erotic / Sensual': {'anchor': 'restrained adult sensual tension',
                      'emotion': ['adult intimacy', 'quiet desire', 'elegant restraint', 'private emotional charge'],
                      'avoid': ['explicit sexual act', 'pornographic staging', 'juvenile styling']},
 'Lyrical / Poetic': {'anchor': 'lyrical melancholy and quiet tenderness',
                      'emotion': ['quiet longing',
                                  'soft emotional distance',
                                  'delicate silence',
                                  'lingering tenderness'],
                      'avoid': ['overly dramatic posing', 'abstract color noise']},
 'Classical / Golden Age': {'anchor': 'timeless graceful poise',
                            'emotion': ['timeless elegance',
                                        'refined poise',
                                        'controlled romance',
                                        'graceful stillness'],
                            'avoid': ['modern casual clutter', 'random streetwear']},
 'Noir / Neo-noir': {'anchor': 'nocturnal suspicion and private unease',
                     'emotion': ['dangerous intimacy', 'silent suspicion', 'nocturnal desire', 'private unease'],
                     'avoid': ['flat daylight', 'comedy tone']},
 'Melodrama': {'anchor': 'lush emotional melodrama',
               'emotion': ['heightened emotion', 'romantic conflict', 'expressive stillness', 'fragile intensity'],
               'avoid': ['neutral documentary tone']},
 'Fashion Editorial': {'anchor': 'confident luxury poise',
                       'emotion': ['controlled sensuality',
                                   'luxury calm',
                                   'confident elegance',
                                   'gallery-like poise'],
                       'avoid': ['messy amateur snapshot', 'cheap costume look']},
 'Arthouse Realism': {'anchor': 'ordinary private realism',
                      'emotion': ['ordinary private moment',
                                  'unposed emotional realism',
                                  'quiet sensuality',
                                  'natural vulnerability'],
                      'avoid': ['over-polished fantasy', 'exaggerated glamour']},
 'Pop Neon': {'anchor': 'electric nightlife excitement',
              'emotion': ['electric attraction', 'modern nightlife energy', 'glossy desire', 'color-driven tension'],
              'avoid': ['muddy lighting', 'desaturated dullness']},
 'Baroque / Operatic': {'anchor': 'operatic emotional grandeur',
                        'emotion': ['theatrical intensity',
                                    'operatic elegance',
                                    'ceremonial drama',
                                    'grand emotional weight'],
                        'avoid': ['minimal empty background',
                                  'literal picture frame',
                                  'decorative outer frame',
                                  'ornate border',
                                  'gilded border',
                                  'framed portrait on wall',
                                  'museum frame',
                                  'letterbox border',
                                  'image border']},
 'Minimalist Psychological': {'anchor': 'restrained psychological distance',
                              'emotion': ['controlled distance',
                                          'cold stillness',
                                          'subtle pressure',
                                          'restrained vulnerability'],
                              'avoid': ['busy decoration', 'chaotic color palette']},
 'Black & White Film': {'anchor': 'timeless classic-film restraint',
                        'emotion': ['austere drama', 'timeless contrast', 'classic film mood', 'tonal seriousness'],
                        'avoid': ['cartoonish brightness', 'casual colorful cheer']},
 'Golden Hour Warmth': {'anchor': 'warm nostalgic tenderness',
                        'emotion': ['warm intimacy', 'soft radiance', 'nostalgic tenderness', 'peaceful affection'],
                        'avoid': ['cold emotional distance', 'clinical harshness']},
 'Vintage / Retro': {'anchor': 'nostalgic memory warmth',
                     'emotion': ['nostalgic warmth', 'faded memory', 'retro charm', 'gentle remembrance'],
                     'avoid': ['clinical modern coldness', 'digital sterility']},
 'Cyberpunk / Sci-fi': {'anchor': 'futuristic alienation and synthetic tension',
                        'emotion': ['futuristic tension', 'digital edge', 'neon isolation', 'synthetic atmosphere'],
                        'avoid': ['pastoral calm', 'old-fashioned nostalgia']},
 'Watercolor / Painterly': {'anchor': 'delicate handmade serenity',
                            'emotion': ['soft artistic beauty',
                                        'gentle impression',
                                        'painted serenity',
                                        'lyrical softness'],
                            'avoid': ['aggressive harshness', 'clinical sharpness']},
 'Bright / High-key': {'anchor': 'cheerful airy optimism',
                       'emotion': ['cheerful lightness', 'clean radiance', 'fresh energy', 'airy calm'],
                       'avoid': ['oppressive darkness', 'heavy gloom']},
 'Cinematic Widescreen': {'anchor': 'grand narrative scale',
                          'emotion': ['epic scale',
                                      'dramatic scope',
                                      'visual storytelling',
                                      'large emotional breadth'],
                          'avoid': ['trivial snapshot feeling', 'small casual mood']},
 'Romantic / Soft Focus': {'anchor': 'tender romantic closeness',
                           'emotion': ['tender romance', 'gentle warmth', 'soft intimacy', 'dreamy closeness'],
                           'avoid': ['cold clinical distance', 'harsh emotional tone']},
 'Horror / Unsettling': {'anchor': 'creeping horror dread and unsettling silence',
                         'emotion': ['creeping dread', 'ominous tension', 'psychological horror', 'eerie silence'],
                         'avoid': ['cheerful mood', 'bright colors', 'comedy tone']}})

STYLE_DNA.update({'Watercolor / Painterly': {'anchor': 'watercolor painterly illustration',
                            'lighting': ['soft ambient wash',
                                         'gentle diffused light',
                                         'even tonal fill',
                                         'transparent luminous wash'],
                            'color': ['soft pigment wash',
                                      'translucent layered hues',
                                      'muted watercolor palette',
                                      'gentle bleed at edges'],
                            'composition': ['loose painterly composition',
                                            'soft edge treatment',
                                            'artistic negative space',
                                            'hand-painted composition'],
                            'texture': ['visible brushstroke texture',
                                        'wet-on-wet paint bleed',
                                        'paper grain beneath pigment',
                                        'soft color diffusion',
                                        'pigment bloom on paper'],
                            'avoid': ['photorealistic rendering',
                                      'realistic camera lens look',
                                      'hard photographic sharpness',
                                      'glossy photo skin',
                                      'cinematic lens realism']},
 'Dream Pastel Diffusion': {'anchor': 'dreamlike pastel illustration glow',
                            'lighting': ['diffused glow',
                                         'soft rear glow',
                                         'ethereal illumination',
                                         'gentle bloom around edges'],
                            'color': ['pastel palette',
                                      'pink lavender tones',
                                      'soft cyan accent',
                                      'pearl white haze'],
                            'composition': ['floating composition',
                                            'soft-focus depth',
                                            'airy dreamlike spacing',
                                            'surreal gentle framing'],
                            'texture': ['soft bloom',
                                        'hazy texture',
                                        'silky tonal blend',
                                        'powdery pastel diffusion'],
                            'avoid': ['photorealistic rendering',
                                      'realistic camera lens look',
                                      'hard photographic sharpness',
                                      'glossy photo skin',
                                      'cinematic lens realism']},
 'Soft Romantic Glow': {'anchor': 'romantic soft luminous glow',
                        'lighting': ['soft warm illumination', 'gentle rear glow', 'diffused glow', 'warm edge glow'],
                        'color': ['warm pink tones', 'soft peach', 'creamy highlights', 'gentle warmth'],
                        'composition': ['close intimate composition',
                                        'soft focus depth',
                                        'gently blurred atmosphere',
                                        'tender visual spacing'],
                        'texture': ['soft bloom',
                                    'dreamy haze',
                                    'smooth luminous texture',
                                    'delicate glow diffusion'],
                        'avoid': ['hard photographic sharpness', 'clinical crisp lighting']},
 'Baroque Operatic Atmosphere': {'anchor': 'baroque operatic atmosphere',
                                 'lighting': ['dramatic chiaroscuro',
                                              'warm theatrical glow',
                                              'deep velvet shadow',
                                              'candlelit stage glow'],
                                 'color': ['antique gold tones',
                                           'burgundy velvet',
                                           'ivory highlights',
                                           'deep umber shadows'],
                                 'composition': ['grand theatrical staging',
                                                 'opulent classical depth',
                                                 'ceremonial pose rhythm',
                                                 'opera-house atmosphere'],
                                 'texture': ['velvet tonal richness',
                                             'painted tonal depth',
                                             'rich classical texture',
                                             'old master style finish'],
                                 'avoid': ['literal picture frame',
                                           'ornate outer border',
                                           'framed portrait on wall',
                                           'museum frame border']},
 'Charcoal Drawing': {'anchor': 'expressive charcoal drawing',
                      'lighting': ['broad tonal shading',
                                   'soft value gradation',
                                   'smudged shadow mass',
                                   'dramatic charcoal contrast'],
                      'color': ['monochrome charcoal tones',
                                'deep black charcoal',
                                'warm paper gray',
                                'soft ash values'],
                      'composition': ['loose sketch composition',
                                      'expressive hand-drawn structure',
                                      'strong silhouette emphasis',
                                      'gestural mark placement'],
                      'texture': ['charcoal grain',
                                  'powdery smudge texture',
                                  'paper tooth',
                                  'visible hand-drawn strokes'],
                      'avoid': ['photorealistic rendering',
                                'realistic camera lens look',
                                'hard photographic sharpness',
                                'glossy photo skin',
                                'cinematic lens realism',
                                'clean vector edges']},
 'Graphite Pencil Sketch': {'anchor': 'graphite pencil sketch',
                            'lighting': ['soft graphite shading',
                                         'delicate value transitions',
                                         'light pencil hatching',
                                         'gentle tonal modeling'],
                            'color': ['graphite gray tones',
                                      'off-white paper',
                                      'subtle silver-gray values',
                                      'pale sketchbook palette'],
                            'composition': ['observational sketch composition',
                                            'precise hand-drawn contour',
                                            'light construction lines',
                                            'quiet negative space'],
                            'texture': ['fine pencil grain',
                                        'visible hatching',
                                        'paper texture',
                                        'eraser-softened shading'],
                            'avoid': ['photorealistic rendering',
                                      'realistic camera lens look',
                                      'hard photographic sharpness',
                                      'glossy photo skin',
                                      'cinematic lens realism',
                                      'ink-heavy outlines']},
 'Pen and Ink Sketch': {'anchor': 'pen and ink illustration',
                        'lighting': ['line-based shadow',
                                     'cross-hatched tonal contrast',
                                     'inked shadow accents',
                                     'graphic light separation'],
                        'color': ['black ink on warm paper',
                                  'monochrome ink tones',
                                  'sepia ink accent',
                                  'clean black linework'],
                        'composition': ['crisp contour drawing',
                                        'expressive ink composition',
                                        'illustrative negative space',
                                        'graphic silhouette rhythm'],
                        'texture': ['crosshatching', 'fine ink linework', 'dry pen texture', 'hand-inked strokes'],
                        'avoid': ['photorealistic rendering',
                                  'realistic camera lens look',
                                  'hard photographic sharpness',
                                  'glossy photo skin',
                                  'cinematic lens realism',
                                  'soft photo blur']},
 'Ink Wash / Sumi-e': {'anchor': 'ink wash sumi-e illustration',
                       'lighting': ['soft ink wash values',
                                    'empty-space tonal balance',
                                    'misty ink gradation',
                                    'gentle paper brightness'],
                       'color': ['black ink wash', 'gray ink gradients', 'rice-paper white', 'subtle sepia wash'],
                       'composition': ['minimal brush composition',
                                       'large quiet negative space',
                                       'calligraphic balance',
                                       'asymmetric ink placement'],
                       'texture': ['bleeding ink wash',
                                   'dry brush texture',
                                   'rice paper grain',
                                   'calligraphic brush marks'],
                       'avoid': ['photorealistic rendering',
                                 'realistic camera lens look',
                                 'hard photographic sharpness',
                                 'glossy photo skin',
                                 'cinematic lens realism',
                                 'busy photorealistic detail']},
 'Colored Pencil Illustration': {'anchor': 'colored pencil illustration',
                                 'lighting': ['soft drawn shading',
                                              'layered pencil highlight',
                                              'gentle value modeling',
                                              'hand-colored light'],
                                 'color': ['layered colored pencil hues',
                                           'soft saturated pencil color',
                                           'warm sketchbook palette',
                                           'subtle color layering'],
                                 'composition': ['illustrated sketch composition',
                                                 'gentle hand-drawn framing',
                                                 'storybook-like arrangement',
                                                 'clear drawn silhouette'],
                                 'texture': ['colored pencil grain',
                                             'visible pencil strokes',
                                             'paper tooth',
                                             'layered waxy pigment'],
                                 'avoid': ['photorealistic rendering',
                                           'realistic camera lens look',
                                           'hard photographic sharpness',
                                           'glossy photo skin',
                                           'cinematic lens realism',
                                           'airbrushed plastic finish']},
 'Pastel Chalk Drawing': {'anchor': 'soft pastel chalk drawing',
                          'lighting': ['powdery soft light',
                                       'diffused tonal glow',
                                       'gentle chalk highlight',
                                       'velvety shade transition'],
                          'color': ['soft pastel pigments',
                                    'chalky pink blue palette',
                                    'powdery warm tones',
                                    'muted pastel layers'],
                          'composition': ['soft handmade composition',
                                          'blurred pastel edges',
                                          'gentle figure-ground balance',
                                          'dreamy sketchbook layout'],
                          'texture': ['chalk dust texture',
                                      'powdery pigment',
                                      'soft smudged edges',
                                      'toothy pastel paper'],
                          'avoid': ['photorealistic rendering',
                                    'realistic camera lens look',
                                    'hard photographic sharpness',
                                    'glossy photo skin',
                                    'cinematic lens realism',
                                    'glossy digital finish']},
 'Gouache Storybook Illustration': {'anchor': 'gouache storybook illustration',
                                    'lighting': ['painted soft light',
                                                 'storybook glow',
                                                 'opaque color lighting',
                                                 'gentle illustrated illumination'],
                                    'color': ['opaque gouache color',
                                              'warm storybook palette',
                                              'matte saturated hues',
                                              'hand-painted color blocks'],
                                    'composition': ['storybook illustration composition',
                                                    'clear readable shapes',
                                                    'charming painted arrangement',
                                                    'hand-painted scenic balance'],
                                    'texture': ['matte gouache texture',
                                                'visible brush marks',
                                                'painted paper surface',
                                                'opaque pigment layering'],
                                    'avoid': ['photorealistic rendering',
                                              'realistic camera lens look',
                                              'hard photographic sharpness',
                                              'glossy photo skin',
                                              'cinematic lens realism',
                                              'photographic depth of field']},
 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted storybook animation style',
                                      'lighting': ['gentle animated light',
                                                   'warm painted glow',
                                                   'soft atmospheric illumination',
                                                   'storybook sky light'],
                                      'color': ['lush hand-painted palette',
                                                'warm natural greens',
                                                'soft sky blues',
                                                'gentle cream highlights'],
                                      'composition': ['animated storybook composition',
                                                      'clear readable silhouette',
                                                      'environmental painted staging',
                                                      'whimsical scenic balance'],
                                      'texture': ['hand-painted background texture',
                                                  'soft animation cel edges',
                                                  'painted brush texture',
                                                  'storybook matte finish'],
                                      'avoid': ['photorealistic rendering',
                                                'realistic camera lens look',
                                                'hard photographic sharpness',
                                                'glossy photo skin',
                                                'cinematic lens realism',
                                                'live-action realism',
                                                'camera lens artifacts']},
 'Clean Cel Animation': {'anchor': 'clean cel animation style',
                         'lighting': ['simple cel-shaded light',
                                      'clean shadow shapes',
                                      'flat animated lighting',
                                      'soft highlight blocks'],
                         'color': ['clear cel color',
                                   'flat saturated palette',
                                   'clean anime color blocks',
                                   'controlled accent colors'],
                         'composition': ['clear animation layout',
                                         'readable character silhouette',
                                         'graphic shot composition',
                                         'balanced animated staging'],
                         'texture': ['clean line art', 'flat color fills', 'subtle cel texture', 'crisp drawn edges'],
                         'avoid': ['photorealistic rendering',
                                   'realistic camera lens look',
                                   'hard photographic sharpness',
                                   'glossy photo skin',
                                   'cinematic lens realism',
                                   'realistic skin pores',
                                   'photographic grain']}})

AUTO_STYLE_BY_MOOD.update({'Watercolor / Painterly': 'Watercolor / Painterly',
 'Dreamlike / Surreal': 'Dream Pastel Diffusion',
 'Romantic / Soft Focus': 'Soft Romantic Glow',
 'Black & White Film': 'Black & White Classic',
 'Golden Hour Warmth': 'Golden Hour Glow',
 'Vintage / Retro': 'Vintage Film Look',
 'Cyberpunk / Sci-fi': 'Cyberpunk Neon',
 'Bright / High-key': 'High-key Clean Light',
 'Cinematic Widescreen': 'Cinematic Widescreen Scope',
 'Baroque / Operatic': 'Baroque Operatic Atmosphere'})

NONPHYSICAL_STYLE_CUES.update({'Watercolor / Painterly': {'anchor': 'watercolor painterly illustration',
                            'lighting': ['soft ambient wash',
                                         'gentle diffused light',
                                         'even tonal fill',
                                         'transparent luminous wash'],
                            'color': ['soft pigment wash',
                                      'translucent layered hues',
                                      'muted watercolor palette',
                                      'gentle bleed at edges'],
                            'composition': ['loose painterly composition',
                                            'soft edge treatment',
                                            'artistic negative space',
                                            'hand-painted composition'],
                            'texture': ['visible brushstroke texture',
                                        'wet-on-wet paint bleed',
                                        'paper grain beneath pigment',
                                        'soft color diffusion',
                                        'pigment bloom on paper']},
 'Dream Pastel Diffusion': {'anchor': 'dreamlike pastel illustration glow',
                            'lighting': ['diffused glow',
                                         'soft rear glow',
                                         'ethereal illumination',
                                         'gentle bloom around edges'],
                            'color': ['pastel palette',
                                      'pink lavender tones',
                                      'soft cyan accent',
                                      'pearl white haze'],
                            'composition': ['floating composition',
                                            'soft-focus depth',
                                            'airy dreamlike spacing',
                                            'surreal gentle framing'],
                            'texture': ['soft bloom',
                                        'hazy texture',
                                        'silky tonal blend',
                                        'powdery pastel diffusion']},
 'Soft Romantic Glow': {'anchor': 'romantic soft luminous glow',
                        'lighting': ['soft warm illumination', 'gentle rear glow', 'diffused glow', 'warm edge glow'],
                        'color': ['warm pink tones', 'soft peach', 'creamy highlights', 'gentle warmth'],
                        'composition': ['close intimate composition',
                                        'soft focus depth',
                                        'gently blurred atmosphere',
                                        'tender visual spacing'],
                        'texture': ['soft bloom',
                                    'dreamy haze',
                                    'smooth luminous texture',
                                    'delicate glow diffusion']},
 'Baroque Operatic Atmosphere': {'anchor': 'baroque operatic atmosphere',
                                 'lighting': ['dramatic chiaroscuro',
                                              'warm theatrical glow',
                                              'deep velvet shadow',
                                              'candlelit stage glow'],
                                 'color': ['antique gold tones',
                                           'burgundy velvet',
                                           'ivory highlights',
                                           'deep umber shadows'],
                                 'composition': ['grand theatrical staging',
                                                 'opulent classical depth',
                                                 'ceremonial pose rhythm',
                                                 'opera-house atmosphere'],
                                 'texture': ['velvet tonal richness',
                                             'painted tonal depth',
                                             'rich classical texture',
                                             'old master style finish']},
 'Charcoal Drawing': {'anchor': 'expressive charcoal drawing',
                      'lighting': ['broad tonal shading',
                                   'soft value gradation',
                                   'smudged shadow mass',
                                   'dramatic charcoal contrast'],
                      'color': ['monochrome charcoal tones',
                                'deep black charcoal',
                                'warm paper gray',
                                'soft ash values'],
                      'composition': ['loose sketch composition',
                                      'expressive hand-drawn structure',
                                      'strong silhouette emphasis',
                                      'gestural mark placement'],
                      'texture': ['charcoal grain',
                                  'powdery smudge texture',
                                  'paper tooth',
                                  'visible hand-drawn strokes']},
 'Graphite Pencil Sketch': {'anchor': 'graphite pencil sketch',
                            'lighting': ['soft graphite shading',
                                         'delicate value transitions',
                                         'light pencil hatching',
                                         'gentle tonal modeling'],
                            'color': ['graphite gray tones',
                                      'off-white paper',
                                      'subtle silver-gray values',
                                      'pale sketchbook palette'],
                            'composition': ['observational sketch composition',
                                            'precise hand-drawn contour',
                                            'light construction lines',
                                            'quiet negative space'],
                            'texture': ['fine pencil grain',
                                        'visible hatching',
                                        'paper texture',
                                        'eraser-softened shading']},
 'Pen and Ink Sketch': {'anchor': 'pen and ink illustration',
                        'lighting': ['line-based shadow',
                                     'cross-hatched tonal contrast',
                                     'inked shadow accents',
                                     'graphic light separation'],
                        'color': ['black ink on warm paper',
                                  'monochrome ink tones',
                                  'sepia ink accent',
                                  'clean black linework'],
                        'composition': ['crisp contour drawing',
                                        'expressive ink composition',
                                        'illustrative negative space',
                                        'graphic silhouette rhythm'],
                        'texture': ['crosshatching', 'fine ink linework', 'dry pen texture', 'hand-inked strokes']},
 'Ink Wash / Sumi-e': {'anchor': 'ink wash sumi-e illustration',
                       'lighting': ['soft ink wash values',
                                    'empty-space tonal balance',
                                    'misty ink gradation',
                                    'gentle paper brightness'],
                       'color': ['black ink wash', 'gray ink gradients', 'rice-paper white', 'subtle sepia wash'],
                       'composition': ['minimal brush composition',
                                       'large quiet negative space',
                                       'calligraphic balance',
                                       'asymmetric ink placement'],
                       'texture': ['bleeding ink wash',
                                   'dry brush texture',
                                   'rice paper grain',
                                   'calligraphic brush marks']},
 'Colored Pencil Illustration': {'anchor': 'colored pencil illustration',
                                 'lighting': ['soft drawn shading',
                                              'layered pencil highlight',
                                              'gentle value modeling',
                                              'hand-colored light'],
                                 'color': ['layered colored pencil hues',
                                           'soft saturated pencil color',
                                           'warm sketchbook palette',
                                           'subtle color layering'],
                                 'composition': ['illustrated sketch composition',
                                                 'gentle hand-drawn framing',
                                                 'storybook-like arrangement',
                                                 'clear drawn silhouette'],
                                 'texture': ['colored pencil grain',
                                             'visible pencil strokes',
                                             'paper tooth',
                                             'layered waxy pigment']},
 'Pastel Chalk Drawing': {'anchor': 'soft pastel chalk drawing',
                          'lighting': ['powdery soft light',
                                       'diffused tonal glow',
                                       'gentle chalk highlight',
                                       'velvety shade transition'],
                          'color': ['soft pastel pigments',
                                    'chalky pink blue palette',
                                    'powdery warm tones',
                                    'muted pastel layers'],
                          'composition': ['soft handmade composition',
                                          'blurred pastel edges',
                                          'gentle figure-ground balance',
                                          'dreamy sketchbook layout'],
                          'texture': ['chalk dust texture',
                                      'powdery pigment',
                                      'soft smudged edges',
                                      'toothy pastel paper']},
 'Gouache Storybook Illustration': {'anchor': 'gouache storybook illustration',
                                    'lighting': ['painted soft light',
                                                 'storybook glow',
                                                 'opaque color lighting',
                                                 'gentle illustrated illumination'],
                                    'color': ['opaque gouache color',
                                              'warm storybook palette',
                                              'matte saturated hues',
                                              'hand-painted color blocks'],
                                    'composition': ['storybook illustration composition',
                                                    'clear readable shapes',
                                                    'charming painted arrangement',
                                                    'hand-painted scenic balance'],
                                    'texture': ['matte gouache texture',
                                                'visible brush marks',
                                                'painted paper surface',
                                                'opaque pigment layering']},
 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted storybook animation style',
                                      'lighting': ['gentle animated light',
                                                   'warm painted glow',
                                                   'soft atmospheric illumination',
                                                   'storybook sky light'],
                                      'color': ['lush hand-painted palette',
                                                'warm natural greens',
                                                'soft sky blues',
                                                'gentle cream highlights'],
                                      'composition': ['animated storybook composition',
                                                      'clear readable silhouette',
                                                      'environmental painted staging',
                                                      'whimsical scenic balance'],
                                      'texture': ['hand-painted background texture',
                                                  'soft animation cel edges',
                                                  'painted brush texture',
                                                  'storybook matte finish']},
 'Clean Cel Animation': {'anchor': 'clean cel animation style',
                         'lighting': ['simple cel-shaded light',
                                      'clean shadow shapes',
                                      'flat animated lighting',
                                      'soft highlight blocks'],
                         'color': ['clear cel color',
                                   'flat saturated palette',
                                   'clean anime color blocks',
                                   'controlled accent colors'],
                         'composition': ['clear animation layout',
                                         'readable character silhouette',
                                         'graphic shot composition',
                                         'balanced animated staging'],
                         'texture': ['clean line art',
                                     'flat color fills',
                                     'subtle cel texture',
                                     'crisp drawn edges']}})

MOOD_FAMILIES = _load_data_dict("mood_families.json", MOOD_FAMILIES)
STYLE_DNA = _load_data_dict("style_dna.json", STYLE_DNA)
AUTO_STYLE_BY_MOOD = _load_data_dict("auto_style_by_mood.json", AUTO_STYLE_BY_MOOD)
ADULT_WARDROBE = _load_data_dict("adult_wardrobe.json", ADULT_WARDROBE)
SCENE_FRAMING = _load_data_dict("scene_framing.json", SCENE_FRAMING)
LENS_PRESETS = _load_data_dict("lens_presets.json", LENS_PRESETS)
EXPLICITNESS = _load_data_dict("explicitness.json", EXPLICITNESS)
MODEL_PROFILES = _load_data_dict("model_profiles.json", MODEL_PROFILES)

STYLE_TUNING_PATCH_2026_05_31 = {'Dream Pastel Diffusion': {'anchor': 'soft pastel atmospheric painting with diffused luminous haze',
                            'lighting': ['milky diffused glow',
                                         'soft rear haze',
                                         'ethereal luminous mist',
                                         'gentle bloom through pastel air',
                                         'low-contrast scattered light',
                                         'pearlescent ambient haze'],
                            'color': ['powder pastel palette',
                                      'pink lavender mist',
                                      'soft cyan veil',
                                      'pearl white haze',
                                      'pale cream undertones'],
                            'composition': ['floating atmospheric composition',
                                            'layered haze depth',
                                            'airy surreal spacing',
                                            'soft drifting balance',
                                            'unsharp painterly depth layers'],
                            'texture': ['powdery pastel diffusion',
                                        'silky haze texture',
                                        'soft pigment bloom',
                                        'blurred pastel edges',
                                        'matte luminous surface'],
                            'avoid': ['photorealistic rendering',
                                      'realistic camera lens look',
                                      'hard photographic sharpness',
                                      'glossy photo skin',
                                      'cinematic lens realism',
                                      'clean cel animation',
                                      'plastic 3D render']},
 'Watercolor / Painterly': {'anchor': 'traditional watercolor painting on textured paper',
                            'lighting': ['transparent watercolor wash light',
                                         'soft ambient paper glow',
                                         'gentle diffused tonal wash',
                                         'pale luminous pigment wash',
                                         'low-contrast hand-painted light'],
                            'color': ['transparent layered pigments',
                                      'soft pigment wash',
                                      'muted watercolor palette',
                                      'edge-bleeding color',
                                      'diluted mineral tones',
                                      'pooled pigment blooms'],
                            'composition': ['loose watercolor study composition',
                                            'brush-led visual flow',
                                            'unfilled paper breathing room',
                                            'hand-painted placement',
                                            'soft unfinished paper margins',
                                            'painterly negative space'],
                            'texture': ['wet-on-wet paint bleed',
                                        'visible watercolor brush marks',
                                        'paper grain beneath pigment',
                                        'pigment bloom on paper',
                                        'feathered edge diffusion',
                                        'granulating watercolor texture',
                                        'uneven hand-painted washes'],
                            'avoid': ['photorealistic rendering',
                                      'realistic camera lens look',
                                      'hard photographic sharpness',
                                      'glossy photo skin',
                                      'cinematic lens realism',
                                      'clean cel animation',
                                      'airbrushed digital finish']},
 'Gouache Storybook Illustration': {'anchor': 'matte gouache painting for a classic picture-book page',
                                    'lighting': ['painted soft light',
                                                 'storybook page glow',
                                                 'opaque color lighting',
                                                 'gentle gouache illumination',
                                                 'flat matte painted light'],
                                    'color': ['opaque gouache color',
                                              'warm picture-book palette',
                                              'matte saturated hues',
                                              'hand-painted color blocks',
                                              'cream paper undertones'],
                                    'composition': ['classic picture-book composition',
                                                    'clear readable painted shapes',
                                                    'charming gouache arrangement',
                                                    'hand-painted scenic balance',
                                                    'simple page-like staging'],
                                    'texture': ['matte gouache texture',
                                                'visible opaque brush marks',
                                                'painted paper surface',
                                                'layered gouache pigment',
                                                'slightly uneven hand-painted edges'],
                                    'avoid': ['photorealistic rendering',
                                              'realistic camera lens look',
                                              'hard photographic sharpness',
                                              'glossy photo skin',
                                              'cinematic lens realism',
                                              'photographic depth of field',
                                              'clean cel animation']},
 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted picture-book painting',
                                      'lighting': ['warm painted glow',
                                                   'gentle storybook light',
                                                   'soft atmospheric painted illumination',
                                                   'paper-soft sky light'],
                                      'color': ['hand-painted natural palette',
                                                'warm gentle greens',
                                                'soft sky blues',
                                                'cream highlights',
                                                'matte storybook colors'],
                                      'composition': ['storybook page composition',
                                                      'clear readable silhouette',
                                                      'painted scenic staging',
                                                      'whimsical picture-book balance',
                                                      'simple hand-painted layout'],
                                      'texture': ['hand-painted background texture',
                                                  'painted brush texture',
                                                  'storybook matte finish',
                                                  'soft paper surface',
                                                  'visible traditional brushwork'],
                                      'avoid': ['photorealistic rendering',
                                                'realistic camera lens look',
                                                'hard photographic sharpness',
                                                'glossy photo skin',
                                                'cinematic lens realism',
                                                'live-action realism',
                                                'camera lens artifacts',
                                                'clean cel animation']},
 'Graphite Pencil Sketch': {'anchor': 'rough graphite pencil preliminary sketch on paper',
                            'lighting': ['soft graphite value shading',
                                         'delicate hand-shaded transitions',
                                         'light pencil hatching',
                                         'loose tonal modeling',
                                         'unfinished graphite shadow blocks'],
                            'color': ['graphite gray tones',
                                      'off-white sketchbook paper',
                                      'silver-gray pencil values',
                                      'pale paper-and-pencil palette'],
                            'composition': ['preliminary observational sketch layout',
                                            'visible construction lines',
                                            'loose exploratory contours',
                                            'unfinished study margins',
                                            'draft underdrawing structure',
                                            'quiet negative paper space'],
                            'texture': ['fine pencil grain',
                                        'visible hatching',
                                        'paper tooth',
                                        'eraser-softened shading',
                                        'graphite dust',
                                        'uneven pencil pressure marks'],
                            'avoid': ['photorealistic rendering',
                                      'realistic camera lens look',
                                      'hard photographic sharpness',
                                      'glossy photo skin',
                                      'cinematic lens realism',
                                      'ink-heavy outlines',
                                      'polished finished render',
                                      'airbrushed digital painting']},
 'Pen and Ink Sketch': {'anchor': 'rough pen and ink sketch on paper',
                        'lighting': ['line-based shadow',
                                     'cross-hatched tonal contrast',
                                     'inked shadow accents',
                                     'graphic light separation',
                                     'unfinished hatch shading'],
                        'color': ['black ink on warm paper',
                                  'monochrome ink tones',
                                  'sepia ink accent',
                                  'raw black linework'],
                        'composition': ['exploratory ink sketch layout',
                                        'loose contour drawing',
                                        'visible drafting marks',
                                        'illustrative negative paper space',
                                        'partly unfinished background lines',
                                        'graphic silhouette rhythm'],
                        'texture': ['crosshatching',
                                    'fine ink linework',
                                    'dry pen texture',
                                    'hand-inked strokes',
                                    'stray pen marks',
                                    'uneven ink pressure'],
                        'avoid': ['photorealistic rendering',
                                  'realistic camera lens look',
                                  'hard photographic sharpness',
                                  'glossy photo skin',
                                  'cinematic lens realism',
                                  'soft photo blur',
                                  'polished vector line art',
                                  'clean cel linework']},
 'Colored Pencil Illustration': {'anchor': 'colored pencil sketch drawing on textured paper',
                                 'lighting': ['soft drawn shading',
                                              'layered pencil highlight',
                                              'gentle value modeling',
                                              'hand-colored light',
                                              'pencil-shaded color transitions'],
                                 'color': ['layered colored pencil hues',
                                           'soft saturated pencil color',
                                           'warm sketchbook palette',
                                           'subtle color layering',
                                           'visible blended pencil pigment'],
                                 'composition': ['colored-pencil sketch composition',
                                                 'visible underdrawing lines',
                                                 'gentle hand-drawn layout',
                                                 'clear drawn silhouette',
                                                 'partly unfinished sketchbook edges'],
                                 'texture': ['colored pencil grain',
                                             'visible pencil strokes',
                                             'paper tooth',
                                             'layered waxy pigment',
                                             'uneven hand pressure marks'],
                                 'avoid': ['photorealistic rendering',
                                           'realistic camera lens look',
                                           'hard photographic sharpness',
                                           'glossy photo skin',
                                           'cinematic lens realism',
                                           'airbrushed plastic finish',
                                           'smooth digital anime coloring']},
 'Pastel Chalk Drawing': {'anchor': 'pastel chalk sketch drawing on textured paper',
                          'lighting': ['powdery soft light',
                                       'diffused tonal glow',
                                       'gentle chalk highlight',
                                       'velvety shade transition',
                                       'chalk-blocked soft shadows'],
                          'color': ['soft pastel pigments',
                                    'chalky pink-blue palette',
                                    'powdery warm tones',
                                    'muted pastel layers',
                                    'matte chalk colors'],
                          'composition': ['loose pastel study composition',
                                          'smudged handmade edges',
                                          'gentle figure-ground balance',
                                          'unfinished sketchbook layout',
                                          'broad chalk blocking'],
                          'texture': ['chalk dust texture',
                                      'powdery pigment',
                                      'soft smudged edges',
                                      'toothy pastel paper',
                                      'visible pastel strokes',
                                      'finger-smudged transitions'],
                          'avoid': ['photorealistic rendering',
                                    'realistic camera lens look',
                                    'hard photographic sharpness',
                                    'glossy photo skin',
                                    'cinematic lens realism',
                                    'glossy digital finish',
                                    'clean vector edges']},
 'Volumetric Dust Light': {'anchor': 'volumetric dust light scattering',
                           'lighting': ['visible light beams through dusty air',
                                        'volumetric light shafts',
                                        'soft scattered backlight',
                                        'hazy side light',
                                        'dust-mote glow'],
                           'color': ['warm amber haze',
                                     'muted golden air',
                                     'pale dusty highlights',
                                     'soft smoky neutrals'],
                           'composition': ['atmosphere-forward composition',
                                           'light rays crossing the scene',
                                           'deep hazy layers',
                                           'subject framed by suspended dust'],
                           'texture': ['floating dust motes',
                                       'fine airborne particles',
                                       'hazy volumetric atmosphere',
                                       'soft bloom in the air',
                                       'subtle particulate texture'],
                           'avoid': ['flat clean air', 'sterile lighting', 'hard flash look', 'empty atmosphere']},
 'Long Exposure Light Trails': {'anchor': 'long-exposure light trails',
                                'lighting': ['streaked moving light',
                                             'extended luminous trails',
                                             'flowing exposure glow',
                                             'night light ribbons',
                                             'motion-blurred highlights'],
                                'color': ['red and white light streaks',
                                          'neon trail accents',
                                          'deep night contrast',
                                          'glowing saturated lines'],
                                'composition': ['dynamic trail-led composition',
                                                'motion path framing',
                                                'diagonal streak rhythm',
                                                'long-exposure scene balance'],
                                'texture': ['smooth light trails',
                                            'motion blur streaks',
                                            'glowing line traces',
                                            'soft exposure bloom'],
                                'avoid': ['frozen static lighting', 'flat daylight', 'no motion trails']},
 'Oil Painting': {'anchor': 'traditional oil painting on canvas',
                  'lighting': ['painted chiaroscuro light',
                               'soft studio-like painted illumination',
                               'warm impasto highlights',
                               'layered oil-paint shadow'],
                  'color': ['rich oil-paint colors',
                            'layered earth tones',
                            'deep blended pigments',
                            'warm varnished palette'],
                  'composition': ['classical painted composition',
                                  'brush-led figure placement',
                                  'canvas-centered balance',
                                  'painterly negative space'],
                  'texture': ['visible oil brushstrokes',
                              'canvas weave texture',
                              'impasto paint ridges',
                              'layered wet-on-dry paint',
                              'thick pigment texture'],
                  'avoid': ['photorealistic rendering',
                            'realistic camera lens look',
                            'smooth digital airbrush',
                            'plastic 3D render']},
 'Miniature Diorama': {'anchor': 'miniature diorama model look',
                       'lighting': ['tiny model lighting',
                                    'soft tabletop illumination',
                                    'small-scale scene glow',
                                    'gentle display-case light'],
                       'color': ['toy-like muted colors',
                                 'painted miniature palette',
                                 'small-scale material colors',
                                 'soft diorama tones'],
                       'composition': ['miniature scale composition',
                                       'diorama staging',
                                       'tiny set arrangement',
                                       'compressed small-world layout'],
                       'texture': ['miniature model texture',
                                   'painted tiny surfaces',
                                   'crafted material detail',
                                   'small-scale set pieces'],
                       'avoid': ['life-size realism', 'ordinary full-scale scene', 'flat photograph look']},
 'Pixel Art': {'anchor': 'pixel art style',
               'lighting': ['blocky pixel lighting',
                            'dithered shadow shapes',
                            'limited-palette highlights',
                            'sprite-like light blocks'],
               'color': ['limited pixel palette', 'indexed color look', 'crisp color blocks', 'retro game colors'],
               'composition': ['sprite-like composition',
                               'grid-based visual structure',
                               'simple readable silhouette',
                               'retro game scene layout'],
               'texture': ['visible square pixels',
                           'hard pixel edges',
                           'dithered texture',
                           'low-resolution pixel grid'],
               'avoid': ['photorealistic rendering',
                         'smooth gradients',
                         'anti-aliased painting',
                         'camera lens realism']},
 '3D Collectible Figure': {'anchor': '3D collectible figure render',
                           'lighting': ['soft product-display lighting',
                                        'gentle plastic highlight',
                                        'toy showcase glow',
                                        'clean studio display light'],
                           'color': ['painted figure colors',
                                     'smooth material colors',
                                     'collectible toy palette',
                                     'clean resin tones'],
                           'composition': ['collectible figure presentation',
                                           'toy-like character staging',
                                           'display-stand composition',
                                           'small figure centered layout'],
                           'texture': ['smooth resin surface',
                                       'painted plastic material',
                                       'subtle toy seams',
                                       'matte vinyl finish',
                                       'miniature sculpt detail'],
                           'avoid': ['real human skin texture',
                                     'photorealistic live-action person',
                                     'ordinary portrait realism']},
 'Apocalyptic Wasteland': {'anchor': 'post-apocalyptic wasteland atmosphere',
                           'lighting': ['ashen overcast light',
                                        'harsh survival sunlight',
                                        'smoky backlight',
                                        'dim dust-filtered glow'],
                           'color': ['desaturated rust tones',
                                     'ash gray palette',
                                     'burnt orange accents',
                                     'dusty earth colors'],
                           'composition': ['desolate survival composition',
                                           'ruined-world staging',
                                           'empty horizon pressure',
                                           'weathered environmental storytelling'],
                           'texture': ['ash in the air',
                                       'worn metal texture',
                                       'cracked concrete',
                                       'dusty debris',
                                       'weathered surfaces'],
                           'avoid': ['clean luxury mood',
                                     'cheerful pristine setting',
                                     'polished fashion editorial atmosphere']},
 'Chibi Style': {'anchor': 'chibi super-deformed character style',
                 'lighting': ['cute simplified lighting',
                              'soft rounded highlights',
                              'bright playful light',
                              'gentle toy-like glow'],
                 'color': ['bright cute colors',
                           'simple saturated palette',
                           'soft candy tones',
                           'clear cheerful color blocks'],
                 'composition': ['large-head small-body proportions',
                                 'super-deformed character composition',
                                 'simple cute pose',
                                 'compact playful silhouette'],
                 'texture': ['clean simplified shapes',
                             'rounded stylized edges',
                             'smooth cute finish',
                             'minimal detail texture'],
                 'avoid': ['realistic adult body proportions', 'photorealistic portrait', 'serious cinematic realism']}}
NONPHYSICAL_STYLE_CUES.update({'Dream Pastel Diffusion': {'anchor': 'soft pastel atmospheric painting with diffused luminous haze',
                            'lighting': ['milky diffused glow',
                                         'soft rear haze',
                                         'ethereal luminous mist',
                                         'gentle bloom through pastel air',
                                         'low-contrast scattered light',
                                         'pearlescent ambient haze'],
                            'color': ['powder pastel palette',
                                      'pink lavender mist',
                                      'soft cyan veil',
                                      'pearl white haze',
                                      'pale cream undertones'],
                            'composition': ['floating atmospheric composition',
                                            'layered haze depth',
                                            'airy surreal spacing',
                                            'soft drifting balance',
                                            'unsharp painterly depth layers'],
                            'texture': ['powdery pastel diffusion',
                                        'silky haze texture',
                                        'soft pigment bloom',
                                        'blurred pastel edges',
                                        'matte luminous surface']},
 'Watercolor / Painterly': {'anchor': 'traditional watercolor painting on textured paper',
                            'lighting': ['transparent watercolor wash light',
                                         'soft ambient paper glow',
                                         'gentle diffused tonal wash',
                                         'pale luminous pigment wash',
                                         'low-contrast hand-painted light'],
                            'color': ['transparent layered pigments',
                                      'soft pigment wash',
                                      'muted watercolor palette',
                                      'edge-bleeding color',
                                      'diluted mineral tones',
                                      'pooled pigment blooms'],
                            'composition': ['loose watercolor study composition',
                                            'brush-led visual flow',
                                            'unfilled paper breathing room',
                                            'hand-painted placement',
                                            'soft unfinished paper margins',
                                            'painterly negative space'],
                            'texture': ['wet-on-wet paint bleed',
                                        'visible watercolor brush marks',
                                        'paper grain beneath pigment',
                                        'pigment bloom on paper',
                                        'feathered edge diffusion',
                                        'granulating watercolor texture',
                                        'uneven hand-painted washes']},
 'Gouache Storybook Illustration': {'anchor': 'matte gouache painting for a classic picture-book page',
                                    'lighting': ['painted soft light',
                                                 'storybook page glow',
                                                 'opaque color lighting',
                                                 'gentle gouache illumination',
                                                 'flat matte painted light'],
                                    'color': ['opaque gouache color',
                                              'warm picture-book palette',
                                              'matte saturated hues',
                                              'hand-painted color blocks',
                                              'cream paper undertones'],
                                    'composition': ['classic picture-book composition',
                                                    'clear readable painted shapes',
                                                    'charming gouache arrangement',
                                                    'hand-painted scenic balance',
                                                    'simple page-like staging'],
                                    'texture': ['matte gouache texture',
                                                'visible opaque brush marks',
                                                'painted paper surface',
                                                'layered gouache pigment',
                                                'slightly uneven hand-painted edges']},
 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted picture-book painting',
                                      'lighting': ['warm painted glow',
                                                   'gentle storybook light',
                                                   'soft atmospheric painted illumination',
                                                   'paper-soft sky light'],
                                      'color': ['hand-painted natural palette',
                                                'warm gentle greens',
                                                'soft sky blues',
                                                'cream highlights',
                                                'matte storybook colors'],
                                      'composition': ['storybook page composition',
                                                      'clear readable silhouette',
                                                      'painted scenic staging',
                                                      'whimsical picture-book balance',
                                                      'simple hand-painted layout'],
                                      'texture': ['hand-painted background texture',
                                                  'painted brush texture',
                                                  'storybook matte finish',
                                                  'soft paper surface',
                                                  'visible traditional brushwork']},
 'Graphite Pencil Sketch': {'anchor': 'rough graphite pencil preliminary sketch on paper',
                            'lighting': ['soft graphite value shading',
                                         'delicate hand-shaded transitions',
                                         'light pencil hatching',
                                         'loose tonal modeling',
                                         'unfinished graphite shadow blocks'],
                            'color': ['graphite gray tones',
                                      'off-white sketchbook paper',
                                      'silver-gray pencil values',
                                      'pale paper-and-pencil palette'],
                            'composition': ['preliminary observational sketch layout',
                                            'visible construction lines',
                                            'loose exploratory contours',
                                            'unfinished study margins',
                                            'draft underdrawing structure',
                                            'quiet negative paper space'],
                            'texture': ['fine pencil grain',
                                        'visible hatching',
                                        'paper tooth',
                                        'eraser-softened shading',
                                        'graphite dust',
                                        'uneven pencil pressure marks']},
 'Pen and Ink Sketch': {'anchor': 'rough pen and ink sketch on paper',
                        'lighting': ['line-based shadow',
                                     'cross-hatched tonal contrast',
                                     'inked shadow accents',
                                     'graphic light separation',
                                     'unfinished hatch shading'],
                        'color': ['black ink on warm paper',
                                  'monochrome ink tones',
                                  'sepia ink accent',
                                  'raw black linework'],
                        'composition': ['exploratory ink sketch layout',
                                        'loose contour drawing',
                                        'visible drafting marks',
                                        'illustrative negative paper space',
                                        'partly unfinished background lines',
                                        'graphic silhouette rhythm'],
                        'texture': ['crosshatching',
                                    'fine ink linework',
                                    'dry pen texture',
                                    'hand-inked strokes',
                                    'stray pen marks',
                                    'uneven ink pressure']},
 'Colored Pencil Illustration': {'anchor': 'colored pencil sketch drawing on textured paper',
                                 'lighting': ['soft drawn shading',
                                              'layered pencil highlight',
                                              'gentle value modeling',
                                              'hand-colored light',
                                              'pencil-shaded color transitions'],
                                 'color': ['layered colored pencil hues',
                                           'soft saturated pencil color',
                                           'warm sketchbook palette',
                                           'subtle color layering',
                                           'visible blended pencil pigment'],
                                 'composition': ['colored-pencil sketch composition',
                                                 'visible underdrawing lines',
                                                 'gentle hand-drawn layout',
                                                 'clear drawn silhouette',
                                                 'partly unfinished sketchbook edges'],
                                 'texture': ['colored pencil grain',
                                             'visible pencil strokes',
                                             'paper tooth',
                                             'layered waxy pigment',
                                             'uneven hand pressure marks']},
 'Pastel Chalk Drawing': {'anchor': 'pastel chalk sketch drawing on textured paper',
                          'lighting': ['powdery soft light',
                                       'diffused tonal glow',
                                       'gentle chalk highlight',
                                       'velvety shade transition',
                                       'chalk-blocked soft shadows'],
                          'color': ['soft pastel pigments',
                                    'chalky pink-blue palette',
                                    'powdery warm tones',
                                    'muted pastel layers',
                                    'matte chalk colors'],
                          'composition': ['loose pastel study composition',
                                          'smudged handmade edges',
                                          'gentle figure-ground balance',
                                          'unfinished sketchbook layout',
                                          'broad chalk blocking'],
                          'texture': ['chalk dust texture',
                                      'powdery pigment',
                                      'soft smudged edges',
                                      'toothy pastel paper',
                                      'visible pastel strokes',
                                      'finger-smudged transitions']},
 'Volumetric Dust Light': {'anchor': 'volumetric dust light scattering',
                           'lighting': ['visible light beams through dusty air',
                                        'volumetric light shafts',
                                        'soft scattered backlight',
                                        'hazy side light',
                                        'dust-mote glow'],
                           'color': ['warm amber haze',
                                     'muted golden air',
                                     'pale dusty highlights',
                                     'soft smoky neutrals'],
                           'composition': ['atmosphere-forward composition',
                                           'light rays crossing the scene',
                                           'deep hazy layers',
                                           'subject framed by suspended dust'],
                           'texture': ['floating dust motes',
                                       'fine airborne particles',
                                       'hazy volumetric atmosphere',
                                       'soft bloom in the air',
                                       'subtle particulate texture']},
 'Long Exposure Light Trails': {'anchor': 'long-exposure light trails',
                                'lighting': ['streaked moving light',
                                             'extended luminous trails',
                                             'flowing exposure glow',
                                             'night light ribbons',
                                             'motion-blurred highlights'],
                                'color': ['red and white light streaks',
                                          'neon trail accents',
                                          'deep night contrast',
                                          'glowing saturated lines'],
                                'composition': ['dynamic trail-led composition',
                                                'motion path framing',
                                                'diagonal streak rhythm',
                                                'long-exposure scene balance'],
                                'texture': ['smooth light trails',
                                            'motion blur streaks',
                                            'glowing line traces',
                                            'soft exposure bloom']},
 'Oil Painting': {'anchor': 'traditional oil painting on canvas',
                  'lighting': ['painted chiaroscuro light',
                               'soft studio-like painted illumination',
                               'warm impasto highlights',
                               'layered oil-paint shadow'],
                  'color': ['rich oil-paint colors',
                            'layered earth tones',
                            'deep blended pigments',
                            'warm varnished palette'],
                  'composition': ['classical painted composition',
                                  'brush-led figure placement',
                                  'canvas-centered balance',
                                  'painterly negative space'],
                  'texture': ['visible oil brushstrokes',
                              'canvas weave texture',
                              'impasto paint ridges',
                              'layered wet-on-dry paint',
                              'thick pigment texture']},
 'Miniature Diorama': {'anchor': 'miniature diorama model look',
                       'lighting': ['tiny model lighting',
                                    'soft tabletop illumination',
                                    'small-scale scene glow',
                                    'gentle display-case light'],
                       'color': ['toy-like muted colors',
                                 'painted miniature palette',
                                 'small-scale material colors',
                                 'soft diorama tones'],
                       'composition': ['miniature scale composition',
                                       'diorama staging',
                                       'tiny set arrangement',
                                       'compressed small-world layout'],
                       'texture': ['miniature model texture',
                                   'painted tiny surfaces',
                                   'crafted material detail',
                                   'small-scale set pieces']},
 'Pixel Art': {'anchor': 'pixel art style',
               'lighting': ['blocky pixel lighting',
                            'dithered shadow shapes',
                            'limited-palette highlights',
                            'sprite-like light blocks'],
               'color': ['limited pixel palette', 'indexed color look', 'crisp color blocks', 'retro game colors'],
               'composition': ['sprite-like composition',
                               'grid-based visual structure',
                               'simple readable silhouette',
                               'retro game scene layout'],
               'texture': ['visible square pixels',
                           'hard pixel edges',
                           'dithered texture',
                           'low-resolution pixel grid']},
 '3D Collectible Figure': {'anchor': '3D collectible figure render',
                           'lighting': ['soft product-display lighting',
                                        'gentle plastic highlight',
                                        'toy showcase glow',
                                        'clean studio display light'],
                           'color': ['painted figure colors',
                                     'smooth material colors',
                                     'collectible toy palette',
                                     'clean resin tones'],
                           'composition': ['collectible figure presentation',
                                           'toy-like character staging',
                                           'display-stand composition',
                                           'small figure centered layout'],
                           'texture': ['smooth resin surface',
                                       'painted plastic material',
                                       'subtle toy seams',
                                       'matte vinyl finish',
                                       'miniature sculpt detail']},
 'Apocalyptic Wasteland': {'anchor': 'post-apocalyptic wasteland atmosphere',
                           'lighting': ['ashen overcast light',
                                        'harsh survival sunlight',
                                        'smoky backlight',
                                        'dim dust-filtered glow'],
                           'color': ['desaturated rust tones',
                                     'ash gray palette',
                                     'burnt orange accents',
                                     'dusty earth colors'],
                           'composition': ['desolate survival composition',
                                           'ruined-world staging',
                                           'empty horizon pressure',
                                           'weathered environmental storytelling'],
                           'texture': ['ash in the air',
                                       'worn metal texture',
                                       'cracked concrete',
                                       'dusty debris',
                                       'weathered surfaces']},
 'Chibi Style': {'anchor': 'chibi super-deformed character style',
                 'lighting': ['cute simplified lighting',
                              'soft rounded highlights',
                              'bright playful light',
                              'gentle toy-like glow'],
                 'color': ['bright cute colors',
                           'simple saturated palette',
                           'soft candy tones',
                           'clear cheerful color blocks'],
                 'composition': ['large-head small-body proportions',
                                 'super-deformed character composition',
                                 'simple cute pose',
                                 'compact playful silhouette'],
                 'texture': ['clean simplified shapes',
                             'rounded stylized edges',
                             'smooth cute finish',
                             'minimal detail texture']}})
STYLE_DNA.update(STYLE_TUNING_PATCH_2026_05_31)
STYLE_REFINEMENT_PATCH_2026_05_31_B = {'Dream Pastel Diffusion': {'anchor': 'dreamlike pastel painting with diffused luminous haze', 'lighting': ['milky diffused glow', 'soft ambient mist light', 'ethereal luminous mist', 'gentle bloom through pastel air', 'low-contrast scattered light', 'pearlescent ambient haze'], 'color': ['powder pastel palette', 'pink lavender mist', 'soft cyan veil', 'pearl white haze', 'pale cream undertones'], 'composition': ['floating atmospheric composition', 'layered haze depth', 'airy surreal spacing', 'soft drifting balance', 'unsharp painterly depth layers'], 'texture': ['powdery pastel diffusion', 'silky haze texture', 'soft pigment bloom', 'blurred pastel edges', 'matte luminous surface'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'anime cel shading', 'clean cel animation', 'hard manga linework', 'plastic 3D render']}, 'Watercolor / Painterly': {'anchor': 'traditional watercolor painting study on textured paper', 'lighting': ['transparent watercolor wash light', 'soft ambient paper glow', 'gentle diffused tonal wash', 'pale luminous pigment wash', 'low-contrast hand-painted light'], 'color': ['transparent layered pigments', 'soft pigment wash', 'muted watercolor palette', 'edge-bleeding color', 'diluted mineral tones', 'pooled pigment blooms'], 'composition': ['loose watercolor study composition', 'brush-led visual flow', 'unfilled paper breathing room', 'hand-painted placement', 'soft unfinished paper margins', 'reserved white paper highlights', 'painterly negative space'], 'texture': ['wet-on-wet paint bleed', 'visible watercolor brush marks', 'paper grain beneath pigment', 'pigment bloom on paper', 'feathered edge diffusion', 'granulating watercolor texture', 'watery edge blooms', 'uneven hand-painted washes'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'anime cel shading', 'clean cel animation', 'airbrushed digital finish']}, 'Graphite Pencil Sketch': {'anchor': 'rough graphite pencil study sketch on paper', 'lighting': ['soft graphite value shading', 'delicate hand-shaded transitions', 'light pencil hatching', 'loose tonal modeling', 'unfinished graphite shadow blocks'], 'color': ['graphite gray tones', 'off-white sketchbook paper', 'silver-gray pencil values', 'pale paper-and-pencil palette'], 'composition': ['preliminary study sketch layout', 'visible construction lines', 'loose exploratory contours', 'unfinished study margins', 'draft underdrawing structure', 'quiet negative paper space'], 'texture': ['fine pencil grain', 'visible hatching', 'paper tooth', 'eraser-softened shading', 'graphite dust', 'smudged graphite', 'uneven pencil pressure marks'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'ink-heavy outlines', 'fully polished finished illustration', 'airbrushed digital painting', 'clean digital cel shading']}, 'Pen and Ink Sketch': {'anchor': 'loose pen-and-ink study sketch on paper', 'lighting': ['line-based shadow', 'cross-hatched tonal contrast', 'inked shadow accents', 'graphic light separation', 'unfinished hatch shading'], 'color': ['black ink on warm paper', 'monochrome ink tones', 'sepia ink accent', 'raw black linework'], 'composition': ['exploratory study sketch layout', 'loose contour drawing', 'visible drafting marks', 'illustrative negative paper space', 'partly unfinished background lines', 'graphic silhouette rhythm'], 'texture': ['crosshatching', 'fine ink linework', 'dry pen texture', 'hand-inked strokes', 'stray pen marks', 'uneven ink pressure'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'soft photo blur', 'polished vector line art', 'clean cel linework', 'fully rendered finished illustration']}, 'Colored Pencil Illustration': {'anchor': 'colored pencil sketch study on textured paper', 'lighting': ['soft drawn shading', 'layered pencil highlight', 'gentle value modeling', 'hand-colored light', 'pencil-shaded color transitions'], 'color': ['layered colored pencil hues', 'soft saturated pencil color', 'warm sketchbook palette', 'subtle color layering', 'visible blended pencil pigment'], 'composition': ['colored-pencil sketch composition', 'visible underdrawing lines', 'gentle hand-drawn layout', 'clear drawn silhouette', 'partly unfinished sketchbook composition'], 'texture': ['colored pencil grain', 'visible pencil strokes', 'paper tooth', 'layered dry pencil pigment', 'uneven hand pressure marks'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'airbrushed plastic finish', 'smooth digital anime coloring', 'fully rendered glossy illustration']}, 'Pastel Chalk Drawing': {'anchor': 'rough pastel chalk study on textured paper', 'lighting': ['powdery soft light', 'diffused tonal glow', 'gentle chalk highlight', 'velvety shade transition', 'chalk-blocked soft shadows'], 'color': ['soft pastel pigments', 'chalky pink-blue palette', 'powdery warm tones', 'muted pastel layers', 'matte chalk colors'], 'composition': ['unfinished pastel study composition', 'smudged handmade edges', 'gentle figure-ground balance', 'unfinished sketchbook layout', 'broad chalk blocking'], 'texture': ['chalk dust texture', 'powdery pigment', 'soft smudged edges', 'toothy pastel paper', 'visible pastel strokes', 'finger-smudged transitions'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'glossy digital finish', 'clean vector edges', 'clean cel shading']}, 'Gouache Storybook Illustration': {'anchor': 'matte gouache storybook painting for a classic picture-book page', 'lighting': ['painted soft light', 'storybook page glow', 'opaque color lighting', 'gentle gouache illumination', 'flat matte painted light'], 'color': ['opaque gouache color', 'warm picture-book palette', 'matte saturated hues', 'hand-painted color blocks', 'cream paper undertones'], 'composition': ['classic picture-book composition', 'clear readable painted shapes', 'charming gouache arrangement', 'hand-painted scenic balance', 'simple storybook page staging'], 'texture': ['matte gouache texture', 'visible opaque brush marks', 'painted paper surface', 'layered gouache pigment', 'slightly uneven hand-painted edges'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'photographic depth of field', 'anime cel shading', 'clean cel animation']}, 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted storybook painting on paper', 'lighting': ['warm painted glow', 'gentle storybook light', 'soft atmospheric painted illumination', 'paper-soft sky light'], 'color': ['hand-painted natural palette', 'warm gentle greens', 'soft sky blues', 'cream highlights', 'matte storybook colors'], 'composition': ['storybook painting composition', 'clear readable silhouette', 'painted scenic staging', 'whimsical picture-book balance', 'simple hand-painted layout'], 'texture': ['hand-painted background texture', 'painted brush texture', 'storybook matte finish', 'soft paper surface', 'visible traditional brushwork'], 'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'live-action realism', 'camera lens artifacts', 'anime cel shading', 'clean cel animation', 'manga line art']}, 'Volumetric Dust Light': {'anchor': 'volumetric light scattering through dusty air', 'lighting': ['visible light beams through dusty air', 'volumetric light shafts', 'soft scattered backlight', 'hazy side light', 'dust-mote glow'], 'color': ['warm amber haze', 'muted golden air', 'pale dusty highlights', 'soft smoky neutrals'], 'composition': ['atmosphere-forward composition', 'light rays crossing the scene', 'deep hazy layers', 'subject framed by suspended dust'], 'texture': ['floating dust motes', 'fine airborne particles', 'hazy volumetric atmosphere', 'soft bloom in the air', 'subtle particulate texture'], 'avoid': ['flat clean air', 'sterile lighting', 'hard flash look', 'empty atmosphere']}, 'Long Exposure Light Trails': {'anchor': 'long-exposure night light trails', 'lighting': ['streaked moving light', 'extended luminous trails', 'flowing exposure glow', 'night light ribbons', 'motion-blurred highlights'], 'color': ['red and white light streaks', 'neon trail accents', 'deep night contrast', 'glowing saturated lines'], 'composition': ['dynamic trail-led composition', 'motion path framing', 'diagonal streak rhythm', 'long-exposure scene balance'], 'texture': ['smooth light trails', 'motion blur streaks', 'glowing line traces', 'soft exposure bloom'], 'avoid': ['frozen static lighting', 'flat daylight', 'no motion trails']}, 'Miniature Diorama': {'anchor': 'miniature diorama model scene', 'lighting': ['tiny model lighting', 'soft tabletop illumination', 'small-scale scene glow', 'gentle display-case light'], 'color': ['toy-like muted colors', 'painted miniature palette', 'small-scale material colors', 'soft diorama tones'], 'composition': ['miniature scale composition', 'diorama staging', 'tiny set arrangement', 'compressed small-world layout'], 'texture': ['miniature model texture', 'painted tiny surfaces', 'crafted material detail', 'small-scale set pieces'], 'avoid': ['life-size realism', 'ordinary full-scale scene', 'flat photograph look']}, '3D Collectible Figure': {'anchor': 'stylized 3D collectible figure render', 'lighting': ['soft product-display lighting', 'gentle plastic highlight', 'toy showcase glow', 'clean studio display light'], 'color': ['painted figure colors', 'smooth material colors', 'collectible toy palette', 'clean resin tones'], 'composition': ['collectible figure presentation', 'toy-like character staging', 'display-stand composition', 'small figure centered layout'], 'texture': ['smooth resin surface', 'painted plastic material', 'subtle toy seams', 'matte vinyl finish', 'miniature sculpt detail'], 'avoid': ['real human skin texture', 'photorealistic live-action person', 'ordinary portrait realism']}}
STYLE_DNA.update(STYLE_REFINEMENT_PATCH_2026_05_31_B)
NONPHYSICAL_STYLE_REFINEMENT_2026_05_31_B = {'Dream Pastel Diffusion': {'anchor': 'dreamlike pastel haze and diffused luminous atmosphere', 'lighting': ['milky diffused glow', 'soft ambient mist light', 'low-contrast scattered light', 'pearlescent ambient haze'], 'color': ['powder pastel palette', 'pink lavender mist', 'soft cyan veil', 'pale cream undertones'], 'texture': ['powdery pastel diffusion', 'silky haze texture', 'soft pigment bloom', 'blurred pastel edges']}, 'Watercolor / Painterly': {'anchor': 'transparent watercolor wash and textured paper feel', 'lighting': ['transparent watercolor wash light', 'soft ambient paper glow', 'gentle diffused tonal wash'], 'color': ['transparent layered pigments', 'soft pigment wash', 'muted watercolor palette', 'edge-bleeding color'], 'texture': ['wet-on-wet paint bleed', 'paper grain beneath pigment', 'pigment bloom on paper', 'granulating watercolor texture']}, 'Graphite Pencil Sketch': {'anchor': 'graphite pencil sketch texture and hand-shaded tonal study', 'lighting': ['soft graphite value shading', 'light pencil hatching', 'unfinished graphite shadow blocks'], 'color': ['graphite gray tones', 'off-white sketchbook paper', 'silver-gray pencil values'], 'texture': ['fine pencil grain', 'visible hatching', 'paper tooth', 'smudged graphite']}, 'Pen and Ink Sketch': {'anchor': 'pen-and-ink linework and hand-drawn hatch shading', 'lighting': ['line-based shadow', 'cross-hatched tonal contrast', 'unfinished hatch shading'], 'color': ['black ink on warm paper', 'monochrome ink tones', 'raw black linework'], 'texture': ['crosshatching', 'fine ink linework', 'dry pen texture', 'stray pen marks']}, 'Colored Pencil Illustration': {'anchor': 'colored pencil texture and visible hand-drawn pigment', 'lighting': ['soft drawn shading', 'layered pencil highlight', 'pencil-shaded color transitions'], 'color': ['layered colored pencil hues', 'soft saturated pencil color', 'warm sketchbook palette'], 'texture': ['colored pencil grain', 'visible pencil strokes', 'paper tooth', 'layered dry pencil pigment']}, 'Pastel Chalk Drawing': {'anchor': 'powdery pastel chalk texture and smudged handmade softness', 'lighting': ['powdery soft light', 'diffused tonal glow', 'chalk-blocked soft shadows'], 'color': ['soft pastel pigments', 'chalky pink-blue palette', 'muted pastel layers'], 'texture': ['chalk dust texture', 'powdery pigment', 'soft smudged edges', 'toothy pastel paper']}, 'Gouache Storybook Illustration': {'anchor': 'matte gouache paint and classic picture-book surface', 'lighting': ['painted soft light', 'storybook page glow', 'flat matte painted light'], 'color': ['opaque gouache color', 'warm picture-book palette', 'matte saturated hues'], 'texture': ['matte gouache texture', 'visible opaque brush marks', 'painted paper surface']}, 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted storybook surface and traditional brushwork', 'lighting': ['warm painted glow', 'gentle storybook light', 'paper-soft sky light'], 'color': ['hand-painted natural palette', 'matte storybook colors', 'cream highlights'], 'texture': ['hand-painted background texture', 'painted brush texture', 'soft paper surface']}, 'Volumetric Dust Light': {'anchor': 'volumetric dust light scattering atmosphere', 'lighting': ['visible light beams through dusty air', 'volumetric light shafts', 'soft scattered backlight', 'dust-mote glow'], 'color': ['warm amber haze', 'muted golden air', 'soft smoky neutrals'], 'texture': ['floating dust motes', 'fine airborne particles', 'hazy volumetric atmosphere']}, 'Long Exposure Light Trails': {'anchor': 'long-exposure glowing motion trails', 'lighting': ['streaked moving light', 'extended luminous trails', 'flowing exposure glow'], 'color': ['red and white light streaks', 'neon trail accents', 'deep night contrast'], 'texture': ['smooth light trails', 'motion blur streaks', 'glowing line traces']}, 'Oil Painting': {'anchor': 'oil paint surface and canvas brushwork', 'lighting': ['painted chiaroscuro light', 'warm impasto highlights', 'layered oil-paint shadow'], 'color': ['rich oil-paint colors', 'layered earth tones', 'deep blended pigments'], 'texture': ['visible oil brushstrokes', 'canvas weave texture', 'impasto paint ridges', 'thick pigment texture']}, 'Miniature Diorama': {'anchor': 'small-scale crafted model atmosphere', 'lighting': ['soft tabletop illumination', 'small-scale scene glow', 'gentle display-case light'], 'color': ['painted miniature palette', 'small-scale material colors', 'soft diorama tones'], 'texture': ['miniature model texture', 'painted tiny surfaces', 'crafted material detail']}, 'Pixel Art': {'anchor': 'crisp pixel-art rendering language', 'lighting': ['blocky pixel lighting', 'dithered shadow shapes', 'sprite-like light blocks'], 'color': ['limited pixel palette', 'indexed color look', 'retro game colors'], 'texture': ['visible square pixels', 'hard pixel edges', 'dithered texture', 'low-resolution pixel grid']}, '3D Collectible Figure': {'anchor': 'stylized collectible figure material and display finish', 'lighting': ['soft product-display lighting', 'gentle plastic highlight', 'toy showcase glow'], 'color': ['painted figure colors', 'collectible toy palette', 'clean resin tones'], 'texture': ['smooth resin surface', 'painted plastic material', 'matte vinyl finish', 'miniature sculpt detail']}, 'Apocalyptic Wasteland': {'anchor': 'post-apocalyptic wasteland atmosphere', 'lighting': ['ashen overcast light', 'smoky backlight', 'dim dust-filtered glow'], 'color': ['desaturated rust tones', 'ash gray palette', 'dusty earth colors'], 'texture': ['ash in the air', 'dusty debris', 'weathered surfaces']}, 'Chibi Style': {'anchor': 'cute simplified chibi visual language', 'lighting': ['cute simplified lighting', 'soft rounded highlights', 'bright playful light'], 'color': ['bright cute colors', 'simple saturated palette', 'soft candy tones'], 'texture': ['clean simplified shapes', 'rounded stylized edges', 'smooth cute finish']}}
NONPHYSICAL_STYLE_CUES.update(NONPHYSICAL_STYLE_REFINEMENT_2026_05_31_B)


STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24 = {
    'Vintage Film Look': {
        'anchor': 'vintage analog film photograph aesthetic',
        'lighting': ['soft analog highlight roll-off', 'warm shadow lift', 'gentle halation around highlights', 'nostalgic low-contrast illumination'],
        'color': ['faded warm film tones', 'subtle amber-green vintage shift', 'muted nostalgic palette', 'aged print color response'],
        'composition': ['casual analog snapshot framing', 'relaxed vintage composition', 'timeless film-photo balance', 'nostalgic candid framing'],
        'texture': ['visible fine film grain', 'soft vignette', 'aged print texture', 'slight emulsion softness', 'subtle scan-like texture'],
        'avoid': ['clean modern digital color grade', 'sterile ultra-sharp digital look', 'plastic HDR crispness', 'flat contemporary smartphone look']
    },
    'Chibi Style': {
        'anchor': 'in-place chibi restyling of existing visible main subject(s)',
        'lighting': ['bright playful lighting', 'soft rounded highlights', 'cute simplified light', 'gentle soft glow'],
        'color': ['bright cute colors', 'soft candy palette', 'simple cheerful color blocks', 'clean saturated anime colors'],
        'composition': ['oversized head with compact body', 'super-deformed SD proportions', 'short limbs and rounded cute face', 'existing visible main subject(s) restyled into chibi SD proportions'],
        'texture': ['clean simplified anime shapes', 'rounded stylized edges', 'smooth cute finish', 'minimal detail linework'],
        'avoid': []
    }
}
STYLE_DNA.update(STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24)
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'clear chibi super-deformed SD character rendering', 'lighting': ['bright playful lighting', 'soft rounded highlights', 'gentle toy-like glow'], 'color': ['bright cute colors', 'soft candy palette', 'simple cheerful color blocks'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges', 'minimal cute linework']}})
STYLE_DNA.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'composition': ['larger head and compact body proportions', 'rounded simplified anime features', 'existing visible subject(s) restyled in place'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges'], 'avoid': []}})
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting'], 'color': ['bright cute colors'], 'texture': ['clean simplified anime shapes']}})

STYLE_DNA_COMPACT_STRENGTH_PATCH_2026_06_24 = {
    'Pastel Chalk Drawing': {'anchor': 'rough pastel-chalk artwork', 'lighting': ['chalky light'], 'color': ['powdery pigment'], 'composition': ['handmade paper study'], 'texture': ['broken chalk strokes and paper tooth'], 'avoid': []},
    'Graphite Pencil Sketch': {'anchor': 'rough graphite sketch', 'lighting': ['smudged graphite shading'], 'color': ['monochrome graphite tones'], 'composition': ['construction-line sketch layout'], 'texture': ['rough hatching and paper tooth'], 'avoid': []},
    'Charcoal Drawing': {'anchor': 'raw charcoal drawing', 'lighting': ['dark smudged shadow'], 'color': ['black charcoal tones'], 'composition': ['gestural drawing layout'], 'texture': ['broken charcoal strokes and dusty paper'], 'avoid': []},
    'Oil Painting': {'anchor': 'thick oil painting', 'lighting': ['painted highlights'], 'color': ['layered pigment'], 'composition': ['painterly composition'], 'texture': ['impasto brushstrokes and canvas texture'], 'avoid': []},
    'Watercolor / Painterly': {'anchor': 'watercolor painting on paper', 'lighting': ['transparent wash light'], 'color': ['diluted pigment'], 'composition': ['loose painted composition'], 'texture': ['bleeding edges and paper grain'], 'avoid': []},
}
STYLE_DNA.update(STYLE_DNA_COMPACT_STRENGTH_PATCH_2026_06_24)
NONPHYSICAL_STYLE_CUES.update({
    'Pastel Chalk Drawing': {'anchor': 'rough pastel-chalk artwork', 'lighting': ['chalky light'], 'color': ['powdery pigment'], 'texture': ['broken chalk strokes and paper tooth']},
    'Graphite Pencil Sketch': {'anchor': 'rough graphite sketch', 'lighting': ['smudged graphite shading'], 'color': ['monochrome graphite tones'], 'texture': ['rough hatching and paper tooth']},
    'Charcoal Drawing': {'anchor': 'raw charcoal drawing', 'lighting': ['dark smudged shadow'], 'color': ['black charcoal tones'], 'texture': ['broken charcoal strokes and dusty paper']},
    'Oil Painting': {'anchor': 'thick oil painting', 'lighting': ['painted highlights'], 'color': ['layered pigment'], 'texture': ['impasto brushstrokes and canvas texture']},
    'Watercolor / Painterly': {'anchor': 'watercolor painting on paper', 'lighting': ['transparent wash light'], 'color': ['diluted pigment'], 'texture': ['bleeding edges and paper grain']},
})
STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_B = {
    'Miniature Diorama': {
        'anchor': 'tabletop miniature diorama scale-model scene',
        'lighting': ['display-case illumination over a tiny model world', 'macro-view miniature lighting', 'small-scale handcrafted scene glow', 'gentle showcase lighting for a tabletop set'],
        'color': ['painted miniature palette', 'toy-like material colors', 'handcrafted scale-model tones', 'soft model-set color harmony'],
        'composition': ['the entire scene transformed into a tabletop miniature diorama', 'small-scale room model composition', 'tiny handcrafted environment staging', 'compressed model-world layout with miniature proportions'],
        'texture': ['handcrafted model texture', 'painted tiny surfaces', 'miniature set-piece detail', 'scale-model material finish', 'tiny props and furniture detail'],
        'avoid': ['life-size realism', 'ordinary full-scale room', 'normal real-size furniture', 'full-scale human proportions', 'flat full-size interior photograph']
    },
    'Gouache Storybook Illustration': {
        'anchor': 'opaque gouache picture-book illustration with a matte storybook page feel',
        'lighting': ['flat matte painted light', 'soft painted storybook glow', 'opaque color lighting', 'gentle gouache illumination', 'calm page-like painted light'],
        'color': ['opaque gouache color blocks', 'warm picture-book palette', 'matte saturated hues', 'layered painted color shapes', 'cream paper undertones'],
        'composition': ['static picture-book illustration composition', 'clear readable painted shapes', 'storybook page staging', 'charming gouache illustration balance', 'single-page illustrated scene design'],
        'texture': ['matte gouache texture', 'visible opaque brush marks', 'painted paper surface', 'layered gouache pigment', 'slightly uneven hand-painted edges'],
        'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'photographic depth of field', 'anime cel shading', 'clean cel animation', 'animation-frame look']
    },
    'Hand-Painted Storybook Animation': {
        'anchor': 'hand-painted 2D storybook animation frame',
        'lighting': ['warm painted animation glow', 'gentle storybook animation light', 'soft atmospheric painted illumination', 'paper-soft scene lighting for a hand-painted animation frame'],
        'color': ['hand-painted animation palette', 'warm gentle greens', 'soft sky blues', 'cream highlights', 'matte painted animation colors'],
        'composition': ['hand-painted animation keyframe composition', 'clear readable animated silhouette', 'storybook animation staging', 'frame-from-a-painted-animation balance', 'scene layout with animated storytelling energy'],
        'texture': ['hand-painted animation background texture', 'painted brush texture', 'storybook matte finish', 'soft paper-and-paint surface', 'visible traditional brushwork'],
        'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'live-action realism', 'camera lens artifacts', 'static gouache picture-book page', 'manga line art']
    },
    'Graphite Pencil Sketch': {
        'anchor': 'monochrome graphite pencil sketch on sketchbook paper',
        'lighting': ['monochrome graphite value shading', 'delicate hand-drawn tonal transitions', 'pencil-built light and shadow', 'cross-hatched tonal modeling', 'soft smudged graphite shading'],
        'color': ['graphite gray tones', 'off-white sketchbook paper', 'silver-gray pencil values', 'monochrome paper-and-pencil palette'],
        'composition': ['preliminary study sketch layout', 'visible construction lines', 'loose exploratory contours', 'unfinished study margins', 'draft underdrawing structure', 'quiet negative paper space'],
        'texture': ['visible graphite strokes', 'cross-hatching', 'paper tooth', 'eraser-softened shading', 'graphite dust', 'smudged graphite', 'uneven pencil pressure marks'],
        'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'ink-heavy outlines', 'fully polished finished illustration', 'airbrushed digital painting', 'clean digital cel shading', 'full-color painting']
    },
    'Volumetric Dust Light': {
        'anchor': 'strong volumetric light rays scattering through dusty air',
        'lighting': ['visible volumetric light shafts', 'floating dust motes dancing in the light rays', 'sunbeams cutting through dusty air', 'soft scattered backlight through haze', 'cinematic shafts of light'],
        'color': ['warm amber haze', 'muted golden air', 'pale dusty highlights', 'soft smoky neutrals'],
        'composition': ['atmosphere-forward cinematic composition', 'light rays crossing the scene', 'deep hazy layers', 'subject framed by illuminated dust-filled air'],
        'texture': ['floating dust motes', 'fine airborne particles', 'hazy volumetric atmosphere', 'soft bloom in the air', 'particulate glow in the beams'],
        'avoid': ['flat clean air', 'sterile lighting', 'hard flash look', 'empty atmosphere', 'crisp air with no haze']
    },
    'Classical Studio Glamour': {
        'anchor': 'classic old-Hollywood studio glamour portrait',
        'lighting': ['controlled studio beauty lighting', 'butterfly lighting', 'broad soft key illumination', 'soft shadow lift', 'subtle edge highlight', 'velvety shadow falloff'],
        'color': ['ivory', 'warm gold', 'deep brown', 'soft champagne'],
        'composition': ['timeless glamour portrait composition', 'elegant beauty-editorial posture', 'balanced portrait composition', 'graceful negative space'],
        'texture': ['satin fabric', 'polished wood', 'soft tonal grain', 'polished studio finish'],
        'avoid': ['casual snapshot feel', 'ordinary ambient room lighting', 'messy amateur lighting', 'everyday documentary look']
    },
    'Neon Melancholy / Rain Glass': {
        'anchor': 'melancholic rainy-night neon city mood through wet glass',
        'lighting': ['neon spill through rain-soaked glass', 'magenta and cyan neon glow', 'blurred urban lights behind raindrops', 'moody wet-night reflections', 'dim ambient shadows with colored neon bloom'],
        'color': ['amber', 'deep red', 'muted cyan', 'green neon trace', 'magenta-violet night accents'],
        'composition': ['framing through wet glass', 'urban intimacy', 'isolated close framing', 'rainy-night city reflection layering', 'emotionally moody window-side composition'],
        'texture': ['rain-soaked neon reflections', 'humid haze', 'wet-window bokeh', 'soft motion blur', 'diffused signage reflections through droplets'],
        'avoid': ['plain raindrops with no neon mood', 'dry clean glass', 'daylight clarity', 'flat neutral lighting']
    }
}
STYLE_DNA.update(STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_B)
NONPHYSICAL_STYLE_CUES.update({
    'Miniature Diorama': {'anchor': 'tabletop miniature diorama small-scale model atmosphere', 'lighting': ['macro-view miniature lighting', 'small-scale handcrafted scene glow'], 'color': ['painted miniature palette', 'toy-like material colors'], 'texture': ['handcrafted model texture', 'scale-model material finish']},
    'Gouache Storybook Illustration': {'anchor': 'opaque gouache picture-book surface and matte painted storybook page feel', 'lighting': ['flat matte painted light', 'soft painted storybook glow'], 'color': ['opaque gouache color blocks', 'warm picture-book palette'], 'texture': ['matte gouache texture', 'visible opaque brush marks']},
    'Hand-Painted Storybook Animation': {'anchor': 'hand-painted 2D storybook animation frame atmosphere', 'lighting': ['warm painted animation glow', 'gentle storybook animation light'], 'color': ['hand-painted animation palette', 'matte painted animation colors'], 'texture': ['painted animation background texture', 'visible traditional brushwork']},
    'Graphite Pencil Sketch': {'anchor': 'monochrome graphite pencil sketch texture and hand-drawn tonal study', 'lighting': ['monochrome graphite value shading', 'cross-hatched tonal modeling'], 'color': ['graphite gray tones', 'monochrome paper-and-pencil palette'], 'texture': ['visible graphite strokes', 'cross-hatching', 'paper tooth', 'smudged graphite']},
    'Volumetric Dust Light': {'anchor': 'strong volumetric dust-lit atmosphere', 'lighting': ['visible volumetric light shafts', 'floating dust motes dancing in the light rays'], 'color': ['warm amber haze', 'muted golden air'], 'texture': ['hazy volumetric atmosphere', 'particulate glow in the beams']},
    'Classical Studio Glamour': {'anchor': 'classic old-Hollywood studio glamour mood', 'lighting': ['controlled studio beauty lighting', 'butterfly lighting'], 'color': ['ivory', 'warm gold', 'soft champagne'], 'texture': ['soft tonal grain', 'polished studio finish']},
    'Neon Melancholy / Rain Glass': {'anchor': 'rainy-night neon melancholy through wet glass', 'lighting': ['magenta and cyan neon glow', 'blurred urban lights behind raindrops'], 'color': ['muted cyan', 'deep red', 'magenta-violet night accents'], 'texture': ['wet-window bokeh', 'diffused signage reflections through droplets']}
})
STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_C = {
    'Chibi Style': {
        'composition': ['oversized head with compact body', 'super-deformed SD proportions', 'short limbs and rounded cute face', 'in-place chibi restyling of the existing visible main subject(s)', 'existing scene population and spatial arrangement kept unchanged', 'external prompt used only as identity, outfit, pose, and scene reference'],
        'avoid': []
    },
    'Pastel Chalk Drawing': {
        'anchor': 'beautifully detailed pastel illustration',
        'lighting': ['gentle daylight softness', 'soft window light', 'warm cozy atmosphere', 'soft pastel glow'],
        'color': ['soft pastel palette', 'delicate pastel-crayon color', 'gentle warm pastel tones', 'clean airy color harmony'],
        'composition': ['coherent illustrated room scene', 'clear indoor-and-window storytelling', 'balanced illustrated composition', 'readable background detail'],
        'texture': ['delicate pastel texture', 'soft hand-drawn surface', 'clean lineart', 'subtle paper texture', 'whimsical illustrative finish'],
        'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'glossy digital finish', 'clean vector edges', 'harsh chalk dust overload', 'mere frame-like soft filter', 'subtle vignette-only effect', 'watercolor-like transparent wash', 'thin transparent paint look']
    },
    'Graphite Pencil Sketch': {
        'anchor': 'detailed pencil illustration with fine line art and soft graphite shading',
        'lighting': ['soft graphite shading', 'hand-drawn tonal depth', 'gentle pencil-modeled light', 'careful value transitions'],
        'color': ['monochrome graphite tones', 'subtle gray pencil palette', 'paper-and-graphite harmony', 'classic sketchbook neutrals'],
        'composition': ['coherent pencil illustration composition', 'clear room-and-window scene structure', 'readable background perspective', 'balanced hand-drawn layout'],
        'texture': ['fine line art', 'delicate pencil strokes', 'precise cross-hatching', 'subtle paper texture', 'rich graphite texture'],
        'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'heavy charcoal smudging', 'ink-heavy outlines', 'fully polished digital painting', 'clean cel shading']
    },
    'Colored Pencil Illustration': {
        'anchor': 'colored-pencil illustration with visible layered pencil work on paper',
        'lighting': ['drawn colored-pencil shading', 'layered pencil highlight', 'dry hand-rendered light', 'pencil-built tonal modeling'],
        'color': ['layered colored-pencil hues', 'visible dry pigment layering', 'warm hand-colored palette', 'cross-layered pencil color'],
        'composition': ['colored-pencil illustration composition', 'visible hand-drawn outlines', 'clear sketched silhouette', 'paper-based illustration layout'],
        'texture': ['obvious colored-pencil strokes', 'paper tooth', 'dry pigment buildup', 'layered pencil grain', 'visible hand-pressure marks'],
        'avoid': ['photorealistic rendering', 'realistic camera lens look', 'hard photographic sharpness', 'glossy photo skin', 'cinematic lens realism', 'airbrushed plastic finish', 'smooth digital anime coloring', 'fully rendered glossy illustration', 'mere border-like effect', 'subtle frame-only treatment']
    },
    'Apocalyptic Wasteland': {
        'anchor': 'bleak devastated post-apocalyptic wasteland',
        'lighting': ['ashen overcast light', 'harsh survival sunlight', 'smoky backlight', 'dim dust-filtered glow', 'soot-choked daylight'],
        'color': ['desaturated rust tones', 'ash gray palette', 'burnt orange accents', 'dusty earth colors', 'charred brown ruin tones'],
        'composition': ['desolate survival composition', 'collapsed-ruin staging', 'ruined-world storytelling', 'abandoned end-of-civilization framing', 'widespread devastation'],
        'texture': ['ash in the air', 'worn metal texture', 'cracked concrete', 'dusty debris', 'weathered surfaces', 'rubble piles', 'scorched ruin detail'],
        'avoid': ['clean luxury mood', 'cheerful pristine setting', 'polished fashion editorial atmosphere', 'lightly weathered but intact environment', 'minor wear only']
    }
}
STYLE_DNA.update(STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_C)
NONPHYSICAL_STYLE_CUES.update({
    'Pastel Chalk Drawing': {'anchor': 'beautifully detailed pastel illustration with a soft whimsical feel', 'lighting': ['soft window light', 'warm cozy pastel glow'], 'color': ['soft pastel palette', 'delicate pastel-crayon color'], 'texture': ['delicate pastel texture', 'clean lineart', 'subtle paper texture', 'whimsical illustrative finish']},
    'Graphite Pencil Sketch': {'anchor': 'detailed pencil illustration with fine line art and soft graphite shading', 'lighting': ['soft graphite shading', 'hand-drawn tonal depth'], 'color': ['monochrome graphite tones', 'subtle gray pencil palette'], 'texture': ['fine line art', 'delicate pencil strokes', 'precise cross-hatching', 'subtle paper texture']},
    'Colored Pencil Illustration': {'anchor': 'colored-pencil illustration texture with visible layered pencil work', 'lighting': ['drawn colored-pencil shading', 'dry hand-rendered light'], 'color': ['layered colored-pencil hues', 'visible dry pigment layering'], 'texture': ['obvious colored-pencil strokes', 'paper tooth', 'dry pigment buildup']},
    'Apocalyptic Wasteland': {'anchor': 'devastated post-apocalyptic wasteland mood', 'lighting': ['ashen overcast light', 'smoky backlight'], 'color': ['desaturated rust tones', 'ash gray palette', 'charred brown ruin tones'], 'texture': ['ash in the air', 'rubble piles', 'scorched ruin detail']},
    'Chibi Style': {'anchor': 'in-place chibi restyling of existing visible main subject(s)', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges']}
})
STYLE_DNA.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'composition': ['larger head and compact body proportions', 'rounded simplified anime features', 'existing visible subject(s) restyled in place'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges'], 'avoid': []}})
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting'], 'color': ['bright cute colors'], 'texture': ['clean simplified anime shapes']}})
# Chibi DNA ratio reinforcement requested in follow-up: keep the prompt simple, but make the DNA itself explicit.
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'delightful adorable chibi style illustration', 'lighting': ['bright playful lighting', 'soft rounded highlights', 'gentle cozy glow'], 'color': ['bright cute colors', 'soft candy palette', 'vibrant cheerful tones'], 'texture': ['clean lineart', 'rounded stylized edges', 'whimsical illustration feel']}})
STYLE_DNA.update({'Chibi Style': {'anchor': 'cute chibi character illustration', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'composition': ['oversized head', 'tiny compact body', 'short simplified limbs when visible', 'super-deformed chibi proportions'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges', 'big expressive eyes', 'soft rosy cheeks'], 'avoid': []}})
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'cute chibi character illustration', 'lighting': ['bright playful lighting'], 'color': ['bright cute colors'], 'texture': ['clean simplified anime shapes', 'clean lineart', 'whimsical illustration feel']}})

AUTO_STYLE_BY_MOOD.update({'Lyrical / Poetic': 'Soft Romantic Glow',
 'Arthouse Realism': 'Neutral / Minimal Carryover',
 'Watercolor / Painterly': 'Watercolor / Painterly',
 'Cinematic Widescreen': 'Cinematic Widescreen Scope',
 'Melodrama': 'Baroque Operatic Atmosphere',
 'Horror / Unsettling': 'Dark Fantasy Shadow Mass'})
UI_LABELS_KO.setdefault('style_dna', {}).update({'Dream Pastel Diffusion': '몽환적인 파스텔 빛',
 'Watercolor / Painterly': '수채화 회화 느낌',
 'Gouache Storybook Illustration': '불투명 물감 동화풍',
 'Hand-Painted Storybook Animation': '손그림 동화 애니풍',
 'Graphite Pencil Sketch': '연필 스케치',
 'Pen and Ink Sketch': '펜화 스케치',
 'Colored Pencil Illustration': '색연필 일러스트',
 'Pastel Chalk Drawing': '파스텔 드로잉',
 'Volumetric Dust Light': '공기 중 먼지 빛',
 'Long Exposure Light Trails': '긴 노출 빛 궤적',
 'Oil Painting': '유화 느낌',
 'Miniature Diorama': '미니어처 디오라마',
 'Pixel Art': '픽셀 아트',
 '3D Collectible Figure': '3D 피규어 느낌',
 'Apocalyptic Wasteland': '폐허 세계 분위기',
 'Chibi Style': '치비 스타일'})

UI_STYLE_LABEL_REFINEMENT_2026_05_31_B = {'Dream Pastel Diffusion': '몽환적인 파스텔 빛', 'Watercolor / Painterly': '수채화 회화 느낌', 'Graphite Pencil Sketch': '연필 스케치', 'Pen and Ink Sketch': '펜화 스케치', 'Colored Pencil Illustration': '색연필 일러스트', 'Pastel Chalk Drawing': '파스텔 드로잉', 'Gouache Storybook Illustration': '불투명 물감 동화풍', 'Hand-Painted Storybook Animation': '손그림 동화 애니풍', 'Volumetric Dust Light': '공기 중 먼지 빛', 'Long Exposure Light Trails': '긴 노출 빛 궤적', 'Oil Painting': '유화 느낌', 'Miniature Diorama': '미니어처 디오라마', 'Pixel Art': '픽셀 아트', '3D Collectible Figure': '3D 피규어 느낌', 'Apocalyptic Wasteland': '폐허 세계 분위기', 'Chibi Style': '치비 스타일'}
UI_LABELS_KO.setdefault('style_dna', {}).update(UI_STYLE_LABEL_REFINEMENT_2026_05_31_B)

STYLE_LABEL_LEGACY_ALIASES_2026_05_31_D = {'먼지 / 볼류메트릭 빛 산란': 'Volumetric Dust Light', '먼지 / 빛 산란(볼류메트릭)': 'Volumetric Dust Light', '아포칼립스': 'Apocalyptic Wasteland', '아포칼립스 / 폐허 세계': 'Apocalyptic Wasteland', '색연필 일러스트': 'Colored Pencil Illustration', '색연필 스케치': 'Colored Pencil Illustration', '손그림 동화풍 애니메이션': 'Hand-Painted Storybook Animation', '손그림 동화풍': 'Hand-Painted Storybook Animation', '작고 귀여운 캐릭터풍': 'Chibi Style'}
UI_VALUE_ALIASES.setdefault('style_dna', {}).update(STYLE_LABEL_LEGACY_ALIASES_2026_05_31_D)
UI_LABELS_KO_REVERSE_BY_WIDGET = {
    widget_name: {ko: canonical for canonical, ko in mapping.items()}
    for widget_name, mapping in UI_LABELS_KO.items()
}
for _widget_name, _alias_map in UI_VALUE_ALIASES.items():
    UI_LABELS_KO_REVERSE_BY_WIDGET.setdefault(_widget_name, {}).update(_alias_map)
_UI_LABELS_KO_REVERSE_COUNTS = {}
for _mapping in UI_LABELS_KO.values():
    for _ko in _mapping.values():
        _UI_LABELS_KO_REVERSE_COUNTS[_ko] = _UI_LABELS_KO_REVERSE_COUNTS.get(_ko, 0) + 1
UI_LABELS_KO_REVERSE_UNAMBIGUOUS = {
    ko: canonical
    for mapping in UI_LABELS_KO.values()
    for canonical, ko in mapping.items()
    if _UI_LABELS_KO_REVERSE_COUNTS.get(ko, 0) == 1
}
for _alias_map in UI_VALUE_ALIASES.values():
    for _alias, _canonical in _alias_map.items():
        UI_LABELS_KO_REVERSE_UNAMBIGUOUS.setdefault(_alias, _canonical)
REMOVED_STYLE_DNA_FROM_UI = frozenset(['Swedish Face Silence', 'French Natural Light New Wave', 'Clean Cel Animation', 'Cinematic Widescreen Scope'])
VISIBLE_STYLE_DNA = ['Auto by Mood',
 'Neutral / Minimal Carryover',
 'Neon Melancholy / Rain Glass',
 'Classical Studio Glamour',
 'Baroque Operatic Atmosphere',
 'Noir Chiaroscuro',
 'Symmetric Psychological Coldness',
 'Mediterranean Sunlight',
 'Gothic Candle Velvet',
 'Dream Pastel Diffusion',
 'Volumetric Dust Light',
 'Long Exposure Light Trails',
 'Fashion Editorial Studio Cinema',
 'Dark Fantasy Shadow Mass',
 'Apocalyptic Wasteland',
 'Black & White Classic',
 'Golden Hour Glow',
 'Vintage Film Look',
 'Cyberpunk Neon',
 'Soft Romantic Glow',
 'High-key Clean Light',
 'Watercolor / Painterly',
 'Oil Painting',
 'Charcoal Drawing',
 'Graphite Pencil Sketch',
 'Pen and Ink Sketch',
 'Ink Wash / Sumi-e',
 'Colored Pencil Illustration',
 'Pastel Chalk Drawing',
 'Gouache Storybook Illustration',
 'Hand-Painted Storybook Animation',
 'Miniature Diorama',
 'Pixel Art',
 '3D Collectible Figure',
 'Chibi Style']
ADDED_NONPHOTOGRAPHIC_STYLE_NAMES = frozenset({'Oil Painting', 'Miniature Diorama', 'Pixel Art', '3D Collectible Figure', 'Chibi Style'})
CAMERA_SUPPRESS_STYLE_NAMES = CAMERA_SUPPRESS_STYLE_NAMES | ADDED_NONPHOTOGRAPHIC_STYLE_NAMES
NONPHOTOGRAPHIC_STYLE_NAMES = NONPHOTOGRAPHIC_STYLE_NAMES | ADDED_NONPHOTOGRAPHIC_STYLE_NAMES

def _visible_style_dna() -> List[str]:
    out: List[str] = []
    seen = set()
    for name in VISIBLE_STYLE_DNA:
        if name in STYLE_DNA and name not in seen:
            out.append(name)
            seen.add(name)
    for name in STYLE_DNA.keys():
        if name not in seen and name not in REMOVED_STYLE_DNA_FROM_UI:
            out.append(name)
            seen.add(name)
    return out or ['Auto by Mood']


def _visible_model_profiles() -> List[str]:
    """Stable UI order, while keeping hidden aliases loadable for old workflows."""
    out = [name for name in VISIBLE_MODEL_PROFILES if name in MODEL_PROFILES]
    for name in MODEL_PROFILES.keys():
        if name not in out and name not in (
            "SDXL / Anima Natural",
            "Pony / Illustrious Tag",
            "Anime Tag General",
            "Flux / Qwen Instruction",
        ):
            out.append(name)
    return out or ["Z-Image Natural"]


def _get_model_profile(model_profile: str) -> Dict[str, Any]:
    if model_profile in MODEL_PROFILES:
        return MODEL_PROFILES[model_profile]
    return MODEL_PROFILES.get("Z-Image Natural") or next(iter(MODEL_PROFILES.values()))


def _model_family(model_profile: str) -> str:
    return str(_get_model_profile(model_profile).get("family", "natural")).lower()


COMPACT_GENERIC_NEGATIVE = "bad anatomy, underage appearance"
MIXED_STYLE_BLOCKING_NEGATIVE_RE = re.compile(
    r"\b(?:photorealistic\s+skin\s+texture|realistic\s+pores|style\s+overpowering\s+the\s+subject)\b",
    re.IGNORECASE,
)

for _profile in MODEL_PROFILES.values():
    if not isinstance(_profile, dict):
        continue
    _family = str(_profile.get("family", "natural")).lower()
    if _family == "natural":
        _profile["negative"] = COMPACT_GENERIC_NEGATIVE
    elif _family == "mixed":
        _chunks = [c.strip() for c in str(_profile.get("negative", "")).split(",") if c.strip()]
        _profile["negative"] = ", ".join(c for c in _chunks if not MIXED_STYLE_BLOCKING_NEGATIVE_RE.search(c))

MODEL_KEY_ALIASES: Dict[str, str] = {
    "z": "zimage",
    "z-image": "zimage",
    "z_image": "zimage",
    "z image": "zimage",
}
MODEL_KEY_KNOWN = {"pony", "ilxl", "sdxl", "sd", "anima", "flux", "qwen", "zimage", "universal"}


def _canonical_model_key(value: Any) -> str:
    key = str(value or "").lower().strip()
    key = MODEL_KEY_ALIASES.get(key, key)
    return key if key in MODEL_KEY_KNOWN else ""


def _model_key(model_profile: str) -> str:
    profile_name = str(model_profile or "").lower().strip()
    if model_profile in MODEL_PROFILES:
        key = _canonical_model_key(MODEL_PROFILES[model_profile].get("model_key"))
        if key:
            return key
    if "pony" in profile_name:
        return "pony"
    if "illustrious" in profile_name or "ilxl" in profile_name:
        return "ilxl"
    if "sdxl" in profile_name:
        return "sdxl"
    if profile_name == "sd" or "sd 1.5" in profile_name:
        return "sd"
    if "anima" in profile_name:
        return "anima"
    if "flux" in profile_name:
        return "flux"
    if "qwen" in profile_name:
        return "qwen"
    if re.search(r"\bz[-_ ]?image\b", profile_name):
        return "zimage"
    fallback = _canonical_model_key(_get_model_profile(model_profile).get("model_key"))
    return fallback or "universal"


UI_WIDGET_DEFAULTS: Dict[str, Any] = {
    "model_profile": "Z-Image Natural",
    "mood_family": "Default / None",
    "style_dna": "Auto by Mood",
    "style_strength": "strong",
    "style_conflict_cleanup": "off",
    "scene_framing": "auto",
    "lens_preset": "auto",
    "adult_tone": "default",
    "adult_wardrobe": "auto",
    "external_prompt_mode": "Prepend style before external prompt",
    "seed": 0,
    "custom_text": "",
}

RANDOM_MOOD_FAMILY_LABEL = "🎲 Random All"
RANDOM_TRANSFORMATIVE_STYLE_LABEL = "🎲 Random Transformative Style"
RANDOM_TRADITIONAL_MEDIA_STYLE_LABEL = "🎲 Random Traditional Media Style"
RANDOM_ALL_INTERNAL_MISC_STYLE_LABEL = "__random_all_internal_misc_style__"

RANDOM_MOOD_STYLE_GROUPS: Dict[str, List[str]] = {
    RANDOM_TRANSFORMATIVE_STYLE_LABEL: [
        "Chibi Style",
        "3D Collectible Figure",
        "Pixel Art",
        "Miniature Diorama",
    ],
    RANDOM_TRADITIONAL_MEDIA_STYLE_LABEL: [
        "Ink Wash / Sumi-e",
        "Watercolor / Painterly",
        "Colored Pencil Illustration",
        "Pen and Ink Sketch",
        "Charcoal Drawing",
        "Graphite Pencil Sketch",
        "Pastel Chalk Drawing",
        "Oil Painting",
        "Gouache Storybook Illustration",
    ],
}

RANDOM_ALL_INTERNAL_MISC_STYLES: List[str] = [
    "Apocalyptic Wasteland",
    "Hand-Painted Storybook Animation",
    "Long Exposure Light Trails",
    "Mediterranean Sunlight",
    "Volumetric Dust Light",
]


def _visible_mood_family_options() -> List[str]:
    base = list(MOOD_FAMILIES.keys())
    specials = [RANDOM_MOOD_FAMILY_LABEL, RANDOM_TRANSFORMATIVE_STYLE_LABEL, RANDOM_TRADITIONAL_MEDIA_STYLE_LABEL]
    if "Default / None" in base:
        rest = [k for k in base if k != "Default / None"]
        return ["Default / None"] + specials + rest
    return specials + base


def _pick_random_mood_family(rng: random.Random) -> str:
    choices = [
        k for k in _visible_mood_family_options()
        if k not in {"Default / None", RANDOM_MOOD_FAMILY_LABEL}
    ]
    if RANDOM_ALL_INTERNAL_MISC_STYLES:
        choices.append(RANDOM_ALL_INTERNAL_MISC_STYLE_LABEL)
    if not choices:
        return "Default / None"
    return rng.choice(choices)


def _pick_random_style_for_special_mood(mood_family: str, rng: random.Random) -> str:
    choices = [s for s in RANDOM_MOOD_STYLE_GROUPS.get(mood_family, []) if s in STYLE_DNA]
    if not choices:
        return "Neutral / Minimal Carryover"
    return rng.choice(choices)


def _ui_allowed_values(widget_name: str) -> set:
    if widget_name == "model_profile":
        return set(_visible_model_profiles()) | set(MODEL_PROFILES.keys())
    if widget_name == "mood_family":
        return set(_visible_mood_family_options()) | set(MOOD_FAMILIES.keys())
    if widget_name == "adult_tone":
        return {"default", "safe", "suggestive", "sensual", "bold sensual", "nsfw", "explicit nsfw", "romantic non-explicit"}
    if widget_name == "adult_wardrobe":
        return set(ADULT_WARDROBE.keys())
    if widget_name == "style_dna":
        return set(STYLE_DNA.keys())
    if widget_name == "style_strength":
        return {"subtle", "balanced", "strong"}
    if widget_name == "style_conflict_cleanup":
        return {"off", "soft", "strong"}
    if widget_name == "scene_framing":
        return set(SCENE_FRAMING.keys())
    if widget_name == "lens_preset":
        return set(LENS_PRESETS.keys())
    if widget_name == "external_prompt_mode":
        return {"Append style after external prompt", "Prepend style before external prompt", "Output style only"}
    return set()


def _safe_ui_value(value: Any, widget_name: str) -> str:
    canonical = _canonical_ui_value(value, widget_name)
    allowed = _ui_allowed_values(widget_name)
    if canonical in allowed:
        return canonical
    default = UI_WIDGET_DEFAULTS.get(widget_name, "")
    if default in allowed or not allowed:
        return default
    return next(iter(allowed)) if allowed else _clean_text(canonical)


def _adult_tone_group(adult_tone: str) -> str:
    tone = _canonical_ui_value(adult_tone, "adult_tone")
    if tone in ("default", "", None):
        return "default"
    if tone in ("nsfw",):
        return "nsfw"
    if tone in ("explicit nsfw",):
        return "explicit"
    if tone in ("bold sensual",):
        return "bold_sensual"
    if tone in ("sensual",):
        return "sensual"
    if tone in ("suggestive", "romantic non-explicit"):
        return "suggestive"
    return "safe"


def _tag_list_without_rating_tokens(tags: List[str]) -> List[str]:
    out: List[str] = []
    for tag in tags:
        key = _normalize_tag_identity(tag)
        if key in {"safe", "nsfw", "rating_safe", "rating_questionable", "rating_explicit", "explicit", "questionable", "sensitive"}:
            continue
        out.append(tag)
    return out


def _quality_with_adult_tone(model_profile: str, adult_tone: str) -> str:
    profile = _get_model_profile(model_profile)
    key = _model_key(model_profile)
    tone_group = _adult_tone_group(adult_tone)
    base_tags = _tag_list_without_rating_tokens(_split_prompt_tags(profile.get("quality", "")))

    if key == "pony":
        rating = {
            "default": "rating_safe",
            "safe": "rating_safe",
            "suggestive": "rating_questionable",
            "sensual": "rating_questionable",
            "bold_sensual": "rating_questionable",
            "nsfw": "rating_explicit",
            "explicit": "rating_explicit",
        }.get(tone_group, "")
        return _join_unique_tags([", ".join(base_tags), rating])

    if key in ("anima", "ilxl"):
        rating = {
            "default": "safe",
            "safe": "safe",
            "suggestive": "safe",
            "sensual": "sensitive",
            "bold_sensual": "sensitive",
            "nsfw": "nsfw",
            "explicit": "nsfw",
        }.get(tone_group, "")
        return _join_unique_tags([", ".join(base_tags), rating])

    if key in ("sdxl", "sd"):
        rating = {
            "default": "",
            "safe": "",
            "suggestive": "",
            "sensual": "suggestive",
            "bold_sensual": "suggestive",
            "nsfw": "nsfw",
            "explicit": "explicit nsfw",
        }.get(tone_group, "")
        return _join_unique_tags([", ".join(base_tags), rating])

    return _clean_text(profile.get("quality", "masterpiece, best quality, highres, detailed"))


def _adult_tone_terms(adult_tone: str, family: str = "tag") -> List[str]:
    tone = _canonical_ui_value(adult_tone, "adult_tone")
    if family == "natural":
        mapping = {
            "default": [],
            "safe": ["tasteful adult mood"],
            "suggestive": ["suggestive adult mood"],
            "sensual": ["sensual adult mood"],
            "bold sensual": ["sensual", "seductive", "adult mood"],
            "nsfw": ["nsfw adult mood", "erotic tension"],
            "explicit nsfw": ["explicit adult erotic mood"],
            "romantic non-explicit": ["romantic intimate adult mood"],
        }
    else:
        mapping = {
            "default": [],
            "safe": ["safe"],
            "suggestive": ["suggestive", "sensual"],
            "sensual": ["sensual", "seductive"],
            "bold sensual": ["sensual", "seductive", "erotic"],
            "nsfw": ["nsfw", "erotic"],
            "explicit nsfw": ["nsfw", "explicit", "erotic"],
            "romantic non-explicit": ["romantic", "intimate"],
        }
    return mapping.get(tone, mapping["default"])


def _adult_tone_tag_terms_for_model(adult_tone: str, model_profile: str) -> List[str]:
    """Return adult-tone tag cues without duplicating model rating/quality tokens.

    SDXL/SD/Anima/Pony quality strings already add rating or ``nsfw`` cues for adult
    tones. Repeating ``nsfw`` and ``explicit`` again as weighted style tags creates
    redundant or contradictory signals, so keep only the extra mood cue there.
    """
    terms = _adult_tone_terms(adult_tone, "tag")
    key = _model_key(model_profile)
    tone_group = _adult_tone_group(adult_tone)
    if key in ("pony", "sdxl", "sd", "anima") and tone_group in ("nsfw", "explicit"):
        return [term for term in terms if _normalize_tag_identity(term) not in {"nsfw", "explicit"}]
    return terms



ADULT_TONE_ORDER = [
    "default",
    "safe",
    "romantic non-explicit",
    "suggestive",
    "sensual",
    "bold sensual",
    "nsfw",
    "explicit nsfw",
]

WARDROBE_TONE_FLOOR: Dict[str, str] = {


    "bikini": "suggestive",
    "one-piece swimsuit": "suggestive",
    "lingerie": "sensual",
    "sheer nightgown": "sensual",
    "silk slip dress": "sensual",
    "corset": "sensual",
    "bodysuit": "sensual",
    "latex outfit": "sensual",
    "leather outfit": "sensual",
    "bathrobe": "sensual",
    "lace lingerie set": "sensual",
    "sheer robe": "sensual",
    "satin robe": "sensual",
    "silk camisole": "sensual",
    "bralette": "sensual",
    "lace bodysuit": "sensual",
    "sheer bodysuit": "sensual",
    "garter belt": "sensual",
    "thigh-high stockings": "suggestive",
    "pantyhose": "suggestive",
    "open shirt": "suggestive",
    "oversized shirt": "suggestive",
    "mini dress": "suggestive",
    "off-shoulder dress": "suggestive",
    "halter dress": "suggestive",
    "fishnet outfit": "sensual",
    "vinyl outfit": "sensual",
    "mesh top": "sensual",
    "topless": "nsfw",
    "nude": "nsfw",
}


def _tone_rank(tone: str) -> int:
    tone = _canonical_ui_value(tone, "adult_tone") or "default"
    try:
        return ADULT_TONE_ORDER.index(tone)
    except ValueError:
        return 0


def _resolve_adult_tone_for_wardrobe(adult_tone: str, adult_wardrobe: str) -> str:
    tone = _canonical_ui_value(adult_tone, "adult_tone") or "default"
    wardrobe = _canonical_ui_value(adult_wardrobe, "adult_wardrobe") or "auto"
    floor = WARDROBE_TONE_FLOOR.get(wardrobe)
    if floor and _tone_rank(tone) < _tone_rank(floor):
        return floor
    return tone


def _tag_quality_for_model(model_profile: str, adult_tone: str = "default") -> str:
    return _quality_with_adult_tone(model_profile, adult_tone)


_KO_MINOR_SUBJECT_SUFFIX = (
    r"(?:에게서는|한테서는|으로서는|로서는|에게는|한테는|께서는|으로는|로는|에서는|"
    r"에게서|한테서|에게|한테|께|으로서|로서|으로|에서|"
    r"은|는|이|가|을|를|의|와|과|도|만|에|로|서|부터|까지|처럼|보다|"
    r"랑|만큼|하고|마다|이나|나|야)?"
)
_KO_MINOR_GIRL_PATTERN = rf"(?<![가-힣])(?:어린|미성년|청소년|10대)\s*소녀{_KO_MINOR_SUBJECT_SUFFIX}(?![가-힣])"
_KO_MINOR_BOY_PATTERN = rf"(?<![가-힣])(?:어린|미성년|청소년|10대)\s*소년{_KO_MINOR_SUBJECT_SUFFIX}(?![가-힣])"
NUMERIC_UNDER_18_AGE_PATTERN = r"(?:[0-9]|1[0-7])\s*(?:-\s*)?(?:years?\s*[-\s]?\s*old|yrs?\s*[-\s]?\s*old|yo|y/o)"
UNDER_18_PHRASE_PATTERN = r"under\s+(?:18|eighteen)"


MINOR_CONFLICT_REPLACEMENTS = [
    (re.compile(r"\b(?:a|the)\s+" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\b" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\b(?:a|the)\s+" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\b" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\b(?:a|the)\s+" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b(?:a|the)\s+" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(wearing|in|with|posing|standing|sitting|lying)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b" + NUMERIC_UNDER_18_AGE_PATTERN + r"\s+(wearing|in|with|posing|standing|sitting|lying)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b(?:a|the)\s+" + NUMERIC_UNDER_18_AGE_PATTERN + r"\b", re.IGNORECASE), "adult person"),
    (re.compile(r"\b" + NUMERIC_UNDER_18_AGE_PATTERN + r"\b", re.IGNORECASE), "adult person"),
    (re.compile(r"\b" + UNDER_18_PHRASE_PATTERN + r"\s+(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\b" + UNDER_18_PHRASE_PATTERN + r"\s+(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\b" + UNDER_18_PHRASE_PATTERN + r"\s+(nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b" + UNDER_18_PHRASE_PATTERN + r"\s+(wearing|in|with|posing|standing|sitting|lying)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b" + UNDER_18_PHRASE_PATTERN + r"\b", re.IGNORECASE), "adult person"),
    (re.compile(r"\bteen(?:age|ager)?\s+(?:[a-z][a-z-]*\s+){0,4}(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\bteen(?:age|ager)?\s+(?:[a-z][a-z-]*\s+){0,4}(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\bteen(?:age|ager)?\b", re.IGNORECASE), "adult"),
    (re.compile(r"\byoung\s+girl\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\byoung\s+boy\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\b(?:a|the)\s+minor\s+(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\b(?:a|the)\s+minor\s+(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\b(?:a|the)\s+minor\s+(nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b(?:a|the)\s+minor\s+(wearing|in|with|posing|standing|sitting|lying)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\b(?:a|the)\s+minor\s*(?=$|[,.;:])", re.IGNORECASE), "adult person"),
    (re.compile(r"\bminor\s+(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\bminor\s+(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\bminor\s+(nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\bminor\s+(wearing|in|with|posing|standing|sitting|lying)\b", re.IGNORECASE), r"adult person \1"),
    (re.compile(r"\bminor\s*(?=$|[,.;:])", re.IGNORECASE), "adult person"),
    (re.compile(r"\bunderage\s+(?:girl|female)\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\bunderage\s+(?:boy|male)\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\bunderage\b", re.IGNORECASE), "adult"),

    (re.compile(_KO_MINOR_GIRL_PATTERN), "성인 여성"),
    (re.compile(_KO_MINOR_BOY_PATTERN), "성인 남성"),
]

MINOR_CONFLICT_MINOR_CUE_RE = re.compile(
    r"\b" + NUMERIC_UNDER_18_AGE_PATTERN + r"\b|"
    r"\b" + UNDER_18_PHRASE_PATTERN + r"\b|"
    r"\bteen(?:age|ager)?\b|\byoung\s+girl\b|"
    r"\byoung\s+boy\b|\bunderage\b|"
    r"\b(?:a|the)\s+minor\s+(?:girl|female|boy|male|"
    r"nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish|"
    r"wearing|in|with|posing|standing|sitting|lying)\b|"
    r"\b(?:a|the)\s+minor\s*(?=$|[,.;:])|"
    r"\bminor\s+(?:girl|female|boy|male|"
    r"nude|naked|topless|nsfw|explicit|sexual|erotic|pornographic|fetish|"
    r"wearing|in|with|posing|standing|sitting|lying)\b|"
    r"\bminor\s*(?=$|[,.;:])|"
    + _KO_MINOR_GIRL_PATTERN + r"|"
    + _KO_MINOR_BOY_PATTERN,
    re.IGNORECASE,
)

MINOR_CONFLICT_EXPLICIT_CUE_RE = re.compile(
    r"\b(?:nsfw|explicit|erotic|nude|naked|topless|sex(?:ual)?|porn(?:ographic)?|fetish|"
    r"bikini|lingerie|swimsuit|sheer|corset)\b"
    r"|노출|나체|누드|성인물|야한|섹스|성행위|포르노|비키니|란제리|속옷|수영복|시스루",
    re.IGNORECASE,
)



VISIBLE_LIGHT_SOURCE_REQUEST_RE = re.compile(
    r"\b(?:lamp|lamps|floor lamp|table lamp|desk lamp|lantern|lanterns|chandelier|chandeliers|"
    r"candle|candles|neon sign|neon signs|streetlight|streetlights|street lamp|street lamps|"
    r"ceiling light|ceiling lights|wall light|wall lights|wall sconce|wall sconces|sconce|sconces|"
    r"light fixture|light fixtures|light bulb|light bulbs|bulb|bulbs|fairy lights|string lights|"
    r"led strip|led strips|practical light|practical lights|softbox|softboxes|light stand|light stands|"
    r"studio light|studio lights|lighting rig|lighting rigs|visible lighting equipment)\b"
    r"|조명기구|조명\s*장비|천장\s*조명|벽\s*조명|전구|램프|랜턴|촛불|양초|샹들리에|네온사인|가로등|스튜디오\s*조명",
    re.IGNORECASE,
)


def _user_requested_visible_light_source(*texts: Any) -> bool:
    joined = " ".join(_normalize_text(t) for t in texts if t is not None)
    return bool(VISIBLE_LIGHT_SOURCE_REQUEST_RE.search(joined))


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).replace("\r", " ").replace("\n", " ").strip()
    s = re.sub(r"\s*,\s*,\s*", ", ", s)
    s = re.sub(r"(?:,\s*){2,}", ", ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" ,")


def _adult_minor_conflict_needs_rewrite(text: Any, adult_tone: str = "default") -> bool:
    s = _normalize_text(text)
    if not s or not MINOR_CONFLICT_MINOR_CUE_RE.search(s):
        return False
    tone = _canonical_ui_value(adult_tone, "adult_tone") or "default"
    return _tone_rank(tone) >= _tone_rank("suggestive") or bool(MINOR_CONFLICT_EXPLICIT_CUE_RE.search(s))


def _sanitize_minor_conflict_text(text: Any, adult_tone: str = "default") -> str:
    """Narrow safety harmonizer for explicit adult/minor cue collisions only."""
    s = _normalize_text(text)
    if not _adult_minor_conflict_needs_rewrite(s, adult_tone):
        return s
    for pat, repl in MINOR_CONFLICT_REPLACEMENTS:
        s = pat.sub(repl, s)
    # When a broader minor cue was replaced, avoid awkward remnants such as
    # "adult Korean girl" in adult-tone prompts while leaving ordinary anime
    # tag usage untouched outside the conflict path.
    s = re.sub(r"\badult\s+((?:[a-z][a-z-]*\s+){0,4})girl\b", r"adult \1woman", s, flags=re.IGNORECASE)
    s = re.sub(r"\badult\s+((?:[a-z][a-z-]*\s+){0,4})boy\b", r"adult \1man", s, flags=re.IGNORECASE)
    s = re.sub(r"\ba\s+adult\b", "an adult", s, flags=re.IGNORECASE)
    return _normalize_text(s)


def _clean_text(text: Any) -> str:
    """Normalize free text without broad age-term censorship or tag rewriting."""
    return _normalize_text(text)


def _clean_negative_text(text: Any) -> str:
    """Normalize negative prompt text without replacing the very terms that should stay blocked."""
    return _normalize_text(text)


def _is_escaped_at(text: str, idx: int) -> bool:
    backslashes = 0
    pos = idx - 1
    while pos >= 0 and text[pos] == "\\":
        backslashes += 1
        pos -= 1
    return bool(backslashes % 2)


def _count_unescaped_char(text: str, target: str) -> int:
    return sum(1 for idx, ch in enumerate(text) if ch == target and not _is_escaped_at(text, idx))


def _remove_unescaped_char(text: str, target: str) -> str:
    return "".join(ch for idx, ch in enumerate(text) if not (ch == target and not _is_escaped_at(text, idx)))


def _plain_comma_split_for_broken_attention(text: Any) -> List[str]:
    """Fallback splitter for malformed attention groups with missing closers.

    It separates user tags again instead of turning "(a, b" into one
    identity token, while still preserving decimal comma weights like 1,4.
    This path is only used after an unmatched bracket/parenthesis is detected.
    """
    s = str(text or "")
    out: List[str] = []
    buf: List[str] = []
    for idx, ch in enumerate(s):
        if ch == ",":
            current = "".join(buf).strip()
            decimal_weight_comma = (
                idx > 0
                and idx + 1 < len(s)
                and s[idx - 1].isdigit()
                and s[idx + 1].isdigit()
                and re.search(r":\s*[-+]?\d+$", current)
            )
            if decimal_weight_comma:
                buf.append(ch)
                continue
            item = "".join(buf).strip()
            if item:
                out.append(item)
            buf = []
            continue
        buf.append(ch)
    item = "".join(buf).strip()
    if item:
        out.append(item)

    cleaned: List[str] = []
    for item in out:
        c = _clean_text(item)
        if not c:
            continue
        if _count_unescaped_char(c, "(") > _count_unescaped_char(c, ")"):
            c = _remove_unescaped_char(c, "(")
        if _count_unescaped_char(c, "[") > _count_unescaped_char(c, "]"):
            c = _remove_unescaped_char(c, "[")
        if _count_unescaped_char(c, ")") > _count_unescaped_char(c, "("):
            c = _remove_unescaped_char(c, ")")
        if _count_unescaped_char(c, "]") > _count_unescaped_char(c, "["):
            c = _remove_unescaped_char(c, "]")
        c = _clean_text(c)
        if c:
            cleaned.append(c)
    return cleaned


def _split_comma_aware(text: Any) -> List[str]:
    """Split on top-level commas only, preserving valid SD attention groups.

    Valid groups such as "(worst quality, low quality:1.4)" stay intact.
    Malformed unclosed groups such as "(worst quality, low quality:1.4"
    are split back into independent safe tokens instead of being auto-closed
    into one merged tag identity.
    """
    s = str(text or "")
    out: List[str] = []
    buf: List[str] = []
    paren_depth = 0
    bracket_depth = 0
    for idx, ch in enumerate(s):
        if ch == "(":
            paren_depth += 1
        elif ch == ")" and paren_depth > 0:
            paren_depth -= 1
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]" and bracket_depth > 0:
            bracket_depth -= 1
        if ch == "," and paren_depth == 0 and bracket_depth == 0:
            current = "".join(buf).strip()
            decimal_weight_comma = (
                idx > 0
                and idx + 1 < len(s)
                and s[idx - 1].isdigit()
                and s[idx + 1].isdigit()
                and re.search(r":\s*[-+]?\d+$", current)
            )
            if decimal_weight_comma:
                buf.append(ch)
                continue
            item = "".join(buf).strip()
            if item:
                out.append(item)
            buf = []
            continue
        buf.append(ch)

    item = "".join(buf).strip()
    if item:
        if paren_depth > 0 or bracket_depth > 0:
            broken_parts = _plain_comma_split_for_broken_attention(item)
            if broken_parts:
                out.extend(broken_parts)
        else:
            out.append(item)
    return out


def _merge_negative_prompt_parts(*parts: Any) -> str:
    safe_parts: List[str] = []
    for part in parts:
        s = _clean_negative_text(part)
        if s:
            safe_parts.append(s)
    return _join_unique_tags(safe_parts)


def _unique(seq: List[str]) -> List[str]:
    out, seen = [], set()
    for item in seq:
        item = _clean_text(item)
        if not item:
            continue
        key = item.lower()
        if key not in seen:
            out.append(item)
            seen.add(key)
    return out


def _style_pool_identity(term: Any, style_name: str, field: str) -> str:
    s = _clean_text(term).lower()
    if style_name == "Watercolor / Painterly":
        if field == "lighting":
            if s in {"soft diffused natural light", "gentle diffused light"}:
                return "watercolor lighting:diffused light"
            if s in {"gentle ambient wash", "soft ambient wash"}:
                return "watercolor lighting:ambient wash"
            if s in {"even tonal illumination", "even tonal fill", "even tonal wash"}:
                return "watercolor lighting:even tonal"
        if field == "color":
            if s in {"soft pigment wash", "soft color wash"}:
                return "watercolor color:soft pigment wash"
            if s in {"translucent layered hues", "translucent pigment"}:
                return "watercolor color:translucent pigment"
            if s in {"muted watercolor palette", "muted natural palette"}:
                return "watercolor color:muted palette"
        if field == "composition":
            if s in {
                "painterly loose composition",
                "loose painterly framing",
                "loose painterly composition",
                "loose painterly layout",
            }:
                return "watercolor composition:loose painterly"
        if field == "texture":
            if s in {"visible brushstroke texture", "brushstroke texture"}:
                return "watercolor texture:brushstroke"
            if s in {"wet-on-wet paint bleed", "wet pigment bleed"}:
                return "watercolor texture:paint bleed"
            if s in {"paper grain beneath pigment", "paper grain"}:
                return "watercolor texture:paper grain"
    return s


def _unique_style_pool(seq: List[str], style_name: str, field: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in seq:
        item = _clean_text(item)
        if not item:
            continue
        key = _style_pool_identity(item, style_name, field)
        if key not in seen:
            out.append(item)
            seen.add(key)
    return out


def _pick(rng: random.Random, items: List[str], count: int = 1) -> List[str]:
    items = _unique(items)
    if not items:
        return []
    if count >= len(items):
        return items[:]
    return rng.sample(items, count)


def _join_comma(parts: List[str]) -> str:
    return ", ".join(_unique(parts))


def _external_custom_note(text: Any) -> str:
    note = _clean_text(text)
    if not note:
        return ""


    segments = [s.strip() for s in _split_comma_aware(note) if s.strip()]
    cleaned_segments: List[str] = []
    for seg in segments:
        cleaned = re.sub(r"\s+", " ", _clean_text(seg)).strip(" ,")
        if cleaned:
            cleaned_segments.append(cleaned)
    return ", ".join(cleaned_segments)


def _safe_camera_terms(camera_terms: List[str], suppress_camera: bool = False) -> List[str]:
    if suppress_camera:
        return []
    out: List[str] = []
    for term in camera_terms:
        cleaned = _clean_text(term)
        if not cleaned:
            continue
        repl = SAFE_CAMERA_TERM_REPLACEMENTS.get(cleaned)
        if repl is None:
            repl = cleaned
        if not repl:
            continue

        if repl.lower() in SAFE_CAMERA_TERM_ALLOWLIST:
            out.append(repl)
            continue

        if not PHYSICAL_STYLE_CUE_PATTERN.search(repl):
            out.append(repl)
    return _unique(out)


def _join_negative_comma(parts: List[str]) -> str:
    return _join_unique_tags(parts)


STYLE_CONFLICT_POLARITIES = [
    (
        "monochrome",
        re.compile(r"\b(?:black\s+and\s+white|monochrome|grayscale|greyscale)\b", re.IGNORECASE),
        "color",
        re.compile(r"\b(?:color|colour|vibrant|saturated|neon|magenta|cyan|purple|pink|blue|red|green|golden|warm|amber|pastel|terracotta|cream|olive|lavender)\b", re.IGNORECASE),
    ),
    (
        "warm",
        re.compile(r"\b(?:warm|golden|amber|sunlight|sunlit|sun-warmed|mediterranean|terracotta|cream)\b", re.IGNORECASE),
        "cold",
        re.compile(r"\b(?:cold|icy|steel\s+blue|clinical)\b", re.IGNORECASE),
    ),
    (
        "bright",
        re.compile(r"\b(?:bright|high-key|clean\s+readable\s+light|soft\s+glow|pastel|pearl\s+white|fresh|cheerful|lightness)\b", re.IGNORECASE),
        "dark",
        re.compile(r"\b(?:dark|darkness|shadow|shadows|low-key|noir|chiaroscuro|gothic|horror|unsettling|ominous|gloom|heavy\s+gloom)\b", re.IGNORECASE),
    ),
    (
        "vintage",
        re.compile(r"\b(?:vintage|retro|old\s+film|classic\s+film|timeless|faded\s+memory)\b", re.IGNORECASE),
        "future",
        re.compile(r"\b(?:cyberpunk|sci-fi|futuristic|holographic|digital|neon)\b", re.IGNORECASE),
    ),
    (
        "painterly",
        re.compile(r"\b(?:watercolor|painterly|painting|brush|washes|gouache|illustration)\b", re.IGNORECASE),
        "photographic",
        re.compile(r"\b(?:photograph|photographic|photo-real|photorealistic|studio\s+glamour|film\s+photograph)\b", re.IGNORECASE),
    ),
]


def _texts_conflict_by_style_polarity(a: Any, b: Any) -> bool:
    left = _normalize_text(a)
    right = _normalize_text(b)
    if not left or not right:
        return False
    for _, left_re, _, right_re in STYLE_CONFLICT_POLARITIES:
        if (left_re.search(left) and right_re.search(right)) or (right_re.search(left) and left_re.search(right)):
            return True
    return False


MONOCHROME_CONTEXT_RE = re.compile(
    r"\b(?:black\s*(?:&|and)\s*white|b\s*&\s*w|monochrome|grayscale|greyscale)\b",
    re.IGNORECASE,
)
CHROMATIC_COLOR_CUE_RE = re.compile(
    r"\b(?:vibrant|saturated|neon|magentas?|cyans?|purples?|pinks?|blues?|reds?|greens?|golden|"
    r"amber|oranges?|pastel|terracotta|cream|olive|lavender|peach|crimson|"
    r"yellows?|teals?|turquoises?|violets?|holographic|rainbow|colorful|colourful|"
    r"oil[-\s]?paint\s+colors?|varnished\s+palette|color-driven)\b",
    re.IGNORECASE,
)
OIL_PAINTING_MONOCHROME_COLOR_REPLACEMENTS_2026_05_31_E: Dict[str, str] = {
    "rich oil-paint colors": "monochrome oil-paint values",
    "layered earth tones": "layered grayscale oil values",
    "deep blended pigments": "deep blended monochrome pigments",
    "warm varnished palette": "tonal varnished surface",
}
WARM_LIGHTING_CUE_RE = re.compile(r"\bwarm\b", re.IGNORECASE)
WARM_COLOR_ONLY_RE = re.compile(r"\bwarm\s+(?:tones?|colors?|colours?|palette|color\s+palette|colour\s+palette)\b", re.IGNORECASE)


def _is_monochrome_output_context(mood_family: str, style_name: str, extra: Any = "") -> bool:
    haystack = " ".join([_clean_text(mood_family), _clean_text(style_name), _normalize_text(extra)])
    return bool(MONOCHROME_CONTEXT_RE.search(haystack))


def _neutralize_warm_lighting_for_monochrome(term: str) -> str:
    cleaned = _clean_text(term)
    if not cleaned or not WARM_LIGHTING_CUE_RE.search(cleaned):
        return cleaned
    if WARM_COLOR_ONLY_RE.search(cleaned):
        return ""
    neutral = re.sub(r"\bwarm\s+(?=(?:off[-\s]?camera|interior|shadow|lift|side|rim|light|lighting|illumination))", "soft ", cleaned, flags=re.IGNORECASE)
    neutral = re.sub(r"\bwarm\s+(?=(?:theatrical|spotlight|stage|glow|candlelit))", "tonal ", neutral, flags=re.IGNORECASE)
    neutral = re.sub(r"\bwarm\b", "tonal", neutral, flags=re.IGNORECASE)
    neutral = re.sub(r"\btonal\s+tones?\b", "monochrome tonal range", neutral, flags=re.IGNORECASE)
    return _clean_text(neutral)


def _filter_chromatic_terms_for_monochrome(parts: List[Any], *, fallback: bool = False, style_name: str = "") -> List[str]:
    out: List[str] = []
    style_key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    for part in parts:
        cleaned = _clean_text(part)
        if not cleaned:
            continue
        if style_key == "Oil Painting":
            replacement = OIL_PAINTING_MONOCHROME_COLOR_REPLACEMENTS_2026_05_31_E.get(cleaned.lower())
            if replacement:
                out.append(replacement)
                continue
        if MONOCHROME_CONTEXT_RE.search(cleaned):
            out.append(cleaned)
            continue
        if CHROMATIC_COLOR_CUE_RE.search(cleaned):
            continue
        if WARM_LIGHTING_CUE_RE.search(cleaned):
            cleaned = _neutralize_warm_lighting_for_monochrome(cleaned)
            if not cleaned:
                continue
        out.append(cleaned)
    if fallback and not out:
        return ["monochrome tonal range"]
    return _unique(out)


def _monochrome_safe_anchor(anchor: Any) -> str:
    cleaned = _clean_text(anchor)
    if not cleaned:
        return ""
    if MONOCHROME_CONTEXT_RE.search(cleaned):
        return cleaned
    if CHROMATIC_COLOR_CUE_RE.search(cleaned):
        return "monochrome tonal treatment"
    if WARM_LIGHTING_CUE_RE.search(cleaned):
        return _neutralize_warm_lighting_for_monochrome(cleaned) or "monochrome tonal treatment"
    return cleaned


ANCHOR_CONFLICT_RULES = [
    (
        # Warm/bright sunlight anchors should not be blindly merged with strongly
        # cold, rain-glass, horror, or dark-mass anchors. This is deliberately
        # narrower than "warm vs neon" so valid warm neon/cyberpunk looks survive.
        re.compile(r"\b(?:mediterranean|sunlight|sunlit|sun-warmed|terracotta|golden\s+hour|golden\s+warm|high-key|clean\s+light|bright\s+even)\b", re.IGNORECASE),
        re.compile(r"\b(?:rain-soaked|rain\s+glass|rainy\s+glass|neon\s+melancholy|melancholy\s+through\s+rain|clinical\s+cold|cold\s+symmetrical|dark\s+fantasy|shadow\s+mass|ominous\s+dark|horror\s+dark|creeping\s+horror|horror\s+dread|dark\s+unsettling|unsettling\s+mood)\b", re.IGNORECASE),
    ),
    (
        # Specific cyberpunk anchor conflict. Do not block all neon; only the
        # explicit cyberpunk-neon anchor is kept from combining with golden or
        # Mediterranean sunlight anchors.
        re.compile(r"\b(?:golden\s+hour\s+warm\s+(?:light|glow)|golden\s+hour|warm\s+golden\s+(?:light|glow)|mediterranean|warm\s+mediterranean)\b", re.IGNORECASE),
        re.compile(r"\b(?:cyberpunk\s+neon\s+sci[-\s]*fi|cyberpunk\s+neon\s+atmosphere|cyberpunk,?\s+neon\s+glow)\b", re.IGNORECASE),
    ),
]


def _anchors_conflict(a: Any, b: Any) -> bool:
    left = _normalize_text(a)
    right = _normalize_text(b)
    if not left or not right:
        return False
    if _texts_conflict_by_style_polarity(left, right):
        return True
    for left_re, right_re in ANCHOR_CONFLICT_RULES:
        if (left_re.search(left) and right_re.search(right)) or (right_re.search(left) and left_re.search(right)):
            return True
    return False


def _style_data_signature(*items: Any) -> str:
    parts: List[str] = []
    def walk(x: Any):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple, set)):
            for v in x:
                walk(v)
        elif x is not None:
            s = _normalize_text(x)
            if s:
                parts.append(s)
    for item in items:
        walk(item)
    return " ".join(parts)


STYLE_AVOID_BLOCK_RULES = [
    (
        re.compile(r"\b(?:color|vibrant\s+color|saturated\s+color\s+palette|bright\s+colors|chaotic\s+color\s+palette)\b", re.IGNORECASE),
        re.compile(r"\b(?:color|colour|vibrant|saturated|neon|magenta|cyan|purple|pink|blue|red|green|golden|warm|amber|pastel|terracotta|cream|olive|lavender)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"\b(?:cold\s+tones?|cold\s+tone|sharp\s+clinical\s+look)\b", re.IGNORECASE),
        re.compile(r"\b(?:cold|icy|steel\s+blue|clinical|psychological\s+coldness)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"\b(?:harsh\s+shadows|dark\s+mood|dark\s+shadows|moody\s+darkness|low-key\s+illumination)\b", re.IGNORECASE),
        re.compile(r"\b(?:dark|shadow|shadows|low-key|noir|chiaroscuro|gothic|horror|unsettling|ominous)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"\b(?:vintage\s+look|modern\s+clean\s+look|digital\s+sharpness)\b", re.IGNORECASE),
        re.compile(r"\b(?:vintage|retro|cyberpunk|sci-fi|futuristic|holographic|digital|neon|clean\s+minimal)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"\b(?:photorealistic|sharp\s+detail|hard\s+edges|ultra-realistic)\b", re.IGNORECASE),
        re.compile(r"\b(?:photograph|photographic|sharp|hard\s+edge|chiaroscuro|studio\s+glamour|film\s+photograph)\b", re.IGNORECASE),
    ),
]


def _avoid_term_blocks_style(term: Any, style_signature: Any) -> bool:
    t = _normalize_text(term)
    sig = _normalize_text(style_signature)
    if not t or not sig:
        return False
    return any(avoid_re.search(t) and style_re.search(sig) for avoid_re, style_re in STYLE_AVOID_BLOCK_RULES)


DARK_STYLE_AVOID_KEEP_RE = re.compile(r"\b(?:bright\s+colors?|cheerful\s+mood)\b", re.IGNORECASE)
DARK_STYLE_SIGNATURE_RE = re.compile(
    r"\b(?:dark\s+fantasy|shadow\s+mass|gothic|noir|horror|unsettling|ominous|dread|creeping\s+horror|low-key|chiaroscuro)\b",
    re.IGNORECASE,
)


def _keep_dark_style_avoid_term(term: Any, style_signature: Any) -> bool:
    t = _normalize_text(term)
    sig = _normalize_text(style_signature)
    if not t or not sig:
        return False
    return bool(DARK_STYLE_AVOID_KEEP_RE.search(t) and DARK_STYLE_SIGNATURE_RE.search(sig))


def _filter_mood_avoid_for_style(avoid_terms: List[str], style_signature: str) -> List[str]:
    out: List[str] = []
    for term in avoid_terms:
        t = _clean_negative_text(term)
        if not t:
            continue
        if _texts_conflict_by_style_polarity(t, style_signature) or _avoid_term_blocks_style(t, style_signature):
            if not _keep_dark_style_avoid_term(t, style_signature):
                continue
        out.append(t)
    return out


def _filter_mood_positive_terms_for_style(terms: List[str], style_signature: str) -> List[str]:
    out: List[str] = []
    for term in terms:
        t = _clean_text(term)
        if not t:
            continue
        if _texts_conflict_by_style_polarity(t, style_signature):
            continue
        out.append(t)
    return _unique(out)


STRONG_DARK_STYLE_BRIDGE_RE = re.compile(
    r"\b(?:dark\s+fantasy|gothic|noir|horror|ominous|unsettling|dread|creeping\s+horror|low-key)\b",
    re.IGNORECASE,
)


def _bridge_mood_emotion_after_conflict(mood_family: str, picked_terms: List[str], style_signature: str, style_name: str = "") -> List[str]:
    if not picked_terms:
        return []
    if mood_family != "Bright / High-key":
        return []
    # Bridge only for explicitly dark style families by style name. Generic
    # technique/lighting cues inside the style data, such as Charcoal Drawing's
    # "smudged shadow mass" or Baroque shadow terms, must not trigger this.
    haystack = _normalize_text(style_name)
    if STRONG_DARK_STYLE_BRIDGE_RE.search(haystack):
        return ["clean light-against-shadow tension"]
    return []


SCHOOL_UNIFORM_REQUEST_RE = re.compile(r"\bschool\s*uniform\b", re.IGNORECASE)
SCHOOL_STYLE_REQUEST_RE = re.compile(r"\bschool\s*(?:girl|uniform)\b|\bschoolgirl\b", re.IGNORECASE)
SCHOOL_UNIFORM_NEGATIVE_CHUNK_RE = re.compile(r"\bschool\s*uniform\b|\bschool\s+uniform\s+implications\b", re.IGNORECASE)
SCHOOL_STYLE_NEGATIVE_CHUNK_RE = re.compile(r"\bschool\s+styling\b|\bschool\s*girl\b|\bschoolgirl\b", re.IGNORECASE)
JUVENILE_STYLING_NEGATIVE_RE = re.compile(r"\bjuvenile\s+styling\b", re.IGNORECASE)


def _remove_negative_chunks(text: Any, *patterns: re.Pattern) -> str:
    chunks = [_clean_negative_text(x) for x in _split_comma_aware(_clean_negative_text(text))]
    out: List[str] = []
    seen = set()
    for chunk in chunks:
        if not chunk:
            continue
        if any(p.search(chunk) for p in patterns):
            continue
        key = chunk.lower()
        if key not in seen:
            out.append(chunk)
            seen.add(key)
    return ", ".join(out)


def _harmonize_negative_with_user_positive(negative: Any, *positive_sources: Any, adult_tone: str = "default") -> str:
    joined_sources = " ".join(_normalize_text(src) for src in positive_sources if src is not None)
    out = _clean_negative_text(negative)
    if not joined_sources or not out:
        return out


    if SCHOOL_UNIFORM_REQUEST_RE.search(joined_sources):
        out = _remove_negative_chunks(out, SCHOOL_UNIFORM_NEGATIVE_CHUNK_RE)
    if SCHOOL_STYLE_REQUEST_RE.search(joined_sources) and not _adult_minor_conflict_needs_rewrite(joined_sources, adult_tone):
        out = _remove_negative_chunks(out, SCHOOL_UNIFORM_NEGATIVE_CHUNK_RE, SCHOOL_STYLE_NEGATIVE_CHUNK_RE, JUVENILE_STYLING_NEGATIVE_RE)
    return out


ADULT_EXPRESSION_NEGATIVE_CHUNK_RE = re.compile(
    r"\b(?:explicit\s+sexual\s+(?:act|action)|pornographic(?:\s+staging)?|pornographic)\b",
    re.IGNORECASE,
)


def _harmonize_negative_with_model_tone(negative: Any, model_profile: str, adult_tone: str = "default") -> str:
    """Remove negative chunks that directly fight selected adult rating for Anima.

    Anima-style tag models commonly use rating/adult tags in the positive prompt.
    Keep age/quality/anatomy/style-protection negatives intact, but do not leave
    adult-expression blockers when the user explicitly selects NSFW/explicit tone.
    """
    out = _clean_negative_text(negative)
    if not out:
        return out
    if _model_key(model_profile) != "anima":
        return out
    if _adult_tone_group(adult_tone) not in {"nsfw", "explicit"}:
        return out
    return _remove_negative_chunks(out, ADULT_EXPRESSION_NEGATIVE_CHUNK_RE)


def _split_prompt_tags(text: Any) -> List[str]:
    return [_clean_text(t) for t in _split_comma_aware(text) if _clean_text(t)]


def _normalize_tag_identity(token: Any) -> str:
    t = str(token or "").strip()
    for _ in range(8):
        prev = t
        t = re.sub(r"\s*:\s*[-+]?\d+(?:[.,]\d+)?$", "", t).strip()
        if len(t) >= 2 and ((t.startswith("(") and t.endswith(")")) or (t.startswith("[") and t.endswith("]"))):
            t = t[1:-1].strip()
        if t == prev:
            break
    return re.sub(r"\s+", " ", t).lower()


def _weighted_tag_token(token: Any, weight: float = 1.25) -> str:
    t = _clean_text(token)
    if not t:
        return ""
    if WEIGHTED_TAG_VALUE_RE.match(t):
        return t
    if re.match(r"^\(.+\)$", t) or re.match(r"^\[.+\]$", t):
        return t
    return f"({t}:{weight:.2f})".replace(":1.00", ":1")


WEIGHTED_TAG_VALUE_RE = re.compile(
    r"^\s*(?:\(.+?:\s*([-+]?\d+(?:[.,]\d+)?)\)|\[.+?:\s*([-+]?\d+(?:[.,]\d+)?)\]|[^\(\)\[\]]+?:\s*([-+]?\d+(?:[.,]\d+)?))\s*$"
)


def _tag_attention_rank(token: Any) -> Tuple[int, float]:
    t = str(token or "").strip()
    if not t:
        return (0, 0.0)
    m = WEIGHTED_TAG_VALUE_RE.match(t)
    if m:
        try:
            weight = next((g for g in m.groups() if g), "1")
            return (2, abs(float(weight.replace(",", ".")) - 1.0))
        except Exception:
            return (2, 0.0)
    if (t.startswith("(") and t.endswith(")")) or (t.startswith("[") and t.endswith("]")):
        return (1, 0.0)
    return (0, 0.0)


def _join_unique_tags(parts: List[Any]) -> str:
    out_order: List[str] = []
    tag_map: Dict[str, str] = {}
    rank_map: Dict[str, Tuple[int, float]] = {}
    for part in parts:
        for tag in _split_prompt_tags(part):
            key = _normalize_tag_identity(tag)
            if not key:
                continue
            rank = _tag_attention_rank(tag)
            if key not in tag_map:
                out_order.append(key)
                tag_map[key] = tag
                rank_map[key] = rank
            elif rank > rank_map.get(key, (0, 0.0)):
                tag_map[key] = tag
                rank_map[key] = rank
    return ", ".join(tag_map[k] for k in out_order if tag_map.get(k))


PONY_EXTERNAL_CONFLICT_TAG_RE = re.compile(r"^(?:rating_[a-z0-9_]+|source_[a-z0-9_]+)$", re.IGNORECASE)
ILXL_EXTERNAL_RATING_TAGS = {"safe", "sensitive", "nsfw"}


def _filter_external_rating_source_conflicts(external_prompt: Any, model_profile: str) -> str:
    key = _model_key(model_profile)
    if key not in ("pony", "ilxl", "anima"):
        return _clean_text(external_prompt)
    out: List[str] = []
    for tag in _split_prompt_tags(external_prompt):
        tag_clean = _clean_text(tag)
        tag_key = _normalize_tag_identity(tag_clean).lower()
        if key == "pony" and PONY_EXTERNAL_CONFLICT_TAG_RE.match(tag_key):
            continue
        if key in ("ilxl", "anima") and tag_key in ILXL_EXTERNAL_RATING_TAGS:
            continue
        out.append(tag_clean)
    return _join_comma(out)


def _split_tag_lead(tag_text: Any, max_items: int = 3) -> Tuple[str, str]:
    tags = _split_prompt_tags(tag_text)
    if max_items <= 0 or not tags:
        return "", ", ".join(tags)
    return ", ".join(tags[:max_items]), ", ".join(tags[max_items:])


def _join_mixed_prompt(tag_block: str, assist: str = "") -> str:
    tag_block = _clean_text(tag_block)
    assist = _clean_text(assist)
    if tag_block and assist:
        return f"{tag_block}. {assist}"
    return tag_block or assist


def _style_tag_fragment(text: Any) -> str:
    tag = _clean_text(text)
    return re.sub(r"^and\b\s*", "", tag, flags=re.IGNORECASE).strip()


def _style_tag_insert_from_raw(raw_parts: List[Any], weight: float = 1.18) -> str:
    weighted: List[str] = []
    for idx, part in enumerate(raw_parts):
        for tag in _split_prompt_tags(part):
            tag = _style_tag_fragment(tag)
            if not tag:
                continue
            weighted.append(_weighted_tag_token(tag, weight if idx == 0 else max(1.08, weight - 0.06)))
    return _join_unique_tags(weighted)

STYLE_TAG_ALIASES_2026_05_31_C: Dict[str, List[str]] = {'Dream Pastel Diffusion': ['pastel', 'dreamy', 'soft colors', 'glow', 'haze'], 'Watercolor / Painterly': ['watercolor', 'traditional media', 'painting', 'paper texture'], 'Graphite Pencil Sketch': ['pencil sketch', 'graphite', 'sketch', 'monochrome', 'hatching'], 'Pen and Ink Sketch': ['pen and ink', 'ink', 'lineart', 'crosshatching', 'monochrome'], 'Colored Pencil Illustration': ['colored pencil', 'traditional media', 'sketch', 'paper texture'], 'Pastel Chalk Drawing': ['pastel chalk', 'pastel', 'traditional media', 'powdery texture'], 'Gouache Storybook Illustration': ['gouache', 'storybook', 'traditional media', 'painting'], 'Hand-Painted Storybook Animation': ['hand-painted', 'storybook', 'traditional media', 'painting'], 'Volumetric Dust Light': ['volumetric lighting', 'light rays', 'dust particles', 'haze'], 'Long Exposure Light Trails': ['long exposure', 'light trails', 'motion blur', 'night'], 'Oil Painting': ['oil painting', 'traditional media', 'canvas', 'impasto'], 'Miniature Diorama': ['miniature', 'diorama', 'scale model', 'toy-like', 'tabletop'], 'Pixel Art': ['pixel art', 'pixelated', 'retro game', 'lowres'], '3D Collectible Figure': ['3d', 'figurine', 'collectible figure', 'toy', 'resin', 'display stand'], 'Apocalyptic Wasteland': ['post-apocalyptic', 'wasteland', 'ruins', 'debris', 'ruined city'], 'Chibi Style': ['chibi', 'super deformed', 'oversized head', 'short limbs', 'tiny body', 'cute proportions']}


# Extra compact tag anchors for Anima/tag-family models.
# The full natural-language style sentence is still kept, but these short tags
# make cinematic/light-based styles easier for tag-sensitive models to pick up.
STYLE_TAG_ALIASES_ANIMA_REFINEMENT_2026_06_23: Dict[str, List[str]] = {
    "Neon Melancholy / Rain Glass": ["neon lighting", "rain", "wet glass", "reflections", "melancholic atmosphere"],
    "Classical Studio Glamour": ["classic glamour", "studio lighting", "elegant", "soft shadows", "vintage portrait"],
    "Baroque Operatic Atmosphere": ["baroque", "dramatic lighting", "chiaroscuro", "theatrical", "ornate atmosphere"],
    "Noir Chiaroscuro": ["film noir", "chiaroscuro", "high contrast", "hard shadows", "dramatic lighting"],
    "Symmetric Psychological Coldness": ["symmetrical composition", "cold atmosphere", "minimalist", "architectural background", "centered composition"],
    "Mediterranean Sunlight": ["sunlight", "warm light", "mediterranean", "linen texture", "relaxed atmosphere"],
    "Gothic Candle Velvet": ["gothic", "candlelight", "dark atmosphere", "velvet", "romantic darkness"],
    "Fashion Editorial Studio Cinema": ["fashion editorial", "studio lighting", "magazine cover", "polished", "high fashion"],
    "Black & White Classic": ["monochrome", "black and white", "grayscale", "classic film", "high contrast"],
    "Golden Hour Glow": ["golden hour", "warm light", "backlight", "soft glow", "sunset lighting"],
    "Vintage Film Look": ["vintage film", "analog film", "film grain", "halation", "faded colors", "soft vignette"],
    "Cyberpunk Neon": ["cyberpunk", "neon lights", "glowing signs", "futuristic", "night city"],
    "Soft Romantic Glow": ["soft glow", "romantic atmosphere", "gentle lighting", "warm pink tones", "dreamy"],
    "High-key Clean Light": ["high key lighting", "bright lighting", "clean background", "soft shadows", "airy atmosphere"],
    "Dark Fantasy Shadow Mass": ["dark fantasy", "deep shadows", "mist", "gothic atmosphere", "ominous lighting"],
}
for _style_name, _aliases in STYLE_TAG_ALIASES_ANIMA_REFINEMENT_2026_06_23.items():
    if _style_name not in STYLE_TAG_ALIASES_2026_05_31_C:
        STYLE_TAG_ALIASES_2026_05_31_C[_style_name] = list(_aliases)

def _style_tag_alias_insert(style_name: str, model_profile: str, weight: float = 1.18) -> str:
    if _model_family(model_profile) not in ("tag", "mixed"):
        return ""
    key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    aliases = STYLE_TAG_ALIASES_2026_05_31_C.get(key, [])
    if not aliases:
        return ""
    return _style_tag_insert_from_raw([_join_comma(aliases)], weight=weight)


# Anima mixed models are tag-sensitive, but some visual-media styles become
# unstable when the general style data contains scene-specific wording such as
# room/window cues.  This layer is intentionally Anima-only: it does not alter
# Z-Image, Qwen, Flux, or other natural-language profiles.
ANIMA_STYLE_LAYER_2026_06_25: Dict[str, Dict[str, Any]] = {
    "Dream Pastel Diffusion": {
        "tags": ["pastel anime illustration", "dreamy pastel", "soft colors", "luminous haze", "powdery glow"],
        "assist": "Render with a dreamy pastel anime illustration look, soft colors, luminous haze, and powdery diffusion.",
    },
    "Watercolor / Painterly": {
        "tags": ["anime watercolor illustration", "watercolor", "transparent washes", "pigment bloom", "paper texture"],
        "assist": "Render as a watercolor anime illustration on textured paper with transparent washes and soft pigment blooms.",
    },
    "Oil Painting": {
        "tags": ["anime oil painting", "oil painting", "painterly", "visible brushstrokes", "canvas texture"],
        "assist": "Render as an anime oil painting with visible brushstrokes, layered paint, and canvas texture.",
    },
    "Charcoal Drawing": {
        "tags": ["anime charcoal drawing", "charcoal drawing", "monochrome", "smudged shading", "paper texture"],
        "assist": "Render as a charcoal anime drawing on paper with bold strokes, dark smudges, and monochrome shading.",
    },
    "Graphite Pencil Sketch": {
        "tags": ["anime pencil sketch", "graphite sketch", "pencil drawing", "fine lineart", "cross-hatching", "monochrome"],
        "assist": "Render as an anime graphite pencil sketch with fine line art, soft graphite shading, and paper texture.",
    },
    "Pen and Ink Sketch": {
        "tags": ["anime ink drawing", "pen and ink", "ink lineart", "crosshatching", "monochrome"],
        "assist": "Render as a pen-and-ink anime drawing with clear ink lines, hatching, and white paper contrast.",
    },
    "Ink Wash / Sumi-e": {
        "tags": ["anime ink wash", "sumi-e", "ink wash", "brush strokes", "rice paper"],
        "assist": "Render as an anime ink-wash illustration with diluted black ink, brush flow, and paper grain.",
    },
    "Colored Pencil Illustration": {
        "tags": ["anime colored pencil illustration", "colored pencil", "pencil strokes", "paper texture", "hand-drawn"],
        "assist": "Render as a colored-pencil anime illustration on textured paper with visible pencil strokes.",
    },
    "Pastel Chalk Drawing": {
        "tags": ["pastel anime illustration", "pastel drawing", "soft pastel", "chalk texture", "paper texture"],
        "assist": "Render as a pastel anime illustration with soft chalk texture, gentle color, and textured paper.",
    },
    "Gouache Storybook Illustration": {
        "tags": ["anime gouache illustration", "gouache", "storybook illustration", "matte paint", "painted paper"],
        "assist": "Render as a gouache anime storybook illustration with matte paint blocks and visible brush texture.",
    },
    "Hand-Painted Storybook Animation": {
        "tags": ["hand-painted anime frame", "storybook animation", "painted animation background", "traditional animation", "painted brush texture"],
        "assist": "Render as a hand-painted anime storybook animation frame with painted background texture and warm illustrated staging.",
    },
    "Clean Cel Animation": {
        "tags": ["clean anime cel animation", "cel shading", "clean lineart", "flat colors", "crisp shadow shapes"],
        "assist": "Render as clean anime cel animation with crisp line art, flat color fills, and simple cel-shaded shadows.",
    },
    "3D Collectible Figure": {
        "tags": ["3d anime figure", "anime figurine", "PVC figure", "painted plastic", "display base", "toy photography"],
        "assist": "Render as a 3D anime collectible figure with figure-like depth, painted plastic material, and display-base presentation.",
    },
    "Cinematic Widescreen Scope": {
        "tags": ["anime cinematic frame", "widescreen composition", "cinematic lighting", "filmic color grading", "wide shot"],
        "assist": "Render as a cinematic anime widescreen frame with filmic color grading and broad scene composition.",
    },
    "Black & White Classic": {
        "tags": ["black and white anime", "monochrome", "grayscale", "classic contrast", "tonal shading"],
        "assist": "Render as a black-and-white anime illustration with classic monochrome contrast and tonal shading.",
    },
    "Vintage Film Look": {
        "tags": ["vintage anime film still", "analog film", "film grain", "halation", "faded colors"],
        "assist": "Render as a vintage anime film still with analog grain, soft halation, and faded color response.",
    },
}

_ANIMA_LEADING_QUALITY_RE = re.compile(
    r"(?i)^\s*(?:masterpiece|best\s+quality|score[_\s-]*[0-9]+|safe|rating[_\s-]*safe|highres|absurdres)\s*[,.;]*\s*"
)

_ANIMA_SOURCE_STYLE_CLAUSE_RE = re.compile(
    r"(?i)\b(?:in\s+the\s+style\s+of|style\s+of)\s+[^,.;:]+[,.;:]?\s*"
)


def _is_anima_mixed_profile(model_profile: Any) -> bool:
    return _model_key(str(model_profile or "")) == "anima" and _model_family(str(model_profile or "")) == "mixed"


def _anima_style_layer_for(bp: "Blueprint") -> Dict[str, Any]:
    if not _is_anima_mixed_profile(bp.model_profile):
        return {}
    if _is_default_style(bp) or _is_custom_text_only(bp):
        return {}
    style_key = _canonical_ui_value(bp.style_name, "style_dna") or _clean_text(bp.style_name)
    return ANIMA_STYLE_LAYER_2026_06_25.get(style_key, {})


def _anima_style_quality(model_profile: str, adult_tone: str = "default") -> str:
    # Keep the familiar Anima rating/quality lead, but do not include highres or
    # absurdres for media/style conversion prompts because they pull back toward
    # polished high-resolution 2D anime and can weaken nonstandard media styles.
    kept: List[str] = []
    for tag in _split_prompt_tags(_tag_quality_for_model(model_profile, adult_tone)):
        key = _normalize_tag_identity(tag).lower()
        if key in {"highres", "absurdres"}:
            continue
        kept.append(tag)
    return _join_unique_tags(kept)


def _anima_external_prompt_for_style(external_prompt: Any) -> str:
    s = _clean_text(external_prompt)
    if not s:
        return ""
    # Remove only a duplicated leading Anima quality/rating preamble and common
    # source-style artist clauses. Do not infer subject count, translate, tagify,
    # or summarize the user's prompt.
    prev = None
    while s and s != prev:
        prev = s
        s = _ANIMA_LEADING_QUALITY_RE.sub("", s).strip()
    s = _ANIMA_SOURCE_STYLE_CLAUSE_RE.sub("", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s+([,.])", r"\1", s)
    s = re.sub(r"([,.])(?=[A-Za-z])", r"\1 ", s)
    return s.strip(" ,.;")


def _anima_style_layer_tag_insert(layer: Dict[str, Any], weight: float = 1.25) -> str:
    tags = [_clean_text(t) for t in layer.get("tags", []) if _clean_text(t)]
    if not tags:
        return ""
    weighted: List[str] = []
    for i, tag in enumerate(tags):
        weighted.append(_weighted_tag_token(tag, weight if i == 0 else max(1.08, weight - 0.06)))
    return _join_unique_tags(weighted)


ANIMA_COMPACT_ASSIST_OVERRIDES_2026_06_24: Dict[str, str] = {
    "Neon Melancholy / Rain Glass": "Rainy-night neon mood through wet glass, cyan-magenta glow, reflections, urban melancholy.",
    "Volumetric Dust Light": "Volumetric dust light, visible light rays, floating particles, hazy atmosphere.",
    "Long Exposure Light Trails": "Long-exposure light trails, glowing motion streaks, night-city energy.",
    "Miniature Diorama": "Render the whole scene as a tabletop miniature diorama.",
    "3D Collectible Figure": "Render the scene as stylized 3D collectible figures with toy-like material.",
    "Pixel Art": "Render the scene as clear pixel art with visible pixels and a limited palette.",
    "Watercolor / Painterly": "Render as a watercolor illustration with soft washes and paper texture.",
    "Graphite Pencil Sketch": "Render as a graphite pencil illustration with fine line art and soft shading.",
    "Pastel Chalk Drawing": "Render as a pastel illustration with soft color and delicate paper texture.",
    "Oil Painting": "Render as an oil painting with painterly brushstrokes and canvas texture.",
    "Charcoal Drawing": "Render as a charcoal drawing with bold strokes and smudged shading.",
    "Colored Pencil Illustration": "Render as a colored-pencil illustration with visible pencil strokes and paper texture.",
    "Hand-Painted Storybook Animation": "Render as a hand-painted storybook animation frame.",
    "Gouache Storybook Illustration": "Render as a gouache storybook illustration with matte painted color blocks.",
    "Black & White Classic": "Render as a black-and-white illustration with strong monochrome contrast.",
    "Vintage Film Look": "Render with a vintage film look, soft grain, and faded analog color.",
    "Clean Cel Animation": "Render as clean cel animation with crisp line art and flat color shading.",
    "Dream Pastel Diffusion": "Render with dreamy pastel color, soft glow, and luminous haze.",
    "Apocalyptic Wasteland": "Render with a clear post-apocalyptic wasteland atmosphere.",
}


def _compact_assist_sentence(text: Any) -> str:
    s = _clean_text(text)
    if not s:
        return ""
    s = re.split(r'(?i)do not', s, maxsplit=1)[0].strip()
    s = re.split(r'(?<=[.!?])\s+', s, maxsplit=1)[0].strip()
    return _sentence(s) if s else ""


def _anima_compact_assist_for(bp: "Blueprint", layer: Optional[Dict[str, Any]] = None) -> str:
    style_key = _canonical_ui_value(bp.style_name, "style_dna") or _clean_text(bp.style_name)
    if style_key in ANIMA_COMPACT_ASSIST_OVERRIDES_2026_06_24:
        return _clean_text(ANIMA_COMPACT_ASSIST_OVERRIDES_2026_06_24[style_key])
    if layer:
        assist = _compact_assist_sentence(layer.get("assist", ""))
        if assist:
            return assist
    directive = _compact_assist_sentence(_style_specific_directive(style_key, bp.style_strength))
    return directive


def _render_anima_style_layer_prompt(
    bp: "Blueprint",
    external_prompt: str = "",
    *,
    style_first: bool = True,
    style_only: bool = False,
    style: Optional[Dict[str, Any]] = None,
) -> str:
    if not _is_anima_mixed_profile(bp.model_profile):
        return ""
    if _is_default_style(bp) or _is_custom_text_only(bp):
        return ""
    layer = _anima_style_layer_for(bp)
    strength = PromptStylerCore._external_strength_settings(bp.style_strength)
    quality = _anima_style_quality(bp.model_profile, bp.adult_tone)
    style = style or PromptStylerCore.external_style_parts(bp)
    style_tags = _anima_style_layer_tag_insert(layer, weight=float(strength["weight"])) if layer else (_style_tag_alias_insert(str(bp.style_name or ""), bp.model_profile, weight=float(strength["weight"])) or _clean_text(style.get("tag_insert", "")))
    tag_block = _join_unique_tags([quality, style_tags])
    if not tag_block:
        return ""
    assist = _anima_compact_assist_for(bp, layer)
    if style_only:
        return _append_sentence(tag_block, assist)
    external = _anima_external_prompt_for_style(external_prompt)
    if style_first:
        return _append_sentence(_join_mixed_prompt(tag_block, external), assist)
    return _append_sentence(_append_sentence(external, tag_block), assist)


def _append_sentence(base: str, addition: str) -> str:
    base = _clean_text(base)
    addition = _clean_text(addition)
    if not base:
        return addition
    if not addition:
        return base
    if base[-1] in ".!?":
        return f"{base} {addition}"
    return f"{base}. {addition}"


def _natural_dedupe_key(text: Any) -> str:
    s = _clean_text(text).lower()
    s = re.sub(r"[\(\)\[\]{}]+", " ", s)
    s = re.sub(r"[^\w]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def _natural_text_contains_full_phrase(text: Any, phrase: Any) -> bool:
    phrase_key = _natural_dedupe_key(phrase)
    if not phrase_key:
        return False

    words = re.findall(r"\w+", phrase_key, flags=re.UNICODE)
    if not words:
        return False
    if len(words) == 1 and len(words[0]) < 3:
        return False

    text_key = _natural_dedupe_key(text)
    if not text_key:
        return False
    return f" {phrase_key} " in f" {text_key} "


def _omit_natural_custom_if_already_external(natural_insert: str, external_prompt: str, custom_note: str) -> str:
    natural = _clean_text(natural_insert)
    custom = _clean_text(custom_note)
    if not natural or not custom or not _natural_text_contains_full_phrase(external_prompt, custom):
        return natural
    custom_sentence = _sentence(custom)
    if not custom_sentence:
        return natural
    updated = re.sub(
        r"(^|\s+)" + re.escape(custom_sentence) + r"(?=\s|$)",
        lambda m: "" if not m.group(1) else " ",
        natural,
        count=1,
    )
    return _clean_text(updated)


def _sentence(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else text + "."


def _natural_list(items: List[Any]) -> str:
    vals = _unique([_clean_text(x) for x in items if _clean_text(x)])
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    if len(vals) == 2:
        return f"{vals[0]} and {vals[1]}"
    return ", ".join(vals[:-1]) + ", and " + vals[-1]


def _natural_direction_phrase(text: Any) -> str:
    """Make tone fragments fit natural sentence wrappers without changing tag prompts."""
    s = _clean_text(text)
    if not s:
        return ""
    s = re.sub(r"\badult\s+mood\b", "adult", s, flags=re.IGNORECASE)
    s = re.sub(r"\bmood\b", "", s, flags=re.IGNORECASE)
    return _normalize_text(s)


def _natural_camera_instruction(camera_terms: List[Any]) -> str:
    terms = _natural_list(camera_terms)
    if not terms:
        return ""


    return _sentence(f"Use {terms} for visual framing")


def _article_for_phrase(phrase: str) -> str:
    s = _clean_text(phrase).lower()
    return "an" if s.startswith(("a", "e", "i", "o", "u", "nsfw")) else "a"


def _natural_style_sentence(
    *,
    wardrobe_note: str = "",
    scene_framing_note: str = "",
    custom_note: str = "",
    adult_natural: List[str] = None,
    emotion: List[str] = None,
    anchor: str = "",
    lighting: List[str] = None,
    color: List[str] = None,
    composition: List[str] = None,
    texture: List[str] = None,
    camera: List[str] = None,
    qwen_structured: bool = False,
    flux_structured: bool = False,
) -> str:
    """Build natural-language style instructions, never weighted/tag-style tokens."""
    adult_natural = adult_natural or []
    emotion = emotion or []
    lighting = lighting or []
    color = color or []
    composition = composition or []
    texture = texture or []
    camera = camera or []

    sentences: List[str] = []
    wardrobe_note = _clean_text(wardrobe_note)
    scene_framing_note = _clean_text(scene_framing_note)
    custom_note = _clean_text(custom_note)
    anchor = _clean_text(anchor)

    if wardrobe_note:
        sentences.append(_sentence(f"Use {wardrobe_note} as the adult wardrobe direction"))
    if scene_framing_note:
        sentences.append(_sentence(f"Use {scene_framing_note}"))
    if custom_note:
        sentences.append(_sentence(custom_note))

    adult_mood_terms = [x for x in adult_natural if re.search(r"\btension\b", _clean_text(x), re.IGNORECASE)]
    adult_direction = _natural_list([_natural_direction_phrase(x) for x in adult_natural if x not in adult_mood_terms])
    emotion_terms = _natural_list(adult_mood_terms + emotion)
    visual_terms = _natural_list([anchor] + lighting + color + composition + texture)
    camera_terms = _natural_list(camera)

    if flux_structured:
        if adult_direction:
            sentences.append(_sentence(f"Use a {adult_direction} adult presentation"))
        if emotion_terms and visual_terms:
            sentences.append(_sentence(f"Let the prompt keep a mood of {emotion_terms} while shifting the visual style toward {visual_terms}"))
        elif emotion_terms:
            sentences.append(_sentence(f"Let the prompt keep a mood of {emotion_terms}"))
        elif visual_terms:
            sentences.append(_sentence(f"Shift the visual style toward {visual_terms}"))
        if camera_terms:
            sentences.append(_sentence(f"Use {camera_terms} for visual framing"))
        return " ".join([s for s in sentences if s])

    camera_instruction = _natural_camera_instruction(camera)

    if adult_direction:
        sentences.append(_sentence(f"Keep the presentation in {_article_for_phrase(adult_direction)} {adult_direction} direction"))
    if emotion_terms:
        if qwen_structured:
            sentences.append(_sentence(f"Mood direction: {emotion_terms}"))
        else:
            sentences.append(_sentence(f"Maintain a mood of {emotion_terms}"))
    if visual_terms:
        if qwen_structured:
            sentences.append(_sentence(f"Style direction: {visual_terms}"))
        else:
            sentences.append(_sentence(f"Apply a visual treatment with {visual_terms}"))
    if camera_instruction:
        sentences.append(camera_instruction)

    return " ".join([s for s in sentences if s])


_TRANSFORMATIVE_STYLE_NAMES = {
    "Hand-Painted Storybook Animation",
    "Miniature Diorama",
    "Pixel Art",
    "3D Collectible Figure",
    "Chibi Style",
}

POSITIVE_STYLE_FIRST_NAMES = frozenset(set(_TRANSFORMATIVE_STYLE_NAMES) | {
    "Dream Pastel Diffusion",
    "Watercolor / Painterly",
    "Oil Painting",
    "Charcoal Drawing",
    "Graphite Pencil Sketch",
    "Pen and Ink Sketch",
    "Ink Wash / Sumi-e",
    "Colored Pencil Illustration",
    "Pastel Chalk Drawing",
    "Gouache Storybook Illustration",
})

COMPACT_MEDIUM_STYLE_NAMES = frozenset({
    "Pastel Chalk Drawing",
    "Graphite Pencil Sketch",
    "Charcoal Drawing",
    "Oil Painting",
    "Watercolor / Painterly",
})


def _is_transformative_style_name(style_name: Any) -> bool:
    return str(style_name or "") in _TRANSFORMATIVE_STYLE_NAMES


def _style_application_mode(style_strength: Any) -> str:
    s = str(style_strength or "balanced").strip().lower()
    if s not in {"subtle", "balanced", "strong"}:
        return "balanced"
    return s


_TEXT_MODEL_TERM_REPLACEMENTS: Tuple[Tuple[str, str], ...] = (
    (r"\bneon\s+signage\s+depth\b", "layered neon depth"),
    (r"\bglowing\s+signs\b", "neon glow"),
    (r"\breadable\s+signs\b", "visible sign-shaped forms"),
    (r"\bextra\s+letters\b", "extra marks"),
)


def _natural_insert_safe_for_model(text: Any, model_key: str) -> str:
    """Keep natural-model prompts from accidentally asking for new readable text."""
    s = _clean_text(text)
    if not s:
        return ""
    if model_key in {"zimage", "qwen", "flux"}:
        for pattern, repl in _TEXT_MODEL_TERM_REPLACEMENTS:
            s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    return _clean_text(s)


def _natural_insert_for_model(style: Dict[str, Any], bp: "Blueprint") -> str:
    key = _model_key(bp.model_profile)
    if key == "flux":
        base = style.get("natural_insert_flux", "")
    elif key == "qwen":
        base = style.get("natural_insert_qwen", "")
    else:
        base = style.get("natural_insert", "")
    return _natural_insert_safe_for_model(base, key)



def _style_specific_directive(style_name: Any, mode: str) -> str:
    style = str(style_name or "")
    mode = _style_application_mode(mode)
    if style == 'Chibi Style':
        if mode == 'subtle':
            return 'Render as a cute chibi-style illustration, with slightly oversized heads, compact bodies, simplified facial features, and short simplified limbs when visible.'
        if mode == 'strong':
            return 'Render as a delightful adorable chibi-style illustration. Restyle every visible person with oversized heads, big expressive eyes, soft rosy cheeks, stylized hair, tiny compact bodies, and short simplified limbs when visible. Use clean lineart, rounded simplified anime shapes, vibrant cute colors, and a whimsical feel.'
        return 'Render as a delightful chibi-style illustration. Restyle every visible person with oversized heads, big expressive eyes, soft rosy cheeks, stylized hair, tiny compact bodies, and short simplified limbs when visible.'
    if style == 'Dream Pastel Diffusion':
        if mode == 'subtle':
            return 'Render with a dreamy pastel-diffusion look, using soft pastel color, luminous haze, and gentle pigment bloom.'
        if mode == 'strong':
            return 'Render as a dreamy pastel-diffusion artwork with a powdery pastel palette, milky glow, soft haze, and low-contrast bloom across the image.'
        return 'Render as a dreamy pastel-diffusion artwork with a powdery pastel palette, milky glow, soft haze, and low-contrast bloom across the image.'
    if style == 'Watercolor / Painterly':
        if mode == 'subtle':
            return 'Render as a watercolor painting on textured paper with transparent washes, soft bleeding edges, and visible paper grain.'
        if mode == 'strong':
            return 'Render as a watercolor painting on textured paper with transparent washes, wet bleeding edges, pigment blooms, and visible paper grain.'
        return 'Render as a watercolor painting on textured paper with transparent washes, wet bleeding edges, pigment blooms, and visible paper grain.'
    if style == 'Oil Painting':
        if mode == 'subtle':
            return 'Render as an oil painting on canvas with visible brushstrokes, painterly surface texture, and hand-painted form.'
        if mode == 'strong':
            return 'Render as an oil painting on canvas with thick brushstrokes, layered paint, and visible canvas texture.'
        return 'Render as an oil painting on canvas with thick brushstrokes, layered paint, and visible canvas texture.'
    if style == 'Ink Wash / Sumi-e':
        if mode == 'subtle':
            return 'Render as an ink wash painting with controlled black ink dilution, soft brush flow, and paper texture.'
        if mode == 'strong':
            return 'Render as a clear ink wash / sumi-e painting, with diluted black ink, expressive brush flow, soft wash gradients, absorbent paper texture, and restrained monochrome elegance. Keep the result recognizably ink-wash rather than graphite, charcoal, or photorealistic.'
        return 'Render as an ink wash / sumi-e painting, with diluted black ink, expressive brush flow, soft wash gradients, absorbent paper texture, and restrained monochrome elegance. Keep the result recognizably ink-wash rather than graphite, charcoal, or photorealistic.'
    if style == 'Vintage Film Look':
        if mode == 'subtle':
            return 'Render with a gentle vintage analog film finish, including subtle film grain, lightly faded color response, and a soft nostalgic print feel.'
        if mode == 'strong':
            return 'Render with a pronounced vintage analog film look: visible fine film grain, soft halation around highlights, faded warm color shifts, gentle vignette, low-contrast tonal roll-off, slight emulsion softness, and a clearly aged print finish.'
        return 'Render with a clear vintage analog film look: visible fine film grain, soft halation around highlights, faded warm color shifts, gentle vignette, low-contrast tonal roll-off, slight emulsion softness, and a slightly aged print finish.'
    if style == 'Miniature Diorama':
        if mode == 'subtle':
            return 'Render the scene as a tabletop miniature diorama with a small-scale model-world feel.'
        if mode == 'strong':
            return 'Render the whole scene as a tabletop miniature diorama with tiny scale-model subjects, props, and environment.'
        return 'Render the whole scene as a tabletop miniature diorama with tiny scale-model subjects, props, and environment.'
    if style == 'Gouache Storybook Illustration':
        if mode == 'subtle':
            return 'Render as an opaque gouache picture-book illustration with matte painted color blocks and a calm storybook page feel.'
        if mode == 'strong':
            return 'Render as a clear opaque gouache picture-book illustration with matte paint blocks, visible brush texture, layered gouache pigment, and a static storybook page feel. Do not interpret the result as cel animation.'
        return 'Render as an opaque gouache picture-book illustration with matte paint blocks, visible brush texture, layered gouache pigment, and a static storybook page feel. Do not interpret the result as cel animation.'
    if style == 'Hand-Painted Storybook Animation':
        if mode == 'subtle':
            return 'Render as a hand-painted storybook animation frame with painted background texture and an illustrated animation feel.'
        if mode == 'strong':
            return 'Render as a clear hand-painted 2D storybook animation frame, like a painted keyframe from a traditional illustrated animation. Preserve the storybook warmth, but do not collapse the result into a static gouache page illustration.'
        return 'Render as a hand-painted 2D storybook animation frame, like a painted keyframe from a traditional illustrated animation. Preserve the storybook warmth, but do not collapse the result into a static gouache page illustration.'
    if style == 'Graphite Pencil Sketch':
        if mode == 'subtle':
            return 'Render as a detailed pencil illustration with fine line art, soft graphite shading, and a classic hand-drawn sketch style.'
        if mode == 'strong':
            return 'Render as a detailed pencil illustration with fine line art, soft graphite shading, delicate pencil strokes, precise cross-hatching for depth, rich monochrome texture, and a subtly textured paper background.'
        return 'Render as a detailed pencil illustration with fine line art, soft graphite shading, delicate pencil strokes, precise cross-hatching for depth, and a classic hand-drawn sketch style.'
    if style == 'Pen and Ink Sketch':
        if mode == 'subtle':
            return 'Render as a pen-and-ink drawing with clear ink lines and light hatching.'
        if mode == 'strong':
            return 'Render as a pen-and-ink drawing with clear ink lines, hatching, and white paper contrast.'
        return 'Render as a pen-and-ink drawing with clear ink lines, hatching, and white paper contrast.'
    if style == 'Charcoal Drawing':
        if mode == 'subtle':
            return 'Render as a charcoal drawing on paper with bold broken charcoal strokes, dark smudges, dusty charcoal residue, and rough paper tooth.'
        if mode == 'strong':
            return 'Render as a charcoal drawing on paper with bold broken charcoal strokes, deep dark smudges, dusty charcoal residue, and rough paper tooth.'
        return 'Render as a charcoal drawing on paper with bold broken charcoal strokes, deep dark smudges, dusty charcoal residue, and rough paper tooth.'
    if style == 'Pixel Art':
        if mode == 'subtle':
            return 'Render the subject and scene as pixel art with visible square pixels, blocky edges, and a limited palette.'
        if mode == 'strong':
            return 'Render the subject and scene as clear pixel art with visible square pixels, blocky edges, and a limited palette.'
        return 'Render the subject and scene as clear pixel art with visible square pixels, blocky edges, and a limited palette.'
    if style == '3D Collectible Figure':
        if mode == 'subtle':
            return 'Render the subject as a stylized 3D collectible figure with toy-like material and display-figure form.'
        if mode == 'strong':
            return 'Render the subject as a stylized 3D collectible figure with toy-like material, simplified form, and clean display lighting.'
        return 'Render the subject as a stylized 3D collectible figure with toy-like material, simplified form, and clean display lighting.'
    if style == 'Pastel Chalk Drawing':
        if mode == 'subtle':
            return 'Render as a beautifully detailed pastel drawing with a soft illustrative feel, gentle pastel color, delicate pastel texture, and a warm cozy atmosphere.'
        if mode == 'strong':
            return 'Render as a beautifully detailed pastel illustration with a soft pastel palette, delicate pastel-crayon texture, clean lineart, soft stylized forms, and a whimsical hand-drawn feel on subtly textured paper.'
        return 'Render as a detailed pastel illustration with a soft pastel palette, delicate pastel-crayon texture, clean lineart, and a gentle whimsical feel.'
    if style == 'Colored Pencil Illustration':
        if mode == 'subtle':
            return 'Render as a colored-pencil illustration with visible dry pencil strokes and textured paper.'
        if mode == 'strong':
            return 'Render as a colored-pencil illustration on paper with visible pencil strokes, light hatching, and paper texture.'
        return 'Render as a colored-pencil illustration on paper with visible pencil strokes, light hatching, and paper texture.'
    if style == 'Volumetric Dust Light':
        if mode == 'subtle':
            return 'Emphasize soft volumetric lighting with gentle haze and faint floating dust visible in the light.'
        if mode == 'strong':
            return 'Emphasize strong volumetric lighting, visible shafts of light, floating dust motes dancing in the light rays, hazy atmospheric depth, and cinematic light scattering through the air.'
        return 'Emphasize volumetric lighting, visible shafts of light, floating dust motes in the light rays, hazy atmospheric depth, and cinematic light scattering through the air.'
    if style == 'Classical Studio Glamour':
        if mode == 'subtle':
            return 'Render with a gentle classic studio glamour finish, controlled portrait lighting, and an elegant timeless beauty feel.'
        if mode == 'strong':
            return 'Render as a classic old-Hollywood studio glamour portrait with controlled beauty lighting, butterfly lighting, soft shadow shaping, elegant posture, and a timeless polished editorial feel.'
        return 'Render as a classic old-Hollywood studio glamour portrait with controlled beauty lighting, butterfly lighting, soft shadow shaping, elegant posture, and a timeless polished editorial feel.'
    if style == 'Apocalyptic Wasteland':
        if mode == 'subtle':
            return 'Render with a clear post-apocalyptic wasteland mood, showing worn ruins, dust, and bleak survival atmosphere.'
        if mode == 'strong':
            return 'Render with a severe post-apocalyptic wasteland atmosphere: heavily ruined structures, cracked concrete, rusted debris, ash-filled air, scorched surfaces, abandoned survival-world desolation, and a clearly devastated end-of-civilization mood. Make the world feel deeply wrecked, not merely slightly old or untidy.'
        return 'Render with a strong post-apocalyptic wasteland atmosphere: ruined structures, cracked concrete, rusted debris, ash-filled air, scorched surfaces, abandoned survival-world desolation, and a clearly devastated mood. Make the world feel genuinely ruined, not merely slightly old or untidy.'
    if style == 'Neon Melancholy / Rain Glass':
        if mode == 'subtle':
            return 'Render with a rainy-night neon mood, showing soft colored reflections and urban melancholy through wet glass.'
        if mode == 'strong':
            return 'Render with a strong rainy-night neon mood: magenta and cyan neon glow, blurred urban lights behind raindrops, wet-window reflections, humid haze, and melancholic city light diffused through rain-soaked glass. Do not satisfy the style with plain raindrops alone.'
        return 'Render with a clear rainy-night neon mood: magenta and cyan neon glow, blurred urban lights behind raindrops, wet-window reflections, humid haze, and melancholic city light diffused through rain-soaked glass. Do not satisfy the style with plain raindrops alone.'
    return ''


def _style_specific_preserve_scope(model_key: str, style_name: Any, mode: str) -> Tuple[str, str]:
    style = str(style_name or '')
    mode = _style_application_mode(mode)
    if style == 'Chibi Style':
        if model_key == 'zimage':
            if mode == 'subtle':
                return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, and important scene objects',
                        'Let the chibi style act as a gentle illustrated restyle while keeping the scene coherent')
            if mode == 'strong':
                return ('Preserve the visible subject count, core facial identity, main outfit idea, pose, setting, and important scene details',
                        'Let the chibi style clearly reshape proportions, lineart, color, and overall illustration feel while keeping the full scene coherent')
            return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, and important scene details',
                    'Let the chibi style clearly restyle the people while keeping the surrounding scene readable')
        if model_key == 'qwen':
            if mode == 'subtle':
                return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, and important scene objects',
                        'Change only: apply a gentle chibi illustrated restyle while keeping the scene coherent')
            if mode == 'strong':
                return ('Preserve: visible subject count, core facial identity, main outfit idea, pose, setting, and important scene details',
                        'Change clearly: restyle every visible person into a cute chibi illustration, with reshaped proportions, clean lineart, cute color styling, and a coherent scene')
            return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, and important scene details',
                    'Change clearly: restyle the people in a chibi illustration style while keeping the surrounding scene readable')
        if model_key == 'flux':
            if mode == 'subtle':
                return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, and important scene objects',
                        'Apply only a gentle chibi illustrated restyle while keeping the scene coherent')
            if mode == 'strong':
                return ('Keep the visible subject count, core facial identity, main outfit idea, pose, setting, and important scene details',
                        'Let the chibi style clearly reshape proportions, lineart, color, and overall illustration feel while keeping the full scene coherent')
            return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, and important scene details',
                    'Restyle the people in a chibi illustration style while keeping the surrounding scene readable')
        return ('', '')
    if style == 'Pastel Chalk Drawing':
        if model_key == 'zimage':
            if mode == 'subtle':
                return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Let the scene become a gentle pastel illustration while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Preserve the visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Restyle the full image as a coherent pastel illustration with soft stylization, while keeping the full scene readable')
            return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Restyle the full image as a pastel illustration while keeping the surrounding scene coherent')
        if model_key == 'qwen':
            if mode == 'subtle':
                return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Change only: turn the image into a gentle pastel illustration while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Preserve: visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Change clearly: restyle the full image as a coherent pastel illustration with soft stylization, while keeping the full scene readable')
            return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Change clearly: restyle the full image as a pastel illustration while keeping the surrounding scene coherent')
        if model_key == 'flux':
            if mode == 'subtle':
                return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Apply a gentle pastel illustration treatment while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Keep the visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Restyle the full image as a coherent pastel illustration with soft stylization, while keeping the full scene readable')
            return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Restyle the full image as a pastel illustration while keeping the surrounding scene coherent')
        return ('', '')
    if style == 'Graphite Pencil Sketch':
        if model_key == 'zimage':
            if mode == 'subtle':
                return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Let the scene become a clean pencil illustration while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Preserve the visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Restyle the full image as a coherent graphite pencil illustration with fine line art and readable background detail')
            return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Restyle the full image as a pencil illustration while keeping the surrounding scene coherent')
        if model_key == 'qwen':
            if mode == 'subtle':
                return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Change only: turn the image into a clean pencil illustration while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Preserve: visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Change clearly: restyle the full image as a coherent graphite pencil illustration with fine line art and readable background detail')
            return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Change clearly: restyle the full image as a pencil illustration while keeping the surrounding scene coherent')
        if model_key == 'flux':
            if mode == 'subtle':
                return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Apply a gentle pencil illustration treatment while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Keep the visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Restyle the full image as a coherent graphite pencil illustration with fine line art and readable background detail')
            return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Restyle the full image as a pencil illustration while keeping the surrounding scene coherent')
        return ('', '')
    if style in {'Charcoal Drawing', 'Oil Painting', 'Watercolor / Painterly'}:
        if model_key == 'zimage':
            return ('Preserve the core subject, pose, and scene idea', '')
        if model_key == 'qwen':
            return ('Preserve: core subject, pose, and scene idea', '')
        if model_key == 'flux':
            return ('Keep the core subject, pose, and scene idea', '')
        return ('', '')
    if style == 'Pixel Art':
        if model_key == 'zimage':
            return ('Preserve the core subject and scene idea',
                    'Render the subject and scene as pixel art with visible square pixels and a limited palette')
        if model_key == 'qwen':
            return ('Preserve: core subject and scene idea',
                    'Change clearly: render the subject and scene as pixel art with visible square pixels and a limited palette')
        if model_key == 'flux':
            return ('Keep the core subject and scene idea',
                    'Render the subject and scene as pixel art with visible square pixels and a limited palette')
        return ('', '')
    if style == '3D Collectible Figure':
        if model_key == 'zimage':
            return ('Preserve the core subject and scene idea',
                    'Render the subject as a stylized 3D collectible figure with toy-like material')
        if model_key == 'qwen':
            return ('Preserve: core subject and scene idea',
                    'Change clearly: render the subject as a stylized 3D collectible figure with toy-like material')
        if model_key == 'flux':
            return ('Keep the core subject and scene idea',
                    'Render the subject as a stylized 3D collectible figure with toy-like material')
        return ('', '')
    if style == 'Miniature Diorama':
        if model_key == 'zimage':
            return ('Preserve the core subject and scene idea',
                    'Render the whole scene as a tabletop miniature diorama')
        if model_key == 'qwen':
            return ('Preserve: core subject and scene idea',
                    'Change clearly: render the whole scene as a tabletop miniature diorama')
        if model_key == 'flux':
            return ('Keep the core subject and scene idea',
                    'Render the whole scene as a tabletop miniature diorama')
        return ('', '')
    return ('', '')

def _wrap_model_specific_natural_insert(insert: str, bp: "Blueprint", *, has_external: bool) -> str:
    insert = _clean_text(insert)
    if not insert:
        return ""
    if not has_external:
        return insert

    model_key = _model_key(bp.model_profile)
    mode = _style_application_mode(bp.style_strength)
    transformative = _is_transformative_style_name(bp.style_name)

    if model_key == "zimage":
        override_preserve, override_scope = _style_specific_preserve_scope(model_key, bp.style_name, mode)
        special_directive = _style_specific_directive(bp.style_name, mode)
        if override_preserve:
            preserve = override_preserve
            scope = override_scope
        elif mode == "subtle":
            preserve = "Keep the original subject, pose, outfit, setting, scene layout, and listed objects as close as possible to the source prompt"
            scope = "Let the selected style act as a gentle visual layer"
        elif mode == "strong" and transformative:
            preserve = "Preserve the core subject identity, main outfit idea, and overall scene intent"
            scope = "Allow the selected style to reshape the final visual presentation more clearly"
        elif mode == "strong":
            preserve = "Keep the original subject, pose, outfit, setting, scene layout, and listed objects recognizable"
            scope = "Let the selected style take clear priority in lighting, color, texture, and presentation"
        else:
            preserve = "Keep the original subject, pose, outfit, setting, scene layout, and listed objects unchanged"
            scope = ""
        if str(bp.style_name or "") == 'Vintage Film Look' and not scope:
            scope = "Let the selected style clearly shape the analog film finish, color response, grain, and nostalgic print character"
        text_guard = "No extra text, logos, or unrelated objects" if str(bp.style_name or "") in COMPACT_MEDIUM_STYLE_NAMES else "Do not add extra readable text, logos, signs, or unrelated objects unless the original prompt explicitly asks for them"
        parts = [_sentence(preserve)]
        if scope:
            parts.append(_sentence(scope))
        if special_directive:
            parts.append(_sentence(special_directive))
        parts.extend([insert, _sentence(text_guard)])
        return " ".join(parts)

    if model_key == "qwen":
        override_preserve, override_change = _style_specific_preserve_scope(model_key, bp.style_name, mode)
        special_directive = _style_specific_directive(bp.style_name, mode)
        if override_preserve:
            preserve = override_preserve
            change = override_change
        elif mode == "subtle":
            preserve = "Preserve: subject identity, clothing, pose, setting, composition, and listed objects as closely as possible"
            change = "Change only: visual style, lighting mood, color tone, surface texture, and any requested framing, with a gentle touch"
        elif mode == "strong" and transformative:
            preserve = "Preserve: core subject identity, main outfit idea, and overall scene intent"
            change = "Change more freely: visual style, rendering method, lighting mood, color tone, surface texture, and framing so the selected style can lead"
        elif mode == "strong":
            preserve = "Preserve: subject identity, clothing, pose, setting, composition, and listed objects in a recognizable way"
            change = "Change more freely: visual style, lighting mood, color tone, surface texture, and any requested framing so the selected style can lead"
        else:
            preserve = "Preserve: subject identity, clothing, pose, setting, composition, and listed objects"
            change = "Change only: visual style, lighting mood, color tone, surface texture, and any requested framing"
        if str(bp.style_name or "") == 'Vintage Film Look' and mode == 'balanced':
            change = "Change clearly: visual style, analog film finish, color response, grain, and nostalgic print character while keeping the scene recognizable"
        parts = [_sentence(preserve), _sentence(change)]
        if special_directive:
            parts.append(_sentence(special_directive))
        parts.append(insert)
        return " ".join(parts)

    if model_key == "flux":
        override_preserve, override_scope = _style_specific_preserve_scope(model_key, bp.style_name, mode)
        special_directive = _style_specific_directive(bp.style_name, mode)
        if override_preserve:
            preserve = override_preserve
            scope = override_scope
        elif mode == "subtle":
            preserve = "Keep the same subject, outfit, pose, setting, composition, and listed objects as closely as possible"
            scope = "Let the selected style work gently through lighting, color, texture, and presentation"
        elif mode == "strong" and transformative:
            preserve = "Keep the core subject identity and overall scene intent"
            scope = "Allow the selected style to more strongly reshape the final visual presentation through rendering, lighting, color, texture, and framing"
        elif mode == "strong":
            preserve = "Keep the same subject, outfit, pose, setting, composition, and listed objects recognizable"
            scope = "Let the selected style take clear priority through lighting, color, texture, and presentation"
        else:
            preserve = "Keep the same subject, outfit, pose, setting, composition, and listed objects"
            scope = "Only shift the visual presentation through the selected style, lighting mood, color tone, and texture"
        if str(bp.style_name or "") == 'Vintage Film Look' and mode == 'balanced':
            scope = "Let the selected style clearly shape the analog film finish, color response, grain, and nostalgic print character"
        parts = [_sentence(preserve), _sentence(scope)]
        if special_directive:
            parts.append(_sentence(special_directive))
        parts.append(insert)
        return " ".join(parts)

    return insert


def _sanitize_prompt_output(text: Any, family: str = "") -> str:
    s = str(text or "")
    s = re.sub(r",\s*,+", ", ", s)
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s*\.", ".", s)
    if family in ("tag", "mixed"):
        s = re.sub(r"\.\s*,", ". ", s)
    else:
        s = re.sub(r"\.\s*,", ".", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.strip(" ,")


def _seed_value(seed: int) -> int:
    try:
        return int(seed)
    except Exception:
        return 0


FULL_BODY_FRAMING_KEYS = {
    "full body (head to toe)",
    "full shot (full body + extra space)",
    "wide shot",
    "seated full body",
}


def _is_full_body_or_wide_framing(scene_framing: str) -> bool:
    return _canonical_ui_value(scene_framing, "scene_framing") in FULL_BODY_FRAMING_KEYS


def _auto_lens(style_name: str, mood_family: str, scene_framing: str = "auto") -> str:

    if _is_camera_suppressed_context(style_name, mood_family):
        return "auto"

    if _is_full_body_or_wide_framing(scene_framing):
        if mood_family in ("Cinematic Widescreen",):
            return "anamorphic widescreen"
        if scene_framing == "wide shot":
            return "24mm wide cinematic"
        return "35mm environmental"
    if style_name in ("Classical Studio Glamour", "Swedish Face Silence", "Fashion Editorial Studio Cinema"):
        return "85mm portrait shallow DOF"
    if style_name in ("Symmetric Psychological Coldness",):
        return "wide architectural"
    if style_name in ("Cyberpunk Neon",):
        return "35mm environmental"
    if style_name in ("Vintage Film Look", "Black & White Classic"):
        return "58mm vintage character"
    if style_name in ("Dark Fantasy Shadow Mass",) or mood_family in ("Horror / Unsettling", "Dark Fantasy Romance"):
        return "low angle dramatic"
    if mood_family in ("Cinematic Widescreen",):
        return "anamorphic widescreen"
    if mood_family in ("Arthouse Realism", "Lyrical / Poetic", "Romantic / Soft Focus"):
        return "40mm cinematic natural"
    if mood_family in ("Noir / Neo-noir", "Pop Neon", "Cyberpunk / Sci-fi"):
        return "35mm environmental"
    if mood_family in ("Vintage / Retro",):
        return "58mm vintage character"
    return "50mm intimate natural"


def _harmonize_camera_terms_for_framing(camera_terms: List[str], scene_framing: str) -> List[str]:
    if not _is_full_body_or_wide_framing(scene_framing):
        return camera_terms
    blocked = {
        "close framing",
        "close detail framing",
        "tight compressed framing",
    }
    out = []
    for term in camera_terms:
        cleaned = _clean_text(term)
        if cleaned.lower() in blocked:
            continue
        if "macro" in cleaned.lower() and "detail" in cleaned.lower():
            continue
        out.append(cleaned)
    return out or ["natural full-body perspective"]


def _scene_terms_need_full_body(scene_terms: List[str]) -> bool:
    joined = " ".join(_clean_text(x).lower() for x in scene_terms)
    return any(key in joined for key in ("full body", "full shot", "wide shot", "head-to-toe", "full figure"))


CLOSE_STYLE_FRAMING_PATTERN = re.compile(
    r"\b(close|tight|headshot|face-focused|macro)\b[^\n]{0,180}?\b(framing|shot|detail)\b|\bportrait framing\b|\bclose-up\b",
    re.IGNORECASE,
)


def _harmonize_style_terms_for_framing(parts: List[str], scene_terms: List[str]) -> List[str]:
    if not _scene_terms_need_full_body(scene_terms):
        return parts
    out = []
    for part in parts:
        cleaned = _clean_text(part)
        if not cleaned or CLOSE_STYLE_FRAMING_PATTERN.search(cleaned):
            continue
        out.append(cleaned)
    return out


@dataclass
class Blueprint:
    model_profile: str
    mood_family: str
    style_name: str
    style_strength: str
    adult_tone: str
    adult_wardrobe: str
    scene_framing: List[str]
    lens_preset: str
    style_anchor: str
    emotion: List[str]
    lighting: List[str]
    color: List[str]
    composition: List[str]
    texture: List[str]
    camera: List[str]
    custom_notes: str
    negative: str


def _is_default_style(bp: "Blueprint") -> bool:
    """Return True when all style-affecting options are at their defaults.

    When the user has not chosen any specific mood, style, tone, wardrobe,
    framing, lens, or custom text, the node should not inject opinionated
    style cues that could override the model's or external prompt's own style.
    """
    return (
        bp.mood_family == "Default / None"
        and bp.style_name in ("Auto by Mood", "Neutral / Minimal Carryover")
        and bp.adult_tone in ("default", "safe", "")
        and not bp.adult_wardrobe
        and not bp.scene_framing
        and bp.lens_preset in ("auto", "")
        and not bp.custom_notes
    )


def _is_custom_text_only(bp: "Blueprint") -> bool:
    """Return True when only the freeform custom text is active.

    In this case, preserve the user's note without adding neutral camera/color
    boilerplate such as balanced color or 50mm medium shot.
    """
    return (
        bp.mood_family == "Default / None"
        and bp.style_name in ("Auto by Mood", "Neutral / Minimal Carryover")
        and bp.adult_tone in ("default", "safe", "")
        and not bp.adult_wardrobe
        and not bp.scene_framing
        and bp.lens_preset in ("auto", "")
        and bool(bp.custom_notes)
    )



STYLE_CONFLICT_CLEANUP_MODEL_KEYS: frozenset = frozenset({"zimage", "qwen", "flux"})

# Style-specific external-prompt cleanup.
# This deliberately avoids one broad "non-photo" cleanup pass. A prompt-word is
# only relaxed when the selected style profile says that phrase is specifically
# likely to suppress that style. In particular, standalone "photorealistic" is
# not globally removed, because it can be intentional for figure, miniature,
# vintage-photo, and hybrid prompts.
STYLE_CONFLICT_PROFILE_GROUPS: Dict[str, frozenset] = {
    "traditional_media": frozenset({
        "Watercolor / Painterly", "Oil Painting", "Charcoal Drawing", "Graphite Pencil Sketch",
        "Pen and Ink Sketch", "Ink Wash / Sumi-e", "Colored Pencil Illustration",
        "Pastel Chalk Drawing", "Gouache Storybook Illustration", "Hand-Painted Storybook Animation",
    }),
    "cel_animation": frozenset({"Clean Cel Animation"}),
    "dream_pastel": frozenset({"Dream Pastel Diffusion", "Soft Romantic Glow"}),
    "pixel_art": frozenset({"Pixel Art"}),
    "miniature": frozenset({"Miniature Diorama"}),
    "collectible_3d": frozenset({"3D Collectible Figure"}),
    "chibi": frozenset({"Chibi Style"}),
    "vintage_film": frozenset({"Vintage Film Look"}),
    "black_white": frozenset({"Black & White Classic"}),
    "noir": frozenset({"Noir Chiaroscuro"}),
    "light_trails": frozenset({"Long Exposure Light Trails"}),
    "volumetric_dust": frozenset({"Volumetric Dust Light"}),
    "apocalyptic": frozenset({"Apocalyptic Wasteland", "Dark Fantasy Shadow Mass"}),
}

STYLE_CONFLICT_STYLE_TO_PROFILE: Dict[str, str] = {
    style: profile
    for profile, styles in STYLE_CONFLICT_PROFILE_GROUPS.items()
    for style in styles
}

STYLE_CONFLICT_COMMON_SAFE_REPLACEMENTS: Tuple[Tuple[re.Pattern, str], ...] = (
    # Conservative structural wording cleanup. Keep this narrow: broad terms
    # such as "photorealistic" or "realistic image structure" may be intentional
    # in photo, miniature, figure, vintage-film, or hybrid prompts, so they are
    # handled only by selected style profiles below.
    (re.compile(r"\bfull[-\s]?body\s+character\s+image\b", re.IGNORECASE), "full-body composition"),
)

STYLE_CONFLICT_PROFILE_REPLACEMENTS: Dict[str, Tuple[Tuple[re.Pattern, str], ...]] = {
    "traditional_media": (
        (re.compile(r"\brealistic\s+image\s+composition\b", re.IGNORECASE), "coherent visual composition"),
        (re.compile(r"\b(?:realistic|real[-\s]?world|lifelike)\s+(?:image\s+)?structure\b", re.IGNORECASE), "coherent visual structure"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|photo[-\s]?realism|photographic\s+realism|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:watercolor|painterly|painting|painted|oil|pencil|graphite|charcoal|ink|sumi[-\s]?e|gouache|pastel|illustration|drawing|sketch)(?:\s+(?:rendering|render|look|style|finish|portrait|image))?\b", re.IGNORECASE), "clear hand-rendered subject"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|photo[-\s]?realism|photographic\s+realism|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:rendering|render|look|style|finish|portrait|image)\b", re.IGNORECASE), "clear subject rendering"),
        (re.compile(r"\bDSLR\s+(?:photo|photograph)(?:\s+quality)?\b", re.IGNORECASE), "clear hand-rendered subject quality"),
        (re.compile(r"\b(?:camera|lens)\s+(?:(?:photo|photograph)(?:\s+quality)?|realism|look|quality)\b", re.IGNORECASE), "clear hand-rendered subject quality"),
        (re.compile(r"\brealistic\s+camera\s+lens\s+look\b", re.IGNORECASE), "hand-rendered depth"),
        (re.compile(r"\bhard\s+photographic\s+sharpness\b", re.IGNORECASE), "clear hand-rendered edges"),
        (re.compile(r"\bphotographic\s+depth\s+of\s+field\b", re.IGNORECASE), "painterly depth layering"),
        (re.compile(r"\bnatural\s+facial\s+details?\b|\brealistic\s+facial\s+details?\b", re.IGNORECASE), "clear facial readability"),
        (re.compile(r"\breal(?:istic)?\s+skin\s+texture\b|\bskin\s+pores\b|\bdetailed\s+skin\s+pores\b|\blifelike\s+skin\b", re.IGNORECASE), "clear skin depiction"),
    ),
    "cel_animation": (
        (re.compile(r"\brealistic\s+image\s+composition\b", re.IGNORECASE), "coherent visual composition"),
        (re.compile(r"\b(?:realistic|real[-\s]?world|lifelike)\s+(?:image\s+)?structure\b", re.IGNORECASE), "coherent visual structure"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:anime|animation|animated|cel)(?:\s+(?:rendering|look|style|finish|portrait|image))?\b", re.IGNORECASE), "clean animation rendering"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:rendering|look|style|finish|portrait|image)\b", re.IGNORECASE), "clean animation rendering"),
        (re.compile(r"\breal(?:istic)?\s+skin\s+texture\b|\bskin\s+pores\b", re.IGNORECASE), "clean simplified skin shading"),
        (re.compile(r"\bDSLR\s+(?:(?:photo|photograph)(?:\s+quality)?|quality)\b", re.IGNORECASE), "clean visual quality"),
        (re.compile(r"\bnatural\s+facial\s+details?\b|\brealistic\s+facial\s+details?\b", re.IGNORECASE), "clear animated facial readability"),
    ),
    "dream_pastel": (
        (re.compile(r"\brealistic\s+image\s+composition\b", re.IGNORECASE), "coherent visual composition"),
        (re.compile(r"\b(?:realistic|real[-\s]?world|lifelike)\s+(?:image\s+)?structure\b", re.IGNORECASE), "coherent visual structure"),
        (re.compile(r"\bhard\s+photographic\s+sharpness\b|\bcrisp\s+digital\s+sharpness\b", re.IGNORECASE), "soft diffused clarity"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:rendering|look|style|finish|portrait|image)\b", re.IGNORECASE), "dreamlike subject rendering"),
        (re.compile(r"\bDSLR\s+(?:(?:photo|photograph)(?:\s+quality)?|quality)\b", re.IGNORECASE), "soft luminous quality"),
        (re.compile(r"\breal(?:istic)?\s+skin\s+texture\b|\bskin\s+pores\b", re.IGNORECASE), "soft skin depiction"),
    ),
    "pixel_art": (
        (re.compile(r"\brealistic\s+image\s+composition\b", re.IGNORECASE), "coherent visual composition"),
        (re.compile(r"\b(?:realistic|real[-\s]?world|lifelike)\s+(?:image\s+)?structure\b", re.IGNORECASE), "coherent visual structure"),
        (re.compile(r"\bsmooth\s+gradients?\b", re.IGNORECASE), "limited pixel color steps"),
        (re.compile(r"\banti[-\s]?aliased\s+(?:painting|edges?|rendering)\b", re.IGNORECASE), "crisp pixel edges"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|high[-\s]?resolution|ultra[-\s]?sharp)\s+(?:pixel[-\s]?art|pixelated)(?:\s+(?:rendering|image|look|style))?\b", re.IGNORECASE), "crisp pixel-art rendering"),
        (re.compile(r"\b(?:high[-\s]?resolution|ultra[-\s]?sharp)\s+(?:rendering|image|look|style)\b", re.IGNORECASE), "crisp pixel-art rendering"),
        (re.compile(r"\bDSLR\s+(?:(?:photo|photograph)(?:\s+quality)?|quality)\b", re.IGNORECASE), "readable pixel quality"),
    ),
    "miniature": (
        (re.compile(r"\blife[-\s]?size\s+realism\b|\bordinary\s+full[-\s]?scale\s+scene\b|\bfull[-\s]?scale\s+realism\b", re.IGNORECASE), "miniature scale presentation"),
        (re.compile(r"\breal\s+human\s+skin\s+texture\b|\brealistic\s+skin\s+pores\b", re.IGNORECASE), "tiny crafted surface detail"),
        (re.compile(r"\blive[-\s]?action\s+person\b", re.IGNORECASE), "miniature figure subject"),
    ),
    "collectible_3d": (
        (re.compile(r"\breal\s+human\s+skin\s+texture\b|\brealistic\s+skin\s+pores\b|\bskin\s+pores\b", re.IGNORECASE), "smooth vinyl-like surface"),
        (re.compile(r"\blive[-\s]?action\s+person\b|\bphotorealistic\s+live[-\s]?action\s+person\b", re.IGNORECASE), "stylized collectible figure subject"),
        (re.compile(r"\bordinary\s+portrait\s+realism\b", re.IGNORECASE), "toy-like character presentation"),
    ),
    "chibi": (
        (re.compile(r"\brealistic\s+image\s+composition\b", re.IGNORECASE), "coherent visual composition"),
        (re.compile(r"\b(?:realistic|real[-\s]?world|lifelike)\s+(?:image\s+)?structure\b", re.IGNORECASE), "coherent visual structure"),
        (re.compile(r"\brealistic\s+adult\s+body\s+proportions?\b|\brealistic\s+human\s+proportions?\b|\bordinary\s+realistic\s+limb\s+proportions?\b", re.IGNORECASE), "chibi super-deformed proportions"),
        (re.compile(r"\bnatural\s+anatomy\b|\brealistic\s+anatomy\b", re.IGNORECASE), "simplified cute anatomy"),
        (re.compile(r"\blong\s+realistic\s+legs?\b", re.IGNORECASE), "short cute limbs"),
        (re.compile(r"\bnatural\s+facial\s+details?\b|\brealistic\s+facial\s+details?\b", re.IGNORECASE), "rounded cute facial readability"),
    ),
    "vintage_film": (
        (re.compile(r"\bclean\s+modern\s+digital\s+(?:color\s+grade|look|finish)\b", re.IGNORECASE), "aged analog film color response"),
        (re.compile(r"\b(?:ultra[-\s]?sharp|sterile|crisp)\s+(?:modern\s+)?digital\s+(?:look|image|clarity|finish)\b", re.IGNORECASE), "soft analog film clarity"),
        (re.compile(r"\bplastic\s+HDR\s+crispness\b|\bHDR\s+(?:look|finish|clarity|image)\b", re.IGNORECASE), "gentle film highlight roll-off"),
        (re.compile(r"\bsmartphone\s+(?:photo\s+)?look\b|\bcontemporary\s+smartphone\s+look\b", re.IGNORECASE), "nostalgic analog snapshot look"),
    ),
    "black_white": (
        (re.compile(r"\bvivid\s+rainbow\s+colors?\b|\bbright\s+saturated\s+color\s+palette\b", re.IGNORECASE), "rich grayscale tonal contrast"),
        (re.compile(r"\bcolorful\s+color\s+grading\b", re.IGNORECASE), "classic monochrome tonal grading"),
    ),
    "noir": (
        (re.compile(r"\bflat\s+even\s+lighting\b|\bcheerful\s+pastel\s+lighting\b", re.IGNORECASE), "dramatic chiaroscuro lighting"),
        (re.compile(r"\bbright\s+high[-\s]?key\s+comedy\s+look\b", re.IGNORECASE), "dark noir contrast"),
    ),
    "light_trails": (
        (re.compile(r"\bfrozen\s+static\s+lighting\b|\bno\s+motion\s+trails?\b", re.IGNORECASE), "long-exposure motion light trails"),
        (re.compile(r"\bflat\s+daylight\b", re.IGNORECASE), "night light-trail atmosphere"),
    ),
    "volumetric_dust": (
        (re.compile(r"\bflat\s+clean\s+air\b|\bempty\s+atmosphere\b|\bsterile\s+lighting\b", re.IGNORECASE), "visible dusty volumetric atmosphere"),
        (re.compile(r"\bhard\s+flash\s+look\b", re.IGNORECASE), "soft scattered light through air"),
    ),
    "apocalyptic": (
        (re.compile(r"\bclean\s+luxury\s+mood\b|\bcheerful\s+pristine\s+setting\b|\bpolished\s+fashion\s+editorial\s+atmosphere\b", re.IGNORECASE), "weathered survival atmosphere"),
    ),
}

STYLE_CONFLICT_PROFILE_CAMERA_REPLACEMENTS: Dict[str, Tuple[Tuple[re.Pattern, str], ...]] = {
    "traditional_media": (
        (re.compile(r"\b(?:shallow\s+)?depth\s+of\s+field\b", re.IGNORECASE), "painterly depth layering"),
        (re.compile(r"\bcreamy\s+bokeh\b|\bbokeh\b", re.IGNORECASE), "soft painted background separation"),
        (re.compile(r"\b(?:18|24|28|35|40|50|58|85|100|135)\s*mm\s+lens\b", re.IGNORECASE), "composed hand-rendered framing"),
    ),
    "cel_animation": (
        (re.compile(r"\b(?:shallow\s+)?depth\s+of\s+field\b", re.IGNORECASE), "clear animation depth"),
        (re.compile(r"\bbokeh\b", re.IGNORECASE), "simple background separation"),
    ),
    "dream_pastel": (
        (re.compile(r"\b(?:shallow\s+)?depth\s+of\s+field\b", re.IGNORECASE), "soft diffused depth"),
        (re.compile(r"\bbokeh\b", re.IGNORECASE), "dreamy background glow"),
    ),
    "pixel_art": (
        (re.compile(r"\b(?:shallow\s+)?depth\s+of\s+field\b|\bbokeh\b", re.IGNORECASE), "layered pixel background separation"),
    ),
    "chibi": (
        (re.compile(r"\b(?:shallow\s+)?depth\s+of\s+field\b|\bbokeh\b", re.IGNORECASE), "cute simplified background separation"),
    ),
}


def _style_conflict_cleanup_mode(value: Any) -> str:
    mode = _canonical_ui_value(value, "style_conflict_cleanup").strip().lower()
    return mode if mode in {"off", "soft", "strong"} else "off"


def _style_conflict_profile_for_style(style_name: Any) -> str:
    style_key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    return STYLE_CONFLICT_STYLE_TO_PROFILE.get(style_key, "")


def _is_style_conflict_cleanup_style(style_name: Any) -> bool:
    return bool(_style_conflict_profile_for_style(style_name))


def _should_force_transformative_style_first(bp: "Blueprint", external_prompt_mode: str) -> bool:
    # Respect the explicit UI mode.
    # Earlier builds forced transformative / medium styles into style-first output even
    # when the user selected "Append style after external prompt", which made the
    # Korean UI label "원본 뒤에 스타일 문구 추가" behave like prepend mode.
    return False


def _should_cleanup_external_prompt(bp: "Blueprint", cleanup_mode: Any, external_prompt_mode: str = "") -> bool:
    mode = _style_conflict_cleanup_mode(cleanup_mode)
    if mode == "off":
        return False
    if external_prompt_mode == "Output style only":
        return False
    if _model_family(bp.model_profile) != "natural":
        return False
    if _model_key(bp.model_profile) not in STYLE_CONFLICT_CLEANUP_MODEL_KEYS:
        return False
    if _is_default_style(bp) or _is_custom_text_only(bp):
        return False
    return _is_style_conflict_cleanup_style(bp.style_name)


def _apply_style_conflict_replacements(text: str, replacements: Tuple[Tuple[re.Pattern, str], ...]) -> str:
    out = text
    for pattern, repl in replacements:
        out = pattern.sub(repl, out)
    return out


def _cleanup_relaxed_external_prompt_text(text: Any) -> str:
    s = _clean_text(text)
    if not s:
        return ""
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s*,+", ", ", s)
    s = re.sub(r"(?:^|(?<=[,.]))\s*,+", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s+([,.])", r"\1", s)
    s = re.sub(r"(?:,\s*){2,}", ", ", s)
    s = re.sub(r"\.\s*,", ".", s)
    # Collapse exact duplicate neutral replacement fragments that can be created
    # when several style-profile phrases appear back-to-back in the external prompt.
    for phrase in (
        "full-body composition",
        "coherent visual structure",
        "coherent visual composition",
        "clear facial readability",
        "clear subject rendering",
        "clear hand-rendered subject quality",
        "clear hand-rendered subject quality quality",
        "hand-rendered depth",
        "painterly depth layering",
        "soft painted background separation",
        "clean animation rendering",
        "clean visual quality",
        "clear animated facial readability",
        "dreamlike subject rendering",
        "soft luminous quality",
        "crisp pixel-art rendering",
        "miniature scale presentation",
        "stylized collectible figure subject",
        "chibi super-deformed proportions",
        "simplified cute anatomy",
        "rounded cute facial readability",
        "aged analog film color response",
        "soft analog film clarity",
        "gentle film highlight roll-off",
        "nostalgic analog snapshot look",
    ):
        s = re.sub(rf"\b{re.escape(phrase)}\b(?:\s*,\s*\b{re.escape(phrase)}\b)+", phrase, s, flags=re.IGNORECASE)
    s = re.sub(r"\b((?:clear|soft|readable|hand-rendered|luminous|visual|pixel|subject)(?:[-\w]*\s+){0,4}quality)\s+quality\b", r"\1", s, flags=re.IGNORECASE)
    s = re.sub(r"\bquality\s+quality\b", "quality", s, flags=re.IGNORECASE)
    return s.strip(" ,")


def _relax_style_conflicting_external_prompt(text: Any, bp: "Blueprint", cleanup_mode: Any) -> str:
    """Relax only the phrases that conflict with the selected style profile.

    The cleanup is intentionally style-specific: it does not globally remove
    broad terms such as "photorealistic". A phrase is rewritten only when the
    active style profile says that phrase directly suppresses that style.
    """
    mode = _style_conflict_cleanup_mode(cleanup_mode)
    out = _clean_text(text)
    if not out or mode == "off":
        return out

    profile = _style_conflict_profile_for_style(bp.style_name)
    if not profile:
        return out

    out = _apply_style_conflict_replacements(out, STYLE_CONFLICT_COMMON_SAFE_REPLACEMENTS)
    out = _apply_style_conflict_replacements(out, STYLE_CONFLICT_PROFILE_REPLACEMENTS.get(profile, ()))

    # User-selected lens presets should be respected. Only soften explicit camera
    # terms typed into the external prompt when the node lens control is auto.
    if bp.lens_preset in ("", "auto"):
        camera_replacements = STYLE_CONFLICT_PROFILE_CAMERA_REPLACEMENTS.get(profile, ())
        if mode == "strong" or profile in {"traditional_media", "pixel_art", "chibi"}:
            out = _apply_style_conflict_replacements(out, camera_replacements)

    return _cleanup_relaxed_external_prompt_text(out)


EXTERNAL_CAMERA_OR_LIGHTING_CUE_RE = re.compile(
    r"\b\d{2,3}\s*mm\b|"
    r"\b(?:lens|camera|focal\s+length|telephoto|macro\s+lens|portrait\s+lens|"
    r"wide[-\s]angle|anamorphic|depth\s+of\s+field|dof|bokeh)\b|"
    r"\b(?:close[-\s]?up|medium\s+shot|wide\s+shot|full\s+shot|"
    r"low[-\s]angle|high[-\s]angle|overhead\s+shot)\b|"
    r"\b(?:lighting|illumination|rim\s+light|backlight|backlit|soft\s+light|hard\s+light|"
    r"natural\s+light|studio\s+light|golden\s+hour|low[-\s]key|high[-\s]key|neon[-\s]lit|"
    r"candle[-\s]?lit|candle\s*light|candlelight|illuminated\s+by|lit\s+by)\b",
    re.IGNORECASE,
)


def _external_prompt_has_camera_or_lighting_cue(text: Any) -> bool:
    return bool(EXTERNAL_CAMERA_OR_LIGHTING_CUE_RE.search(_normalize_text(text)))


def _should_keep_external_prompt_cues_over_neutral(bp: "Blueprint", external_prompt: Any) -> bool:
    return (
        bp.mood_family == "Default / None"
        and bp.style_name in ("Auto by Mood", "Neutral / Minimal Carryover")
        and _adult_tone_group(bp.adult_tone) not in ("default", "safe", "")
        and not bp.adult_wardrobe
        and not bp.scene_framing
        and bp.lens_preset in ("auto", "")
        and not bp.custom_notes
        and _external_prompt_has_camera_or_lighting_cue(external_prompt)
    )


STYLE_NEGATIVE_CONFLICT_PATCH_2026_05_31_D = True
PAINTERLY_PROTECTED_CONTEXT_RE_2026_05_31_E = re.compile(
    r"\b(?:watercolor|painterly|painting|painted|brush|brushwork|washes|gouache|illustration|sumi[-\s]?e|ink\s+wash|oil\s+painting)\b",
    re.IGNORECASE,
)
PHOTOGRAPHIC_PROTECTIVE_NEGATIVE_RE_2026_05_31_E = re.compile(
    r"\b(?:photorealistic|photo[-\s]?realistic|photographic|realistic\s+camera|camera\s+lens|live[-\s]?action|real\s+human\s+skin|realistic\s+skin|glossy\s+photo|hard\s+photographic|photographic\s+depth)\b",
    re.IGNORECASE,
)
_NEGATIVE_CONFLICT_STOP_TOKENS = frozenset({
    "style", "mood", "tone", "visual", "image", "scene", "setting", "atmosphere", "composition",
    "treatment", "rendering", "light", "lighting", "look", "feel", "quality", "subject", "details",
    "random", "noise", "generic", "ordinary", "flat", "bad", "worst", "low", "extra", "deformed",
})


def _semantic_tokens_for_conflict(text: Any) -> set:
    tokens = set()
    for tok in re.findall(r"[a-z]+", _normalize_text(text).lower()):
        if len(tok) < 5:
            continue
        if tok in _NEGATIVE_CONFLICT_STOP_TOKENS:
            continue
        tokens.add(tok)
    return tokens


def _negative_term_conflicts_with_positive_context(negative_term: Any, positive_terms: List[Any]) -> bool:
    neg = _clean_text(negative_term)
    if not neg:
        return False
    neg_tokens = _semantic_tokens_for_conflict(neg)
    for pos in positive_terms:
        pos_clean = _clean_text(pos)
        if not pos_clean:
            continue
        # Painterly positives and photographic negatives are intentionally paired:
        # the negative protects watercolor/gouache/oil/ink styles from drifting
        # back into photorealism. Do not treat that as a removable conflict.
        if (
            PHOTOGRAPHIC_PROTECTIVE_NEGATIVE_RE_2026_05_31_E.search(neg)
            and PAINTERLY_PROTECTED_CONTEXT_RE_2026_05_31_E.search(pos_clean)
        ):
            continue
        if _texts_conflict_by_style_polarity(neg, pos_clean):
            return True
        pos_tokens = _semantic_tokens_for_conflict(pos_clean)
        if neg_tokens and pos_tokens and neg_tokens.intersection(pos_tokens):
            return True
    return False


def _filter_negative_terms_against_positive_context(negative_terms: List[Any], positive_terms: List[Any]) -> List[str]:
    out: List[str] = []
    for term in negative_terms:
        cleaned = _clean_negative_text(term)
        if not cleaned:
            continue
        if _negative_term_conflicts_with_positive_context(cleaned, positive_terms):
            continue
        out.append(cleaned)
    return _unique(out)


YOUTHFUL_STYLE_ADULT_GUARD_2026_05_31_D = frozenset({
    "Chibi Style",
    "Gouache Storybook Illustration",
    "Hand-Painted Storybook Animation",
})


def _guard_youthful_style_adult_tone(style_name: str, adult_tone: str, adult_wardrobe_key: str) -> Tuple[str, str]:
    style_key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    tone = _canonical_ui_value(adult_tone, "adult_tone") or "default"
    wardrobe_key = _canonical_ui_value(adult_wardrobe_key, "adult_wardrobe") or "auto"
    if style_key not in YOUTHFUL_STYLE_ADULT_GUARD_2026_05_31_D:
        return tone, wardrobe_key
    # Keep the visual style available, but avoid combining childlike/storybook cues
    # with sensual/NSFW direction or adult-only wardrobe cues.
    if _adult_tone_group(tone) in {"suggestive", "sensual", "bold_sensual", "nsfw", "explicit"}:
        tone = "default"
    if wardrobe_key not in ("auto", "evening dress", "tailored suit", "oversized shirt"):
        wardrobe_key = "auto"
    return tone, wardrobe_key


def _should_suppress_youthful_style_adult_context(style_name: str, mood_family: str, requested_adult_tone: str, requested_wardrobe_key: str) -> bool:
    style_key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    if style_key not in YOUTHFUL_STYLE_ADULT_GUARD_2026_05_31_D:
        return False
    tone_group = _adult_tone_group(requested_adult_tone)
    wardrobe_key = _canonical_ui_value(requested_wardrobe_key, "adult_wardrobe") or "auto"
    if mood_family in {"Erotic / Sensual"}:
        return True
    if tone_group in {"suggestive", "sensual", "bold_sensual", "nsfw", "explicit"}:
        return True
    if wardrobe_key not in ("auto", "evening dress", "tailored suit", "oversized shirt"):
        return True
    return False


class PromptStylerCore:
    @staticmethod
    def build_blueprint(
        model_profile: str,
        mood_family: str,
        style_dna: str,
        adult_wardrobe: str,
        scene_framing: str,
        lens_preset: str,
        explicitness: str,
        custom_notes: str,
        seed: int,
        style_strength: str,
    ) -> Blueprint:
        rng = random.Random(_seed_value(seed))
        model = _get_model_profile(model_profile)
        neutral_mood = {"anchor": "", "emotion": [], "avoid": []}
        if mood_family == RANDOM_MOOD_FAMILY_LABEL:
            mood_family = _pick_random_mood_family(rng)

        if mood_family in RANDOM_MOOD_STYLE_GROUPS:
            if style_dna == "Auto by Mood":
                style_dna = _pick_random_style_for_special_mood(mood_family, rng)
            mood_family = "Default / None"
        elif mood_family == RANDOM_ALL_INTERNAL_MISC_STYLE_LABEL:
            if style_dna == "Auto by Mood":
                misc_choices = [s for s in RANDOM_ALL_INTERNAL_MISC_STYLES if s in STYLE_DNA]
                if misc_choices:
                    style_dna = rng.choice(misc_choices)
            mood_family = "Default / None"

        mood = MOOD_FAMILIES.get(mood_family) or MOOD_FAMILIES.get("Default / None") or neutral_mood

        if style_dna == "Auto by Mood":
            style_dna = AUTO_STYLE_BY_MOOD.get(mood_family, "Neutral / Minimal Carryover")

        neutral_style = {
            "anchor": "natural visual continuity",
            "lighting": [],
            "color": [],
            "composition": [],
            "texture": [],
            "avoid": [],
        }
        style = STYLE_DNA.get(style_dna)
        if style is None:
            style = STYLE_DNA.get("Neutral / Minimal Carryover")
        if style is None:
            style = STYLE_DNA.get("Neon Melancholy / Rain Glass")
        if style is None:
            style = next((v for v in STYLE_DNA.values() if isinstance(v, dict)), neutral_style)
        if not isinstance(style, dict):
            style = neutral_style

        adult_wardrobe_key = _canonical_ui_value(adult_wardrobe, "adult_wardrobe") or "auto"
        requested_adult_wardrobe_key = adult_wardrobe_key
        requested_adult_tone = _resolve_adult_tone_for_wardrobe(explicitness, adult_wardrobe_key)
        suppress_youthful_adult_context = _should_suppress_youthful_style_adult_context(style_dna, mood_family, requested_adult_tone, requested_adult_wardrobe_key)
        adult_tone_effective, adult_wardrobe_key = _guard_youthful_style_adult_tone(style_dna, requested_adult_tone, adult_wardrobe_key)
        if suppress_youthful_adult_context:
            mood_family = "Default / None"
            mood = MOOD_FAMILIES.get(mood_family) or neutral_mood
        adult_wardrobe_text = _clean_text(ADULT_WARDROBE.get(adult_wardrobe_key, ""))
        scene_framing_key = _canonical_ui_value(scene_framing, "scene_framing") or "auto"
        scene_framing_terms = SCENE_FRAMING.get(scene_framing_key, SCENE_FRAMING.get("auto", []))
        scene_framing_terms = _unique(scene_framing_terms)

        lens = _auto_lens(style_dna, mood_family, scene_framing_key) if lens_preset == "auto" else lens_preset
        _suppress_camera_bp = _suppress_auto_camera_for_prompt(style_dna, mood_family, lens_preset)
        if _suppress_camera_bp:
            camera_terms = []
        else:
            camera_terms = _style_auto_camera_terms(style_dna, lens_preset)
            if not camera_terms:
                camera_terms = LENS_PRESETS.get(lens, LENS_PRESETS["50mm intimate natural"])
                camera_terms = _harmonize_camera_terms_for_framing(camera_terms, scene_framing_key)


        cue_count = {"subtle": 2, "balanced": 3, "strong": 4}.get(style_strength, 3)
        emotion_count = {"subtle": 1, "balanced": 2, "strong": 3}.get(style_strength, 2)


        np_cues = NONPHYSICAL_STYLE_CUES.get(style_dna, {})
        def _merged_pool(field: str) -> List[str]:
            return _unique_style_pool(style.get(field, []) + np_cues.get(field, []), style_dna, field)

        lighting = _pick(rng, _merged_pool("lighting"), cue_count)
        color = _pick(rng, _merged_pool("color"), min(cue_count, 4))
        composition = _pick(rng, _merged_pool("composition"), cue_count)
        texture = _pick(rng, _merged_pool("texture"), cue_count)
        style_signature = _style_data_signature(style, np_cues)
        if _is_monochrome_output_context(mood_family, style_dna, style_signature):
            lighting = _filter_chromatic_terms_for_monochrome(lighting)
            color = _filter_chromatic_terms_for_monochrome(color, fallback=True, style_name=style_dna)
            texture = _filter_chromatic_terms_for_monochrome(texture)
        picked_emotion = _pick(rng, mood.get("emotion", []), emotion_count)
        emotion = _filter_mood_positive_terms_for_style(picked_emotion, style_signature)
        if picked_emotion and not emotion:
            emotion = _bridge_mood_emotion_after_conflict(mood_family, picked_emotion, style_signature, style_dna)
        anchor = _clean_text(style.get("anchor") or mood.get("anchor") or "")

        positive_context_terms = [MOOD_FAMILIES.get(mood_family, {}).get("anchor", ""), anchor] + emotion + lighting + color + composition + texture
        negative_parts = []
        model_negative = _clean_negative_text(model.get("negative", ""))
        if model_negative and _is_transformative_style_name(style_dna):
            # This generic model-profile negative conflicts with subject-transform styles
            # such as Chibi, Pixel Art, Miniature, and 3D Collectible Figure.
            model_negative = re.sub(r"\bAvoid making the style replace the subject\.?\s*", "", model_negative, flags=re.IGNORECASE)
            model_negative = _clean_negative_text(model_negative)
        if model_negative:
            negative_parts.append(model_negative)
        # CFG 1 / turbo-style workflows often ignore negative prompts. Therefore style
        # enforcement must live in the positive prompt, not in mood/style avoid terms.
        # Keep only model-profile safety/quality negatives here; user-provided external
        # negatives are merged later unchanged. The STYLE_DNA/MOOD avoid lists remain as
        # reference data for documentation/conflict checks, but are not used to strengthen
        # a selected style through the generated negative prompt.
        negative = _join_negative_comma(negative_parts)

        return Blueprint(
            model_profile=model_profile,
            mood_family=mood_family,
            style_name=style_dna,
            style_strength=style_strength,
            adult_tone=adult_tone_effective,
            adult_wardrobe=adult_wardrobe_text,
            scene_framing=scene_framing_terms,
            lens_preset=lens_preset,
            style_anchor=anchor,
            emotion=emotion,
            lighting=lighting,
            color=color,
            composition=composition,
            texture=texture,
            camera=camera_terms,
            custom_notes=_sanitize_minor_conflict_text(custom_notes, adult_tone_effective),
            negative=negative,
        )


    @staticmethod
    def _external_strength_settings(style_strength: str) -> Dict[str, Any]:
        strength = _canonical_ui_value(style_strength, "style_strength")
        if strength == "strong":
            return {"lighting": 2, "color": 2, "composition": 2, "texture": 2, "camera": 3, "weight": 1.25, "mode": "strong", "lead": "pronounced"}
        if strength == "subtle":
            return {"lighting": 1, "color": 1, "composition": 0, "texture": 0, "camera": 1, "weight": 1.08, "mode": "subtle", "lead": "restrained"}
        return {"lighting": 2, "color": 1, "composition": 1, "texture": 1, "camera": 2, "weight": 1.15, "mode": "balanced", "lead": "clear"}


    @staticmethod
    def _empty_style_parts() -> Dict[str, str]:
        empty = ""
        return {
            "style_insert": empty,
            "natural_insert": empty,
            "natural_insert_flux": empty,
            "natural_insert_qwen": empty,
            "tag_insert": empty,
            "style_anchor": empty,
            "combined_anchor": empty,
            "lighting_prompt": empty,
            "color_prompt": empty,
            "camera_prompt": empty,
            "custom_note": empty,
        }

    @staticmethod
    def _custom_only_style_parts(bp: Blueprint) -> Dict[str, str]:
        custom_note = _external_custom_note(bp.custom_notes)
        natural = _sentence(custom_note) if custom_note else ""
        return {
            "style_insert": custom_note,
            "natural_insert": natural,
            "natural_insert_flux": natural,
            "natural_insert_qwen": natural,
            "tag_insert": custom_note,
            "style_anchor": "",
            "combined_anchor": "",
            "lighting_prompt": "",
            "color_prompt": "",
            "camera_prompt": "",
            "custom_note": custom_note,
        }

    @staticmethod
    def _tone_only_style_parts(bp: Blueprint) -> Dict[str, str]:
        strength = PromptStylerCore._external_strength_settings(bp.style_strength)
        adult_natural = _adult_tone_terms(bp.adult_tone, "natural")
        adult_tags = _adult_tone_tag_terms_for_model(bp.adult_tone, bp.model_profile)
        natural = _natural_style_sentence(adult_natural=adult_natural)
        tag_insert = _style_tag_insert_from_raw(adult_tags, weight=float(strength["weight"]))
        style_insert = _join_comma(adult_tags)
        return {
            "style_insert": style_insert,
            "natural_insert": natural,
            "natural_insert_flux": natural,
            "natural_insert_qwen": natural,
            "tag_insert": tag_insert,
            "style_anchor": "",
            "combined_anchor": "",
            "lighting_prompt": "",
            "color_prompt": "",
            "camera_prompt": "",
            "custom_note": "",
        }

    @staticmethod
    def external_style_parts_for_prompt(bp: Blueprint, external_prompt: Any) -> Dict[str, Any]:
        if _should_keep_external_prompt_cues_over_neutral(bp, external_prompt):
            return PromptStylerCore._tone_only_style_parts(bp)
        return PromptStylerCore.external_style_parts(bp)


    @staticmethod
    def _anchor_tokens(value: Any) -> set:
        stop = {
            "a", "an", "and", "as", "at", "atmosphere", "by", "for", "from",
            "in", "into", "lit", "mood", "of", "on", "style", "the", "through",
            "to", "with", "against",
        }
        return {tok for tok in re.findall(r"[a-z0-9]+", _normalize_text(value).lower()) if tok and tok not in stop}

    @staticmethod
    def _merge_style_anchors(mood_value: str, style_value: str) -> str:
        mood_value = _clean_text(mood_value)
        style_value = _clean_text(style_value)
        if not mood_value:
            return style_value
        if not style_value:
            return mood_value
        if mood_value.lower() == style_value.lower():
            return style_value
        mood_tokens = PromptStylerCore._anchor_tokens(mood_value)
        style_tokens = PromptStylerCore._anchor_tokens(style_value)
        if mood_tokens and mood_tokens.issubset(style_tokens):
            return style_value
        if style_tokens and style_tokens.issubset(mood_tokens):
            return mood_value
        return f"{mood_value}, {style_value}"

    @staticmethod
    def _resolve_external_anchors(bp: Blueprint, fallback: Dict[str, Any]) -> Tuple[str, str]:
        suppress_camera_anchor = _is_camera_suppressed_context(bp.style_name, bp.mood_family)
        anchor_fallback = "painterly visual style" if suppress_camera_anchor else "cinematic tonal styling"
        style_anchor = _clean_text(bp.style_anchor) or _clean_text(fallback.get("anchor")) or anchor_fallback or "natural visual continuity"
        if _is_monochrome_output_context(bp.mood_family, bp.style_name, style_anchor):
            style_anchor = _monochrome_safe_anchor(style_anchor)

        mood_anchor = _clean_text(MOOD_FAMILIES.get(bp.mood_family, {}).get("anchor", ""))
        style_signature_for_conflict = _style_data_signature(style_anchor, fallback)
        if mood_anchor and _anchors_conflict(mood_anchor, style_signature_for_conflict):
            mood_anchor = ""

        return style_anchor, PromptStylerCore._merge_style_anchors(mood_anchor, style_anchor)

    @staticmethod
    def _parts_or_fallback(bp_parts: List[str], fallback: Dict[str, Any], fallback_key: str, limit: int) -> List[str]:
        safe = [_clean_text(x) for x in bp_parts if _clean_text(x)]
        if len(safe) >= limit:
            return safe[:limit]

        seen = {s.lower() for s in safe}
        for item in [_clean_text(x) for x in fallback.get(fallback_key, []) if _clean_text(x)]:
            if item.lower() not in seen:
                safe.append(item)
                seen.add(item.lower())
            if len(safe) >= limit:
                break
        return safe[:limit]

    @staticmethod
    def _external_style_components(bp: Blueprint, fallback: Dict[str, Any], strength: Dict[str, Any]) -> Dict[str, Any]:
        composition = PromptStylerCore._parts_or_fallback(bp.composition, fallback, "composition", strength["composition"])
        composition = _harmonize_style_terms_for_framing(composition, bp.scene_framing)
        lighting = PromptStylerCore._parts_or_fallback(bp.lighting, fallback, "lighting", strength["lighting"])
        color = PromptStylerCore._parts_or_fallback(bp.color, fallback, "color", strength["color"])
        texture = PromptStylerCore._parts_or_fallback(bp.texture, fallback, "texture", strength["texture"])
        lighting = _filter_nonphoto_style_terms(lighting, bp.style_name)
        color = _filter_nonphoto_style_terms(color, bp.style_name)
        composition = _filter_nonphoto_style_terms(composition, bp.style_name)
        texture = _filter_nonphoto_style_terms(texture, bp.style_name)
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            lighting = _filter_chromatic_terms_for_monochrome(lighting)
            color = _filter_chromatic_terms_for_monochrome(color, fallback=True, style_name=bp.style_name)
            texture = _filter_chromatic_terms_for_monochrome(texture)
        suppress_camera = _suppress_auto_camera_for_prompt(bp.style_name, bp.mood_family, bp.lens_preset)
        return {
            "lighting": lighting,
            "color": color,
            "composition": composition,
            "texture": texture,
            "camera": _safe_camera_terms(bp.camera, suppress_camera=suppress_camera)[:strength["camera"]],
            "custom_note": _external_custom_note(bp.custom_notes),
            "wardrobe_note": _clean_text(bp.adult_wardrobe),
            "scene_framing_note": _join_comma(bp.scene_framing),
            "emotion": [_clean_text(x) for x in bp.emotion if _clean_text(x)],
            "adult_natural": _adult_tone_terms(bp.adult_tone, "natural"),
            "adult_tags": _adult_tone_tag_terms_for_model(bp.adult_tone, bp.model_profile),
        }

    @staticmethod
    def _render_external_style_parts(
        bp: Blueprint,
        style_anchor: str,
        combined_anchor: str,
        parts: Dict[str, Any],
        strength: Dict[str, Any],
    ) -> Dict[str, Any]:
        sentence_args = {
            "wardrobe_note": parts["wardrobe_note"],
            "scene_framing_note": parts["scene_framing_note"],
            "custom_note": parts["custom_note"],
            "adult_natural": parts["adult_natural"],
            "emotion": parts["emotion"],
            "anchor": combined_anchor,
            "lighting": parts["lighting"],
            "color": parts["color"],
            "composition": parts["composition"],
            "texture": parts["texture"],
            "camera": parts["camera"],
        }
        natural_insert_default = _natural_style_sentence(**sentence_args)
        natural_insert_flux = _natural_style_sentence(**sentence_args, flux_structured=True)
        natural_insert_qwen = _natural_style_sentence(**sentence_args, qwen_structured=True)

        lead_tag_parts = ([] if not parts["wardrobe_note"] else [parts["wardrobe_note"]]) + ([] if not parts["scene_framing_note"] else [parts["scene_framing_note"]])
        style_detail_parts = [
            _join_comma(parts["lighting"]),
            _join_comma(parts["color"]),
            _join_comma(parts["composition"]),
            _join_comma(parts["texture"]),
            _join_comma(parts["camera"]),
        ]
        ordered_tag_parts = ([] if not combined_anchor else [combined_anchor]) + lead_tag_parts + parts["adult_tags"] + parts["emotion"] + style_detail_parts
        base_tag_insert = _style_tag_insert_from_raw(list(ordered_tag_parts), weight=float(strength["weight"]))
        alias_tag_insert = _style_tag_alias_insert(bp.style_name, bp.model_profile, weight=float(strength["weight"]))
        tag_insert = _join_unique_tags([alias_tag_insert, base_tag_insert])
        if parts["custom_note"]:
            tag_insert = _join_comma([tag_insert, parts["custom_note"]])

        return {
            "style_insert": _join_comma(list(ordered_tag_parts) + ([] if not parts["custom_note"] else [parts["custom_note"]])),
            "natural_insert": natural_insert_default,
            "natural_insert_flux": natural_insert_flux,
            "natural_insert_qwen": natural_insert_qwen,
            "tag_insert": tag_insert,
            "style_anchor": style_anchor,
            "combined_anchor": combined_anchor,
            "lighting_prompt": _join_comma(parts["lighting"]),
            "color_prompt": _join_comma(parts["color"]),
            "camera_prompt": _join_comma(parts["camera"] + parts["composition"]),
            "custom_note": parts["custom_note"],
        }

    @staticmethod
    def external_style_parts(bp: Blueprint) -> Dict[str, Any]:
        if _is_default_style(bp):
            return PromptStylerCore._empty_style_parts()
        if _is_custom_text_only(bp):
            return PromptStylerCore._custom_only_style_parts(bp)

        fallback = NONPHYSICAL_STYLE_CUES.get(bp.style_name) or {}
        strength = PromptStylerCore._external_strength_settings(bp.style_strength)
        style_anchor, combined_anchor = PromptStylerCore._resolve_external_anchors(bp, fallback)
        parts = PromptStylerCore._external_style_components(bp, fallback, strength)
        return PromptStylerCore._render_external_style_parts(bp, style_anchor, combined_anchor, parts, strength)

    @staticmethod
    def _mixed_natural_assist(style: Dict[str, Any], bp: "Blueprint", has_external: bool = True, external_text: str = "", style_first: bool = False) -> str:
        """Short natural-language support sentence for mixed prompts.

        Mixed/tag-first models benefit from a compact natural-language assist.
        For transformation/media-first styles, the assist must explicitly state
        the conversion so the external prompt is interpreted as reference, not
        as the final rendering instruction.
        """
        natural = _clean_text(style.get("natural_insert"))
        anchor = _clean_text(style.get("combined_anchor")) or _clean_text(style.get("style_anchor"))
        lighting = _clean_text(style.get("lighting_prompt"))
        color = _clean_text(style.get("color_prompt"))
        camera = _clean_text(style.get("camera_prompt"))
        parts = [p for p in [anchor, lighting, color, camera] if p]
        directive = _clean_text(_style_specific_directive(bp.style_name, bp.style_strength))
        ref_hint = "Use the external prompt as reference only" if str(bp.style_name or "") in COMPACT_MEDIUM_STYLE_NAMES else "Treat the external prompt only as reference for subject identity, outfit, pose, composition, and scene content"
        out_parts: List[str] = []
        if style_first:
            if directive:
                out_parts.append(_sentence(directive))
            if parts:
                out_parts.append(_sentence("Apply " + ", ".join(parts)))
            elif natural:
                out_parts.append(_sentence(natural))
            if has_external and _clean_text(external_text):
                out_parts.append(_sentence(ref_hint))
            return " ".join(p for p in out_parts if p)
        if directive and str(bp.style_name or "") in POSITIVE_STYLE_FIRST_NAMES:
            out_parts.append(_sentence(directive))
        if parts:
            if has_external:
                out_parts.append(_sentence("Keep the original subject and scene readable while applying " + ", ".join(parts)))
            else:
                out_parts.append(_sentence("Apply " + ", ".join(parts)))
        elif natural:
            custom = _clean_text(style.get("custom_note"))
            if not (custom and _natural_dedupe_key(natural) == _natural_dedupe_key(custom)):
                out_parts.append(natural)
        if has_external and directive and str(bp.style_name or "") in POSITIVE_STYLE_FIRST_NAMES:
            out_parts.append(_sentence(ref_hint))
        return " ".join(p for p in out_parts if p)

    @staticmethod
    def render_external_positive(bp: Blueprint, external_prompt: str) -> str:
        external = _clean_text(external_prompt)
        style = PromptStylerCore.external_style_parts_for_prompt(bp, external)
        family = _model_family(bp.model_profile)
        key = _model_key(bp.model_profile)
        quality = _tag_quality_for_model(bp.model_profile, bp.adult_tone)
        if family == "tag":


            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            return _join_unique_tags([quality, external_tag_prompt, style["tag_insert"]])
        if family == "mixed":
            if key == "anima":
                layered = _render_anima_style_layer_prompt(bp, external, style_first=False, style=style)
                if layered:
                    return layered

            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            tag_block = _join_unique_tags([quality, external_tag_prompt, style["tag_insert"]])
            assist = PromptStylerCore._mixed_natural_assist(style, bp, has_external=bool(external), external_text=external)
            return _join_mixed_prompt(tag_block, assist)


        custom_note = style.get("custom_note", "")
        natural_quality = _natural_quality_for_prompt(bp)
        # In append mode, keep the user's original prompt visibly first, then add
        # quality/style wording after it. This matches the UI label.
        external_with_quality = _append_sentence(external, natural_quality) if natural_quality else external
        insert = _natural_insert_for_model(style, bp)
        insert = _omit_natural_custom_if_already_external(insert, external_with_quality, custom_note)
        insert = _wrap_model_specific_natural_insert(insert, bp, has_external=bool(external))
        return _append_sentence(external_with_quality, insert)

    @staticmethod
    def render_prepend_style(bp: Blueprint, external_prompt: str) -> str:
        """Style first, then external prompt — useful when style should dominate."""
        external = _clean_text(external_prompt)
        style = PromptStylerCore.external_style_parts_for_prompt(bp, external)
        family = _model_family(bp.model_profile)
        key = _model_key(bp.model_profile)
        quality = _tag_quality_for_model(bp.model_profile, bp.adult_tone)
        if family == "tag":
            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            return _join_unique_tags([quality, style["tag_insert"], external_tag_prompt])
        if family == "mixed":
            if key == "anima":
                layered = _render_anima_style_layer_prompt(bp, external, style_first=True, style=style)
                if layered:
                    return layered

            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            # In explicit prepend mode, keep the full style tag block before the
            # external prompt. Older builds split the style tags around the
            # external prompt, which made the output order look inconsistent.
            tag_block = _join_unique_tags([quality, style["tag_insert"], external_tag_prompt])
            assist = PromptStylerCore._mixed_natural_assist(style, bp, has_external=bool(external), external_text=external, style_first=True)
            return _join_mixed_prompt(tag_block, assist)

        custom_note = style.get("custom_note", "")
        natural_quality = _natural_quality_for_prompt(bp)
        external_with_quality = _append_sentence(natural_quality, external) if natural_quality else external
        insert = _natural_insert_for_model(style, bp)
        insert = _omit_natural_custom_if_already_external(insert, external_with_quality, custom_note)
        insert = _wrap_model_specific_natural_insert(insert, bp, has_external=bool(external))
        style_with_quality = _append_sentence(natural_quality, insert) if natural_quality else insert
        if str(bp.style_name or "") in POSITIVE_STYLE_FIRST_NAMES and external:
            reference_sentence = ("Use as reference only: " if str(bp.style_name or "") in COMPACT_MEDIUM_STYLE_NAMES else "Use the following only as reference for subject identity, outfit, pose, composition, and scene content: ") + external
            return _append_sentence(style_with_quality, reference_sentence)
        return _append_sentence(style_with_quality, external)

    @staticmethod
    def render_external_style_only(bp: Blueprint) -> str:
        style = PromptStylerCore.external_style_parts(bp)
        family = _model_family(bp.model_profile)
        key = _model_key(bp.model_profile)
        if family == "tag":
            return _join_unique_tags([_tag_quality_for_model(bp.model_profile, bp.adult_tone), style["tag_insert"]])
        if family == "mixed":
            if key == "anima":
                layered = _render_anima_style_layer_prompt(bp, "", style_first=True, style_only=True, style=style)
                if layered:
                    return layered
            tag_block = _join_unique_tags([_tag_quality_for_model(bp.model_profile, bp.adult_tone), style["tag_insert"]])
            assist = PromptStylerCore._mixed_natural_assist(style, bp, has_external=False, external_text="")
            return _join_mixed_prompt(tag_block, assist)
        natural_quality = _natural_quality_for_prompt(bp)
        insert = _natural_insert_for_model(style, bp)
        insert = _wrap_model_specific_natural_insert(insert, bp, has_external=False)
        return _append_sentence(natural_quality, insert)


class UltraPromptStyler:
    """Compact PromptStyler node.

    A single lightweight node for prompt style wording.
    It keeps prompt text assembly deterministic and does not include external AI/API panels.
    """

    CATEGORY = NODE_CATEGORY
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_profile": (_ui_options("model_profile", _visible_model_profiles()), {"default": "Z-Image Natural"}),
                "mood_family": (_ui_options("mood_family", _visible_mood_family_options()), {"default": "Default / None"}),
                "style_dna": (_ui_options("style_dna", _visible_style_dna()), {"default": "Auto by Mood"}),
                "style_strength": (_ui_options("style_strength", ["subtle", "balanced", "strong"]), {"default": "strong"}),
                "style_conflict_cleanup": (_ui_options("style_conflict_cleanup", ["off", "soft", "strong"]), {"default": "off"}),
                "scene_framing": (_ui_options("scene_framing", ["auto"] + [k for k in SCENE_FRAMING.keys() if k != "auto"]), {"default": "auto"}),
                "lens_preset": (_ui_options("lens_preset", ["auto"] + [k for k in LENS_PRESETS.keys() if k != "auto"]), {"default": "auto"}),
                "adult_tone": (_ui_options("adult_tone", ["default", "safe", "suggestive", "sensual", "bold sensual", "nsfw", "explicit nsfw", "romantic non-explicit"]), {"default": "default"}),
                "adult_wardrobe": (_ui_options("adult_wardrobe", ["auto"] + [k for k in ADULT_WARDROBE.keys() if k != "auto"]), {"default": "auto"}),
                "external_prompt_mode": (_ui_options("external_prompt_mode", [
                    "Append style after external prompt",
                    "Prepend style before external prompt",
                    "Output style only",
                ]), {"default": "Prepend style before external prompt"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "custom_text": ("STRING", {"default": "", "multiline": True, "placeholder": "Ex) modern city skyline, luxury living room, black dress, night street"}),
            },
            "optional": {
                "external_positive_in": ("STRING", {"forceInput": True}),
                "external_negative_in": ("STRING", {"forceInput": True}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        watched_keys = (
            "model_profile", "mood_family", "style_dna", "style_strength", "style_conflict_cleanup",
            "adult_tone", "adult_wardrobe", "scene_framing", "lens_preset",
            "external_prompt_mode", "seed", "custom_text",
            "external_positive_in", "external_negative_in",
        )
        state: Dict[str, Any] = {}
        for key in watched_keys:
            value = kwargs.get(key, "")
            if key == "seed":
                try:
                    value = int(value)
                except Exception:
                    value = 0
            else:
                value = "" if value is None else str(value)
            state[key] = value
        return json.dumps(state, ensure_ascii=False, sort_keys=True)

    def generate(
        self,
        model_profile: str,
        mood_family: str,
        style_dna: str,
        style_strength: str,
        style_conflict_cleanup: str,
        scene_framing: str,
        lens_preset: str,
        adult_tone: str,
        adult_wardrobe: str,
        external_prompt_mode: str,
        seed: int,
        custom_text: str = "",
        external_positive_in: str = "",
        external_negative_in: str = "",
    ):


        model_profile = _safe_ui_value(model_profile, "model_profile")
        mood_family = _safe_ui_value(mood_family, "mood_family")
        style_dna = _safe_ui_value(style_dna, "style_dna")
        style_strength = _safe_ui_value(style_strength, "style_strength")
        style_conflict_cleanup = _safe_ui_value(style_conflict_cleanup, "style_conflict_cleanup")
        scene_framing = _safe_ui_value(scene_framing, "scene_framing")
        lens_preset = _safe_ui_value(lens_preset, "lens_preset")
        adult_tone = _safe_ui_value(adult_tone, "adult_tone")
        adult_wardrobe = _safe_ui_value(adult_wardrobe, "adult_wardrobe")
        external_prompt_mode = _safe_ui_value(external_prompt_mode, "external_prompt_mode")

        external_positive_in = external_positive_in if external_positive_in is not None else ""
        external_negative_in = external_negative_in if external_negative_in is not None else ""
        custom_text = custom_text if custom_text is not None else ""

        effective_adult_tone_for_text = _resolve_adult_tone_for_wardrobe(adult_tone, adult_wardrobe)
        external_positive = _sanitize_minor_conflict_text(external_positive_in, effective_adult_tone_for_text)
        external_negative = _clean_negative_text(external_negative_in)

        bp = PromptStylerCore.build_blueprint(
            model_profile=model_profile,
            mood_family=mood_family,
            style_dna=style_dna,
            adult_wardrobe=adult_wardrobe,
            scene_framing=scene_framing,
            lens_preset=lens_preset,
            explicitness=adult_tone,
            custom_notes=custom_text,
            seed=seed,
            style_strength=style_strength,
        )
        custom_text = bp.custom_notes

        if _should_cleanup_external_prompt(bp, style_conflict_cleanup, external_prompt_mode):
            external_positive = _relax_style_conflicting_external_prompt(external_positive, bp, style_conflict_cleanup)

        negative_context_sources = [custom_text]
        if external_prompt_mode != "Output style only":
            negative_context_sources.insert(0, external_positive)

        generated_negative = _harmonize_negative_with_user_positive(
            bp.negative,
            *negative_context_sources,
            adult_tone=effective_adult_tone_for_text,
        )
        generated_negative = _harmonize_negative_with_model_tone(
            generated_negative,
            bp.model_profile,
            bp.adult_tone,
        )

        if not external_positive or external_prompt_mode == "Output style only":


            positive = PromptStylerCore.render_external_style_only(bp)
        elif external_prompt_mode == "Prepend style before external prompt" or _should_force_transformative_style_first(bp, external_prompt_mode):
            positive = PromptStylerCore.render_prepend_style(bp, external_positive)
        else:


            positive = PromptStylerCore.render_external_positive(bp, external_positive)

        family = _model_family(bp.model_profile)
        positive = _sanitize_prompt_output(positive, family)
        negative = _sanitize_prompt_output(_merge_negative_prompt_parts(generated_negative, external_negative), "tag")

        return (positive, negative)


NODE_CLASS_MAPPINGS = {
    "UltraPromptStyler": UltraPromptStyler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltraPromptStyler": "Ultra Tools Prompt Styler",
}


STABILITY_FIX_E_VERIFIED_2026_05_31 = True
