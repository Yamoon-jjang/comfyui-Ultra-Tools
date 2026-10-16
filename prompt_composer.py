# -*- coding: utf-8 -*-
"""
comfyui-Ultra_Prompt_Composer
A deterministic ComfyUI prompt composition node that adapts prompt wording to model-specific rules.

Design goals:
- Build a structured prompt-style blueprint first.
- Render that blueprint differently for tag / natural-language / instruction-following models.
- Keep adult-related wording clearly adult and user-directed.
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
        
    },
    "Erotic / Sensual": {
        "anchor": "cinematic restrained sensual tension",
        "emotion": ["adult intimacy", "quiet desire", "elegant restraint", "private emotional charge"],
        
    },
    "Lyrical / Poetic": {
        "anchor": "lyrical cinematic melancholy",
        "emotion": ["quiet longing", "soft emotional distance", "delicate silence", "lingering tenderness"],
        
    },
    "Classical / Golden Age": {
        "anchor": "classical studio glamour",
        "emotion": ["timeless elegance", "refined poise", "controlled romance", "graceful stillness"],
        
    },
    "Noir / Neo-noir": {
        "anchor": "adult cinematic noir tension",
        "emotion": ["dangerous intimacy", "silent suspicion", "nocturnal desire", "private unease"],
        
    },
    "Dreamlike / Surreal": {
        "anchor": "dreamlike sensual atmosphere",
        "emotion": ["ambiguous emotion", "soft unreality", "subconscious intimacy", "floating calm"],
        
    },
    "Gothic Romance": {
        "anchor": "gothic romantic darkness",
        "emotion": ["romantic unease", "low amber longing", "velvet tension", "haunted elegance"],
        
    },
    "Melodrama": {
        "anchor": "lush cinematic melodrama",
        "emotion": ["heightened emotion", "romantic conflict", "expressive stillness", "fragile intensity"],
        
    },
    "Fashion Editorial": {
        "anchor": "high-end cinematic fashion editorial",
        "emotion": ["controlled sensuality", "luxury calm", "confident elegance", "gallery-like poise"],
        
    },
    "Arthouse Realism": {
        "anchor": "intimate arthouse realism",
        "emotion": ["ordinary private moment", "unposed emotional realism", "quiet sensuality", "natural vulnerability"],
        
    },
    "Pop Neon": {
        "anchor": "stylized pop neon cinema",
        "emotion": ["electric attraction", "modern nightlife energy", "glossy desire", "color-driven tension"],
        
    },
    "Baroque / Operatic": {
        "anchor": "baroque theatrical grandeur with dramatic chiaroscuro and velvet-lit opulence",
        "emotion": ["theatrical intensity", "operatic elegance", "ceremonial drama", "deep chiaroscuro tension"],
        
    },
    "Minimalist Psychological": {
        "anchor": "minimalist psychological intimacy",
        "emotion": ["controlled distance", "cold stillness", "subtle pressure", "restrained vulnerability"],
        
    },
    "Dark Fantasy Romance": {
        "anchor": "dark fantasy romantic unease",
        "emotion": ["shadowy attraction", "ominous elegance", "mythic sensuality", "chased by darkness atmosphere"],
        
    },
    "Black & White Film": {
        "anchor": "black and white, high contrast monochrome",
        "emotion": ["monochrome drama", "timeless contrast", "classic film mood", "tonal depth"],
        
    },
    "Golden Hour Warmth": {
        "anchor": "golden hour warm light",
        "emotion": ["warm intimacy", "soft radiance", "sunlit tenderness", "gentle glow"],
        
    },
    "Vintage / Retro": {
        "anchor": "vintage retro photograph",
        "emotion": ["nostalgic warmth", "faded memory", "retro charm", "nostalgic beauty"],
        
    },
    "Cyberpunk / Sci-fi": {
        "anchor": "cyberpunk neon sci-fi",
        "emotion": ["futuristic tension", "digital edge", "neon isolation", "synthetic atmosphere"],
        
    },
    "Watercolor / Painterly": {
        "anchor": "watercolor painterly style",
        "emotion": ["soft artistic beauty", "gentle impression", "painted serenity", "delicate color blending"],
        
    },
    "Bright / High-key": {
        "anchor": "bright high-key illumination",
        "emotion": ["cheerful lightness", "clean radiance", "fresh energy", "airy calm"],
        
    },
    "Cinematic Widescreen": {
        "anchor": "cinematic widescreen anamorphic",
        "emotion": ["epic scale", "cinematic grandeur", "dramatic scope", "visual storytelling"],
        
    },
    "Romantic / Soft Focus": {
        "anchor": "romantic soft focus",
        "emotion": ["tender romance", "gentle warmth", "soft intimacy", "dreamy closeness"],
        
    },
    "Horror / Unsettling": {
        "anchor": "horror dark unsettling mood",
        "emotion": ["creeping dread", "ominous tension", "psychological horror", "eerie silence"],
        
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
        "anchor": "sun-faded analog film photograph aesthetic",
        "lighting": ["soft analog highlight roll-off", "soft halation around highlights", "bleached highlight bloom", "lifted shadows", "nostalgic low-contrast illumination"],
        "color": ["washed-out colors", "sun-faded film palette", "bleached color response", "subtle amber-green film shift"],
        "composition": ["casual 35mm snapshot framing", "relaxed candid composition", "timeless film-photo balance"],
        "texture": ["visible fine film grain", "slight emulsion softness", "soft vignette", "aged print texture", "faded print look"],
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
    "full body (head to toe)": ["full-body framing", "full-length composition", "entire figure visible", "feet visible in frame"],
    "full shot (full body + extra space)": ["full-body framing with extra space", "full-length composition", "entire figure fully visible", "space above the head and below the feet", "feet visible in frame"],
    "wide shot": ["wide framing", "subject smaller within the frame", "full figure visible", "space around the entire body"],
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
    "safe": "adult presentation",
    "suggestive": "suggestive adult tone",
    "sensual": "adult sensuality",
    "bold sensual": "bold adult sensual mood",
    "nsfw": "adult erotic tone",
    "explicit nsfw": "explicit adult erotic presentation",
    "romantic non-explicit": "romantic adult intimacy",
}

# Keep a copy of the shipped explicitness descriptors so user edits in
# data/explicitness.json can be detected without changing the tuned default
# adult-tone wording for existing workflows.
EXPLICITNESS_DEFAULT = copy.deepcopy(EXPLICITNESS)


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
        "lighting": ["crisp tonal separation", "dramatic side light", "sharp highlight"],
        "color": ["monochrome", "neutral gray range", "deep blacks"],
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
        "anchor": "faded analog film photograph aesthetic",
        "lighting": ["soft analog highlight roll-off", "gentle halation around highlights", "lifted shadows"],
        "color": ["washed-out film colors", "muted vintage palette", "subtle amber-green film shift"],
        "composition": ["casual analog snapshot framing", "relaxed candid composition", "snapshot feel"],
        "texture": ["visible fine film grain", "slight emulsion softness", "soft vignette"],
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
    "Krea2 Natural": {
        "family": "natural",
        "model_key": "krea2",
        "quality": "detailed subject, defined pose, refined realistic composition, spatial depth, consistent details",
        "negative": "low quality, bad anatomy, childish appearance, teen, underage, schoolgirl, school uniform, explicit sexual act, pornographic staging, random abstract color noise, unreadable subject",
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
    "Krea2 Natural",
    "Qwen Natural",
    "Flux Natural",
    "Anima Mixed",
    "SDXL Tag",
    "ILXL / Illustrious Tag",
    "Pony Tag",
    "SD 1.5 Tag",
]


UI_LABELS_KO: Dict[str, Dict[str, str]] = {
    "model_profile": {
        "Z-Image Natural": "Z-Image 자연어",
        "Krea2 Natural": "Krea2 자연어",
        "Qwen Natural": "Qwen 자연어",
        "Flux Natural": "Flux 자연어",
        "Anima Mixed": "Anima 태그+문장",
        "SDXL Tag": "SDXL 태그형",
        "ILXL / Illustrious Tag": "ILXL / Illustrious 태그형",
        "Pony Tag": "Pony 태그형",
        "SD 1.5 Tag": "SD 1.5 태그형",
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
        "Vintage Film Look": "색바랜 필름 사진",
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
    "model_profile": {
        "Universal Natural Language": "Krea2 Natural",
        "범용 자연어": "Krea2 Natural",
    },
    "external_prompt_mode": {
        "External prompt + style only": "Output style only",
    },
    "subject_age": {
        "young adult": "20s",
        # Preserve legacy generic adult age instead of forcing it into 30s.
        # New UI still exposes decade bands only; this hidden value is accepted
        # only so old saved workflows keep their original broad age meaning.
        "adult": "adult",
        "mature adult": "50s",
        "elderly adult": "60s+",
        "성인": "adult",
        "20대": "20s",
        "30대": "30s",
        "40대": "40s",
        "50대": "50s",
        "60대 이상": "60s+",
    },
    "subject_appearance": {
        "선택 안함": "auto",
        "자연스러운": "natural-looking",
        "귀여운": "cute",
        "아름다운": "beautiful",
        "우아한": "elegant",
        "화려한": "glamorous",
        "평범한": "ordinary-looking",
        "수수한": "simple-looking",
        "덜 예쁜": "less conventionally attractive",
        "개성적인": "distinctive-looking",
    },
    "subject_ethnicity": {
        "Korean-looking": "Korean",
        "East Asian-looking": "East Asian",
        "Southeast Asian-looking": "Southeast Asian",
        "South Asian-looking": "South Asian",
        "Western-looking": "Western",
        "Middle Eastern-looking": "Middle Eastern",
        "한국인 느낌": "Korean",
        "한국인": "Korean",
        "동아시아 느낌": "East Asian",
        "동아시아": "East Asian",
        "동남아시아 느낌": "Southeast Asian",
        "동남아시아": "Southeast Asian",
        "남아시아 느낌": "South Asian",
        "남아시아": "South Asian",
        "서양인 느낌": "Western",
        "서양인": "Western",
        "중동계 느낌": "Middle Eastern",
        "중동계": "Middle Eastern",
        "혼혈 느낌": "mixed-heritage",
        "혼혈": "mixed-heritage",
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
        "빈티지 필름 느낌": "Vintage Film Look",
        "색바랜 필름 사진": "Vintage Film Look",
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


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_composer_data")

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
            print(f"[Ultra-PromptComposer] Ignoring empty/non-dict data file: {filename}")
    except Exception as e:
        print(f"[Ultra-PromptComposer] Failed to load data/{filename}: {e}")
    return copy.deepcopy(fallback)

# Keep embedded fallback data synchronized with the external JSON data files.
# Normal runtime still prefers ./data/*.json. These updates preserve the
# role-separated mood/style behavior if a data file is missing.
MOOD_FAMILIES.update({'Erotic / Sensual': {'anchor': 'restrained adult sensual tension',
                      'emotion': ['adult intimacy', 'quiet desire', 'elegant restraint', 'private emotional charge']},
 'Lyrical / Poetic': {'anchor': 'lyrical melancholy and quiet tenderness',
                      'emotion': ['quiet longing',
                                  'soft emotional distance',
                                  'delicate silence',
                                  'lingering tenderness']},
 'Classical / Golden Age': {'anchor': 'timeless graceful poise',
                            'emotion': ['timeless elegance',
                                        'refined poise',
                                        'controlled romance',
                                        'graceful stillness']},
 'Noir / Neo-noir': {'anchor': 'nocturnal suspicion and private unease',
                     'emotion': ['dangerous intimacy', 'silent suspicion', 'nocturnal desire', 'private unease']},
 'Melodrama': {'anchor': 'lush emotional melodrama',
               'emotion': ['heightened emotion', 'romantic conflict', 'expressive stillness', 'fragile intensity']},
 'Fashion Editorial': {'anchor': 'confident luxury poise',
                       'emotion': ['controlled sensuality',
                                   'luxury calm',
                                   'confident elegance',
                                   'gallery-like poise']},
 'Arthouse Realism': {'anchor': 'ordinary private realism',
                      'emotion': ['ordinary private moment',
                                  'unposed emotional realism',
                                  'quiet sensuality',
                                  'natural vulnerability']},
 'Pop Neon': {'anchor': 'electric nightlife excitement',
              'emotion': ['electric attraction', 'modern nightlife energy', 'glossy desire', 'color-driven tension']},
 'Baroque / Operatic': {'anchor': 'operatic emotional grandeur',
                        'emotion': ['theatrical intensity',
                                    'operatic elegance',
                                    'ceremonial drama',
                                    'grand emotional weight']},
 'Minimalist Psychological': {'anchor': 'restrained psychological distance',
                              'emotion': ['controlled distance',
                                          'cold stillness',
                                          'subtle pressure',
                                          'restrained vulnerability']},
 'Black & White Film': {'anchor': 'timeless classic-film restraint',
                        'emotion': ['austere drama', 'timeless contrast', 'classic film mood', 'tonal seriousness']},
 'Golden Hour Warmth': {'anchor': 'warm nostalgic tenderness',
                        'emotion': ['warm intimacy', 'soft radiance', 'nostalgic tenderness', 'peaceful affection']},
 'Vintage / Retro': {'anchor': 'nostalgic memory warmth',
                     'emotion': ['nostalgic warmth', 'faded memory', 'retro charm', 'gentle remembrance']},
 'Cyberpunk / Sci-fi': {'anchor': 'futuristic alienation and synthetic tension',
                        'emotion': ['futuristic tension', 'digital edge', 'neon isolation', 'synthetic atmosphere']},
 'Watercolor / Painterly': {'anchor': 'delicate handmade serenity',
                            'emotion': ['soft artistic beauty',
                                        'gentle impression',
                                        'painted serenity',
                                        'lyrical softness']},
 'Bright / High-key': {'anchor': 'cheerful airy optimism',
                       'emotion': ['cheerful lightness', 'clean radiance', 'fresh energy', 'airy calm']},
 'Cinematic Widescreen': {'anchor': 'grand narrative scale',
                          'emotion': ['epic scale',
                                      'dramatic scope',
                                      'visual storytelling',
                                      'large emotional breadth']},
 'Romantic / Soft Focus': {'anchor': 'tender romantic closeness',
                           'emotion': ['tender romance', 'gentle warmth', 'soft intimacy', 'dreamy closeness']},
 'Horror / Unsettling': {'anchor': 'creeping horror dread and unsettling silence',
                         'emotion': ['creeping dread', 'ominous tension', 'psychological horror', 'eerie silence']}})

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
 'Charcoal Drawing': {'anchor': 'expressive tonal drawing',
                      'lighting': ['broad tonal shading',
                                   'soft value gradation',
                                   'smudged shadow mass',
                                   'dramatic dark-paper contrast'],
                      'color': ['monochrome dark tones',
                                'deep black pigment',
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
 'Graphite Pencil Sketch': {'anchor': 'hand-drawn pencil study',
                            'lighting': ['soft drawn shading',
                                         'delicate value transitions',
                                         'light pencil hatching',
                                         'gentle tonal modeling'],
                            'color': ['silvery gray drawing tones',
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
 'Ink Wash / Sumi-e': {'anchor': 'sumi-e brush illustration',
                       'lighting': ['soft tonal wash values',
                                    'empty-space tonal balance',
                                    'misty ink gradation',
                                    'gentle paper brightness'],
                       'color': ['black brush tones', 'gray wash gradients', 'rice-paper white', 'subtle sepia wash'],
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
                         'texture': ['clean line art', 'flat color fills', 'subtle cel texture', 'crisp drawn edges']}})

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
                            'lighting': ['subtle graphite value modeling',
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
 'Pixel Art': {'anchor': 'crisp pixel-art rendering',
               'lighting': ['blocky lighting',
                            'dithered shadow shapes',
                            'limited-palette highlights',
                            'sprite-like light blocks'],
               'color': ['limited indexed palette', 'indexed color look', 'crisp color blocks', 'retro game colors'],
               'composition': ['sprite-like composition',
                               'grid-based visual structure',
                               'simple readable silhouette',
                               'retro game scene layout'],
               'texture': ['visible square grid',
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
                             'minimal detail texture']}}
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
STYLE_REFINEMENT_PATCH_2026_05_31_B = {'Dream Pastel Diffusion': {'anchor': 'dreamlike pastel painting with diffused luminous haze', 'lighting': ['milky diffused glow', 'soft ambient mist light', 'ethereal luminous mist', 'gentle bloom through pastel air', 'low-contrast scattered light', 'pearlescent ambient haze'], 'color': ['powder pastel palette', 'pink lavender mist', 'soft cyan veil', 'pearl white haze', 'pale cream undertones'], 'composition': ['floating atmospheric composition', 'layered haze depth', 'airy surreal spacing', 'soft drifting balance', 'unsharp painterly depth layers'], 'texture': ['powdery pastel diffusion', 'silky haze texture', 'soft pigment bloom', 'blurred pastel edges', 'matte luminous surface']}, 'Watercolor / Painterly': {'anchor': 'traditional watercolor painting study on textured paper', 'lighting': ['transparent watercolor wash light', 'soft ambient paper glow', 'gentle diffused tonal wash', 'pale luminous pigment wash', 'low-contrast hand-painted light'], 'color': ['transparent layered pigments', 'soft pigment wash', 'muted watercolor palette', 'edge-bleeding color', 'diluted mineral tones', 'pooled pigment blooms'], 'composition': ['loose watercolor study composition', 'brush-led visual flow', 'unfilled paper breathing room', 'hand-painted placement', 'soft unfinished paper margins', 'reserved white paper highlights', 'painterly negative space'], 'texture': ['wet-on-wet paint bleed', 'visible watercolor brush marks', 'paper grain beneath pigment', 'pigment bloom on paper', 'feathered edge diffusion', 'granulating watercolor texture', 'watery edge blooms', 'uneven hand-painted washes']}, 'Graphite Pencil Sketch': {'anchor': 'rough graphite pencil study sketch on paper', 'lighting': ['soft graphite value shading', 'delicate hand-shaded transitions', 'light pencil hatching', 'loose tonal modeling', 'unfinished graphite shadow blocks'], 'color': ['graphite gray tones', 'off-white sketchbook paper', 'silver-gray pencil values', 'pale paper-and-pencil palette'], 'composition': ['preliminary study sketch layout', 'visible construction lines', 'loose exploratory contours', 'unfinished study margins', 'draft underdrawing structure', 'quiet negative paper space'], 'texture': ['fine pencil grain', 'visible hatching', 'paper tooth', 'eraser-softened shading', 'graphite dust', 'smudged graphite', 'uneven pencil pressure marks']}, 'Pen and Ink Sketch': {'anchor': 'loose pen-and-ink study sketch on paper', 'lighting': ['line-based shadow', 'cross-hatched tonal contrast', 'inked shadow accents', 'graphic light separation', 'unfinished hatch shading'], 'color': ['black ink on warm paper', 'monochrome ink tones', 'sepia ink accent', 'raw black linework'], 'composition': ['exploratory study sketch layout', 'loose contour drawing', 'visible drafting marks', 'illustrative negative paper space', 'partly unfinished background lines', 'graphic silhouette rhythm'], 'texture': ['crosshatching', 'fine ink linework', 'dry pen texture', 'hand-inked strokes', 'stray pen marks', 'uneven ink pressure']}, 'Colored Pencil Illustration': {'anchor': 'colored pencil sketch study on textured paper', 'lighting': ['soft drawn shading', 'layered pencil highlight', 'gentle value modeling', 'hand-colored light', 'pencil-shaded color transitions'], 'color': ['layered colored pencil hues', 'soft saturated pencil color', 'warm sketchbook palette', 'subtle color layering', 'visible blended pencil pigment'], 'composition': ['colored-pencil sketch composition', 'visible underdrawing lines', 'gentle hand-drawn layout', 'clear drawn silhouette', 'partly unfinished sketchbook composition'], 'texture': ['colored pencil grain', 'visible pencil strokes', 'paper tooth', 'layered dry pencil pigment', 'uneven hand pressure marks']}, 'Pastel Chalk Drawing': {'anchor': 'rough pastel chalk study on textured paper', 'lighting': ['powdery soft light', 'diffused tonal glow', 'gentle chalk highlight', 'velvety shade transition', 'chalk-blocked soft shadows'], 'color': ['soft pastel pigments', 'chalky pink-blue palette', 'powdery warm tones', 'muted pastel layers', 'matte chalk colors'], 'composition': ['unfinished pastel study composition', 'smudged handmade edges', 'gentle figure-ground balance', 'unfinished sketchbook layout', 'broad chalk blocking'], 'texture': ['chalk dust texture', 'powdery pigment', 'soft smudged edges', 'toothy pastel paper', 'visible pastel strokes', 'finger-smudged transitions']}, 'Gouache Storybook Illustration': {'anchor': 'matte gouache storybook painting for a classic picture-book page', 'lighting': ['painted soft light', 'storybook page glow', 'opaque color lighting', 'gentle gouache illumination', 'flat matte painted light'], 'color': ['opaque gouache color', 'warm picture-book palette', 'matte saturated hues', 'hand-painted color blocks', 'cream paper undertones'], 'composition': ['classic picture-book composition', 'clear readable painted shapes', 'charming gouache arrangement', 'hand-painted scenic balance', 'simple storybook page staging'], 'texture': ['matte gouache texture', 'visible opaque brush marks', 'painted paper surface', 'layered gouache pigment', 'slightly uneven hand-painted edges']}, 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted storybook painting on paper', 'lighting': ['warm painted glow', 'gentle storybook light', 'soft atmospheric painted illumination', 'paper-soft sky light'], 'color': ['hand-painted natural palette', 'warm gentle greens', 'soft sky blues', 'cream highlights', 'matte storybook colors'], 'composition': ['storybook painting composition', 'clear readable silhouette', 'painted scenic staging', 'whimsical picture-book balance', 'simple hand-painted layout'], 'texture': ['hand-painted background texture', 'painted brush texture', 'storybook matte finish', 'soft paper surface', 'visible traditional brushwork']}, 'Volumetric Dust Light': {'anchor': 'volumetric light scattering through dusty air', 'lighting': ['visible light beams through dusty air', 'volumetric light shafts', 'soft scattered backlight', 'hazy side light', 'dust-mote glow'], 'color': ['warm amber haze', 'muted golden air', 'pale dusty highlights', 'soft smoky neutrals'], 'composition': ['atmosphere-forward composition', 'light rays crossing the scene', 'deep hazy layers', 'subject framed by suspended dust'], 'texture': ['floating dust motes', 'fine airborne particles', 'hazy volumetric atmosphere', 'soft bloom in the air', 'subtle particulate texture']}, 'Long Exposure Light Trails': {'anchor': 'long-exposure night light trails', 'lighting': ['streaked moving light', 'extended luminous trails', 'flowing exposure glow', 'night light ribbons', 'motion-blurred highlights'], 'color': ['red and white light streaks', 'neon trail accents', 'deep night contrast', 'glowing saturated lines'], 'composition': ['dynamic trail-led composition', 'motion path framing', 'diagonal streak rhythm', 'long-exposure scene balance'], 'texture': ['smooth light trails', 'motion blur streaks', 'glowing line traces', 'soft exposure bloom']}, 'Miniature Diorama': {'anchor': 'miniature diorama model scene', 'lighting': ['tiny model lighting', 'soft tabletop illumination', 'small-scale scene glow', 'gentle display-case light'], 'color': ['toy-like muted colors', 'painted miniature palette', 'small-scale material colors', 'soft diorama tones'], 'composition': ['miniature scale composition', 'diorama staging', 'tiny set arrangement', 'compressed small-world layout'], 'texture': ['miniature model texture', 'painted tiny surfaces', 'crafted material detail', 'small-scale set pieces']}, '3D Collectible Figure': {'anchor': 'stylized 3D collectible figure render', 'lighting': ['soft product-display lighting', 'gentle plastic highlight', 'toy showcase glow', 'clean studio display light'], 'color': ['painted figure colors', 'smooth material colors', 'collectible toy palette', 'clean resin tones'], 'composition': ['collectible figure presentation', 'toy-like character staging', 'display-stand composition', 'small figure centered layout'], 'texture': ['smooth resin surface', 'painted plastic material', 'subtle toy seams', 'matte vinyl finish', 'miniature sculpt detail']}}
STYLE_DNA.update(STYLE_REFINEMENT_PATCH_2026_05_31_B)
NONPHYSICAL_STYLE_REFINEMENT_2026_05_31_B = {'Dream Pastel Diffusion': {'anchor': 'dreamlike pastel haze and diffused luminous atmosphere', 'lighting': ['milky diffused glow', 'soft ambient mist light', 'low-contrast scattered light', 'pearlescent ambient haze'], 'color': ['powder pastel palette', 'pink lavender mist', 'soft cyan veil', 'pale cream undertones'], 'texture': ['powdery pastel diffusion', 'silky haze texture', 'soft pigment bloom', 'blurred pastel edges']}, 'Watercolor / Painterly': {'anchor': 'transparent watercolor wash and textured paper feel', 'lighting': ['transparent watercolor wash light', 'soft ambient paper glow', 'gentle diffused tonal wash'], 'color': ['transparent layered pigments', 'soft pigment wash', 'muted watercolor palette', 'edge-bleeding color'], 'texture': ['wet-on-wet paint bleed', 'paper grain beneath pigment', 'pigment bloom on paper', 'granulating watercolor texture']}, 'Graphite Pencil Sketch': {'anchor': 'graphite pencil sketch texture and hand-shaded tonal study', 'lighting': ['soft graphite value shading', 'light pencil hatching', 'unfinished graphite shadow blocks'], 'color': ['graphite gray tones', 'off-white sketchbook paper', 'silver-gray pencil values'], 'texture': ['fine pencil grain', 'visible hatching', 'paper tooth', 'smudged graphite']}, 'Pen and Ink Sketch': {'anchor': 'pen-and-ink linework and hand-drawn hatch shading', 'lighting': ['line-based shadow', 'cross-hatched tonal contrast', 'unfinished hatch shading'], 'color': ['black ink on warm paper', 'monochrome ink tones', 'raw black linework'], 'texture': ['crosshatching', 'fine ink linework', 'dry pen texture', 'stray pen marks']}, 'Colored Pencil Illustration': {'anchor': 'colored pencil texture and visible hand-drawn pigment', 'lighting': ['soft drawn shading', 'layered pencil highlight', 'pencil-shaded color transitions'], 'color': ['layered colored pencil hues', 'soft saturated pencil color', 'warm sketchbook palette'], 'texture': ['colored pencil grain', 'visible pencil strokes', 'paper tooth', 'layered dry pencil pigment']}, 'Pastel Chalk Drawing': {'anchor': 'powdery pastel chalk texture and smudged handmade softness', 'lighting': ['powdery soft light', 'diffused tonal glow', 'chalk-blocked soft shadows'], 'color': ['soft pastel pigments', 'chalky pink-blue palette', 'muted pastel layers'], 'texture': ['chalk dust texture', 'powdery pigment', 'soft smudged edges', 'toothy pastel paper']}, 'Gouache Storybook Illustration': {'anchor': 'matte gouache paint and classic picture-book surface', 'lighting': ['painted soft light', 'storybook page glow', 'flat matte painted light'], 'color': ['opaque gouache color', 'warm picture-book palette', 'matte saturated hues'], 'texture': ['matte gouache texture', 'visible opaque brush marks', 'painted paper surface']}, 'Hand-Painted Storybook Animation': {'anchor': 'hand-painted storybook surface and traditional brushwork', 'lighting': ['warm painted glow', 'gentle storybook light', 'paper-soft sky light'], 'color': ['hand-painted natural palette', 'matte storybook colors', 'cream highlights'], 'texture': ['hand-painted background texture', 'painted brush texture', 'soft paper surface']}, 'Volumetric Dust Light': {'anchor': 'volumetric dust light scattering atmosphere', 'lighting': ['visible light beams through dusty air', 'volumetric light shafts', 'soft scattered backlight', 'dust-mote glow'], 'color': ['warm amber haze', 'muted golden air', 'soft smoky neutrals'], 'texture': ['floating dust motes', 'fine airborne particles', 'hazy volumetric atmosphere']}, 'Long Exposure Light Trails': {'anchor': 'long-exposure glowing motion trails', 'lighting': ['streaked moving light', 'extended luminous trails', 'flowing exposure glow'], 'color': ['red and white light streaks', 'neon trail accents', 'deep night contrast'], 'texture': ['smooth light trails', 'motion blur streaks', 'glowing line traces']}, 'Oil Painting': {'anchor': 'oil paint surface and canvas brushwork', 'lighting': ['painted chiaroscuro light', 'warm impasto highlights', 'layered oil-paint shadow'], 'color': ['rich oil-paint colors', 'layered earth tones', 'deep blended pigments'], 'texture': ['visible oil brushstrokes', 'canvas weave texture', 'impasto paint ridges', 'thick pigment texture']}, 'Miniature Diorama': {'anchor': 'small-scale crafted model atmosphere', 'lighting': ['soft tabletop illumination', 'small-scale scene glow', 'gentle display-case light'], 'color': ['painted miniature palette', 'small-scale material colors', 'soft diorama tones'], 'texture': ['miniature model texture', 'painted tiny surfaces', 'crafted material detail']}, 'Pixel Art': {'anchor': 'crisp pixel-art rendering language', 'lighting': ['blocky pixel lighting', 'dithered shadow shapes', 'sprite-like light blocks'], 'color': ['limited pixel palette', 'indexed color look', 'retro game colors'], 'texture': ['visible square pixels', 'hard pixel edges', 'dithered texture', 'low-resolution pixel grid']}, '3D Collectible Figure': {'anchor': 'stylized collectible figure material and display finish', 'lighting': ['soft product-display lighting', 'gentle plastic highlight', 'toy showcase glow'], 'color': ['painted figure colors', 'collectible toy palette', 'clean resin tones'], 'texture': ['smooth resin surface', 'painted plastic material', 'matte vinyl finish', 'miniature sculpt detail']}, 'Apocalyptic Wasteland': {'anchor': 'post-apocalyptic wasteland atmosphere', 'lighting': ['ashen overcast light', 'smoky backlight', 'dim dust-filtered glow'], 'color': ['desaturated rust tones', 'ash gray palette', 'dusty earth colors'], 'texture': ['ash in the air', 'dusty debris', 'weathered surfaces']}, 'Chibi Style': {'anchor': 'cute simplified chibi visual language', 'lighting': ['cute simplified lighting', 'soft rounded highlights', 'bright playful light'], 'color': ['bright cute colors', 'simple saturated palette', 'soft candy tones'], 'texture': ['clean simplified shapes', 'rounded stylized edges', 'smooth cute finish']}}
NONPHYSICAL_STYLE_CUES.update(NONPHYSICAL_STYLE_REFINEMENT_2026_05_31_B)


STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24 = {
    'Vintage Film Look': {
        'anchor': 'faded analog film photograph aesthetic',
        'lighting': ['soft analog highlight roll-off', 'gentle halation around highlights', 'lifted shadows', 'nostalgic low-contrast illumination'],
        'color': ['washed-out film colors', 'muted vintage palette', 'faded color response', 'subtle amber-green film shift'],
        'composition': ['casual analog snapshot framing', 'relaxed candid composition', 'timeless film-photo balance', 'nostalgic snapshot framing'],
        'texture': ['visible fine film grain', 'slight emulsion softness', 'soft vignette', 'aged print texture', 'subtle scan-like texture']
    },
    'Chibi Style': {
        'anchor': 'in-place chibi restyling of existing visible main subject(s)',
        'lighting': ['bright playful lighting', 'soft rounded highlights', 'cute simplified light', 'gentle soft glow'],
        'color': ['bright cute colors', 'soft candy palette', 'simple cheerful color blocks', 'clean saturated anime colors'],
        'composition': ['oversized head with compact body', 'super-deformed SD proportions', 'short limbs and rounded cute face', 'existing visible main subject(s) restyled into chibi SD proportions'],
        'texture': ['clean simplified anime shapes', 'rounded stylized edges', 'smooth cute finish', 'minimal detail linework']
    }
}
STYLE_DNA.update(STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24)
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'clear chibi super-deformed SD character rendering', 'lighting': ['bright playful lighting', 'soft rounded highlights', 'gentle toy-like glow'], 'color': ['bright cute colors', 'soft candy palette', 'simple cheerful color blocks'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges', 'minimal cute linework']}})
STYLE_DNA.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'composition': ['larger head and compact body proportions', 'rounded simplified anime features', 'existing visible subject(s) restyled in place'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges']}})
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting'], 'color': ['bright cute colors'], 'texture': ['clean simplified anime shapes']}})

STYLE_DNA_COMPACT_STRENGTH_PATCH_2026_06_24 = {
    'Pastel Chalk Drawing': {'anchor': 'rough pastel-chalk artwork', 'lighting': ['chalky light'], 'color': ['powdery pigment'], 'composition': ['handmade paper study'], 'texture': ['broken chalk strokes and paper tooth']},
    'Graphite Pencil Sketch': {'anchor': 'rough graphite sketch', 'lighting': ['smudged graphite shading'], 'color': ['monochrome graphite tones'], 'composition': ['construction-line sketch layout'], 'texture': ['rough hatching and paper tooth']},
    'Charcoal Drawing': {'anchor': 'raw charcoal drawing', 'lighting': ['dark smudged shadow'], 'color': ['black charcoal tones'], 'composition': ['gestural drawing layout'], 'texture': ['broken charcoal strokes and dusty paper']},
    'Oil Painting': {'anchor': 'thick oil painting', 'lighting': ['painted highlights'], 'color': ['layered pigment'], 'composition': ['painterly composition'], 'texture': ['impasto brushstrokes and canvas texture']},
    'Watercolor / Painterly': {'anchor': 'watercolor painting on paper', 'lighting': ['transparent wash light'], 'color': ['diluted pigment'], 'composition': ['loose painted composition'], 'texture': ['bleeding edges and paper grain']},
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
        'anchor': 'crafted scale-model scene',
        'lighting': ['display-case illumination over a tiny model world', 'soft tabletop display lighting', 'small-scale handcrafted scene glow', 'gentle showcase lighting for a tabletop set'],
        'color': ['painted model-set palette', 'toy-like material colors', 'handcrafted scale-model tones', 'soft model-set color harmony'],
        'composition': ['small-scale handcrafted model composition', 'small-scale room model composition', 'tiny handcrafted environment staging', 'compressed model-world layout with tiny scale proportions'],
        'texture': ['handcrafted model texture', 'painted tiny surfaces', 'tiny set-piece detail', 'scale-model material finish', 'tiny props and furniture detail']
    },
    'Gouache Storybook Illustration': {
        'anchor': 'opaque gouache picture-book illustration with a matte storybook page feel',
        'lighting': ['flat matte painted light', 'soft painted storybook glow', 'opaque color lighting', 'gentle gouache illumination', 'calm page-like painted light'],
        'color': ['opaque gouache color blocks', 'warm picture-book palette', 'matte saturated hues', 'layered painted color shapes', 'cream paper undertones'],
        'composition': ['static picture-book illustration composition', 'clear readable painted shapes', 'storybook page staging', 'charming gouache illustration balance', 'single-page illustrated scene design'],
        'texture': ['matte gouache texture', 'visible opaque brush marks', 'painted paper surface', 'layered gouache pigment', 'slightly uneven hand-painted edges']
    },
    'Hand-Painted Storybook Animation': {
        'anchor': 'hand-painted 2D storybook animation frame',
        'lighting': ['warm painted animation glow', 'gentle storybook animation light', 'soft atmospheric painted illumination', 'paper-soft scene lighting for a hand-painted animation frame'],
        'color': ['hand-painted animation palette', 'warm gentle greens', 'soft sky blues', 'cream highlights', 'matte painted animation colors'],
        'composition': ['hand-painted animation keyframe composition', 'clear readable animated silhouette', 'storybook animation staging', 'frame-from-a-painted-animation balance', 'scene layout with animated storytelling energy'],
        'texture': ['hand-painted animation background texture', 'painted brush texture', 'storybook matte finish', 'soft paper-and-paint surface', 'visible traditional brushwork']
    },
    'Graphite Pencil Sketch': {
        'anchor': 'monochrome graphite pencil sketch on sketchbook paper',
        'lighting': ['monochrome graphite value shading', 'delicate hand-drawn tonal transitions', 'pencil-built light and shadow', 'cross-hatched tonal modeling', 'soft smudged graphite shading'],
        'color': ['graphite gray tones', 'off-white sketchbook paper', 'silver-gray pencil values', 'monochrome paper-and-pencil palette'],
        'composition': ['preliminary study sketch layout', 'visible construction lines', 'loose exploratory contours', 'unfinished study margins', 'draft underdrawing structure', 'quiet negative paper space'],
        'texture': ['visible graphite strokes', 'cross-hatching', 'paper tooth', 'eraser-softened shading', 'graphite dust', 'smudged graphite', 'uneven pencil pressure marks']
    },
    'Volumetric Dust Light': {
        'anchor': 'strong volumetric light rays scattering through dusty air',
        'lighting': ['visible volumetric light shafts', 'floating dust motes dancing in the light rays', 'sunbeams cutting through dusty air', 'soft scattered backlight through haze', 'cinematic shafts of light'],
        'color': ['warm amber haze', 'muted golden air', 'pale dusty highlights', 'soft smoky neutrals'],
        'composition': ['atmosphere-forward cinematic composition', 'light rays crossing the scene', 'deep hazy layers', 'subject framed by illuminated dust-filled air'],
        'texture': ['floating dust motes', 'fine airborne particles', 'hazy volumetric atmosphere', 'soft bloom in the air', 'particulate glow in the beams']
    },
    'Classical Studio Glamour': {
        'anchor': 'classic old-Hollywood studio glamour portrait',
        'lighting': ['controlled studio beauty lighting', 'butterfly lighting', 'broad soft key illumination', 'soft shadow lift', 'subtle edge highlight', 'velvety shadow falloff'],
        'color': ['ivory', 'warm gold', 'deep brown', 'soft champagne'],
        'composition': ['timeless glamour portrait composition', 'elegant beauty-editorial posture', 'balanced portrait composition', 'graceful negative space'],
        'texture': ['satin fabric', 'polished wood', 'soft tonal grain', 'polished studio finish']
    },
    'Neon Melancholy / Rain Glass': {
        'anchor': 'melancholic rainy-night neon city mood through wet glass',
        'lighting': ['neon spill through rain-soaked glass', 'magenta and cyan neon glow', 'blurred urban lights behind raindrops', 'moody wet-night reflections', 'dim ambient shadows with colored neon bloom'],
        'color': ['amber', 'deep red', 'muted cyan', 'green neon trace', 'magenta-violet night accents'],
        'composition': ['framing through wet glass', 'urban intimacy', 'isolated close framing', 'rainy-night city reflection layering', 'emotionally moody window-side composition'],
        'texture': ['rain-soaked neon reflections', 'humid haze', 'wet-window bokeh', 'soft motion blur', 'diffused signage reflections through droplets']
    }
}
STYLE_DNA.update(STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_B)
NONPHYSICAL_STYLE_CUES.update({
    'Miniature Diorama': {'anchor': 'crafted scale-model atmosphere with miniature figure subject', 'lighting': ['soft tabletop display lighting', 'small-scale handcrafted scene glow'], 'color': ['painted model-set palette', 'toy-like material colors'], 'texture': ['handcrafted model texture', 'scale-model material finish']},
    'Pastel Chalk Drawing': {'anchor': 'chalky soft pastel drawing atmosphere', 'lighting': ['powder-soft diffuse light', 'soft chalk-muted light'], 'color': ['soft pastel pigments', 'chalky pastel tones'], 'texture': ['visible chalky pastel strokes', 'paper tooth texture', 'hand-smudged shading']},
    'Gouache Storybook Illustration': {'anchor': 'opaque gouache picture-book surface and matte painted storybook page feel', 'lighting': ['flat matte painted light', 'soft painted storybook glow'], 'color': ['opaque gouache color blocks', 'warm picture-book palette'], 'texture': ['matte gouache texture', 'visible opaque brush marks']},
    'Hand-Painted Storybook Animation': {'anchor': 'hand-painted 2D storybook animation frame atmosphere', 'lighting': ['warm painted animation glow', 'gentle storybook animation light'], 'color': ['hand-painted animation palette', 'matte painted animation colors'], 'texture': ['painted animation background texture', 'visible traditional brushwork']},
    'Graphite Pencil Sketch': {'anchor': 'monochrome graphite pencil sketch texture and hand-drawn tonal study', 'lighting': ['monochrome graphite value shading', 'cross-hatched tonal modeling'], 'color': ['graphite gray tones', 'monochrome paper-and-pencil palette'], 'texture': ['visible graphite strokes', 'cross-hatching', 'paper tooth', 'smudged graphite']},
    'Volumetric Dust Light': {'anchor': 'strong volumetric dust-lit atmosphere', 'lighting': ['visible volumetric light shafts', 'floating dust motes dancing in the light rays'], 'color': ['warm amber haze', 'muted golden air'], 'texture': ['hazy volumetric atmosphere', 'particulate glow in the beams']},
    'Classical Studio Glamour': {'anchor': 'classic old-Hollywood studio glamour mood', 'lighting': ['controlled studio beauty lighting', 'butterfly lighting'], 'color': ['ivory', 'warm gold', 'soft champagne'], 'texture': ['soft tonal grain', 'polished studio finish']},
    'Neon Melancholy / Rain Glass': {'anchor': 'rainy-night neon melancholy through wet glass', 'lighting': ['magenta and cyan neon glow', 'blurred urban lights behind raindrops'], 'color': ['muted cyan', 'deep red', 'magenta-violet night accents'], 'texture': ['wet-window bokeh', 'diffused signage reflections through droplets']}
})
STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_C = {
    'Chibi Style': {
        'composition': ['oversized head with compact body', 'super-deformed SD proportions', 'short limbs and rounded cute face', 'in-place chibi restyling of the existing visible main subject(s)', 'existing scene population and spatial arrangement kept unchanged', 'external prompt used only as identity, outfit, pose, and scene reference']
    },
    'Pastel Chalk Drawing': {
        'anchor': 'true soft pastel drawing on textured paper',
        'lighting': ['powder-soft diffuse light', 'gentle pastel-lit atmosphere', 'soft chalk-muted light', 'low-contrast pastel illumination'],
        'color': ['soft pastel pigments', 'chalky pastel tones', 'powdery pink-blue-lilac color harmony', 'muted layered pastel color'],
        'composition': ['hand-drawn pastel composition', 'clear but softly rendered scene structure', 'readable figure-and-background placement', 'soft sketchbook scene balance'],
        'texture': ['visible chalky pastel strokes', 'powdery pigment buildup', 'hand-smudged shading', 'paper tooth texture', 'dry pastel edges']
    },
    'Miniature Diorama': {
        'anchor': 'handcrafted tabletop miniature diorama with miniature figure subject',
        'lighting': ['display-case illumination over a tiny model world', 'soft tabletop display lighting', 'small-scale handcrafted scene glow', 'gentle showcase lighting for a tabletop set'],
        'color': ['painted model-set palette', 'toy-like material colors', 'handcrafted scale-model tones', 'soft model-set color harmony'],
        'composition': ['the main subject appears as a miniature figure', 'subject, props, and environment share one consistent miniature scale', 'small-scale handcrafted model composition', 'tiny handcrafted environment staging', 'compressed model-world layout with tiny scale proportions'],
        'texture': ['handcrafted model texture', 'painted tiny surfaces', 'tiny set-piece detail', 'scale-model material finish', 'tiny props and furniture detail']
    },
    'Graphite Pencil Sketch': {
        'anchor': 'detailed pencil illustration with fine line art and soft graphite shading',
        'lighting': ['subtle graphite value modeling', 'hand-drawn tonal depth', 'gentle pencil-modeled light', 'careful value transitions'],
        'color': ['monochrome graphite tones', 'subtle gray pencil palette', 'paper-and-graphite harmony', 'classic sketchbook neutrals'],
        'composition': ['coherent pencil illustration composition', 'clear room-and-window scene structure', 'readable background perspective', 'balanced hand-drawn layout'],
        'texture': ['delicate graphite linework', 'delicate pencil strokes', 'precise cross-hatching', 'subtle paper texture', 'rich graphite texture']
    },
    'Colored Pencil Illustration': {
        'anchor': 'colored-pencil illustration with visible layered pencil work on paper',
        'lighting': ['drawn colored-pencil shading', 'layered pencil highlight', 'dry hand-rendered light', 'pencil-built tonal modeling'],
        'color': ['layered colored-pencil hues', 'visible dry pigment layering', 'warm hand-colored palette', 'cross-layered pencil color'],
        'composition': ['colored-pencil illustration composition', 'visible hand-drawn outlines', 'clear sketched silhouette', 'paper-based illustration layout'],
        'texture': ['obvious colored-pencil strokes', 'paper tooth', 'dry pigment buildup', 'layered pencil grain', 'visible hand-pressure marks']
    },
    'Apocalyptic Wasteland': {
        'anchor': 'bleak devastated post-apocalyptic wasteland',
        'lighting': ['ashen overcast light', 'harsh survival sunlight', 'smoky backlight', 'dim dust-filtered glow', 'soot-choked daylight'],
        'color': ['desaturated rust tones', 'ash gray palette', 'burnt orange accents', 'dusty earth colors', 'charred brown ruin tones'],
        'composition': ['desolate survival composition', 'collapsed-ruin staging', 'ruined-world storytelling', 'abandoned end-of-civilization framing', 'widespread devastation'],
        'texture': ['ash in the air', 'worn metal texture', 'cracked concrete', 'dusty debris', 'weathered surfaces', 'rubble piles', 'scorched ruin detail']
    }
}
STYLE_DNA.update(STYLE_TARGETED_REINFORCEMENT_PATCH_2026_06_24_C)
NONPHYSICAL_STYLE_CUES.update({
    'Pastel Chalk Drawing': {'anchor': 'true soft pastel drawing atmosphere', 'lighting': ['powder-soft diffuse light', 'soft chalk-muted light'], 'color': ['soft pastel pigments', 'chalky pastel tones'], 'texture': ['visible chalky pastel strokes', 'paper tooth texture', 'hand-smudged shading']},
    'Graphite Pencil Sketch': {'anchor': 'detailed pencil illustration with fine line art and soft graphite shading', 'lighting': ['subtle graphite value modeling', 'hand-drawn tonal depth'], 'color': ['monochrome graphite tones', 'subtle gray pencil palette'], 'texture': ['delicate graphite linework', 'delicate pencil strokes', 'precise cross-hatching', 'subtle paper texture']},
    'Colored Pencil Illustration': {'anchor': 'colored-pencil illustration texture with visible layered pencil work', 'lighting': ['drawn colored-pencil shading', 'dry hand-rendered light'], 'color': ['layered colored-pencil hues', 'visible dry pigment layering'], 'texture': ['obvious colored-pencil strokes', 'paper tooth', 'dry pigment buildup']},
    'Apocalyptic Wasteland': {'anchor': 'devastated post-apocalyptic wasteland mood', 'lighting': ['ashen overcast light', 'smoky backlight'], 'color': ['desaturated rust tones', 'ash gray palette', 'charred brown ruin tones'], 'texture': ['ash in the air', 'rubble piles', 'scorched ruin detail']},
    'Chibi Style': {'anchor': 'in-place chibi restyling of existing visible main subject(s)', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges']}
})
STYLE_DNA.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'composition': ['larger head and compact body proportions', 'rounded simplified anime features', 'existing visible subject(s) restyled in place'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges']}})
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'in-place SD restyle', 'lighting': ['bright playful lighting'], 'color': ['bright cute colors'], 'texture': ['clean simplified anime shapes']}})
# Chibi DNA ratio reinforcement requested in follow-up: keep the prompt simple, but make the DNA itself explicit.
NONPHYSICAL_STYLE_CUES.update({'Chibi Style': {'anchor': 'delightful adorable chibi style illustration', 'lighting': ['bright playful lighting', 'soft rounded highlights', 'gentle cozy glow'], 'color': ['bright cute colors', 'soft candy palette', 'vibrant cheerful tones'], 'texture': ['clean lineart', 'rounded stylized edges', 'whimsical illustration feel']}})
STYLE_DNA.update({'Chibi Style': {'anchor': 'cute chibi character illustration', 'lighting': ['bright playful lighting', 'soft rounded highlights'], 'color': ['bright cute colors', 'soft candy palette'], 'composition': ['oversized head', 'tiny compact body', 'short simplified limbs when visible', 'super-deformed chibi proportions'], 'texture': ['clean simplified anime shapes', 'rounded stylized edges', 'big expressive eyes', 'soft rosy cheeks']}})
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
MODEL_KEY_KNOWN = {"pony", "ilxl", "sdxl", "sd", "anima", "flux", "qwen", "zimage", "krea2", "universal"}


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
    if "krea" in profile_name:
        return "krea2"
    if "qwen" in profile_name:
        return "qwen"
    if re.search(r"\bz[-_ ]?image\b", profile_name):
        return "zimage"
    fallback = _canonical_model_key(_get_model_profile(model_profile).get("model_key"))
    return fallback or "universal"



# ── Standalone prompt builder UI/options ─────────────────────────────────────
PROMPT_SOURCE_MODE_OPTIONS: List[str] = [
    "Auto",
    "External Prompt Composer",
    "Standalone Scene Builder",
    "Style Only",
]

STANDALONE_OPTIONS: Dict[str, List[str]] = {
    "prompt_source_mode": PROMPT_SOURCE_MODE_OPTIONS,
    "builder_detail_mode": ["simple", "advanced", "professional"],
    "subject_profile": [
        "auto",
        "adult woman",
        "adult man",
        "adult couple",
        "two adult women",
        "two adult men",
        "small adult group",
        "background only",
        "product / object",
    ],
    "subject_age": ["auto", "20s", "30s", "40s", "50s", "60s+"],
    "subject_appearance": [
        "auto",
        "natural-looking",
        "cute",
        "beautiful",
        "elegant",
        "glamorous",
        "ordinary-looking",
        "simple-looking",
        "less conventionally attractive",
        "distinctive-looking",
    ],
    "subject_ethnicity": [
        "auto",
        "Korean",
        "East Asian",
        "Southeast Asian",
        "South Asian",
        "Western",
        "Black",
        "Latino",
        "Middle Eastern",
        "mixed-heritage",
    ],
    "subject_hair": [
        "auto",
        "short hair",
        "long dark hair",
        "long hair",
        "wavy hair",
        "bob cut",
        "ponytail",
        "updo",
        "straight long hair",
        "shoulder-length hair",
        "medium-length hair",
        "layered hair",
        "side-parted hair",
        "bangs",
        "braided hair",
        "twin braids",
        "messy bun",
        "half-up hairstyle",
        "short bob",
        "pixie cut",
        "curly hair",
        "wet hair",
        "wind-swept hair",
        "tied-back hair",
    ],
    "subject_outfit": [
        "auto",
        "casual jeans and t-shirt",
        "white blouse and dark skirt",
        "knit sweater and skirt",
        "summer dress",
        "elegant long dress",
        "business suit",
        "office blouse and slacks",
        "hoodie and jeans",
        "denim jacket outfit",
        "trench coat outfit",
        "winter coat and scarf",
        "sportswear",
        "swimwear / beachwear",
        "traditional hanbok",
        "simple black dress",
        "blouse and jeans",
        "cardigan and skirt",
        "oversized knit sweater",
        "blazer and jeans",
        "leather jacket outfit",
        "long coat outfit",
        "cropped jacket outfit",
        "pleated skirt outfit",
        "denim shorts and blouse",
        "linen shirt and trousers",
        "floral dress",
        "satin blouse and skirt",
        "evening gown",
        "cocktail dress",
        "business casual outfit",
        "streetwear outfit",
        "casual athleisure",
        "yoga outfit",
        "raincoat outfit",
        "apron dress",
        "modern hanbok",
        "pajamas / loungewear",
    ],
    "subject_expression": [
        "auto",
        "natural expression",
        "gentle smile",
        "broad smile",
        "bright happy smile",
        "laughing face",
        "soft closed-mouth smile",
        "shy smile",
        "playful wink",
        "confident smile",
        "serious expression",
        "dreamy expression",
        "thoughtful expression",
        "melancholic expression",
        "sad expression",
        "tearful eyes",
        "crying face",
        "lonely expression",
        "worried expression",
        "anxious expression",
        "surprised expression",
        "angry expression",
        "annoyed expression",
        "pouting face",
        "sulky expression",
        "coy expression",
        "sassy expression",
        "smug expression",
        "embarrassed blush",
        "tired expression",
        "calm blank expression",
        "determined expression",
        "seductive expression",
    ],
    "subject_pose": [
        "auto",
        "standing",
        "sitting",
        "leaning",
        "walking",
        "looking back",
        "reclining",
        "lying down",
        "standing with arms crossed",
        "standing with hands on hips",
        "standing with one hand in pocket",
        "hand near face",
        "hand on cheek",
        "sitting cross-legged",
        "seated sideways",
        "crouching",
        "kneeling",
        "running",
        "dancing",
        "jumping lightly",
        "stretching",
        "reaching upward",
        "turning sideways",
        "side profile pose",
    ],
    "subject_action": [
        "auto",
        "standing still",
        "sitting at a table",
        "walking naturally",
        "looking out the window",
        "looking at the camera",
        "reading a book",
        "using a phone",
        "working on a laptop",
        "drinking from a cup",
        "holding a flower bouquet",
        "carrying a handbag",
        "taking a selfie",
        "listening to music",
        "looking in a mirror",
        "resting on a bed",
        "standing in water",
        "waiting at a station",
        "shopping on a street",
        "opening curtains",
        "cooking in kitchen",
        "writing in a notebook",
        "sketching in a notebook",
        "applying makeup",
        "brushing hair",
        "watering plants",
        "arranging flowers",
        "browsing bookshelves",
        "browsing a shop display",
        "taking a photo",
        "holding an umbrella",
        "carrying a suitcase",
        "playing guitar",
        "dancing",
        "jogging",
        "riding a bicycle",
        "stretching on a mat",
        "fixing hair",
        "adjusting glasses",
        "tying shoelaces",
        "looking down thoughtfully",
        "smiling at someone",
        "talking with another person",
        "waiting under rain",
        "sitting by the window",
    ],
    "location_type": [
        "auto",
        "cozy living room",
        "modern apartment",
        "bedroom",
        "bathroom",
        "hotel room",
        "cafe",
        "restaurant",
        "office",
        "library",
        "bookstore",
        "kitchen",
        "art gallery",
        "bar / lounge",
        "balcony",
        "rooftop",
        "city street",
        "shopping street",
        "alley",
        "train station",
        "subway platform",
        "park",
        "garden",
        "forest",
        "beach",
        "poolside",
        "studio backdrop",
        "private studio",
        "hanok room",
        "traditional Korean courtyard",
        "greenhouse",
        "museum",
        "theater stage",
        "dressing room",
        "makeup room",
        "photo studio",
        "hotel lobby",
        "corridor hallway",
        "elevator lobby",
        "convenience store",
        "supermarket",
        "bakery",
        "flower shop",
        "salon",
        "gym",
        "yoga studio",
        "airport terminal",
        "riverside walkway",
        "bridge",
        "lake shore",
        "mountain trail",
        "campsite",
        "parking garage",
        "night market",
        "indoor pool",
        "laundromat",
    ],
    "location_detail": [
        "auto",
        "minimal modern",
        "luxury",
        "vintage classic",
        "dark intimate",
        "bright spacious",
        "natural organic",
        "cozy warm",
        "cinematic",
        "soft romantic",
        "moody low-key",
        "rainy urban",
        "rustic worn",
        "cluttered lived-in",
        "clean minimal",
        "premium hotel",
        "traditional Korean",
        "industrial",
        "futuristic neon",
        "soft pastel",
        "high-contrast dramatic",
    ],
    "time_of_day": [
        "auto",
        "dawn",
        "morning",
        "daytime",
        "afternoon",
        "late afternoon",
        "evening",
        "sunset",
        "night",
        "late night",
    ],
    "weather_light": [
        "auto",
        "clear",
        "cloudy",
        "rainy",
        "snowy",
        "foggy",
        "indoor lighting only",
        "soft indoor lighting",
        "golden hour sunlight",
        "sunset backlight",
        "moonlight",
        "neon lights",
        "window light",
        "strong sunlight",
        "overcast soft light",
        "backlit silhouette",
        "low-key lighting",
        "rim light",
        "candlelight",
        "fluorescent indoor light",
        "streetlights",
        "rainy neon reflections",
    ],
    "scene_props": [
        "auto",
        "none",
        "plants",
        "book / magazine",
        "cup / drink",
        "smartphone",
        "lamp",
        "mirror",
        "umbrella",
        "studio lighting",
        "luxury interior details",
        "cosmetic product",
        "laptop",
        "flower bouquet",
        "handbag",
        "shopping bag",
        "camera",
        "suitcase",
        "headphones",
        "tableware",
        "window",
        "curtains",
        "sofa",
        "chair",
        "desk",
        "bed",
        "bookshelf",
        "picture frames",
        "potted plants",
        "vase",
        "flowers",
        "notebook and pen",
        "art supplies",
        "makeup tools",
        "perfume bottle",
        "blanket / fabric",
        "pillows",
        "street signs",
        "neon signs",
        "bench",
        "bicycle",
        "food / dessert",
        "display shelves",
        "shopping cart",
        "luggage",
        "train doors",
        "guitar",
        "microphone",
    ],
    "auto_extra_detail": [
        "auto",
        "light auto fill",
        "balanced auto fill",
        "rich auto fill",
    ],
    "adult_menu_level": ["essential", "professional"],
    "adult_exposure_level": [
        "auto",
        "clothed sensual",
        "revealing outfit",
        "lingerie / underwear",
        "swimwear",
        "implied nude / covered",
        "sheet-covered nude",
        "nude",
        "topless",
        "wet look swimwear",
        "bodycon fashion",
    ],
    "adult_scene_privacy": [
        "auto",
        "private indoor",
        "bedroom / hotel room",
        "boudoir bedroom",
        "luxury hotel suite",
        "private lounge",
        "studio",
        "dressing room",
        "bathroom",
        "spa / bath",
        "poolside / beach",
    ],
    "adult_scene_mood": [
        "auto",
        "soft boudoir",
        "romantic warm intimacy",
        "fashion editorial sensual",
        "luxury hotel evening",
        "private mirror moment",
        "noir intimate",
        "spa calm",
        "poolside glamour",
        "beach sunset sensual",
        "studio glamour",
        "cozy morning softness",
        "after-bath softness",
        "midnight hotel intimacy",
        "soft lingerie editorial",
        "warm sheet-covered mood",
        "fine-art nude calm",
        "private dressing-room mood",
        "mirror-lit sensuality",
        "rainy-window intimacy",
        "candlelit romantic privacy",
        "glossy fashion sensuality",
        "quiet teasing mood",
    ],
    "adult_pose_style": [
        "auto",
        "relaxed sensual pose",
        "reclining sensual pose",
        "seated sensual pose",
        "standing confident pose",
        "looking over shoulder",
        "intimate portrait pose",
        "sitting on bed edge",
        "lying on side",
        "wrapped in sheets",
        "standing by mirror",
        "leaning against wall",
        "adjusting robe",
        "poolside lounging",
        "back turned silhouette",
        "seated on floor",
        "kneeling portrait pose",
        "sitting by window",
        "lying on stomach",
        "stretching on bed",
        "hands in hair",
        "covering with sheet",
        "holding robe closed",
        "side-profile silhouette",
        "seated mirror pose",
        "one leg bent pose",
        "soft arched pose",
        "hands near collarbone",
        "looking down softly",
        "turning away with glance",
    ],
    "adult_lighting": [
        "auto",
        "warm bedside light",
        "low-key shadow",
        "soft window backlight",
        "candlelit glow",
        "studio rim light",
        "neon lounge light",
        "steamy bathroom light",
        "sunset backlight",
        "warm window glow",
        "moonlit room",
        "rainy window light",
        "bathroom mirror light",
        "soft vanity lights",
        "hotel lamp glow",
        "silhouette backlight",
        "high-key studio glamour",
        "softbox glow",
        "colored gel rim light",
    ],
    "adult_scene_props": [
        "auto",
        "satin sheets",
        "sheer curtains",
        "bedside lamp",
        "large mirror",
        "velvet chair",
        "silk fabric",
        "candles",
        "bath steam",
        "pool reflection",
        "studio softbox",
        "curtains and pillows",
        "robe",
        "towel",
        "vanity table",
        "makeup mirror",
        "perfume bottle",
        "glass shower",
        "bathtub edge",
        "lace curtains",
        "soft rug",
        "dressing screen",
        "window curtains",
        "silk pillow",
        "jewelry tray",
        "floor cushion",
    ],
    "adult_body_focus": [
        "auto",
        "face and expression",
        "upper body elegance",
        "full body silhouette",
        "legs-focused fashion framing",
        "back and shoulder silhouette",
        "hands and fabric detail",
        "non-graphic body line",
        "face with hands",
        "neckline and shoulders",
        "waist silhouette",
        "fabric-covered form",
        "profile body line",
        "hair and shoulder line",
        "mirror reflection focus",
    ],
    "adult_framing_bias": [
        "auto",
        "portrait safe",
        "close portrait",
        "upper body",
        "waist-up",
        "full body",
        "tasteful silhouette",
        "editorial full body",
        "fabric detail close-up",
        "body-focused non-graphic",
    ],
}

STANDALONE_UI_DEFAULTS: Dict[str, Any] = {
    "prompt_source_mode": "Auto",
    "builder_detail_mode": "simple",
    "subject_profile": "auto",
    "subject_age": "auto",
    "subject_appearance": "auto",
    "subject_ethnicity": "auto",
    "subject_hair": "auto",
    "subject_outfit": "auto",
    "subject_expression": "auto",
    "subject_pose": "auto",
    "subject_action": "auto",
    "location_type": "auto",
    "location_detail": "auto",
    "time_of_day": "auto",
    "weather_light": "auto",
    "scene_props": "auto",
    "auto_extra_detail": "auto",
    "adult_menu_level": "essential",
    "adult_exposure_level": "auto",
    "adult_scene_privacy": "auto",
    "adult_scene_mood": "auto",
    "adult_pose_style": "auto",
    "adult_lighting": "auto",
    "adult_scene_props": "auto",
    "adult_body_focus": "auto",
    "adult_framing_bias": "auto",
}


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
    **STANDALONE_UI_DEFAULTS,
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
    if widget_name in STANDALONE_OPTIONS:
        values = set(STANDALONE_OPTIONS.get(widget_name, []))
        if widget_name == "subject_age":
            values.add("adult")
        return values
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


def _explicitness_text_pool(value: Any) -> List[str]:
    """Return safe custom adult-tone phrases from data/explicitness.json.

    The file is public and user-editable. Strings are treated as one natural
    phrase; lists of strings are accepted for advanced customization; dicts and
    other structured values are ignored so Python/JSON representations never
    leak into the prompt.
    """
    if isinstance(value, str):
        cleaned = _clean_text(value)
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                cleaned = _clean_text(item)
                if cleaned:
                    out.append(cleaned)
        return out
    return []


def _explicitness_value_signature(value: Any) -> Tuple[str, ...]:
    return tuple(x.lower() for x in _explicitness_text_pool(value))


def _custom_explicitness_terms(adult_tone: str) -> Tuple[bool, List[str]]:
    """Return user-edited natural adult-tone cues, if explicitness.json changed.

    Shipped data/explicitness.json exists for editing/documentation, but older
    tuned prompts did not use it. To avoid broad prompt drift, default shipped
    values do not replace the internal wording. When a user changes an existing
    key, that key becomes the natural-language adult-tone override.
    """
    tone = _canonical_ui_value(adult_tone, "adult_tone")
    if not isinstance(EXPLICITNESS, dict):
        return False, []
    if tone not in EXPLICITNESS:
        return False, []
    current_sig = _explicitness_value_signature(EXPLICITNESS.get(tone, ""))
    default_sig = _explicitness_value_signature(EXPLICITNESS_DEFAULT.get(tone, ""))
    if current_sig == default_sig:
        return False, []
    return True, _explicitness_text_pool(EXPLICITNESS.get(tone, ""))


def _adult_tone_terms(adult_tone: str, family: str = "tag") -> List[str]:
    tone = _canonical_ui_value(adult_tone, "adult_tone")
    if family == "natural":
        has_custom_explicitness, custom_terms = _custom_explicitness_terms(tone)
        if has_custom_explicitness:
            return custom_terms
        mapping = {
            "default": [],
            "safe": ["tasteful adult mood"],
            "suggestive": ["suggestive adult mood"],
            "sensual": ["sensual adult mood"],
            "bold sensual": ["bold mature sensual mood", "seductive tension"],
            "nsfw": ["adult erotic mood", "erotic tension"],
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
    "lace slip": "sensual",
    "satin lingerie": "sensual",
    "sheer blouse": "suggestive",
    "transparent robe": "sensual",
    "high-slit dress": "suggestive",
    "backless dress": "suggestive",
    "deep v dress": "suggestive",
    "bodycon dress": "suggestive",
    "wet shirt": "sensual",
    "silk pajamas": "suggestive",
    "oversized sweater": "suggestive",
    "stockings and garter": "sensual",
    "strappy lingerie": "sensual",
    "lace bralette set": "sensual",
    "satin corset set": "sensual",
    "see-through cover-up": "sensual",
    "black lace lingerie": "sensual",
    "white button shirt": "suggestive",
    "black bodysuit": "suggestive",
    "red evening dress": "suggestive",
    "satin slip dress": "sensual",
    "swimsuit cover-up": "suggestive",
    "robe and lingerie": "sensual",
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
    r"(에게서는|한테서는|으로서는|로서는|에게는|한테는|께서는|으로는|로는|에서는|"
    r"에게서|한테서|에게|한테|께|으로서|로서|으로|에서|"
    r"은|는|이|가|을|를|의|와|과|도|만|에|로|서|부터|까지|처럼|보다|"
    r"랑|만큼|하고|마다|이나|나|야)?"
)
_KO_MINOR_GIRL_PATTERN = rf"(?<![가-힣])(?:어린|미성년|청소년|10대)\s*소녀{_KO_MINOR_SUBJECT_SUFFIX}(?![가-힣])"
_KO_MINOR_BOY_PATTERN = rf"(?<![가-힣])(?:어린|미성년|청소년|10대)\s*소년{_KO_MINOR_SUBJECT_SUFFIX}(?![가-힣])"

def _ko_particle_after_adult_subject(particle: str) -> str:
    particle = particle or ""
    return {
        "가": "이",
        "를": "을",
        "는": "은",
        "와": "과",
        "로": "으로",
        "로서": "으로서",
        "로는": "으로는",
        "랑": "이랑",
        "나": "이나",
        "야": "이야",
        "서": "으로서",
    }.get(particle, particle)

def _replace_ko_minor_girl(match: re.Match) -> str:
    return "성인 여성" + _ko_particle_after_adult_subject(match.group(1) or "")

def _replace_ko_minor_boy(match: re.Match) -> str:
    return "성인 남성" + _ko_particle_after_adult_subject(match.group(1) or "")
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
    (re.compile(r"\bteen(?:age|ager)?\s+(?:[a-z][a-z-]*\s+){0,4}school\s*girl\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\bteen(?:age|ager)?\s+(?:[a-z][a-z-]*\s+){0,4}schoolgirl\b", re.IGNORECASE), "adult woman"),
    (re.compile(r"\bteen(?:age|ager)?\s+(?:[a-z][a-z-]*\s+){0,4}school\s*boy\b", re.IGNORECASE), "adult man"),
    (re.compile(r"\bteen(?:age|ager)?\s+(?:[a-z][a-z-]*\s+){0,4}schoolboy\b", re.IGNORECASE), "adult man"),
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

    (re.compile(_KO_MINOR_GIRL_PATTERN), _replace_ko_minor_girl),
    (re.compile(_KO_MINOR_BOY_PATTERN), _replace_ko_minor_boy),
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
    r"lingerie|underwear)\b"
    r"|노출|나체|누드|성인물|야한|섹스|성행위|포르노|란제리|속옷",
    re.IGNORECASE,
)




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


def _rewrite_adult_school_terms(text: Any, adult_tone: str = "default") -> str:
    s = _normalize_text(text)
    tone = _canonical_ui_value(adult_tone, "adult_tone") or "default"
    if _tone_rank(tone) < _tone_rank("suggestive"):
        return s
    s = re.sub(r"\badult\s+(?:[a-z][a-z-]*\s+){0,4}school\s*girl\b", "adult woman", s, flags=re.IGNORECASE)
    s = re.sub(r"\badult\s+(?:[a-z][a-z-]*\s+){0,4}schoolgirl\b", "adult woman", s, flags=re.IGNORECASE)
    s = re.sub(r"\badult\s+(?:[a-z][a-z-]*\s+){0,4}school\s*boy\b", "adult man", s, flags=re.IGNORECASE)
    s = re.sub(r"\badult\s+(?:[a-z][a-z-]*\s+){0,4}schoolboy\b", "adult man", s, flags=re.IGNORECASE)
    return _normalize_text(s)


def _sanitize_minor_conflict_text(text: Any, adult_tone: str = "default") -> str:
    """Narrow safety harmonizer for explicit adult/minor cue collisions only."""
    s = _rewrite_adult_school_terms(text, adult_tone)
    if not _adult_minor_conflict_needs_rewrite(s, adult_tone):
        return s
    for pat, repl in MINOR_CONFLICT_REPLACEMENTS:
        s = pat.sub(repl, s)
    s = _rewrite_adult_school_terms(s, adult_tone)
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


def _safe_free_text_input(value: Any) -> str:
    """Accept only actual text for free-text prompt inputs.

    ComfyUI force-input sockets can sometimes receive non-string objects from a
    mismatched upstream node.  Returning an empty string prevents Python/JSON
    representations such as ``['x']`` or ``{'a': 1}`` from leaking into prompts
    while preserving normal string inputs byte-for-byte for the existing cleanup
    pipeline.
    """
    if value is None:
        return ""
    return value if isinstance(value, str) else ""


def _is_escaped_at(text: str, idx: int) -> bool:
    backslashes = 0
    pos = idx - 1
    while pos >= 0 and text[pos] == "\\":
        backslashes += 1
        pos -= 1
    return bool(backslashes % 2)


def _count_unescaped_char(text: str, target: str) -> int:
    return sum(1 for idx, ch in enumerate(text) if ch == target and not _is_escaped_at(text, idx))



def _remove_unescaped_char_limited(text: str, target: str, limit: int, *, from_right: bool = False) -> str:
    if limit <= 0:
        return text
    indices = [
        idx
        for idx, ch in enumerate(text)
        if ch == target and not _is_escaped_at(text, idx)
    ]
    if not indices:
        return text
    remove = set(indices[-limit:] if from_right else indices[:limit])
    return "".join(ch for idx, ch in enumerate(text) if idx not in remove)


def _balance_outer_attention_edges(text: str) -> str:
    c = _clean_text(text)
    for opening, closing in (("(", ")"), ("[", "]")):
        opening_count = _count_unescaped_char(c, opening)
        closing_count = _count_unescaped_char(c, closing)
        if opening_count > closing_count:
            c = _remove_unescaped_char_limited(c, opening, opening_count - closing_count, from_right=False)
        elif closing_count > opening_count:
            c = _remove_unescaped_char_limited(c, closing, closing_count - opening_count, from_right=True)
    return _clean_text(c)


def _attention_brackets_balanced(text: str) -> bool:
    return (
        _count_unescaped_char(text, "(") == _count_unescaped_char(text, ")")
        and _count_unescaped_char(text, "[") == _count_unescaped_char(text, "]")
    )


def _has_attention_pair(text: str) -> bool:
    return (
        _count_unescaped_char(text, "(") > 0
        and _count_unescaped_char(text, ")") > 0
    ) or (
        _count_unescaped_char(text, "[") > 0
        and _count_unescaped_char(text, "]") > 0
    )


def _has_top_level_comma(text: str) -> bool:
    paren_depth = 0
    bracket_depth = 0
    for idx, ch in enumerate(text):
        if ch == "(" and not _is_escaped_at(text, idx):
            paren_depth += 1
        elif ch == ")" and paren_depth > 0 and not _is_escaped_at(text, idx):
            paren_depth -= 1
        elif ch == "[" and not _is_escaped_at(text, idx):
            bracket_depth += 1
        elif ch == "]" and bracket_depth > 0 and not _is_escaped_at(text, idx):
            bracket_depth -= 1
        elif ch == "," and paren_depth == 0 and bracket_depth == 0:
            return True
    return False


def _plain_comma_split_for_broken_attention(text: Any) -> List[str]:
    """Fallback splitter for malformed attention groups with missing closers.

    It separates user tags again instead of turning "(a, b" into one
    identity token, while still preserving decimal comma weights like 1,4.
    When a broken outer wrapper still contains one valid attention group, it
    preserves that inner group instead of stripping every weight marker.
    This path is only used after an unmatched bracket/parenthesis is detected.
    """
    s = str(text or "")
    repaired = _balance_outer_attention_edges(s)
    if (
        repaired
        and repaired != _clean_text(s)
        and _attention_brackets_balanced(repaired)
        and _has_attention_pair(repaired)
        and not _has_top_level_comma(repaired)
    ):
        return [repaired]
    if repaired:
        s = repaired
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
            c = _remove_unescaped_char_limited(c, "(", _count_unescaped_char(c, "(") - _count_unescaped_char(c, ")"), from_right=False)
        if _count_unescaped_char(c, "[") > _count_unescaped_char(c, "]"):
            c = _remove_unescaped_char_limited(c, "[", _count_unescaped_char(c, "[") - _count_unescaped_char(c, "]"), from_right=False)
        if _count_unescaped_char(c, ")") > _count_unescaped_char(c, "("):
            c = _remove_unescaped_char_limited(c, ")", _count_unescaped_char(c, ")") - _count_unescaped_char(c, "("), from_right=True)
        if _count_unescaped_char(c, "]") > _count_unescaped_char(c, "["):
            c = _remove_unescaped_char_limited(c, "]", _count_unescaped_char(c, "]") - _count_unescaped_char(c, "["), from_right=True)
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


def _style_text_pool(value: Any) -> List[str]:
    """Return a safe list of text cues from user-editable style JSON fields.

    The public data/style_dna.json file is intended to be edited by users.
    A missing pair of brackets should not crash the whole node, but dicts and
    other structured values should not leak Python/JSON representations into
    the prompt either.  Valid list/tuple/set values are preserved byte-for-byte
    after the same text normalization used by the existing prompt pipeline.
    """
    if isinstance(value, str):
        cleaned = _clean_text(value)
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                cleaned = _clean_text(item)
                if cleaned:
                    out.append(cleaned)
        return out
    return []


def _style_text_scalar(value: Any) -> str:
    """Return one safe text phrase from a user-editable style scalar field."""
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, (list, tuple, set)):
        return _clean_text(" ".join(item for item in value if isinstance(item, str)))
    return ""


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
GENERIC_STYLE_COLOR_CUE_RE = re.compile(
    r"\b(?:color|colour|colors|colours|colored|coloured|palette|hues?)\b|colored[-\s]?pencil|coloured[-\s]?pencil",
    re.IGNORECASE,
)


def _neutralize_generic_style_color_for_monochrome(term: Any) -> str:
    """Neutralize style-level color wording without touching subject/object colors.

    This helper is used only inside confirmed monochrome style paths or on short
    fragments that were already classified as global/style/lighting cues.
    """
    s = _clean_text(term)
    if not s or not GENERIC_STYLE_COLOR_CUE_RE.search(s):
        return s
    s = re.sub(r"\bcolored[-\s]?pencil\b|\bcoloured[-\s]?pencil\b", "pencil", s, flags=re.IGNORECASE)
    s = re.sub(r"\bhand[-\s]?colored\b|\bhand[-\s]?coloured\b", "hand-shaded", s, flags=re.IGNORECASE)
    s = re.sub(r"\bcolor\s+grade\b|\bcolour\s+grade\b", "tonal grade", s, flags=re.IGNORECASE)
    s = re.sub(r"\bcolor\s+grading\b|\bcolour\s+grading\b", "tonal grading", s, flags=re.IGNORECASE)
    s = re.sub(r"\bcolor\s+response\b|\bcolour\s+response\b", "tonal response", s, flags=re.IGNORECASE)
    s = re.sub(r"\bcolor\s+harmony\b|\bcolour\s+harmony\b", "tonal harmony", s, flags=re.IGNORECASE)
    s = re.sub(r"\bcolor\s+balance\b|\bcolour\s+balance\b", "tonal balance", s, flags=re.IGNORECASE)
    s = re.sub(r"\bbalanced\s+color\b|\bbalanced\s+colour\b", "balanced tonal value", s, flags=re.IGNORECASE)
    s = re.sub(r"\bnatural\s+color\s+balance\b|\bnatural\s+colour\s+balance\b", "natural tonal balance", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:color|colour)\s+(?:blocks?|fills?|shapes?)\b", "tonal shapes", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:color|colour)\s+(?:lighting|lights?|glow|illumination)\b", "tonal light", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:color|colour)\s+(?:palette|tones?|accents?)\b", "tonal range", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:colors|colours)\b", "tones", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:color|colour)\b", "tonal value", s, flags=re.IGNORECASE)
    s = re.sub(r"\bpalette\b", "tonal range", s, flags=re.IGNORECASE)
    s = re.sub(r"\bhues?\b", "values", s, flags=re.IGNORECASE)
    s = re.sub(r"\btonal\s+value\s+tonal\s+balance\b", "tonal balance", s, flags=re.IGNORECASE)
    s = re.sub(r"\btonal\s+value\s+tones\b", "tonal values", s, flags=re.IGNORECASE)
    s = re.sub(r"\btonal\s+range\s+tones\b", "tonal range", s, flags=re.IGNORECASE)
    return _clean_text(s)


def _style_monochrome_context_signature(style_name: Any, mood_family: Any = "") -> str:
    """Return affirmative style fields that can prove a monochrome output context.

    Some monochrome styles do not put the word "monochrome" in their anchor, but
    do put it in color/texture/style-support fields. Exclude generated negative
    guidance so negative-control phrases cannot become false positives.
    """
    key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    if key == "Auto by Mood":
        mood_key = _canonical_ui_value(mood_family, "mood_family") or _clean_text(mood_family)
        key = AUTO_STYLE_BY_MOOD.get(mood_key, key)
    chunks: List[str] = []
    style = STYLE_DNA.get(key)
    if isinstance(style, dict):
        for field in ("anchor", "color", "lighting", "composition", "texture"):
            value = style.get(field)
            if isinstance(value, (list, tuple)):
                chunks.extend(_clean_text(x) for x in value if _clean_text(x))
            else:
                cleaned = _clean_text(value)
                if cleaned:
                    chunks.append(cleaned)
    np_cues = NONPHYSICAL_STYLE_CUES.get(key)
    if isinstance(np_cues, dict):
        for field in ("anchor", "color", "lighting", "composition", "texture"):
            value = np_cues.get(field)
            if isinstance(value, (list, tuple)):
                chunks.extend(_clean_text(x) for x in value if _clean_text(x))
            else:
                cleaned = _clean_text(value)
                if cleaned:
                    chunks.append(cleaned)
    return _normalize_text(" ".join(chunks))


def _is_monochrome_output_context(mood_family: str, style_name: str, extra: Any = "") -> bool:
    style_key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    signature = _style_monochrome_context_signature(style_key, mood_family)
    haystack = " ".join([
        _clean_text(mood_family),
        _clean_text(style_key),
        _normalize_text(extra),
        signature,
    ])
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
    neutral = re.sub(r"\bsoft\s+soft\b", "soft", neutral, flags=re.IGNORECASE)
    neutral = re.sub(r"\btonal\s+tonal\b", "tonal", neutral, flags=re.IGNORECASE)
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
        inline_neutral = _monochrome_safe_inline_text(cleaned)
        if inline_neutral != cleaned:
            if inline_neutral and not CHROMATIC_COLOR_CUE_RE.search(inline_neutral) and not GENERIC_STYLE_COLOR_CUE_RE.search(inline_neutral):
                out.append(inline_neutral)
            continue
        neutralized_generic_color = _neutralize_generic_style_color_for_monochrome(cleaned)
        if neutralized_generic_color != cleaned:
            if CHROMATIC_COLOR_CUE_RE.search(neutralized_generic_color):
                continue
            if WARM_LIGHTING_CUE_RE.search(neutralized_generic_color):
                neutralized_generic_color = _neutralize_warm_lighting_for_monochrome(neutralized_generic_color)
            if neutralized_generic_color:
                out.append(neutralized_generic_color)
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
    generic_neutral = _neutralize_generic_style_color_for_monochrome(cleaned)
    if generic_neutral != cleaned:
        if generic_neutral and not CHROMATIC_COLOR_CUE_RE.search(generic_neutral) and not GENERIC_STYLE_COLOR_CUE_RE.search(generic_neutral):
            return generic_neutral
        return "monochrome tonal treatment"
    inline_neutral = _monochrome_safe_inline_text(cleaned)
    if inline_neutral != cleaned:
        if inline_neutral and not CHROMATIC_COLOR_CUE_RE.search(inline_neutral) and not GENERIC_STYLE_COLOR_CUE_RE.search(inline_neutral):
            return inline_neutral
        return "monochrome tonal treatment"
    if CHROMATIC_COLOR_CUE_RE.search(cleaned):
        return "monochrome tonal treatment"
    if WARM_LIGHTING_CUE_RE.search(cleaned):
        return _neutralize_warm_lighting_for_monochrome(cleaned) or "monochrome tonal treatment"
    return cleaned


MONOCHROME_TAG_CUE_REPLACEMENTS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"\b(?:cyan\s*(?:and|&|-|/)\s*magenta|magenta\s*(?:and|&|-|/)\s*cyan)\s+(?:neon[-\s]?)?(?:lit|lights?|lighting|glows?|illumination)\b", re.IGNORECASE), "high-contrast monochrome city lighting"),
    (re.compile(r"\bneon[-\s]?lit\b|\bneon\s+lights?\b|\bneon\s+lighting\b|\bneon\s+glow\b", re.IGNORECASE), "high-contrast monochrome city lighting"),
    (re.compile(r"\b(?:rainy[-\s]?night\s+)?neon\s+mood\b", re.IGNORECASE), "high-contrast monochrome city-light mood"),
    (re.compile(r"\bneon\s+signs?\b|\bglowing\s+signs?\b|\bluminous\s+signs?\b", re.IGNORECASE), "luminous monochrome signage"),
    (re.compile(r"\b(?:cyan\s*(?:and|&|-|/)\s*magenta|magenta\s*(?:and|&|-|/)\s*cyan)\s+(?:colors?|colours?|palette|tones?)\b", re.IGNORECASE), "monochrome tonal contrast"),
    (re.compile(r"\b(?:warm\s+pink|pink|magenta|cyan|blue|red|green|purple|teal|turquoise|violet|rainbow|holographic)\s+(?:tones?|colors?|colours?|palette|accents?|lights?|lighting|glows?)\b", re.IGNORECASE), "monochrome tonal contrast"),
    (re.compile(r"\bsoft\s+pastel\s+colors?\b|\bpastel\s+(?:colors?|colours?|palette|tones?)\b", re.IGNORECASE), "soft grayscale tonal range"),
    (re.compile(r"\bdreamy\s+pastel\s+glow\b", re.IGNORECASE), "dreamy soft grayscale glow"),
    (re.compile(r"\bsoft\s+pastel\s+color\s+transitions?\b", re.IGNORECASE), "soft grayscale tonal transitions"),
    (re.compile(r"\bpowdery\s+pastel\s+color\b", re.IGNORECASE), "powdery grayscale tone"),
    (re.compile(r"\bcolored\s+reflections?\b", re.IGNORECASE), "tonal reflections"),
    (re.compile(r"\bfluid\s+color\s+transitions?\b", re.IGNORECASE), "fluid tonal transitions"),
    (re.compile(r"\bmatte\s+painted\s+color\s+blocks?\b", re.IGNORECASE), "matte painted tonal blocks"),
    (re.compile(r"\bvibrant\s+cute\s+colors?\b", re.IGNORECASE), "lively cute tonal contrast"),
    (re.compile(r"\bwashed[-\s]?out\s+colors?\b|\bfaded\s+film\s+colors?\b", re.IGNORECASE), "faded grayscale tones"),
    (re.compile(r"\bgolden\s+hour\s+(?:sunlight|lighting|lights?|glow|sunbeams?)\b|\bgolden\s+hour\b|\bsunset\s+(?:sunlight|lighting|lights?|glow)\b", re.IGNORECASE), "low-angle monochrome light"),
    (re.compile(r"\bsoft\s+warm\s+(?:lights?|lighting)\b", re.IGNORECASE), "soft tonal light"),
    (re.compile(r"\bwarm\s+light\b|\bwarm\s+lighting\b", re.IGNORECASE), "soft tonal light"),
)

# Shared B&W fallback for short tag fragments and natural-language clauses.
# Keep the scope intentionally global/style/lighting oriented so subject colors
# such as "red dress", "blue eyes", or "green hair" remain intact.
MONOCHROME_EXACT_CHROMA_TAG_REPLACEMENTS: Dict[str, str] = {
    "pastel": "powdery chalk texture",
    "pastel chalk": "powdery chalk drawing",
    "colored pencil": "pencil illustration",
    "coloured pencil": "pencil illustration",
    "colored pencil illustration": "pencil illustration",
    "coloured pencil illustration": "pencil illustration",
    "balanced color": "balanced tonal value",
    "natural color balance": "natural tonal balance",
    "coherent natural color grade": "coherent natural tonal grade",
    "filmic color grade": "filmic tonal grade",
    "filmic color grading": "filmic tonal grading",
    "faded color response": "faded tonal response",
    "dreamy pastel glow": "dreamy soft grayscale glow",
    "soft pastel colors": "soft grayscale tonal range",
    "soft pastel colours": "soft grayscale tonal range",
    "ambient pastel mist": "ambient soft grayscale mist",
    "powder pastel palette": "powdery grayscale tonal range",
    "pink lavender softness": "soft grayscale tonal softness",
    "soft cyan tint": "soft grayscale tint",
    "pale cream undertones": "pale grayscale undertones",
}
MONOCHROME_GLOBAL_CHROMA_NOUN_RE = re.compile(
    r"\b(?:colors?|colours?|palette|tones?|tints?|shades?|accents?|background|backdrop|scene|"
    r"atmosphere|mood|look|style|treatment|lighting|lights?|glow|illumination|reflections?|"
    r"gradient|transitions?|signs?|signage|city\s+lights?)\b",
    re.IGNORECASE,
)
MONOCHROME_INLINE_GLOBAL_CHROMA_REPLACEMENTS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"\blimited\s+palette\b", re.IGNORECASE), "limited tonal range"),
    (re.compile(r"\bflat\s+color\s+shading\b", re.IGNORECASE), "flat tonal shading"),
    (re.compile(r"\bflat\s+color\s+fills?\b", re.IGNORECASE), "flat tonal fills"),
    (re.compile(r"\bpastel[-\s]?lit\b", re.IGNORECASE), "grayscale-lit"),
    (re.compile(r"\b(?:true\s+)?soft[-\s]+pastel\s+drawing\b", re.IGNORECASE), "powdery chalk drawing"),
    (re.compile(r"\bgentle\s+soft[-\s]+pastel\s+drawing\b", re.IGNORECASE), "gentle powdery chalk drawing"),
    (re.compile(r"\bvisible\s+chalky\s+pastel\s+strokes?\b", re.IGNORECASE), "visible chalk strokes"),
    (re.compile(r"\bchalky\s+pastel\s+tones?\b", re.IGNORECASE), "chalky grayscale tones"),
    (re.compile(r"\bpastel\s+pigments?\b", re.IGNORECASE), "grayscale chalk tones"),
    (re.compile(r"\bpastel\s+tones?\b", re.IGNORECASE), "grayscale tones"),
    (re.compile(r"\bpastel\s+illumination\b", re.IGNORECASE), "grayscale illumination"),
    (re.compile(r"\bpastel\s+composition\b", re.IGNORECASE), "chalk composition"),
    (re.compile(r"\bpastel\s+strokes?\b", re.IGNORECASE), "chalk strokes"),
    (re.compile(r"\bpastel\s+edges?\b", re.IGNORECASE), "chalk edges"),
    (re.compile(r"\b(?:soft|subtle|delicate|faint|gentle)?\s*pastel\s+accents?\b", re.IGNORECASE), "soft grayscale tonal accents"),
    (re.compile(r"\bpastel\s+diffusion\b", re.IGNORECASE), "soft grayscale diffusion"),
    (re.compile(r"\bpastel\s+color\b", re.IGNORECASE), "grayscale tone"),
    (re.compile(r"\b(?:colorful|colourful|vibrant|saturated|rainbow|holographic|color-driven)\s+(?:background|backdrop)\b", re.IGNORECASE), "monochrome tonal background"),
    (re.compile(r"\b(?:colorful|colourful|vibrant|saturated|rainbow|holographic|color-driven)\s+(?:scene|atmosphere|mood|look|style|treatment)\b", re.IGNORECASE), "monochrome tonal treatment"),
    (re.compile(r"\b(?:colorful|colourful|vibrant|saturated|rainbow|holographic|color-driven)\s+(?:colors?|colours?|palette|tones?|accents?)\b", re.IGNORECASE), "monochrome tonal contrast"),
    (re.compile(r"\b(?:pastel|soft\s+pastel|powder\s+pastel)\s+(?:background|backdrop|scene|atmosphere|mood|look|style|treatment)\b", re.IGNORECASE), "soft grayscale tonal treatment"),
    (re.compile(r"\b(?:pastel|soft\s+pastel|powder\s+pastel)\s+(?:lighting|lights?|glow|illumination|mist|haze)\b", re.IGNORECASE), "soft grayscale light"),
    (re.compile(r"\bpastel\s+chalk\b", re.IGNORECASE), "powdery chalk drawing"),
    (re.compile(r"\bcolored[-\s]?pencil(?:\s+illustration)?\b|\bcoloured[-\s]?pencil(?:\s+illustration)?\b", re.IGNORECASE), "pencil"),
    (re.compile(r"\b(?:pink|magenta|cyan|blue|red|green|purple|teal|turquoise|violet|golden|amber|orange|yellow|lavender|peach|crimson|terracotta|cream|olive)\s+(?:background|backdrop|scene|lighting|lights?|glow|illumination|atmosphere|mood|palette|tones?|colors?|colours?|accents?)\b", re.IGNORECASE), "monochrome tonal contrast"),
)


def _monochrome_generic_chroma_replacement(fragment: Any) -> str:
    cleaned = _clean_text(fragment)
    if not cleaned:
        return ""
    normalized = _normalize_tag_identity(cleaned) or _normalize_text(cleaned).lower()
    exact = MONOCHROME_EXACT_CHROMA_TAG_REPLACEMENTS.get(normalized)
    if exact:
        return exact
    if MONOCHROME_CONTEXT_RE.search(normalized):
        return ""
    if re.search(r"\b(?:colorful|colourful|vibrant|saturated|rainbow|holographic|color-driven)\b", normalized, flags=re.IGNORECASE) and MONOCHROME_GLOBAL_CHROMA_NOUN_RE.search(normalized):
        if re.search(r"\b(?:background|backdrop)\b", normalized, flags=re.IGNORECASE):
            return "monochrome tonal background"
        if re.search(r"\b(?:scene|atmosphere|mood|look|style|treatment)\b", normalized, flags=re.IGNORECASE):
            return "monochrome tonal treatment"
        return "monochrome tonal contrast"
    generic_color = _neutralize_generic_style_color_for_monochrome(normalized)
    if generic_color != normalized and MONOCHROME_GLOBAL_CHROMA_NOUN_RE.search(normalized):
        return generic_color
    if not CHROMATIC_COLOR_CUE_RE.search(normalized):
        return ""
    if re.fullmatch(r"(?:colorful|colourful|vibrant|saturated|rainbow|holographic|neon|magenta|cyan|purple|pink|blue|red|green|golden|amber|orange|yellow|teal|turquoise|violet|pastel)", normalized, flags=re.IGNORECASE):
        return "monochrome tonal contrast"
    if re.fullmatch(r"(?:pastel|soft\s+pastel|powder\s+pastel)\s+(?:chalk|texture|medium|drawing)", normalized, flags=re.IGNORECASE):
        return "powdery chalk drawing"
    if MONOCHROME_GLOBAL_CHROMA_NOUN_RE.search(normalized):
        if re.search(r"\b(?:background|backdrop)\b", normalized, flags=re.IGNORECASE):
            return "monochrome tonal background"
        if re.search(r"\b(?:lighting|lights?|glow|illumination|city\s+lights?)\b", normalized, flags=re.IGNORECASE):
            return "monochrome tonal light"
        if re.search(r"\b(?:scene|atmosphere|mood|look|style|treatment)\b", normalized, flags=re.IGNORECASE):
            return "monochrome tonal treatment"
        return "monochrome tonal contrast"
    return ""


def _monochrome_safe_tag_fragment(tag: Any) -> str:
    cleaned = _clean_text(tag)
    if not cleaned:
        return ""
    normalized = _normalize_tag_identity(cleaned)
    target = normalized or cleaned
    for pattern, repl in MONOCHROME_TAG_CUE_REPLACEMENTS:
        if pattern.search(target) or pattern.search(cleaned):
            return repl
    if MONOCHROME_CONTEXT_RE.search(target):
        return cleaned
    inline_neutral = _monochrome_safe_inline_text(target)
    if inline_neutral != target and inline_neutral and not CHROMATIC_COLOR_CUE_RE.search(inline_neutral) and not GENERIC_STYLE_COLOR_CUE_RE.search(inline_neutral):
        return inline_neutral
    replacement = _monochrome_generic_chroma_replacement(target)
    if replacement:
        return replacement
    return cleaned


def _monochrome_safe_wardrobe_note(text: Any) -> str:
    out = _clean_text(text)
    if not out:
        return ""
    replacements = {
        "red evening dresses": "dark evening dresses",
        "red evening dress": "dark evening dress",
        "red dresses": "dark dresses",
        "red dress": "dark dress",
    }
    for source, repl in replacements.items():
        out = re.sub(rf"\b{re.escape(source)}\b", repl, out, flags=re.IGNORECASE)
    return _clean_text(out)


def _krea2_monochrome_safe_positive_text(text: Any) -> str:
    """Apply the shared lightweight monochrome cleanup used by natural profiles.

    Krea2 monochrome prompts should stay readable and should not aggressively parse
    or rewrite user-provided free-text color phrases.  Generated wardrobe cleanup
    is handled separately at the standalone-builder sentence level.
    """
    return _monochrome_safe_inline_text(text)


def _krea2_monochrome_safe_generated_wardrobe_sentence(text: Any) -> str:
    """Neutralize only the generated standalone wardrobe phrase in sentence one.

    This prevents selected builder wardrobe such as red evening dress from
    conflicting with Black & White style, without rewriting arbitrary external
    or custom user text that may intentionally mention color.
    """
    out = _clean_text(text)
    if not out:
        return ""
    first, sep, rest = out.partition(".")
    first = _monochrome_safe_wardrobe_note(first)
    return _clean_text(first + (sep + rest if sep else ""))


def _monochrome_safe_inline_text(text: Any) -> str:
    out = _clean_text(text)
    if not out:
        return ""
    for pattern, repl in MONOCHROME_TAG_CUE_REPLACEMENTS:
        out = pattern.sub(repl, out)
    for pattern, repl in MONOCHROME_INLINE_GLOBAL_CHROMA_REPLACEMENTS:
        out = pattern.sub(repl, out)
    for source, repl in sorted(MONOCHROME_EXACT_CHROMA_TAG_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        if source == "pastel":
            continue
        out = re.sub(rf"\b{re.escape(source)}\b", repl, out, flags=re.IGNORECASE)
    # Do not replace every standalone "pastel" with a chalk phrase here.
    # In non-pastel styles, phrases such as "soft pastel accents" describe a
    # color accent, not a chalk medium; broad replacement damaged grammar and
    # could make clean-light/photo styles look like pastel illustrations.
    out = re.sub(r"\bcolorful\s+vibrant\s+neon\b", "high-contrast monochrome city lighting", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(?:cyan\s*(?:and|&|-|/)\s*magenta|magenta\s*(?:and|&|-|/)\s*cyan)\b", "monochrome", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(?:colorful|colourful|vibrant|saturated|rainbow|holographic|neon|magenta|cyan|purple|pink|blue|red|green|golden|amber|orange|yellow|teal|turquoise|violet|pastel)\s+(?=monochrome\s+tonal\s+(?:background|contrast|treatment|light))", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"\bsoft\s+grayscale\s+tonal\s+range\s+palette\b", "soft grayscale tonal range", out, flags=re.IGNORECASE)
    out = re.sub(r"\bsoft\s+grayscale\s+tonal\s+range\s+transitions?\b", "soft grayscale tonal transitions", out, flags=re.IGNORECASE)
    out = re.sub(r"\bfaded\s+grayscale\s+tones\s+palette\b", "faded grayscale tones", out, flags=re.IGNORECASE)
    out = re.sub(r"\blow-angle\s+monochrome\s+light\s+(?:light|lighting|sunlight|glow)\b", "low-angle monochrome light", out, flags=re.IGNORECASE)
    out = re.sub(r"\bsoft\s+soft\s+tonal\s+light\b", "soft tonal light", out, flags=re.IGNORECASE)
    out = re.sub(r"\bsoft\s+soft\s+grayscale\b", "soft grayscale", out, flags=re.IGNORECASE)
    out = re.sub(r"\bchalky\s+soft\s+grayscale\s+chalk\s+texture\b", "chalky grayscale texture", out, flags=re.IGNORECASE)
    out = re.sub(
        r"\ban\s+(?=(?:monochrome|tonal|grayscale|greyscale)\b)",
        "a ",
        out,
        flags=re.IGNORECASE,
    )
    return _clean_text(out)


def _monochrome_safe_style_scope_text(text: Any) -> str:
    out = _monochrome_safe_inline_text(text)
    if not out:
        return ""
    out = re.sub(r"\blineart,\s*color\b", "lineart, tonal value", out, flags=re.IGNORECASE)
    out = re.sub(r"\bline\s+art,\s*color\b", "line art, tonal value", out, flags=re.IGNORECASE)
    out = re.sub(r"\blighting,\s*color,\s*texture\b", "lighting, tonal value, texture", out, flags=re.IGNORECASE)
    out = re.sub(r"\blighting\s+mood,\s*color\s+tone,\s*surface\s+texture\b", "lighting mood, tonal value, surface texture", out, flags=re.IGNORECASE)
    out = re.sub(r"\bcolor\s+tone\b", "tonal value", out, flags=re.IGNORECASE)
    out = re.sub(r"\bcolor\s+response\b", "tonal response", out, flags=re.IGNORECASE)
    out = re.sub(r"\bflat\s+color\s+shading\b", "flat tonal shading", out, flags=re.IGNORECASE)
    return _clean_text(out)


def _monochrome_safe_tag_parts(parts: List[Any], *, fallback: bool = False) -> List[str]:
    out: List[str] = []
    for part in parts:
        for tag in _split_prompt_tags(part):
            safe = _monochrome_safe_tag_fragment(tag)
            if safe:
                out.append(safe)
    if fallback and not out:
        return ["monochrome tonal contrast"]
    return _unique(out)


def _looks_like_external_sentence_fragment_for_monochrome(fragment: Any) -> bool:
    cleaned = _clean_text(fragment)
    if not cleaned:
        return False
    # Weighted or parenthesized prompt tags should stay in tag-fragment mode;
    # otherwise attention syntax may be weakened by inline sentence handling.
    if WEIGHTED_TAG_VALUE_RE.match(cleaned):
        return False
    normalized = _normalize_tag_identity(cleaned)
    words = re.findall(r"[A-Za-z]+", normalized)
    if len(words) < 6:
        return False
    return bool(re.search(
        r"\b(?:a|an|the|with|under|through|across|along|inside|outside|beside|near|in|on|at|of|from|toward|towards|walking|standing|sitting|wearing|holding|looking)\b",
        normalized,
        flags=re.IGNORECASE,
    ))


def _monochrome_safe_external_tag_fragment(fragment: Any) -> str:
    cleaned = _clean_text(fragment)
    if not cleaned:
        return ""
    # External prompts are often pasted as natural-language clauses rather than
    # comma-separated tags.  In that case, replace only the chromatic phrase
    # inside the clause instead of replacing the entire subject/scene clause.
    if _looks_like_external_sentence_fragment_for_monochrome(cleaned):
        return _monochrome_safe_inline_text(cleaned)
    return _monochrome_safe_tag_fragment(cleaned)


def _neutralize_external_tag_prompt_for_monochrome(external_prompt: Any) -> str:
    out: List[str] = []
    for fragment in _split_prompt_tags(external_prompt):
        safe = _monochrome_safe_external_tag_fragment(fragment)
        if safe:
            out.append(safe)
    return _join_unique_tags(out)


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
            for k, v in x.items():
                if k == "avoid":
                    continue
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
    """Remove negative chunks that directly fight explicit adult rating tags.

    Keep age/quality/anatomy/style-protection negatives intact. Only adult-expression
    blockers such as explicit sexual action / pornographic staging are removed, and
    only when the user explicitly selects NSFW/explicit tone for models that emit
    adult/rating tags in the positive prompt.
    """
    out = _clean_negative_text(negative)
    if not out:
        return out
    if _model_key(model_profile) not in {"anima", "ilxl", "sdxl", "sd", "pony"}:
        return out
    if _adult_tone_group(adult_tone) not in {"nsfw", "explicit"}:
        return out
    return _remove_negative_chunks(out, ADULT_EXPRESSION_NEGATIVE_CHUNK_RE)


def _split_prompt_tags(text: Any) -> List[str]:
    return [_clean_text(t) for t in _split_comma_aware(text) if _clean_text(t)]


def _normalize_tag_identity(token: Any) -> str:
    t = str(token or "").strip()
    # Peel nested attention brackets and trailing weights defensively.  Older
    # builds stopped after 8 layers, which could leave deeply pasted junk such
    # as (((((((((tag))))))))) partially normalized.  Keep a generous hard cap
    # to avoid any theoretical infinite loop while preserving the existing
    # early-break behavior for normal tags.
    for _ in range(64):
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
        if PONY_EXTERNAL_CONFLICT_TAG_RE.match(tag_key):
            continue
        if key in ("ilxl", "anima") and tag_key in ILXL_EXTERNAL_RATING_TAGS:
            continue
        out.append(tag_clean)
    return _join_comma(out)



def _join_mixed_prompt(tag_block: str, assist: str = "") -> str:
    tag_block = _clean_text(tag_block)
    assist = _clean_text(assist)
    if tag_block and assist:
        return f"{tag_block}. {assist}"
    return tag_block or assist


def _style_tag_fragment(text: Any) -> str:
    tag = _clean_text(text)
    return re.sub(r"^and\b\s*", "", tag, flags=re.IGNORECASE).strip()


_COMPACT_STYLE_TAG_FRAGMENT_MAP: Dict[str, Tuple[str, ...]] = {
    # Tag-family models generally follow concise tags better than long prose-like
    # weighted fragments. Keep the meaning, but split a few known long scene/mood
    # fragments into compact tag pieces before weighting.
    "subject smaller within the frame": ("wide shot", "small subject"),
    "full figure visible": ("full body", "full figure"),
    "space around the entire body": ("wide framing", "ample space"),
    "entire figure visible": ("full body", "full figure"),
    "entire figure fully visible": ("full body", "full figure"),
    "subject integrated with surroundings": ("environmental composition", "integrated setting"),
    "restrained adult sensual tension and private magnetism": ("sensual mood", "intimate atmosphere", "mature tension"),
    "tender romantic closeness and dreamy intimacy": ("romantic mood", "dreamy intimacy", "soft tenderness"),
    "handcrafted tabletop miniature diorama with miniature figure subject": ("miniature diorama", "tabletop model", "miniature figure"),
    "display-case illumination over a tiny model world": ("display-case lighting", "tiny model world"),
    "compressed model-world layout with tiny scale proportions": ("compressed diorama layout", "tiny scale proportions"),
    "environment share one consistent miniature scale": ("consistent miniature scale",),
    "the main subject appears as a miniature figure": ("miniature figure subject",),
    "latex-like shine without explicitness": ("latex-like shine", "non-explicit"),
    "dreamy pastel glow and soft luminous haze": ("dreamy pastel glow", "soft luminous haze"),
    "small-scale handcrafted model composition": ("small-scale model", "handcrafted miniature"),
    "tiny props and furniture detail": ("tiny props", "miniature furniture detail"),
    "full-body framing with extra space": ("full body", "full shot", "extra space"),
    "space above the head and below the feet": ("full body", "full frame", "feet visible"),
    "electric nightlife allure and glossy modern excitement": ("nightlife", "glossy neon", "urban energy"),
    "dreamlike emotional suspension and soft unreality": ("dreamlike mood", "surreal softness"),
    "cheerful airy optimism and clean uplift": ("bright mood", "airy atmosphere", "clean light"),
    "nostalgic memory warmth and lived-in retro charm": ("vintage mood", "nostalgic warmth", "retro atmosphere"),
    "opaque gouache picture-book illustration with a matte storybook page feel": ("gouache illustration", "picture book", "matte paint"),
    "gentle gouache illumination": ("soft gouache light",),
    "calm page-like painted light": ("storybook light", "painted light"),
    "charming gouache illustration balance": ("charming composition", "gouache balance"),
    "slightly uneven hand-painted edges": ("hand-painted edges",),
    "stylized 3D collectible figure render": ("stylized 3d figure", "collectible figure"),
    "soft product-display lighting": ("soft display lighting",),
    "gentle plastic highlight": ("plastic highlights",),
    "painted figure colors": ("painted colors",),
    "collectible toy palette": ("toy palette", "collectible colors"),
    "small figure centered layout": ("centered figure", "display layout"),
    "timeless monochrome restraint and austere classic gravity": ("monochrome restraint", "classic gravity"),
    "classic monochrome tonal contrast": ("monochrome contrast",),
    "operatic emotional grandeur and candlelit ceremony": ("operatic grandeur", "candlelit mood"),
    "strong volumetric light rays scattering through dusty air": ("volumetric light rays", "dusty air"),
    "ordinary private realism and hushed intimacy": ("private realism", "hushed intimacy"),
    "melancholic rainy-night neon city mood through wet glass": ("rainy neon mood", "wet glass"),
    "gothic longing and haunted romantic elegance": ("gothic romance", "haunted elegance"),
    "bleak devastated post-apocalyptic wasteland": ("bleak wasteland", "ruined landscape"),
    "dreamy soft grayscale glow and soft luminous haze": ("dreamy grayscale glow", "soft luminous haze"),
    "impasto brushstrokes and canvas texture": ("impasto brushstrokes", "canvas texture"),
    "timeless graceful poise and classical romantic dignity": ("classical poise", "romantic dignity"),
    "confident luxury poise and sculpted editorial presence": ("luxury poise", "editorial presence"),
    "lush emotional melodrama and suspended yearning": ("melodramatic mood", "suspended yearning"),
    "loose pen-and-ink study sketch on paper": ("pen-and-ink sketch", "paper texture"),
    "thick oil painting": ("oil painting", "thick paint"),
    "baroque operatic atmosphere": ("baroque", "operatic atmosphere"),
    "detailed pencil illustration with fine line art and soft graphite shading": ("pencil illustration", "fine lineart", "graphite shading"),
    "classic old-Hollywood studio glamour portrait": ("classic glamour", "studio lighting", "editorial look"),
    "soft romantic glow and tender luminous intimacy": ("soft romantic glow", "tender intimacy"),
    "faded analog film photograph aesthetic": ("analog film", "faded photo aesthetic"),
    "true soft pastel drawing on textured paper": ("pastel drawing", "textured paper"),
    "clear but softly rendered scene structure": ("soft scene structure", "clear composition"),
    "restrained psychological distance and quiet inner pressure": ("psychological distance", "inner pressure"),
    "cute chibi character illustration": ("chibi character", "cute illustration"),
    "powdery chalk drawing on textured paper": ("chalk drawing", "textured paper"),
    "warm nostalgic tenderness and radiant calm": ("nostalgic tenderness", "warm calm"),
    "hand-painted 2D storybook animation frame": ("hand-painted animation", "storybook frame"),
    "paper-soft scene lighting for a hand-painted animation frame": ("paper-soft lighting", "hand-painted scene"),
    "broken charcoal strokes and dusty paper": ("charcoal strokes", "dusty paper"),
    "dim ambient shadows with colored neon bloom": ("dim shadows", "neon bloom"),
    "diffused signage reflections through droplets": ("signage reflections", "raindrops"),
    "colored-pencil illustration with visible layered pencil work on paper": ("colored pencil illustration", "layered pencil", "paper texture"),
    "gentle showcase lighting for a tabletop set": ("showcase lighting", "tabletop set"),
    "subject framed by illuminated dust-filled air": ("dusty light framing", "illuminated dust"),
    "scene layout with animated storytelling energy": ("animated storytelling", "scene layout"),
    "timeless glamour product presentation composition": ("glamour product presentation", "timeless composition"),
}


def _compact_style_tag_fragments(tag: Any) -> List[str]:
    cleaned = _style_tag_fragment(tag)
    if not cleaned:
        return []
    mapped = _COMPACT_STYLE_TAG_FRAGMENT_MAP.get(_normalize_text(cleaned))
    if mapped:
        return [_clean_text(x) for x in mapped if _clean_text(x)]
    return [cleaned]


def _style_tag_insert_from_raw(raw_parts: List[Any], weight: float = 1.18) -> str:
    weighted: List[str] = []
    for idx, part in enumerate(raw_parts):
        for tag in _split_prompt_tags(part):
            tag_weight = weight if idx == 0 else max(1.08, weight - 0.06)
            for fragment in _compact_style_tag_fragments(tag):
                if not fragment:
                    continue
                weighted.append(_weighted_tag_token(fragment, tag_weight))
    return _join_unique_tags(weighted)

STYLE_TAG_ALIASES_2026_05_31_C: Dict[str, List[str]] = {'Dream Pastel Diffusion': ['dreamy pastel glow', 'soft pastel colors', 'soft lighting', 'ethereal softness', 'soft glow', 'luminous haze', 'gentle bloom', 'low contrast'], 'Watercolor / Painterly': ['watercolor', 'traditional media', 'painting', 'paper texture'], 'Graphite Pencil Sketch': ['pencil sketch', 'graphite', 'sketch', 'monochrome', 'hatching'], 'Pen and Ink Sketch': ['pen and ink', 'ink', 'lineart', 'crosshatching', 'monochrome'], 'Colored Pencil Illustration': ['colored pencil', 'traditional media', 'sketch', 'paper texture'], 'Pastel Chalk Drawing': ['pastel chalk', 'pastel', 'traditional media', 'powdery texture'], 'Gouache Storybook Illustration': ['gouache', 'storybook', 'traditional media', 'painting'], 'Hand-Painted Storybook Animation': ['hand-painted', 'storybook', 'traditional media', 'painting'], 'Volumetric Dust Light': ['volumetric lighting', 'light rays', 'dust particles', 'haze'], 'Long Exposure Light Trails': ['long exposure', 'light trails', 'motion blur', 'night'], 'Oil Painting': ['oil painting', 'traditional media', 'canvas', 'impasto'], 'Miniature Diorama': ['miniature', 'diorama', 'scale model', 'toy-like', 'tabletop'], 'Pixel Art': ['pixel art', 'pixelated', 'retro game', 'lowres'], '3D Collectible Figure': ['3d', 'figurine', 'collectible figure', 'toy', 'resin', 'display stand'], 'Apocalyptic Wasteland': ['post-apocalyptic', 'wasteland', 'ruins', 'debris', 'ruined city'], 'Chibi Style': ['chibi', 'super deformed', 'oversized head', 'short limbs', 'tiny body', 'cute proportions']}


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
    "Black & White Classic": ["black and white", "classic film"],
    "Golden Hour Glow": ["golden hour", "warm light", "backlight", "soft glow", "sunset lighting"],
    "Vintage Film Look": ["analog photo", "35mm film", "faded film photo", "washed-out colors", "film grain", "soft halation", "faded print", "low contrast"],
    "Cyberpunk Neon": ["cyberpunk", "neon lights", "glowing signs", "futuristic", "night city"],
    "Soft Romantic Glow": ["soft glow", "romantic atmosphere", "gentle lighting", "warm pink tones", "dreamy"],
    "High-key Clean Light": ["high key lighting", "bright lighting", "clean background", "soft shadows", "airy atmosphere"],
    "Dark Fantasy Shadow Mass": ["dark fantasy", "deep shadows", "mist", "gothic atmosphere", "ominous lighting"],
}
for _style_name, _aliases in STYLE_TAG_ALIASES_ANIMA_REFINEMENT_2026_06_23.items():
    if _style_name not in STYLE_TAG_ALIASES_2026_05_31_C:
        STYLE_TAG_ALIASES_2026_05_31_C[_style_name] = list(_aliases)

def _style_tag_alias_insert(style_name: str, model_profile: str, weight: float = 1.18, *, monochrome_context: bool = False) -> str:
    if _model_family(model_profile) not in ("tag", "mixed"):
        return ""
    key = _canonical_ui_value(style_name, "style_dna") or _clean_text(style_name)
    aliases = STYLE_TAG_ALIASES_2026_05_31_C.get(key, [])
    if not aliases:
        return ""
    if monochrome_context:
        aliases = _monochrome_safe_tag_parts(aliases, fallback=False)
    if not aliases:
        return ""
    return _style_tag_insert_from_raw([_join_comma(aliases)], weight=weight)


# Anima mixed models are tag-sensitive, but some visual-media styles become
# unstable when the general style data contains scene-specific wording such as
# room/window cues.  This layer is intentionally Anima-only: it does not alter
# Z-Image, Qwen, Flux, or other natural-language profiles.
ANIMA_STYLE_LAYER_2026_06_25: Dict[str, Dict[str, Any]] = {
    "Dream Pastel Diffusion": {
        "tags": ["dreamy pastel glow", "soft pastel colors", "soft lighting", "ethereal softness", "soft glow", "luminous haze", "gentle bloom", "low contrast"],
        "assist": "Render with dreamy pastel glow, soft pastel colors, soft lighting, ethereal softness, soft glow, luminous haze, gentle bloom, and low contrast.",
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
        "tags": ["soft pastel drawing", "chalky pastel strokes", "powdery pastel pigment", "smudged shading", "textured paper"],
        "assist": "Render as a soft pastel drawing with visible chalky pastel strokes, powdery pigment, smudged shading, and textured paper.",
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
        "tags": ["anime analog photo", "35mm film", "faded film photo", "washed-out colors", "film grain", "soft halation", "faded print", "low contrast"],
        "assist": "Render as an anime sun-faded film photo with visible fine film grain, soft halation, washed-out colors, low contrast, slight emulsion softness, and a nostalgic 35mm snapshot feel.",
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



ANIMA_COMPACT_ASSIST_OVERRIDES_2026_06_24: Dict[str, str] = {
    "Neon Melancholy / Rain Glass": "Rainy-night neon mood through wet glass, cyan-magenta glow, reflections, urban melancholy.",
    "Volumetric Dust Light": "Volumetric dust light, visible light rays, floating particles, hazy atmosphere.",
    "Long Exposure Light Trails": "Long-exposure light trails, glowing motion streaks, night-city energy.",
    "Miniature Diorama": "Render the whole scene as a handcrafted tabletop miniature diorama, with the main subject also appearing as a miniature figure in the same scale-model world.",
    "3D Collectible Figure": "Render the scene as stylized 3D collectible figures with toy-like material.",
    "Pixel Art": "Render the scene as clear pixel art with visible pixels and a limited palette.",
    "Watercolor / Painterly": "Render as a watercolor illustration with soft washes and paper texture.",
    "Graphite Pencil Sketch": "Render as a graphite pencil illustration with fine line art and soft shading.",
    "Pastel Chalk Drawing": "Render as a soft pastel drawing with visible chalky pastel strokes, powdery pigment, hand-smudged shading, and textured paper.",
    "Oil Painting": "Render as an oil painting with painterly brushstrokes and canvas texture.",
    "Charcoal Drawing": "Render as a charcoal drawing with bold strokes and smudged shading.",
    "Colored Pencil Illustration": "Render as a colored-pencil illustration with visible pencil strokes and paper texture.",
    "Hand-Painted Storybook Animation": "Render as a hand-painted storybook animation frame.",
    "Gouache Storybook Illustration": "Render as a gouache storybook illustration with matte painted color blocks.",
    "Black & White Classic": "Render as a black-and-white illustration with strong monochrome contrast.",
    "Vintage Film Look": "Render as a sun-faded film photo with visible film grain, washed-out colors, soft halation, low contrast, and a nostalgic 35mm snapshot feel.",
    "Clean Cel Animation": "Render as clean cel animation with crisp line art and flat color shading.",
    "Dream Pastel Diffusion": "Render with dreamy pastel glow, soft pastel colors, soft diffused lighting, gentle bloom, luminous haze, and low contrast.",
    "Apocalyptic Wasteland": "Render with a clear post-apocalyptic wasteland atmosphere.",
}

# Dream Pastel final wording refinement: keep it as a light/color treatment, not a scene, medium, or fantasy-world generator.
DREAM_PASTEL_LIGHT_STYLE_2026_06_30 = {
    "anchor": "dreamy pastel glow and soft luminous haze",
    "lighting": ["soft diffused lighting", "soft glow", "gentle bloom", "ambient pastel mist", "low-contrast scattered light"],
    "color": ["soft pastel colors", "powder pastel palette", "pink lavender softness", "soft cyan tint", "pale cream undertones"],
    "composition": ["gentle visual softness", "soft diffused depth", "airy low-contrast balance"],
    "texture": ["ethereal softness", "soft haze", "matte luminous softness", "delicate pastel diffusion"],
    
}
STYLE_DNA["Dream Pastel Diffusion"] = dict(DREAM_PASTEL_LIGHT_STYLE_2026_06_30)
NONPHYSICAL_STYLE_CUES["Dream Pastel Diffusion"] = dict(DREAM_PASTEL_LIGHT_STYLE_2026_06_30)
ANIMA_STYLE_LAYER_2026_06_25["Dream Pastel Diffusion"] = {
    "tags": ["dreamy pastel glow", "soft pastel colors", "soft lighting", "ethereal softness", "soft glow", "luminous haze", "gentle bloom", "low contrast"],
    "assist": "Render with dreamy pastel glow, soft pastel colors, soft lighting, ethereal softness, soft glow, luminous haze, gentle bloom, and low contrast.",
}
ANIMA_COMPACT_ASSIST_OVERRIDES_2026_06_24["Dream Pastel Diffusion"] = "Render with dreamy pastel glow, soft pastel colors, soft diffused lighting, gentle bloom, luminous haze, and low contrast."
STYLE_TAG_ALIASES_2026_05_31_C["Dream Pastel Diffusion"] = ["dreamy pastel glow", "soft pastel colors", "soft lighting", "ethereal softness", "soft glow", "luminous haze", "gentle bloom", "low contrast"]


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
    directive = _compact_assist_sentence(_style_specific_directive(style_key, bp.style_strength, bp.mood_family))
    return directive


def _normalized_phrase_present_in_text(phrase: Any, text: Any) -> bool:
    phrase_norm = _normalize_text(phrase).lower()
    text_norm = _normalize_text(text).lower()
    if not phrase_norm or not text_norm:
        return False
    variants = {phrase_norm}
    for prefix in ("in a ", "in an ", "in ", "wearing a ", "wearing an ", "wearing "):
        if phrase_norm.startswith(prefix):
            variants.add(phrase_norm[len(prefix):])
    if phrase_norm.endswith(" outfit"):
        variants.add(phrase_norm[:-7] + " outfits")
    if phrase_norm.endswith(" outfits"):
        variants.add(phrase_norm[:-8] + " outfit")
    if phrase_norm.startswith("a "):
        variants.add(phrase_norm[2:])
    if phrase_norm.startswith("an "):
        variants.add(phrase_norm[3:])
    for variant in variants:
        variant = _clean_text(variant).lower()
        if not variant:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(variant) + r"(?![a-z0-9])", text_norm):
            return True
    return False


def _strip_tag_fragments_matching_phrase(tag_text: Any, phrase: Any) -> str:
    phrase_norm = _normalize_text(phrase).lower()
    if not phrase_norm:
        return _clean_text(tag_text)
    kept: List[str] = []
    for tag in _split_prompt_tags(tag_text):
        raw = _clean_text(tag)
        if not raw:
            continue
        inner = raw
        m = re.match(r"^\((.*?):\s*[0-9]+(?:\.[0-9]+)?\)$", inner)
        if m:
            inner = m.group(1)
        if _normalized_phrase_present_in_text(phrase_norm, inner):
            continue
        kept.append(raw)
    return _join_unique_tags(kept)


def _anima_shared_tag_insert(
    bp: "Blueprint",
    weight: float,
    monochrome_context: bool = False,
    source_text: str = "",
) -> str:
    """Build the shared non-style tag block for Anima mixed style rendering.

    This keeps the Anima-specific layer/alias style core separate from user-driven
    shared controls that should behave consistently across render paths: wardrobe,
    scene framing, adult-tone tags, mood emotion cues, and explicit lens/camera
    presets. Fallback style paths continue to use the common tag_insert output.
    """
    shared_parts: List[Any] = []
    source_signature = _normalize_text(source_text)
    wardrobe_note = _clean_text(getattr(bp, "adult_wardrobe", ""))
    if wardrobe_note and not _normalized_phrase_present_in_text(wardrobe_note, source_signature):
        shared_parts.append(wardrobe_note)
    scene_framing_terms = [_clean_text(x) for x in getattr(bp, "scene_framing", []) if _clean_text(x)]
    shared_parts.extend(scene_framing_terms)
    shared_parts.extend(_adult_tone_tag_terms_for_model(bp.adult_tone, bp.model_profile))
    shared_parts.extend([_clean_text(x) for x in getattr(bp, "emotion", []) if _clean_text(x)])
    lens_key = _canonical_ui_value(bp.lens_preset, "lens_preset") or str(bp.lens_preset or "auto")
    if lens_key not in ("", "auto"):
        suppress_camera = _suppress_auto_camera_for_prompt(bp.style_name, bp.mood_family, bp.lens_preset)
        camera_tags = _safe_camera_terms(getattr(bp, "camera", []), suppress_camera=suppress_camera)
        if monochrome_context and camera_tags:
            camera_tags = _monochrome_safe_tag_parts(camera_tags, fallback=False)
        shared_parts.extend([_clean_text(x) for x in camera_tags if _clean_text(x)])
    return _style_tag_insert_from_raw(shared_parts, weight=weight) if shared_parts else ""


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
    strength = PromptComposerCore._external_strength_settings(bp.style_strength)
    quality = _anima_style_quality(bp.model_profile, bp.adult_tone)
    style = style or PromptComposerCore.external_style_parts(bp)
    monochrome_context = _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", ""))
    shared_tag_insert = _anima_shared_tag_insert(
        bp,
        float(strength["weight"]),
        monochrome_context=monochrome_context,
        source_text="" if style_only else external_prompt,
    )
    if layer:
        layer_tags = [_clean_text(t) for t in layer.get("tags", []) if _clean_text(t)]
        if monochrome_context:
            layer_tags = _monochrome_safe_tag_parts(layer_tags, fallback=False)
        layer_tag_insert = _style_tag_insert_from_raw([_join_comma(layer_tags)], weight=float(strength["weight"])) if layer_tags else ""
        style_tags = _join_unique_tags([shared_tag_insert, layer_tag_insert])
    else:
        alias_style_tags = _style_tag_alias_insert(
            str(bp.style_name or ""),
            bp.model_profile,
            weight=float(strength["weight"]),
            monochrome_context=monochrome_context,
        )
        if alias_style_tags:
            style_tags = _join_unique_tags([shared_tag_insert, alias_style_tags])
        else:
            style_tags = _clean_text(style.get("tag_insert", ""))
            wardrobe_note = _clean_text(getattr(bp, "adult_wardrobe", ""))
            if wardrobe_note and not style_only and _normalized_phrase_present_in_text(wardrobe_note, external_prompt):
                style_tags = _strip_tag_fragments_matching_phrase(style_tags, wardrobe_note)
    custom_note_raw = _clean_text(style.get("custom_note", "")) or _external_custom_note(getattr(bp, "custom_notes", ""))
    custom_note = custom_note_raw if style_only else _filter_custom_note_against_external(custom_note_raw, external_prompt)
    tag_block = _join_unique_tags([quality, style_tags, custom_note])
    if not tag_block:
        return ""
    assist = _anima_compact_assist_for(bp, layer)
    if monochrome_context:
        assist = _monochrome_safe_inline_text(assist)
    if style_only:
        return _append_sentence(tag_block, assist)
    external = _anima_external_prompt_for_style(external_prompt)
    if monochrome_context:
        external = _neutralize_external_tag_prompt_for_monochrome(external)
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


def _filter_custom_note_against_external(custom_note: Any, external_prompt: Any) -> str:
    custom = _clean_text(custom_note)
    if not custom:
        return ""
    external = _clean_text(external_prompt)
    if not external:
        return custom
    chunks = [_clean_text(x) for x in _split_comma_aware(custom) if _clean_text(x)]
    if len(chunks) <= 1:
        return "" if _natural_text_contains_full_phrase(external, custom) else custom
    kept: List[str] = []
    for chunk in chunks:
        if _natural_text_contains_full_phrase(external, chunk):
            continue
        kept.append(chunk)
    return ", ".join(kept)


def _omit_natural_custom_if_already_external(natural_insert: str, external_prompt: str, custom_note: str) -> str:
    natural = _clean_text(natural_insert)
    custom = _clean_text(custom_note)
    if not natural or not custom:
        return natural
    filtered_custom = _filter_custom_note_against_external(custom, external_prompt)
    if _natural_dedupe_key(filtered_custom) == _natural_dedupe_key(custom):
        return natural
    custom_sentence = _sentence(custom)
    replacement_sentence = _sentence(f"Additional custom direction: {filtered_custom}") if filtered_custom else ""
    if not custom_sentence:
        return natural
    updated = re.sub(
        r"(^|\s+)" + re.escape(custom_sentence) + r"(?=\s|$)",
        lambda m: ("" if not m.group(1) else " ") + replacement_sentence,
        natural,
        count=1,
    )
    return _clean_text(updated)


def _sentence(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else text + "."


def _sentence_core_key(text: Any) -> str:
    s = _clean_text(text).lower().rstrip(".!? ")
    s = re.sub(r"^(?:change clearly:\s*|change only:\s*|only shift\s+|apply\s+|render\s+|restyle\s+|let\s+)", "", s)
    s = re.sub(r"\b(?:the|whole|full|entire|scene|subject|and|as|a|an|with|to|into)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _append_non_redundant_sentence(parts: List[str], text: Any) -> None:
    sentence = _sentence(_clean_text(text))
    if not sentence:
        return
    key = _sentence_core_key(sentence)
    if key:
        for existing in parts:
            existing_key = _sentence_core_key(existing)
            if existing_key and (key in existing_key or existing_key in key):
                return
    parts.append(sentence)


def _dedupe_classical_glamour_anchor_insert(insert: Any, directive: Any, style_name: Any, style_anchor: Any, kind: Any = "") -> str:
    """Remove only the duplicated Classical Studio Glamour anchor from style-detail sentences.

    This intentionally avoids broad n-gram or generic anchor deduplication.  The
    duplicate comes from the Classical Studio Glamour directive and STYLE_DNA
    anchor using the exact same anchor phrase before standalone product/environment
    wording is normalized.  Keep the directive and preserve the lighting/color/
    texture details in the natural insert.
    """
    text = _clean_text(insert)
    directive_text = _clean_text(directive)
    anchor_text = _clean_text(style_anchor)
    if str(style_name or "") != "Classical Studio Glamour":
        return text
    if _clean_text(kind).lower() not in {"environment", "product"}:
        return text
    if not text or not directive_text or not anchor_text:
        return text
    if anchor_text.lower() not in directive_text.lower():
        return text

    escaped_anchor = re.escape(anchor_text)
    prefix_pattern = (
        r"(Describe the scene with|"
        r"Shift the visual style toward|"
        r"Style direction:|"
        r"Apply a visual treatment with)"
    )

    # Preferred path: remove the repeated leading anchor phrase while preserving
    # the rest of the sentence, e.g.
    #   Describe the scene with <anchor>, butterfly lighting, ...
    # -> Describe the scene with butterfly lighting, ...
    text = re.sub(
        prefix_pattern + r"\s+" + escaped_anchor + r"\s*,\s*",
        lambda m: m.group(1) + " ",
        text,
        count=1,
        flags=re.IGNORECASE,
    )

    # Defensive path for the unlikely case where the sentence contains only the
    # duplicated anchor and no detail list.  Do not touch user text elsewhere.
    text = re.sub(
        r"(?:^|(?<=\.\s))" + prefix_pattern + r"\s+" + escaped_anchor + r"\.\s*",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return _clean_text(text)


def _remove_exact_phrase_from_list_sentence(sentence: str, phrase: str) -> str:
    """Remove one generated comma-list item while preserving the sentence."""
    s = _clean_text(sentence)
    p = _clean_text(phrase)
    if not s or not p:
        return s
    esc = re.escape(p)
    # Middle of a comma list: "A, phrase, B" -> "A, B".
    s = re.sub(r",\s*" + esc + r"\s*,\s*", ", ", s, count=1, flags=re.I)
    # First item after an introducer: "with phrase, B" -> "with B".
    s = re.sub(r"(\bwith\s+)" + esc + r"\s*,\s*", r"\1", s, count=1, flags=re.I)
    # Final item: "A, and phrase." or "A, phrase." -> "A.".
    s = re.sub(r",\s*(?:and\s+)?" + esc + r"(?=\.)", "", s, count=1, flags=re.I)
    # Degenerate sentence: leave it empty rather than returning a bare introducer.
    if re.fullmatch(r"(?:Describe the scene with|Style direction:|Apply a visual treatment with)\s*\.?", s, flags=re.I):
        return ""
    s = re.sub(r",\s*,", ",", s)
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s*\.", ".", s)
    return _clean_text(s)


def _dedupe_classical_glamour_context_echo(text: Any, kind: Any) -> str:
    """Krea2-only fix for Classical Studio Glamour environment/product echoes.

    The Classical directive and STYLE_DNA composition can start as different
    person-oriented phrases ("elegant posture" and "elegant beauty-editorial
    posture") but converge to the same environment/product wording after Krea2
    context cleanup.  Remove only the second generated style-detail occurrence;
    do not run broad n-gram deduplication or touch user text.
    """
    s = _clean_text(text)
    k = _clean_text(kind).lower()
    if k == "environment":
        anchor = "classic old-Hollywood studio glamour interior scene"
        phrase = "elegant spatial arrangement"
    elif k == "product":
        anchor = "classic old-Hollywood studio glamour product presentation"
        phrase = "elegant product arrangement"
    else:
        return s
    lower = s.lower()
    if anchor.lower() not in lower or "timeless polished editorial feel" not in lower:
        return s
    if lower.count(phrase.lower()) < 2:
        return s

    pieces = [x for x in re.split(r"(?<=[.!?])\s+", s) if _clean_text(x)]
    seen_generated_phrase = False
    changed = False
    kept: List[str] = []
    for sentence in pieces:
        clean_sentence = _clean_text(sentence)
        if phrase.lower() in clean_sentence.lower():
            if seen_generated_phrase and re.match(r"^Describe the scene with\b", clean_sentence, flags=re.I):
                clean_sentence = _remove_exact_phrase_from_list_sentence(clean_sentence, phrase)
                changed = True
                if clean_sentence:
                    kept.append(clean_sentence)
                continue
            if anchor.lower() in clean_sentence.lower() or "timeless polished editorial feel" in clean_sentence.lower():
                seen_generated_phrase = True
        kept.append(clean_sentence)
    return _clean_text(" ".join(kept)) if changed else s



def _apply_adult_menu_level_to_pro_fields(
    adult_menu_level: str,
    adult_pose_style: str,
    adult_lighting: str,
    adult_scene_props: str,
    adult_body_focus: str,
    adult_framing_bias: str,
) -> Tuple[str, str, str, str, str]:
    if _safe_ui_value(adult_menu_level, "adult_menu_level") != "professional":
        return "auto", "auto", "auto", "auto", "auto"
    return adult_pose_style, adult_lighting, adult_scene_props, adult_body_focus, adult_framing_bias


def _apply_builder_detail_mode_to_advanced_fields(
    builder_detail_mode: str,
    subject_age: str,
    subject_appearance: str,
    subject_ethnicity: str,
    subject_hair: str,
    subject_outfit: str,
    subject_expression: str,
    location_detail: str,
    time_of_day: str,
    weather_light: str,
    scene_props: str,
) -> Tuple[str, str, str, str, str, str, str, str, str, str]:
    """Deactivate standalone advanced fields when the menu scope hides them.

    The frontend hides these widgets in the simple standalone menu scope.  Keep
    server-side generation symmetric with the UI so stale values from a previous
    advanced/professional session cannot silently affect the prompt while the
    controls are hidden.
    """
    if _safe_ui_value(builder_detail_mode, "builder_detail_mode") == "simple":
        return ("auto", "auto", "auto", "auto", "auto", "auto", "auto", "auto", "auto", "auto")
    return (
        subject_age,
        subject_appearance,
        subject_ethnicity,
        subject_hair,
        subject_outfit,
        subject_expression,
        location_detail,
        time_of_day,
        weather_light,
        scene_props,
    )


_STANDALONE_MULTI_WARDROBE_PHRASES = {
    # Adult wardrobe and general standalone outfit phrases share this map so
    # multi/group subjects do not read as if several people share one garment.
    "wearing jeans and a t-shirt": "wearing jeans and t-shirts",
    "wearing a white blouse and a dark skirt": "wearing white blouses and dark skirts",
    "wearing a knit sweater and skirt": "wearing knit sweaters and skirts",
    "wearing a summer dress": "wearing summer dresses",
    "wearing an elegant long dress": "wearing elegant long dresses",
    "wearing a business suit": "wearing business suits",
    "wearing an office blouse and slacks": "wearing office blouses and slacks",
    "wearing a hoodie and jeans": "wearing hoodies and jeans",
    "wearing a denim jacket outfit": "wearing denim jackets",
    "wearing a trench coat outfit": "wearing trench coats",
    "wearing a winter coat and scarf": "wearing winter coats and scarves",
    "wearing sportswear": "wearing sportswear",
    "wearing practical swimwear or beachwear": "wearing practical swimwear or beachwear",
    "wearing a traditional hanbok": "wearing traditional hanbok outfits",
    "wearing a simple black dress": "wearing simple black dresses",
    "in a bikini": "in bikinis",
    "in a one-piece swimsuit": "in one-piece swimsuits",
    "in a lace lingerie set": "in lace lingerie sets",
    "in a sheer nightgown": "in sheer nightgowns",
    "in a silk slip dress": "in silk slip dresses",
    "wearing a corset": "wearing corsets",
    "in a bodysuit": "in bodysuits",
    "in a latex outfit": "in latex outfits",
    "in a leather outfit": "in leather outfits",
    "in an evening dress": "in evening dresses",
    "in a tailored suit": "in tailored suits",
    "in a bathrobe": "in bathrobes",
    "in a sheer robe": "in sheer robes",
    "in a satin robe": "in satin robes",
    "in a silk camisole": "in silk camisoles",
    "in a bralette": "in bralettes",
    "in a lace bodysuit": "in lace bodysuits",
    "in a sheer bodysuit": "in sheer bodysuits",
    "wearing a garter belt": "wearing garter belts",
    "in an open shirt": "in open shirts",
    "in an oversized shirt": "in oversized shirts",
    "in a mini dress": "in mini dresses",
    "in an off-shoulder dress": "in off-shoulder dresses",
    "in a halter dress": "in halter dresses",
    "in a fishnet outfit": "in fishnet outfits",
    "in a glossy vinyl outfit": "in glossy vinyl outfits",
    "in a mesh top": "in mesh tops",
    "in a lace slip": "in lace slips",
    "in a sheer blouse": "in sheer blouses",
    "in a transparent robe": "in transparent robes",
    "in a high-slit dress": "in high-slit dresses",
    "in a backless dress": "in backless dresses",
    "in a deep V dress": "in deep V dresses",
    "in a bodycon dress": "in bodycon dresses",
    "in a wet shirt": "in wet shirts",
    "in an oversized sweater": "in oversized sweaters",
    "in a lace bralette set": "in lace bralette sets",
    "in a satin corset set": "in satin corset sets",
    "in a see-through cover-up": "in see-through cover-ups",
    "in a white button shirt": "in white button shirts",
    "in a black bodysuit": "in black bodysuits",
    "in a red evening dress": "in red evening dresses",
    "in a satin slip dress": "in satin slip dresses",
    "in a swimsuit cover-up": "in swimsuit cover-ups",
}


def _standalone_pluralize_wardrobe_for_multi(wardrobe_phrase: str, kind: str) -> str:
    phrase = _clean_text(wardrobe_phrase)
    if not phrase or kind not in {"multi", "group"}:
        return phrase
    return _STANDALONE_MULTI_WARDROBE_PHRASES.get(phrase, phrase)


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


def _nonphotographic_adult_direction_context(style_terms: List[Any]) -> str:
    haystack = " ".join(_clean_text(x).lower() for x in style_terms if _clean_text(x))
    patterns = (
        (r"\bwatercolor\b", "watercolor illustration"),
        (r"\bcharcoal\b", "charcoal drawing"),
        (r"\boil(?:[-\s]?paint|\s+painting|\s+paint)\b", "oil-painting"),
        (r"\bink\s*wash\b|\bsumi[-\s]?e\b", "ink-wash illustration"),
        (r"\bgraphite\b|\bpencil\b", "pencil illustration"),
        (r"\bpastel\b|\bchalk\b", "pastel illustration"),
        (r"\bgouache\b", "gouache illustration"),
        (r"\bstorybook\b|\bhand-painted\b", "hand-painted illustration"),
        (r"\bcolored[-\s]?pencil\b", "colored-pencil illustration"),
    )
    for pattern, label in patterns:
        if re.search(pattern, haystack, re.IGNORECASE):
            return label
    return ""


def _article_for_phrase(phrase: str) -> str:
    return _english_article(phrase)


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
    krea_structured: bool = False,
    krea_framing_context: str = "",
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

    nonphoto_adult_context = _nonphotographic_adult_direction_context([anchor] + lighting + color + composition + texture) if adult_direction else ""

    if flux_structured:
        if adult_direction:
            if nonphoto_adult_context:
                direction = f"{adult_direction} {nonphoto_adult_context} direction"
                sentences.append(_sentence(f"Use {_article_for_phrase(direction)} {direction}"))
            else:
                presentation = f"{adult_direction} presentation"
                sentences.append(_sentence(f"Use {_article_for_phrase(presentation)} {presentation}"))
        if emotion_terms and visual_terms:
            sentences.append(_sentence(f"Let the prompt keep a mood of {emotion_terms} while shifting the visual style toward {visual_terms}"))
        elif emotion_terms:
            sentences.append(_sentence(f"Let the prompt keep a mood of {emotion_terms}"))
        elif visual_terms:
            sentences.append(_sentence(f"Shift the visual style toward {visual_terms}"))
        if camera_terms:
            sentences.append(_sentence(f"Use {camera_terms} for visual framing"))
        return " ".join([s for s in sentences if s])

    if krea_structured:
        if adult_direction:
            if nonphoto_adult_context:
                direction = f"{adult_direction} {nonphoto_adult_context} direction"
                sentences.append(_sentence(f"Use {_article_for_phrase(direction)} {direction}"))
            else:
                presentation = f"{adult_direction} presentation"
                sentences.append(_sentence(f"Use {_article_for_phrase(presentation)} {presentation}"))
        if emotion_terms and visual_terms:
            sentences.append(_sentence(f"Describe the scene with {visual_terms} while keeping a mood of {emotion_terms}"))
        elif visual_terms:
            sentences.append(_sentence(f"Describe the scene with {visual_terms}"))
        elif emotion_terms:
            sentences.append(_sentence(f"Keep a mood of {emotion_terms}"))
        if camera_terms:
            krea_framing_context_clean = _clean_text(krea_framing_context).lower()
            if krea_framing_context_clean == "environment":
                framing_suffix = "scene orientation, environmental scale, and spatial depth"
            elif krea_framing_context_clean == "product":
                framing_suffix = "object orientation, product scale, and spatial depth"
            else:
                framing_suffix = "body direction, subject scale, and spatial depth"
            sentences.append(_sentence(f"Describe the framing with {camera_terms}, including {framing_suffix}"))
        return " ".join([s for s in sentences if s])

    camera_instruction = _natural_camera_instruction(camera)

    if adult_direction:
        if nonphoto_adult_context:
            direction = f"{adult_direction} {nonphoto_adult_context} direction"
            sentences.append(_sentence(f"Use {_article_for_phrase(direction)} {direction}"))
        else:
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
    if model_key in {"zimage", "qwen", "flux", "krea2"}:
        for pattern, repl in _TEXT_MODEL_TERM_REPLACEMENTS:
            s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    return _clean_text(s)


def _natural_insert_for_model(style: Dict[str, Any], bp: "Blueprint") -> str:
    key = _model_key(bp.model_profile)
    if key == "krea2":
        base = style.get("natural_insert_krea2", "")
    elif key == "flux":
        base = style.get("natural_insert_flux", "")
    elif key == "qwen":
        base = style.get("natural_insert_qwen", "")
    else:
        base = style.get("natural_insert", "")
    return _natural_insert_safe_for_model(base, key)



def _style_specific_directive(style_name: Any, mode: str, mood_family: Any = "") -> str:
    style = str(style_name or "")
    mode = _style_application_mode(mode)

    def _finish(text: str) -> str:
        cleaned = _clean_text(text)
        if cleaned and _is_monochrome_output_context(mood_family, style, cleaned):
            return _monochrome_safe_inline_text(cleaned)
        return cleaned
    if style == 'Chibi Style':
        if mode == 'subtle':
            return _finish('Render as a cute chibi-style illustration, with slightly oversized heads, compact bodies, simplified facial features, and short simplified limbs when visible.')
        if mode == 'strong':
            return _finish('Render as a delightful adorable chibi-style illustration. Restyle every visible person with oversized heads, big expressive eyes, soft rosy cheeks, stylized hair, tiny compact bodies, and short simplified limbs when visible. Use clean lineart, rounded simplified anime shapes, vibrant cute colors, and a whimsical feel.')
        return _finish('Render as a delightful chibi-style illustration. Restyle every visible person with oversized heads, big expressive eyes, soft rosy cheeks, stylized hair, tiny compact bodies, and short simplified limbs when visible.')
    if style == 'Dream Pastel Diffusion':
        if mode == 'subtle':
            return _finish('Render with a dreamy pastel glow, soft pastel colors, diffused lighting, gentle bloom, luminous haze, and low-contrast softness.')
        if mode == 'strong':
            return _finish('Render with a clear dreamy pastel glow: soft pastel colors, soft diffused lighting, ethereal softness, gentle bloom, luminous haze, and low-contrast softness across the image.')
        return _finish('Render with a dreamy pastel glow, soft pastel colors, soft diffused lighting, ethereal softness, gentle bloom, luminous haze, and low-contrast softness across the image.')
    if style == 'Watercolor / Painterly':
        if mode == 'subtle':
            return _finish('Render as a watercolor painting on textured paper with transparent washes, soft bleeding edges, and visible paper grain.')
        if mode == 'strong':
            return _finish('Restyle the full image decisively as a watercolor painting on textured paper; make transparent washes, wet bleeding edges, pigment blooms, paper grain, and fluid color transitions visibly dominate the final image.')
        return _finish('Render as a watercolor painting on textured paper with transparent washes, wet bleeding edges, pigment blooms, and visible paper grain.')
    if style == 'Oil Painting':
        if mode == 'subtle':
            return _finish('Render as an oil painting on canvas with visible brushstrokes, painterly surface texture, and hand-painted form.')
        if mode == 'strong':
            return _finish('Restyle the full image decisively as an oil painting on canvas; make thick brushstrokes, layered paint, impasto texture, painterly highlights, and visible canvas surface dominate the final image.')
        return _finish('Render as an oil painting on canvas with thick brushstrokes, layered paint, and visible canvas texture.')
    if style == 'Ink Wash / Sumi-e':
        if mode == 'subtle':
            return _finish('Render as an ink wash painting with controlled black ink dilution, soft brush flow, and paper texture.')
        if mode == 'strong':
            return _finish('Render as a clear ink wash / sumi-e painting, with diluted black ink, expressive brush flow, soft wash gradients, absorbent paper texture, and restrained monochrome elegance. Keep the result recognizably ink-wash rather than graphite, charcoal, or photorealistic.')
        return _finish('Render as an ink wash / sumi-e painting, with diluted black ink, expressive brush flow, soft wash gradients, absorbent paper texture, and restrained monochrome elegance. Keep the result recognizably ink-wash rather than graphite, charcoal, or photorealistic.')
    if style == 'Vintage Film Look':
        if mode == 'subtle':
            return _finish('Render as a faded film photo with soft film grain, washed-out colors, light halation, and a nostalgic analog snapshot feel.')
        if mode == 'strong':
            return _finish('Render as a clearly sun-faded analog film photograph: visible fine film grain, soft halation around highlights, washed-out colors, bleached highlights, low contrast, slight emulsion softness, faded print character, and a nostalgic 35mm snapshot finish.')
        return _finish('Render as a sun-faded analog film photograph with visible fine film grain, soft halation around highlights, washed-out colors, low contrast, slight emulsion softness, faded print character, and a nostalgic 35mm snapshot feel.')
    if style == 'Miniature Diorama':
        if mode == 'subtle':
            return _finish('Render the scene as a handcrafted tabletop miniature diorama, with the main subject also appearing as a miniature figure inside the same small-scale model world.')
        if mode == 'strong':
            return _finish('Render the whole scene as a handcrafted tabletop miniature diorama, with the main subject, props, furniture, and environment all appearing as miniature scale-model elements in one consistent tiny world.')
        return _finish('Render the whole scene as a handcrafted tabletop miniature diorama, with the main subject, props, furniture, and environment all appearing as miniature scale-model elements in one consistent tiny world.')
    if style == 'Gouache Storybook Illustration':
        if mode == 'subtle':
            return _finish('Render as an opaque gouache picture-book illustration with matte painted color blocks and a calm storybook page feel.')
        if mode == 'strong':
            return _finish('Render as a clear opaque gouache picture-book illustration with matte paint blocks, visible brush texture, layered gouache pigment, and a static storybook page feel. Do not interpret the result as cel animation.')
        return _finish('Render as an opaque gouache picture-book illustration with matte paint blocks, visible brush texture, layered gouache pigment, and a static storybook page feel. Do not interpret the result as cel animation.')
    if style == 'Hand-Painted Storybook Animation':
        if mode == 'subtle':
            return _finish('Render as a hand-painted storybook animation frame with painted background texture and an illustrated animation feel.')
        if mode == 'strong':
            return _finish('Render as a clear hand-painted 2D storybook animation frame, like a painted keyframe from a traditional illustrated animation. Preserve the storybook warmth, but do not collapse the result into a static gouache page illustration.')
        return _finish('Render as a hand-painted 2D storybook animation frame, like a painted keyframe from a traditional illustrated animation. Preserve the storybook warmth, but do not collapse the result into a static gouache page illustration.')
    if style == 'Graphite Pencil Sketch':
        if mode == 'subtle':
            return _finish('Render as a detailed pencil illustration with fine line art, soft graphite shading, and a classic hand-drawn sketch style.')
        if mode == 'strong':
            return _finish('Render as a detailed pencil illustration with fine line art, soft graphite shading, delicate pencil strokes, precise cross-hatching for depth, rich monochrome texture, and a subtly textured paper background.')
        return _finish('Render as a detailed pencil illustration with fine line art, soft graphite shading, delicate pencil strokes, precise cross-hatching for depth, and a classic hand-drawn sketch style.')
    if style == 'Pen and Ink Sketch':
        if mode == 'subtle':
            return _finish('Render as a pen-and-ink drawing with clear ink lines and light hatching.')
        if mode == 'strong':
            return _finish('Render as a pen-and-ink drawing with clear ink lines, hatching, and white paper contrast.')
        return _finish('Render as a pen-and-ink drawing with clear ink lines, hatching, and white paper contrast.')
    if style == 'Charcoal Drawing':
        if mode == 'subtle':
            return _finish('Render as a charcoal drawing on paper with bold broken charcoal strokes, dark smudges, dusty charcoal residue, and rough paper tooth.')
        if mode == 'strong':
            return _finish('Restyle the full image decisively as a charcoal drawing on rough paper; make bold broken strokes, deep smudged shadows, dusty residue, rough paper tooth, and dramatic tonal contrast dominate the final image.')
        return _finish('Render as a charcoal drawing on paper with bold broken charcoal strokes, deep dark smudges, dusty charcoal residue, and rough paper tooth.')
    if style == 'Pixel Art':
        if mode == 'subtle':
            return _finish('Render the subject and scene as pixel art with visible square pixels, blocky edges, and a limited palette.')
        if mode == 'strong':
            return _finish('Render the subject and scene as clear pixel art with visible square pixels, blocky edges, and a limited palette.')
        return _finish('Render the subject and scene as clear pixel art with visible square pixels, blocky edges, and a limited palette.')
    if style == '3D Collectible Figure':
        if mode == 'subtle':
            return _finish('Render the subject as a stylized 3D collectible figure with toy-like material and display-figure form.')
        if mode == 'strong':
            return _finish('Render the subject as a stylized 3D collectible figure with toy-like material, simplified form, and clean display lighting.')
        return _finish('Render the subject as a stylized 3D collectible figure with toy-like material, simplified form, and clean display lighting.')
    if style == 'Pastel Chalk Drawing':
        if mode == 'subtle':
            return _finish('Render as a soft pastel drawing on textured paper with visible chalky pastel marks, powdery pastel color, gentle smudged shading, and a soft hand-drawn finish.')
        if mode == 'strong':
            return _finish('Render as a true soft pastel drawing on textured paper with visible chalky pastel strokes, powdery pigment buildup, hand-smudged shading, paper tooth, dry pastel edges, and soft pastel color transitions. Avoid clean lineart or polished illustration rendering.')
        return _finish('Render as a soft pastel drawing on textured paper with visible chalky pastel texture, powdery pigment, hand-smudged shading, and soft pastel color transitions.')
    if style == 'Colored Pencil Illustration':
        if mode == 'subtle':
            return _finish('Render as a colored-pencil illustration with visible dry pencil strokes and textured paper.')
        if mode == 'strong':
            return _finish('Render as a colored-pencil illustration on paper with visible pencil strokes, light hatching, and paper texture.')
        return _finish('Render as a colored-pencil illustration on paper with visible pencil strokes, light hatching, and paper texture.')
    if style == 'Volumetric Dust Light':
        if mode == 'subtle':
            return _finish('Emphasize soft volumetric lighting with gentle haze and faint floating dust visible in the light.')
        if mode == 'strong':
            return _finish('Emphasize strong volumetric lighting, visible shafts of light, floating dust motes dancing in the light rays, hazy atmospheric depth, and cinematic light scattering through the air.')
        return _finish('Emphasize volumetric lighting, visible shafts of light, floating dust motes in the light rays, hazy atmospheric depth, and cinematic light scattering through the air.')
    if style == 'Classical Studio Glamour':
        if mode == 'subtle':
            return _finish('Render with a gentle classic studio glamour finish, controlled portrait lighting, and an elegant timeless beauty feel.')
        if mode == 'strong':
            return _finish('Render as a classic old-Hollywood studio glamour portrait with controlled beauty lighting, butterfly lighting, soft shadow shaping, elegant posture, and a timeless polished editorial feel.')
        return _finish('Render as a classic old-Hollywood studio glamour portrait with controlled beauty lighting, butterfly lighting, soft shadow shaping, elegant posture, and a timeless polished editorial feel.')
    if style == 'Apocalyptic Wasteland':
        if mode == 'subtle':
            return _finish('Render with a clear post-apocalyptic wasteland mood, showing worn ruins, dust, and bleak survival atmosphere.')
        if mode == 'strong':
            return _finish('Render with a severe post-apocalyptic wasteland atmosphere: heavily ruined structures, cracked concrete, rusted debris, ash-filled air, scorched surfaces, abandoned survival-world desolation, and a clearly devastated end-of-civilization mood. Make the world feel deeply wrecked, not merely slightly old or untidy.')
        return _finish('Render with a strong post-apocalyptic wasteland atmosphere: ruined structures, cracked concrete, rusted debris, ash-filled air, scorched surfaces, abandoned survival-world desolation, and a clearly devastated mood. Make the world feel genuinely ruined, not merely slightly old or untidy.')
    if style == 'Neon Melancholy / Rain Glass':
        if mode == 'subtle':
            return _finish('Render with a rainy-night neon mood, showing soft colored reflections and urban melancholy through wet glass.')
        if mode == 'strong':
            return _finish('Render with a strong rainy-night neon mood: magenta and cyan neon glow, blurred urban lights behind raindrops, wet-window reflections, humid haze, and melancholic city light diffused through rain-soaked glass. Do not satisfy the style with plain raindrops alone.')
        return _finish('Render with a clear rainy-night neon mood: magenta and cyan neon glow, blurred urban lights behind raindrops, wet-window reflections, humid haze, and melancholic city light diffused through rain-soaked glass. Do not satisfy the style with plain raindrops alone.')
    return _finish('')


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
        if model_key in {'flux', 'krea2'}:
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
                        'Let the scene become a gentle soft-pastel drawing while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Preserve the visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Restyle the full image as a coherent soft-pastel drawing with visible chalky pastel marks, hand-smudged shading, and readable scene detail on textured paper')
            return ('Preserve the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Restyle the full image as a soft-pastel drawing while keeping the surrounding scene coherent')
        if model_key == 'qwen':
            if mode == 'subtle':
                return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Change only: turn the image into a gentle soft-pastel drawing while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Preserve: visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Change clearly: restyle the full image as a coherent soft-pastel drawing with visible chalky pastel marks, hand-smudged shading, and readable scene detail on textured paper')
            return ('Preserve: visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Change clearly: restyle the full image as a soft-pastel drawing while keeping the surrounding scene coherent')
        if model_key in {'flux', 'krea2'}:
            if mode == 'subtle':
                return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene objects',
                        'Apply a gentle soft-pastel drawing treatment while keeping the room details and outside view readable')
            if mode == 'strong':
                return ('Keep the visible subject count, core facial identity, main outfit idea, pose, setting, window, and important indoor and outdoor scene details',
                        'Restyle the full image as a coherent soft-pastel drawing with visible chalky pastel marks, hand-smudged shading, and readable scene detail on textured paper')
            return ('Keep the visible subject count, facial identity, main outfit idea, pose, setting, window, and important scene details',
                    'Restyle the full image as a soft-pastel drawing while keeping the surrounding scene coherent')
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
        if model_key in {'flux', 'krea2'}:
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
        if model_key in {'flux', 'krea2'}:
            return ('Keep the core subject, pose, and scene idea', '')
        return ('', '')
    if style == 'Pixel Art':
        if model_key == 'zimage':
            return ('Preserve the core subject and scene idea', '')
        if model_key == 'qwen':
            return ('Preserve: core subject and scene idea', '')
        if model_key in {'flux', 'krea2'}:
            return ('Keep the core subject and scene idea', '')
        return ('', '')
    if style == '3D Collectible Figure':
        if model_key == 'zimage':
            return ('Preserve the core subject and scene idea', '')
        if model_key == 'qwen':
            return ('Preserve: core subject and scene idea', '')
        if model_key in {'flux', 'krea2'}:
            return ('Keep the core subject and scene idea', '')
        return ('', '')
    if style == 'Miniature Diorama':
        if model_key == 'zimage':
            return ('Preserve the core subject and scene idea', '')
        if model_key == 'qwen':
            return ('Preserve: core subject and scene idea', '')
        if model_key in {'flux', 'krea2'}:
            return ('Keep the core subject and scene idea', '')
        return ('', '')
    return ('', '')



def _krea2_anchor_preserve_sentence(kind: Any = "", variant: str = "default") -> str:
    """Return Krea2 anchor wording without person-only mechanical substitutions.

    Person/couple/group prompts keep the established wording exactly.  Standalone
    environment/product prompts use separate semantic anchor slots so later
    generic environment/product postprocess does not create phrases like
    "environmental detail idea" or repeated "product arrangement" anchors.
    """
    k = _clean_text(kind).lower()
    v = _clean_text(variant).lower()
    if k == "environment":
        if v == "identity_intent":
            return "Use the setting identity, spatial layout, atmosphere, and scene intent as anchors"
        if v == "sketch_window":
            return "Use the same setting, spatial layout, window context when present, atmosphere, and key environmental details as anchors"
        if v == "compact_style":
            return "Use the same setting, spatial layout, atmosphere, and scene idea as anchors"
        return "Use the same setting, spatial layout, atmosphere, composition, and important environmental details as anchors"
    if k == "product":
        if v == "identity_intent":
            return "Use the product identity, material, arrangement, and scene intent as anchors"
        if v == "sketch_window":
            return "Use the same product identity, material, arrangement, setting context, and key scene details as anchors"
        if v == "compact_style":
            return "Use the same product identity, material, arrangement, and scene idea as anchors"
        return "Use the same product identity, material, arrangement, setting, composition, and important scene details as anchors"
    if v == "identity_intent":
        return "Use the subject identity, visible styling, main pose, and scene intent as anchors"
    if v == "style_specific_main":
        return "Use visible subject count, facial identity, main outfit idea, pose, setting, and important scene objects as anchors"
    if v == "style_specific_basic":
        return "Use visible subject count, facial identity, outfit idea, pose, setting, and key scene details as anchors"
    if v == "style_specific_window_objects":
        return "Use subject count, facial identity, outfit idea, pose, setting, window, and key scene objects as anchors"
    if v == "style_specific_window_indoor":
        return "Use subject count, facial identity, outfit idea, pose, setting, window, and key indoor/outdoor scene details as anchors"
    if v == "style_specific_window_details":
        return "Use subject count, facial identity, outfit idea, pose, setting, window, and key scene details as anchors"
    if v == "compact_style":
        return "Use the subject and scene idea as anchors"
    if v == "subject_pose_scene":
        return "Use the subject, pose, and scene idea as anchors"
    return "Use the same subject, visible styling, pose, setting, composition, and important objects as anchors"

def _krea2_style_specific_preserve_scope(style_name: Any, mode: str, kind: str = "") -> Tuple[str, str]:
    """Krea2 style anchors with concrete visual wording and minimal meta-helper prose."""
    style = str(style_name or '')
    mode = _style_application_mode(mode)
    if style == 'Chibi Style':
        if mode == 'subtle':
            return (_krea2_anchor_preserve_sentence(kind, 'style_specific_main'),
                    'Apply a gentle chibi illustration layer with rounded proportions, simplified lineart, and cute color styling')
        if mode == 'strong':
            return (_krea2_anchor_preserve_sentence(kind, 'style_specific_basic'),
                    'Restyle visible people with oversized chibi proportions, clean lineart, cute color styling, and compact simplified bodies')
        return (_krea2_anchor_preserve_sentence(kind, 'style_specific_basic'),
                'Restyle the people in a chibi illustration style with rounded proportions and simplified cute forms')
    if style == 'Pastel Chalk Drawing':
        if mode == 'subtle':
            return (_krea2_anchor_preserve_sentence(kind, 'sketch_window' if _clean_text(kind).lower() in {'environment', 'product'} else 'style_specific_window_objects'),
                    'Apply soft pastel paper texture, light chalk strokes, and gentle smudged shading')
        if mode == 'strong':
            return (_krea2_anchor_preserve_sentence(kind, 'sketch_window' if _clean_text(kind).lower() in {'environment', 'product'} else 'style_specific_window_indoor'),
                    'Restyle the full image as a soft-pastel drawing with chalk marks, powdery pigment, hand-smudged shading, and textured paper')
        return (_krea2_anchor_preserve_sentence(kind, 'sketch_window' if _clean_text(kind).lower() in {'environment', 'product'} else 'style_specific_window_details'),
                'Restyle the image as a soft-pastel drawing with chalk texture and smudged paper shading')
    if style == 'Graphite Pencil Sketch':
        if mode == 'subtle':
            return (_krea2_anchor_preserve_sentence(kind, 'sketch_window' if _clean_text(kind).lower() in {'environment', 'product'} else 'style_specific_window_objects'),
                    'Apply graphite pencil linework, light hatching, and paper texture')
        if mode == 'strong':
            return (_krea2_anchor_preserve_sentence(kind, 'sketch_window' if _clean_text(kind).lower() in {'environment', 'product'} else 'style_specific_window_indoor'),
                    'Restyle the full image as a graphite pencil sketch with fine line art, hatching, paper tooth, and background detail')
        return (_krea2_anchor_preserve_sentence(kind, 'sketch_window' if _clean_text(kind).lower() in {'environment', 'product'} else 'style_specific_window_details'),
                'Restyle the image as a graphite pencil sketch with linework, hatching, and paper texture')
    if style in {'Charcoal Drawing', 'Oil Painting', 'Watercolor / Painterly'}:
        return (_krea2_anchor_preserve_sentence(kind, 'subject_pose_scene'), '')
    if style in {'Pixel Art', '3D Collectible Figure', 'Miniature Diorama'}:
        return (_krea2_anchor_preserve_sentence(kind, 'compact_style'), '')
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
        special_directive = _style_specific_directive(bp.style_name, mode, bp.mood_family)
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
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            scope = _monochrome_safe_style_scope_text(scope)
        parts = [_sentence(preserve)]
        if scope:
            _append_non_redundant_sentence(parts, scope)
        if special_directive:
            _append_non_redundant_sentence(parts, special_directive)
        insert = _dedupe_classical_glamour_anchor_insert(insert, special_directive, bp.style_name, bp.style_anchor, getattr(bp, "krea_framing_context", ""))
        parts.append(insert)
        return " ".join(parts)

    if model_key == "qwen":
        override_preserve, override_change = _style_specific_preserve_scope(model_key, bp.style_name, mode)
        special_directive = _style_specific_directive(bp.style_name, mode, bp.mood_family)
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
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            change = _monochrome_safe_style_scope_text(change)
        parts = [_sentence(preserve)]
        if change:
            _append_non_redundant_sentence(parts, change)
        if special_directive:
            _append_non_redundant_sentence(parts, special_directive)
        insert = _dedupe_classical_glamour_anchor_insert(insert, special_directive, bp.style_name, bp.style_anchor, getattr(bp, "krea_framing_context", ""))
        parts.append(insert)
        return " ".join(parts)

    if model_key == "flux":
        override_preserve, override_scope = _style_specific_preserve_scope(model_key, bp.style_name, mode)
        special_directive = _style_specific_directive(bp.style_name, mode, bp.mood_family)
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
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            scope = _monochrome_safe_style_scope_text(scope)
        parts = [_sentence(preserve)]
        if scope:
            _append_non_redundant_sentence(parts, scope)
        if special_directive:
            _append_non_redundant_sentence(parts, special_directive)
        insert = _dedupe_classical_glamour_anchor_insert(insert, special_directive, bp.style_name, bp.style_anchor, getattr(bp, "krea_framing_context", ""))
        parts.append(insert)
        return " ".join(parts)

    if model_key == "krea2":
        override_preserve, override_scope = _krea2_style_specific_preserve_scope(bp.style_name, mode, bp.krea_framing_context)
        special_directive = _style_specific_directive(bp.style_name, mode, bp.mood_family)
        if override_preserve:
            preserve = override_preserve
            scope = override_scope
        elif mode == "subtle":
            preserve = _krea2_anchor_preserve_sentence(bp.krea_framing_context)
            scope = "Apply gentle style changes to lighting, color treatment, texture, and presentation"
        elif mode == "strong" and transformative:
            preserve = _krea2_anchor_preserve_sentence(bp.krea_framing_context, "identity_intent")
            scope = "Restyle rendering, lighting, color, texture, and framing around those anchors"
        elif mode == "strong":
            preserve = _krea2_anchor_preserve_sentence(bp.krea_framing_context)
            scope = "Give the selected style priority in lighting, color treatment, texture, and presentation"
        else:
            preserve = _krea2_anchor_preserve_sentence(bp.krea_framing_context)
            scope = "Shift visual presentation through the selected style, lighting mood, color treatment, texture, and requested framing"
        if str(bp.style_name or "") == 'Vintage Film Look' and mode == 'balanced':
            scope = "Shape the image with analog film finish, tonal response, grain, and nostalgic print character"
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            scope = _monochrome_safe_style_scope_text(scope)
        parts = [_sentence(preserve)]
        # Krea2 benefits more from concrete style directives than generic
        # "make the style stronger / keep it readable" scaffolding.  When a
        # style-specific directive exists, let that visual wording carry the
        # style change and skip the generic scope sentence.
        if scope and not special_directive:
            _append_non_redundant_sentence(parts, scope)
        if special_directive:
            _append_non_redundant_sentence(parts, special_directive)
        insert = _dedupe_classical_glamour_anchor_insert(insert, special_directive, bp.style_name, bp.style_anchor, getattr(bp, "krea_framing_context", ""))
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
    s = re.sub(r"(?<!\.)\.\.(?!\.)", ".", s)
    s = re.sub(r"\.\s+\.", ". ", s)
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

FULL_BODY_NO_AUTO_LENS_KEYS = {
    "full body (head to toe)",
    "full shot (full body + extra space)",
    "seated full body",
}


def _is_full_body_or_wide_framing(scene_framing: str) -> bool:
    return _canonical_ui_value(scene_framing, "scene_framing") in FULL_BODY_FRAMING_KEYS


def _is_full_body_no_auto_lens_framing(scene_framing: str) -> bool:
    return _canonical_ui_value(scene_framing, "scene_framing") in FULL_BODY_NO_AUTO_LENS_KEYS


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
    framing_key = _canonical_ui_value(scene_framing, "scene_framing") or _clean_text(scene_framing)
    if framing_key in {"overhead portrait", "high-angle portrait"}:
        out: List[str] = []
        for term in camera_terms:
            cleaned = _clean_text(term)
            low = cleaned.lower()
            if not cleaned:
                continue
            if "low-angle" in low or "low angle" in low or "upward perspective" in low:
                continue
            out.append(cleaned)
        if len(out) != len([_clean_text(t) for t in camera_terms if _clean_text(t)]):
            if not any("dramatic" in _clean_text(t).lower() for t in out):
                out.append("dramatic spatial composition")
            return _unique(out)
    if not _is_full_body_or_wide_framing(scene_framing):
        return camera_terms
    blocked = {
        "close framing",
        "close detail framing",
        "tight compressed framing",
        "product-display close framing",
        "controlled studio depth",
        "soft focus depth",
        "shallow depth of field",
        "creamy bokeh",
    }
    out = []
    for term in camera_terms:
        cleaned = _clean_text(term)
        low = cleaned.lower()
        if low in blocked:
            continue
        if re.search(r"\b(?:85|100|105|135|200)\s*mm\b", low):
            continue
        if any(token in low for token in ("telephoto", "long lens", "macro lens", "compressed perspective", "compressed depth", "soft background separation", "close framing", "close-up framing", "close-up", "controlled studio depth")):
            continue
        if "macro" in low and "detail" in low:
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
    krea_framing_context: str = ""


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



STYLE_CONFLICT_CLEANUP_MODEL_KEYS: frozenset = frozenset({"zimage", "qwen", "flux", "krea2"})

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
        (re.compile(r"\b(?:hard\s+photographic\s+sharpness|crisp\s+digital\s+sharpness|hard\s+sharp\s+focus|ultra[-\s]?sharp\s+focus|sharp\s+focus)\b", re.IGNORECASE), "soft diffused clarity"),
        (re.compile(r"\b(?:black\s+and\s+white\s+noir\s+lighting|noir\s+lighting|high\s+contrast\s+shadows?|harsh\s+contrast|stark\s+contrast)\b", re.IGNORECASE), "soft low-contrast pastel lighting"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photorealistic|photoreal|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+DSLR\s+(?:(?:photo|photograph)(?:\s+quality)?|quality)\b", re.IGNORECASE), "clear image quality"),
        (re.compile(r"\b(?:photo[-\s]?realistic|photoreal|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:rendering|look|style|finish|portrait|image)\b", re.IGNORECASE), "soft luminous subject rendering"),
        (re.compile(r"\bDSLR\s+(?:(?:photo|photograph)(?:\s+quality)?|quality)\b", re.IGNORECASE), "clear image quality"),
        (re.compile(r"\breal(?:istic)?\s+skin\s+texture\b|\b(?:realistic\s+)?skin\s+pores\b", re.IGNORECASE), "soft skin depiction"),
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
        (re.compile(r"\bcolorful\s+vibrant\s+neon\s+saturated\s+palette(?:\s+and\s+vibrant\s+colors?)?\b", re.IGNORECASE), "high-contrast monochrome neon-like lighting"),
        (re.compile(r"\bcolorful\s+vibrant\s+neon(?:\s+(?:lighting|lights?|glow|signage|signs?|colors?|colours?|accents?|atmosphere|style|world))?\b", re.IGNORECASE), "high-contrast monochrome neon-like lighting"),
        (re.compile(r"\bvibrant\s+neon(?:\s+(?:lighting|lights?|glow|signage|signs?|colors?|colours?|accents?|atmosphere|style|world))?\b", re.IGNORECASE), "high-contrast neon-like lighting"),
        (re.compile(r"\bvivid\s+rainbow\s+colors?\b|\bbright\s+saturated\s+color\s+palette\b", re.IGNORECASE), "rich grayscale tonal contrast"),
        (re.compile(r"\bcolorful\s+color\s+grading\b", re.IGNORECASE), "classic monochrome tonal grading"),
        (re.compile(r"\b(?:colorful|vibrant|saturated)\s+(?:color\s+palette|colour\s+palette|colors?|colours?|palette|tones?|lighting|grade|grading)\b", re.IGNORECASE), "rich grayscale tonal contrast"),
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


STYLE_CONFLICT_STRONG_PHOTO_REPLACEMENTS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"\b(?:photorealistic|photo[-\s]?realistic|photoreal|photographic|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+DSLR\s+(?:portrait\s+)?(?:photo|photograph|image|depiction)(?:\s+quality)?\s+of\b", re.IGNORECASE), "clear subject depiction of"),
    (re.compile(r"\b(?:photorealistic|photo[-\s]?realistic|photoreal|photographic|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+DSLR\s+(?:portrait\s+)?(?:photo|photograph|image|depiction|rendering|render|look|style|finish)(?:\s+quality)?\b", re.IGNORECASE), "clear subject depiction"),
    (re.compile(r"\b(?:photorealistic|photo[-\s]?realistic|photoreal|photographic|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+portrait\s+photo\s+of\b", re.IGNORECASE), "clear subject depiction of"),
    (re.compile(r"\b(?:photorealistic|photo[-\s]?realistic|photoreal|photographic|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?:portrait\s+)?(?:photo|photograph|image|rendering|render|look|style|finish)\b", re.IGNORECASE), "clear subject depiction"),
    (re.compile(r"\bportrait\s+photo\s+of\b", re.IGNORECASE), "subject depiction of"),
    (re.compile(r"\b(?:photo|photograph)\s+of\b", re.IGNORECASE), "depiction of"),
    (re.compile(r"\bsharp\s+camera\s+lens\b|\bcamera\s+lens\b|\brealistic\s+camera\s+lens\b", re.IGNORECASE), "clear visual structure"),
    (re.compile(r"\b(?:shallow\s+)?depth\s+of\s+field\b|\bsoft\s+focus\s+depth\b|\bbokeh\b", re.IGNORECASE), "layered visual depth"),
)


STYLE_CONFLICT_STRONG_PHOTO_PROFILES: frozenset = frozenset({
    "traditional_media",
    "pixel_art",
    "miniature",
    "collectible_3d",
    "chibi",
    "cel_animation",
    "dream_pastel",
    "noir",
    "black_white",
    "light_trails",
    "volumetric_dust",
    "apocalyptic",
})


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
    if _is_default_style(bp) or _is_custom_text_only(bp):
        return False
    style_key = _canonical_ui_value(bp.style_name, "style_dna") or _clean_text(bp.style_name)
    # Dream Pastel is a light/color treatment. In strong cleanup, remove direct
    # sharp/noir/high-contrast conflicts even for tag-family outputs, because
    # the external text is still appended and can overpower the pastel lighting.
    if style_key == "Dream Pastel Diffusion" and mode == "strong":
        return True
    if _model_family(bp.model_profile) != "natural":
        return False
    if _model_key(bp.model_profile) not in STYLE_CONFLICT_CLEANUP_MODEL_KEYS:
        return False
    if _is_style_conflict_cleanup_style(bp.style_name):
        return True
    return mode == "strong" and style_key not in {"Auto by Mood", "Neutral / Minimal Carryover"}


def _apply_style_conflict_replacements(text: str, replacements: Tuple[Tuple[re.Pattern, str], ...]) -> str:
    out = text
    for pattern, repl in replacements:
        out = pattern.sub(repl, out)
    return out


KREA2_TRACKED_RELAX_REPLACEMENTS: frozenset = frozenset({
    "clear hand-rendered subject quality",
    "clear hand-rendered edges",
})


def _apply_style_conflict_replacements_tracked(
    text: str,
    replacements: Tuple[Tuple[re.Pattern, str], ...],
    *,
    marker_counter: List[int],
) -> str:
    """Apply style-conflict replacements while marking only generated fragments.

    This is used for Krea2 external-prompt cleanup so a later Krea2 residue
    pass can distinguish text the node generated from the exact same wording a
    user may have typed.  Non-target replacement strings remain unchanged.
    """
    out = text
    for pattern, repl in replacements:
        def replace_match(match, repl=repl):
            value = match.expand(repl)
            if _clean_text(value).lower() in KREA2_TRACKED_RELAX_REPLACEMENTS:
                idx = marker_counter[0]
                marker_counter[0] += 1
                return f"__UPS_KREA2_RELAX_BEGIN_{idx}__{value}__UPS_KREA2_RELAX_END_{idx}__"
            return value
        out = pattern.sub(replace_match, out)
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
        "rich grayscale tonal contrast",
        "classic monochrome tonal grading",
        "high-contrast monochrome neon-like lighting",
        "high-contrast neon-like lighting",
        "tonally rich",
        "high-contrast",
        "deep-toned",
        "layered visual depth",
        "visible dusty volumetric atmosphere",
        "clear skin depiction",
        "clear visual structure",
        "weathered survival atmosphere",
        "soft diffused clarity",
        "soft low-contrast pastel lighting",
        "soft skin depiction",
        "clear image quality",
    ):
        s = re.sub(rf"\b{re.escape(phrase)}\b(?:\s*(?:,|and|with)\s*\b{re.escape(phrase)}\b)+", phrase, s, flags=re.IGNORECASE)
        s = re.sub(rf"\b{re.escape(phrase)}\b(?:\s+\b{re.escape(phrase)}\b)+", phrase, s, flags=re.IGNORECASE)
    s = re.sub(r"\bhigh-contrast\s+neon-like\s+lighting\s+lighting\b", "high-contrast neon-like lighting", s, flags=re.IGNORECASE)
    s = re.sub(r"\bhigh-contrast\s+monochrome\s+neon-like\s+lighting\s+lighting\b", "high-contrast monochrome neon-like lighting", s, flags=re.IGNORECASE)
    s = re.sub(r"\blayered\s+visual\s+depth\s+blur\b", "layered visual depth", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:photorealistic|photo[-\s]?realistic|photoreal|photographic|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?=(?:clear\s+hand-rendered\s+subject\s+quality|readable\s+pixel\s+quality|clean\s+visual\s+quality|clear\s+image\s+quality|clear\s+subject\s+(?:depiction|rendering)|clean\s+animation\s+rendering)\b)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bclear\s+hand-rendered\s+subject\s+quality\s+of\b", "clear hand-rendered subject depiction of", s, flags=re.IGNORECASE)
    s = re.sub(r"\breadable\s+pixel\s+quality\s+of\b", "readable pixel-art depiction of", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:clean\s+visual|clear\s+image)\s+quality\s+of\b", "clear subject depiction of", s, flags=re.IGNORECASE)
    s = re.sub(r"\b((?:clear|soft|readable|hand-rendered|luminous|visual|pixel|subject)(?:[-\w]*\s+){0,4}quality)\s+quality\b", r"\1", s, flags=re.IGNORECASE)
    s = re.sub(r"\bquality\s+quality\b", "quality", s, flags=re.IGNORECASE)
    return s.strip(" ,")


def _relax_style_conflicting_external_prompt(
    text: Any,
    bp: "Blueprint",
    cleanup_mode: Any,
    *,
    track_krea2_generated_fragments: bool = False,
) -> str:
    """Relax only the phrases that conflict with the selected style profile.

    The cleanup is intentionally style-specific: it does not globally remove
    broad terms such as "photorealistic". A phrase is rewritten only when the
    active style profile says that phrase directly suppresses that style.
    When Krea2 asks for tracked fragments, only replacement text generated by
    this function is marked; identical user-authored wording remains unmarked.
    """
    mode = _style_conflict_cleanup_mode(cleanup_mode)
    out = _clean_text(text)
    if not out or mode == "off":
        return out

    marker_counter = [0]

    def apply(replacements: Tuple[Tuple[re.Pattern, str], ...]) -> str:
        nonlocal out
        if track_krea2_generated_fragments:
            out = _apply_style_conflict_replacements_tracked(out, replacements, marker_counter=marker_counter)
        else:
            out = _apply_style_conflict_replacements(out, replacements)
        return out

    profile = _style_conflict_profile_for_style(bp.style_name)
    if not profile:
        if mode == "strong":
            apply(STYLE_CONFLICT_COMMON_SAFE_REPLACEMENTS)
            apply(STYLE_CONFLICT_STRONG_PHOTO_REPLACEMENTS)
            return _cleanup_relaxed_external_prompt_text(out)
        return out

    apply(STYLE_CONFLICT_COMMON_SAFE_REPLACEMENTS)
    apply(STYLE_CONFLICT_PROFILE_REPLACEMENTS.get(profile, ()))
    if mode == "strong" and profile in STYLE_CONFLICT_STRONG_PHOTO_PROFILES:
        apply(STYLE_CONFLICT_STRONG_PHOTO_REPLACEMENTS)

    # User-selected lens presets should be respected. Only soften explicit camera
    # terms typed into the external prompt when the node lens control is auto.
    if bp.lens_preset in ("", "auto"):
        camera_replacements = STYLE_CONFLICT_PROFILE_CAMERA_REPLACEMENTS.get(profile, ())
        if mode == "strong" or profile in {"traditional_media", "pixel_art", "chibi"}:
            apply(camera_replacements)

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


class PromptComposerCore:
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
        neutral_mood = {"anchor": "", "emotion": []}
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
        if suppress_youthful_adult_context and mood_family in {"Erotic / Sensual"}:
            # Keep the youth-style adult safety guard narrow: remove only the
            # explicitly sensual mood itself.  Other user-selected moods such as
            # Black & White Film still drive monochrome, camera, and emotion logic.
            mood_family = "Default / None"
            mood = MOOD_FAMILIES.get(mood_family) or neutral_mood
        adult_wardrobe_text = _clean_text(ADULT_WARDROBE.get(adult_wardrobe_key, ""))
        scene_framing_key = _canonical_ui_value(scene_framing, "scene_framing") or "auto"
        scene_framing_terms = SCENE_FRAMING.get(scene_framing_key, SCENE_FRAMING.get("auto", []))
        scene_framing_terms = _unique(scene_framing_terms)

        lens = _auto_lens(style_dna, mood_family, scene_framing_key) if lens_preset == "auto" else lens_preset
        _suppress_camera_bp = _suppress_auto_camera_for_prompt(style_dna, mood_family, lens_preset)
        _suppress_framing_auto_lens = (lens_preset == "auto" and _is_full_body_no_auto_lens_framing(scene_framing_key))
        if _suppress_camera_bp or _suppress_framing_auto_lens:
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
            return _unique_style_pool(_style_text_pool(style.get(field, [])) + _style_text_pool(np_cues.get(field, [])), style_dna, field)

        lighting = _pick(rng, _merged_pool("lighting"), cue_count)
        color = _pick(rng, _merged_pool("color"), min(cue_count, 4))
        composition = _pick(rng, _merged_pool("composition"), cue_count)
        texture = _pick(rng, _merged_pool("texture"), cue_count)
        style_signature = _style_data_signature(style, np_cues)
        if _is_monochrome_output_context(mood_family, style_dna, style_signature):
            lighting = _filter_chromatic_terms_for_monochrome(lighting)
            color = _filter_chromatic_terms_for_monochrome(color, fallback=True, style_name=style_dna)
            composition = _filter_chromatic_terms_for_monochrome(composition)
            texture = _filter_chromatic_terms_for_monochrome(texture)
        picked_emotion = _pick(rng, mood.get("emotion", []), emotion_count)
        emotion = _filter_mood_positive_terms_for_style(picked_emotion, style_signature)
        if picked_emotion and not emotion:
            emotion = _bridge_mood_emotion_after_conflict(mood_family, picked_emotion, style_signature, style_dna)
        anchor = _style_text_scalar(style.get("anchor")) or _style_text_scalar(mood.get("anchor"))

        positive_context_terms = [_style_text_scalar(MOOD_FAMILIES.get(mood_family, {}).get("anchor", "")), anchor] + emotion + lighting + color + composition + texture
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
        # enforcement must live in the positive prompt. Keep only model-profile
        # safety/quality negatives here; user-provided external negatives are merged
        # later unchanged.
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
        strength = PromptComposerCore._external_strength_settings(bp.style_strength)
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
            return PromptComposerCore._tone_only_style_parts(bp)
        return PromptComposerCore.external_style_parts(bp)


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
        mood_tokens = PromptComposerCore._anchor_tokens(mood_value)
        style_tokens = PromptComposerCore._anchor_tokens(style_value)
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

        return style_anchor, PromptComposerCore._merge_style_anchors(mood_anchor, style_anchor)

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
        composition = PromptComposerCore._parts_or_fallback(bp.composition, fallback, "composition", strength["composition"])
        composition = _harmonize_style_terms_for_framing(composition, bp.scene_framing)
        lighting = PromptComposerCore._parts_or_fallback(bp.lighting, fallback, "lighting", strength["lighting"])
        color = PromptComposerCore._parts_or_fallback(bp.color, fallback, "color", strength["color"])
        texture = PromptComposerCore._parts_or_fallback(bp.texture, fallback, "texture", strength["texture"])
        lighting = _filter_nonphoto_style_terms(lighting, bp.style_name)
        color = _filter_nonphoto_style_terms(color, bp.style_name)
        composition = _filter_nonphoto_style_terms(composition, bp.style_name)
        texture = _filter_nonphoto_style_terms(texture, bp.style_name)
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            lighting = _filter_chromatic_terms_for_monochrome(lighting)
            color = _filter_chromatic_terms_for_monochrome(color, fallback=True, style_name=bp.style_name)
            composition = _filter_chromatic_terms_for_monochrome(composition)
            texture = _filter_chromatic_terms_for_monochrome(texture)
        suppress_camera = _suppress_auto_camera_for_prompt(bp.style_name, bp.mood_family, bp.lens_preset)
        wardrobe_note = _clean_text(bp.adult_wardrobe)
        if _is_monochrome_output_context(bp.mood_family, bp.style_name):
            wardrobe_note = _monochrome_safe_wardrobe_note(wardrobe_note)
        return {
            "lighting": lighting,
            "color": color,
            "composition": composition,
            "texture": texture,
            "camera": _safe_camera_terms(bp.camera, suppress_camera=suppress_camera)[:strength["camera"]],
            "custom_note": _external_custom_note(bp.custom_notes),
            "wardrobe_note": wardrobe_note,
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
            "krea_framing_context": getattr(bp, "krea_framing_context", ""),
        }
        natural_insert_default = _natural_style_sentence(**sentence_args)
        natural_insert_flux = _natural_style_sentence(**sentence_args, flux_structured=True)
        natural_insert_krea2 = _natural_style_sentence(**sentence_args, krea_structured=True)
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
        alias_tag_insert = _style_tag_alias_insert(
            bp.style_name,
            bp.model_profile,
            weight=float(strength["weight"]),
            monochrome_context=_is_monochrome_output_context(bp.mood_family, bp.style_name, combined_anchor),
        )
        tag_insert = _join_unique_tags([alias_tag_insert, base_tag_insert])
        if parts["custom_note"]:
            tag_insert = _join_comma([tag_insert, parts["custom_note"]])

        return {
            "style_insert": _join_comma(list(ordered_tag_parts) + ([] if not parts["custom_note"] else [parts["custom_note"]])),
            "natural_insert": natural_insert_default,
            "natural_insert_flux": natural_insert_flux,
            "natural_insert_krea2": natural_insert_krea2,
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
            return PromptComposerCore._empty_style_parts()
        if _is_custom_text_only(bp):
            return PromptComposerCore._custom_only_style_parts(bp)

        fallback = NONPHYSICAL_STYLE_CUES.get(bp.style_name) or {}
        strength = PromptComposerCore._external_strength_settings(bp.style_strength)
        style_anchor, combined_anchor = PromptComposerCore._resolve_external_anchors(bp, fallback)
        parts = PromptComposerCore._external_style_components(bp, fallback, strength)
        return PromptComposerCore._render_external_style_parts(bp, style_anchor, combined_anchor, parts, strength)

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
        directive = _clean_text(_style_specific_directive(bp.style_name, bp.style_strength, bp.mood_family))
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
        style = PromptComposerCore.external_style_parts_for_prompt(bp, external)
        family = _model_family(bp.model_profile)
        key = _model_key(bp.model_profile)
        quality = _tag_quality_for_model(bp.model_profile, bp.adult_tone)
        if family == "tag":


            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            if _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", "")):
                external_tag_prompt = _neutralize_external_tag_prompt_for_monochrome(external_tag_prompt)
            return _join_unique_tags([quality, external_tag_prompt, style["tag_insert"]])
        if family == "mixed":
            if key == "anima":
                layered = _render_anima_style_layer_prompt(bp, external, style_first=False, style=style)
                if layered:
                    return layered

            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            if _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", "")):
                external_tag_prompt = _neutralize_external_tag_prompt_for_monochrome(external_tag_prompt)
            tag_block = _join_unique_tags([quality, external_tag_prompt, style["tag_insert"]])
            assist = PromptComposerCore._mixed_natural_assist(style, bp, has_external=bool(external), external_text=external)
            return _join_mixed_prompt(tag_block, assist)


        if _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", "")):
            external = _monochrome_safe_inline_text(external)

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
        style = PromptComposerCore.external_style_parts_for_prompt(bp, external)
        family = _model_family(bp.model_profile)
        key = _model_key(bp.model_profile)
        quality = _tag_quality_for_model(bp.model_profile, bp.adult_tone)
        if family == "tag":
            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            if _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", "")):
                external_tag_prompt = _neutralize_external_tag_prompt_for_monochrome(external_tag_prompt)
            return _join_unique_tags([quality, style["tag_insert"], external_tag_prompt])
        if family == "mixed":
            if key == "anima":
                layered = _render_anima_style_layer_prompt(bp, external, style_first=True, style=style)
                if layered:
                    return layered

            external_tag_prompt = _filter_external_rating_source_conflicts(external, bp.model_profile)
            if _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", "")):
                external_tag_prompt = _neutralize_external_tag_prompt_for_monochrome(external_tag_prompt)
            # In explicit prepend mode, keep the full style tag block before the
            # external prompt. Older builds split the style tags around the
            # external prompt, which made the output order look inconsistent.
            tag_block = _join_unique_tags([quality, style["tag_insert"], external_tag_prompt])
            assist = PromptComposerCore._mixed_natural_assist(style, bp, has_external=bool(external), external_text=external, style_first=True)
            return _join_mixed_prompt(tag_block, assist)

        if _is_monochrome_output_context(bp.mood_family, bp.style_name, style.get("combined_anchor", "")):
            external = _monochrome_safe_inline_text(external)

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
        style = PromptComposerCore.external_style_parts(bp)
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
            assist = PromptComposerCore._mixed_natural_assist(style, bp, has_external=False, external_text="")
            return _join_mixed_prompt(tag_block, assist)
        natural_quality = _natural_quality_for_prompt(bp)
        insert = _natural_insert_for_model(style, bp)
        insert = _wrap_model_specific_natural_insert(insert, bp, has_external=False)
        return _append_sentence(natural_quality, insert)



# ── Integrated standalone prompt builder engine ──────────────────────────────

_STANDALONE_PERSON_PROFILES = {
    "auto": ("woman", 1),
    "adult woman": ("woman", 1),
    "adult man": ("man", 1),
    "adult couple": ("adult couple", 2),
    "two adult women": ("two women", 2),
    "two adult men": ("two men", 2),
    "small adult group": ("small group", 4),
}

_STANDALONE_PUBLIC_LOCATIONS = {"city street", "shopping street", "alley", "park", "garden", "cafe", "restaurant", "bar / lounge", "rooftop", "balcony", "train station", "subway platform", "art gallery", "bookstore"}
_STANDALONE_OUTDOOR_LOCATIONS = {"city street", "shopping street", "alley", "park", "garden", "forest", "beach", "poolside", "rooftop", "balcony"}
_STANDALONE_PRIVATE_LOCATIONS = {"bedroom", "bathroom", "hotel room", "private studio", "studio backdrop", "modern apartment", "cozy living room", "kitchen", "office"}
_STANDALONE_WATER_LOCATIONS = {"beach", "poolside", "bathroom"}
_STANDALONE_WINDOW_LOCATIONS = {"cozy living room", "modern apartment", "bedroom", "hotel room", "cafe", "restaurant", "office", "library", "bookstore", "private studio"}


_SUBJECT_OUTFIT_PARTS = {
    "casual jeans and t-shirt": ("wearing jeans and a t-shirt", "casual outfit"),
    "white blouse and dark skirt": ("wearing a white blouse and a dark skirt", "white blouse, dark skirt"),
    "knit sweater and skirt": ("wearing a knit sweater and skirt", "knit sweater, skirt"),
    "summer dress": ("wearing a summer dress", "summer dress"),
    "elegant long dress": ("wearing an elegant long dress", "elegant dress"),
    "business suit": ("wearing a business suit", "business suit"),
    "office blouse and slacks": ("wearing an office blouse and slacks", "office outfit"),
    "hoodie and jeans": ("wearing a hoodie and jeans", "hoodie, jeans"),
    "denim jacket outfit": ("wearing a denim jacket outfit", "denim jacket"),
    "trench coat outfit": ("wearing a trench coat outfit", "trench coat"),
    "winter coat and scarf": ("wearing a winter coat and scarf", "winter coat, scarf"),
    "sportswear": ("wearing sportswear", "sportswear"),
    "swimwear / beachwear": ("wearing practical swimwear or beachwear", "swimwear, beachwear"),
    "traditional hanbok": ("wearing a traditional hanbok", "hanbok"),
    "simple black dress": ("wearing a simple black dress", "black dress"),
}

_LOCATION_PHRASES = {
    "cozy living room": "inside a cozy living room",
    "modern apartment": "inside a modern apartment",
    "bedroom": "inside a bedroom",
    "bathroom": "inside a bathroom",
    "hotel room": "inside a hotel room",
    "cafe": "inside a cafe",
    "restaurant": "inside a restaurant",
    "office": "inside an office",
    "library": "inside a library",
    "bookstore": "inside a bookstore",
    "kitchen": "inside a kitchen",
    "art gallery": "inside an art gallery",
    "bar / lounge": "inside a bar lounge",
    "balcony": "on a balcony",
    "rooftop": "on a rooftop",
    "city street": "on a city street",
    "shopping street": "on a shopping street",
    "alley": "in a narrow alley",
    "train station": "inside a train station",
    "subway platform": "on a subway platform",
    "park": "in a park",
    "garden": "in a garden",
    "forest": "in a forest",
    "beach": "on a beach",
    "poolside": "beside a swimming pool",
    "studio backdrop": "against a studio backdrop",
    "private studio": "inside a private studio",
}

_LOCATION_TAGS = {
    "cozy living room": ["living room", "indoor"],
    "modern apartment": ["modern apartment", "indoor"],
    "bedroom": ["bedroom", "indoor"],
    "bathroom": ["bathroom", "indoor"],
    "hotel room": ["hotel room", "indoor"],
    "cafe": ["cafe", "indoor"],
    "restaurant": ["restaurant", "indoor"],
    "office": ["office", "indoor"],
    "library": ["library", "indoor"],
    "bookstore": ["bookstore", "indoor"],
    "kitchen": ["kitchen", "indoor"],
    "art gallery": ["art gallery", "indoor"],
    "bar / lounge": ["bar lounge", "indoor"],
    "balcony": ["balcony", "outdoors"],
    "rooftop": ["rooftop", "outdoors"],
    "city street": ["city street", "outdoors"],
    "shopping street": ["shopping street", "outdoors"],
    "alley": ["alley", "outdoors"],
    "train station": ["train station", "indoor"],
    "subway platform": ["subway platform", "indoor"],
    "park": ["park", "outdoors"],
    "garden": ["garden", "outdoors"],
    "forest": ["forest", "outdoors"],
    "beach": ["beach", "outdoors"],
    "poolside": ["poolside", "outdoors"],
    "studio backdrop": ["studio backdrop", "plain backdrop"],
    "private studio": ["private studio", "controlled indoor setting"],
}

_LOCATION_DETAIL_PHRASES = {
    "minimal modern": "with a minimal, modern atmosphere",
    "luxury": "with a refined luxury atmosphere",
    "vintage classic": "with a vintage classic atmosphere",
    "dark intimate": "with a dark, intimate atmosphere",
    "bright spacious": "with a bright, spacious atmosphere",
    "natural organic": "with a natural, organic atmosphere",
}

_LOCATION_DETAIL_TAGS = {
    "minimal modern": ["minimal", "modern"],
    "luxury": ["luxury"],
    "vintage classic": ["vintage", "classic"],
    "dark intimate": ["dark atmosphere", "intimate atmosphere"],
    "bright spacious": ["bright", "spacious"],
    "natural organic": ["natural atmosphere", "organic"],
}

_AUTO_PROPS_BY_LOCATION = {
    "cozy living room": ["sofa", "coffee table", "curtains", "bookshelf", "floor lamp", "indoor plants"],
    "modern apartment": ["large window", "minimal furniture", "curtains", "indoor plants", "soft lamp"],
    "bedroom": ["bed", "pillows", "curtains", "bedside lamp", "mirror"],
    "bathroom": ["mirror", "tiles", "sink", "steam", "soft towel"],
    "hotel room": ["bed", "curtains", "side table", "city-view window", "warm lamp"],
    "cafe": ["small table", "cup", "window seat", "warm lights", "plants"],
    "restaurant": ["dining table", "tableware", "warm lights"],
    "office": ["desk", "laptop", "office chair", "window blinds"],
    "library": ["bookshelves", "reading table", "soft lamps"],
    "bookstore": ["book displays", "shelves", "warm lights"],
    "kitchen": ["countertop", "tableware", "soft kitchen light"],
    "art gallery": ["framed artwork", "gallery wall", "spotlights"],
    "bar / lounge": ["bar counter", "dim lights", "glassware", "velvet seating"],
    "balcony": ["railing", "city view", "potted plants"],
    "rooftop": ["city skyline", "railing", "night lights"],
    "city street": ["streetlights", "storefronts", "wet pavement"],
    "shopping street": ["storefronts", "display windows", "streetlights"],
    "alley": ["narrow walls", "streetlights", "wet pavement"],
    "train station": ["platform lights", "signage", "suitcase"],
    "subway platform": ["platform edge", "station lights", "train doors"],
    "park": ["trees", "walking path", "benches", "greenery"],
    "garden": ["flowers", "greenery", "stone path", "soft foliage"],
    "forest": ["trees", "moss", "soft mist", "filtered light"],
    "beach": ["sand", "shoreline", "distant waves", "soft horizon"],
    "poolside": ["pool water", "deck chair", "reflections", "sunlit tiles"],
    "studio backdrop": ["studio lighting", "plain backdrop"],
    "private studio": ["studio lighting", "soft backdrop", "minimal set pieces"],
}

# Scene-detail auto fill should enrich the location safely without adding new people,
# animals, actions, wardrobe, pose, identity, or style directions. Keep these phrases
# structural/atmospheric so higher detail levels do not fight the user's main prompt.
_AUTO_SCENE_QUALITY_BY_LOCATION = {
    "cozy living room": ["coherent room layout", "soft lived-in interior texture", "balanced background depth"],
    "modern apartment": ["clean apartment layout", "subtle interior texture", "balanced window light depth"],
    "bedroom": ["coherent bedroom layout", "soft fabric texture", "gentle background depth"],
    "bathroom": ["clean bathroom layout", "subtle tile texture", "soft diffused depth"],
    "hotel room": ["coherent hotel room layout", "soft premium interior texture", "balanced background depth"],
    "cafe": ["natural cafe layout", "warm interior texture", "soft background depth"],
    "restaurant": ["coherent dining layout", "warm table-setting texture", "balanced ambient depth"],
    "office": ["clean workspace layout", "subtle office texture", "balanced background depth"],
    "library": ["layered bookshelf depth", "quiet reading-room texture", "balanced interior depth"],
    "bookstore": ["layered book-display depth", "warm shelf texture", "balanced interior depth"],
    "kitchen": ["coherent kitchen layout", "clean countertop texture", "soft practical depth"],
    "art gallery": ["clean gallery spacing", "subtle wall texture", "balanced spotlight depth"],
    "bar / lounge": ["coherent lounge layout", "soft reflective texture", "muted atmospheric depth"],
    "balcony": ["clear balcony depth", "subtle railing texture", "open-air background depth"],
    "rooftop": ["clear rooftop depth", "subtle city texture", "open-air background depth"],
    "city street": ["clear street perspective", "urban background texture", "balanced environmental depth"],
    "shopping street": ["clear storefront perspective", "urban display texture", "balanced environmental depth"],
    "alley": ["clear alley perspective", "subtle wall texture", "moody background depth"],
    "train station": ["clear platform perspective", "subtle station texture", "balanced environmental depth"],
    "subway platform": ["clear platform perspective", "subtle station texture", "balanced environmental depth"],
    "park": ["natural greenery depth", "readable walking path layout", "soft open air atmosphere"],
    "garden": ["layered foliage depth", "natural garden texture", "soft open air atmosphere"],
    "forest": ["layered woodland depth", "natural organic texture", "soft filtered atmosphere"],
    "beach": ["clear shoreline depth", "natural sand and water texture", "soft open air atmosphere"],
    "poolside": ["clear poolside layout", "subtle reflective texture", "soft resort-like depth"],
    "studio backdrop": ["clean backdrop separation", "controlled studio depth", "balanced foreground-background spacing"],
    "private studio": ["clean studio layout", "soft backdrop texture", "balanced foreground-background spacing"],
}


_PROP_PHRASES = {
    "plants": ["plants", "indoor plants"],
    "book / magazine": ["book", "magazine"],
    "cup / drink": ["cup", "drink"],
    "smartphone": ["smartphone"],
    "lamp": ["lamp", "soft lamp"],
    "mirror": ["mirror"],
    "umbrella": ["umbrella"],
    "studio lighting": ["studio lighting"],
    "luxury interior details": ["luxury interior details"],
    "cosmetic product": ["sleek cosmetic bottle"],
    "laptop": ["laptop"],
    "flower bouquet": ["flower bouquet"],
    "handbag": ["handbag"],
    "shopping bag": ["shopping bag"],
    "camera": ["camera"],
    "suitcase": ["suitcase"],
    "headphones": ["headphones"],
    "tableware": ["tableware"],
}

_PROP_ALLOWED_LOCATIONS = {
    "plants": None,
    "book / magazine": {"cozy living room", "modern apartment", "bedroom", "cafe", "park"},
    "cup / drink": {"cozy living room", "modern apartment", "bedroom", "hotel room", "cafe", "bar / lounge", "poolside"},
    "smartphone": None,
    "lamp": {"cozy living room", "modern apartment", "bedroom", "hotel room", "cafe", "private studio"},
    "mirror": {"bedroom", "bathroom", "hotel room", "private studio", "modern apartment"},
    "umbrella": {"city street", "alley", "park", "rooftop"},
    "studio lighting": {"studio backdrop", "private studio"},
    "luxury interior details": {"cozy living room", "modern apartment", "bedroom", "hotel room", "bar / lounge", "private studio"},
    "cosmetic product": {"studio backdrop", "private studio", "bathroom", "bedroom", "hotel room"},
    "laptop": {"office", "library", "bookstore", "cafe", "modern apartment", "cozy living room", "hotel room"},
    "flower bouquet": {"garden", "park", "city street", "cafe", "studio backdrop", "private studio", "bedroom", "hotel room"},
    "handbag": None,
    "shopping bag": {"shopping street", "city street", "cafe", "modern apartment", "hotel room"},
    "camera": {"city street", "park", "garden", "beach", "studio backdrop", "private studio", "art gallery"},
    "suitcase": {"hotel room", "train station", "subway platform", "city street"},
    "headphones": {"city street", "subway platform", "train station", "office", "bedroom", "modern apartment"},
    "tableware": {"restaurant", "cafe", "kitchen", "cozy living room", "modern apartment"},
}

_TIME_PHRASES = {
    "dawn": "at dawn",
    "morning": "in the morning",
    "daytime": "during the day",
    "afternoon": "in the afternoon",
    "evening": "in the evening",
    "night": "at night",
}

_WEATHER_PHRASES = {
    "clear": "with clear weather",
    "cloudy": "under a cloudy sky",
    "rainy": "in a rainy atmosphere",
    "snowy": "with falling snow",
    "foggy": "in soft fog",
    "indoor lighting only": "with indoor lighting",
    "soft indoor lighting": "with soft indoor lighting",
}

_ADULT_WARDROBE_SCENE = {
    "nude": ("nude", "nude", 1.20, "high"),
    "topless": ("topless", "topless", 1.18, "high"),
    "lingerie": ("in lingerie", "lingerie", 1.15, "intimate"),
    "lace lingerie set": ("in a lace lingerie set", "lace lingerie", 1.16, "intimate"),
    "bikini": ("in a bikini", "bikini", 1.12, "swimwear"),
    "one-piece swimsuit": ("in a one-piece swimsuit", "one-piece swimsuit", 1.10, "swimwear"),
    "sheer nightgown": ("in a sheer nightgown", "sheer nightgown", 1.13, "intimate"),
    "silk slip dress": ("in a silk slip dress", "silk slip dress", 1.10, "fashion"),
    "corset": ("wearing a corset", "corset", 1.10, "fashion"),
    "bodysuit": ("in a bodysuit", "bodysuit", 1.10, "fashion"),
    "latex outfit": ("in a latex outfit", "latex outfit", 1.10, "fashion"),
    "leather outfit": ("in a leather outfit", "leather outfit", 1.10, "fashion"),
    "evening dress": ("in an evening dress", "evening dress", 1.08, "fashion"),
    "tailored suit": ("in a tailored suit", "tailored suit", 1.06, "fashion"),
    "bathrobe": ("in a bathrobe", "bathrobe", 1.07, "private"),
    "sheer robe": ("in a sheer robe", "sheer robe", 1.12, "intimate"),
    "satin robe": ("in a satin robe", "satin robe", 1.08, "private"),
    "silk camisole": ("in a silk camisole", "silk camisole", 1.10, "intimate"),
    "bralette": ("in a bralette", "bralette", 1.10, "intimate"),
    "lace bodysuit": ("in a lace bodysuit", "lace bodysuit", 1.12, "intimate"),
    "sheer bodysuit": ("in a sheer bodysuit", "sheer bodysuit", 1.13, "intimate"),
    "garter belt": ("wearing a garter belt", "garter belt", 1.12, "intimate"),
    "thigh-high stockings": ("wearing thigh-high stockings", "thigh-high stockings", 1.08, "intimate"),
    "pantyhose": ("wearing pantyhose", "pantyhose", 1.06, "fashion"),
    "open shirt": ("in an open shirt", "open shirt", 1.09, "intimate"),
    "oversized shirt": ("in an oversized shirt", "oversized shirt", 1.06, "private"),
    "mini dress": ("in a mini dress", "mini dress", 1.08, "fashion"),
    "off-shoulder dress": ("in an off-shoulder dress", "off-shoulder dress", 1.08, "fashion"),
    "halter dress": ("in a halter dress", "halter dress", 1.08, "fashion"),
    "fishnet outfit": ("in a fishnet outfit", "fishnet outfit", 1.12, "intimate"),
    "vinyl outfit": ("in a glossy vinyl outfit", "vinyl outfit", 1.10, "fashion"),
    "mesh top": ("in a mesh top", "mesh top", 1.10, "intimate"),
    "lace slip": ("in a lace slip", "lace slip", 1.11, "intimate"),
    "satin lingerie": ("in satin lingerie", "satin lingerie", 1.12, "intimate"),
    "sheer blouse": ("in a sheer blouse", "sheer blouse", 1.10, "fashion"),
    "transparent robe": ("in a transparent robe", "transparent robe", 1.13, "intimate"),
    "high-slit dress": ("in a high-slit dress", "high-slit dress", 1.09, "fashion"),
    "backless dress": ("in a backless dress", "backless dress", 1.09, "fashion"),
    "deep v dress": ("in a deep V dress", "deep v dress", 1.09, "fashion"),
    "bodycon dress": ("in a bodycon dress", "bodycon dress", 1.08, "fashion"),
    "wet shirt": ("in a wet shirt", "wet shirt", 1.12, "intimate"),
    "silk pajamas": ("in silk pajamas", "silk pajamas", 1.07, "private"),
    "oversized sweater": ("in an oversized sweater", "oversized sweater", 1.06, "private"),
    "stockings and garter": ("wearing stockings and a garter", "stockings and garter", 1.12, "intimate"),
    "strappy lingerie": ("in strappy lingerie", "strappy lingerie", 1.13, "intimate"),
    "lace bralette set": ("in a lace bralette set", "lace bralette set", 1.11, "intimate"),
    "satin corset set": ("in a satin corset set", "satin corset set", 1.11, "intimate"),
    "see-through cover-up": ("in a see-through cover-up", "see-through cover-up", 1.11, "intimate"),
    "black lace lingerie": ("in black lace lingerie", "black lace lingerie", 1.13, "intimate"),
    "white button shirt": ("in a white button shirt", "white button shirt", 1.08, "private"),
    "black bodysuit": ("in a black bodysuit", "black bodysuit", 1.10, "fashion"),
    "red evening dress": ("in a red evening dress", "red evening dress", 1.09, "fashion"),
    "satin slip dress": ("in a satin slip dress", "satin slip dress", 1.10, "fashion"),
    "swimsuit cover-up": ("in a swimsuit cover-up", "swimsuit cover-up", 1.08, "swimwear"),
    "robe and lingerie": ("in a robe and lingerie", "robe and lingerie", 1.12, "intimate"),
}


_ADULT_SCENE_MOOD_PARTS = {
    "soft boudoir": ("with a soft boudoir mood", ["soft boudoir", "intimate mood"]),
    "romantic warm intimacy": ("with a warm romantic intimate mood", ["romantic intimacy", "warm intimate mood"]),
    "fashion editorial sensual": ("with a sensual fashion editorial mood", ["sensual editorial", "fashion editorial"]),
    "luxury hotel evening": ("with a polished luxury hotel evening mood", ["luxury hotel evening", "elegant intimacy"]),
    "private mirror moment": ("with a private mirror-shot mood", ["mirror shot", "private moment"]),
    "noir intimate": ("with a low-key noir intimate mood", ["noir intimacy", "low-key sensual mood"]),
    "spa calm": ("with a calm spa-like private mood", ["spa calm", "private bath mood"]),
    "poolside glamour": ("with a poolside glamour mood", ["poolside glamour", "luxury mood"]),
    "beach sunset sensual": ("with a tasteful beach sunset sensual mood", ["beach sunset", "tasteful sensual mood"]),
    "studio glamour": ("with a controlled studio glamour mood", ["studio glamour", "polished studio lighting"]),
    "cozy morning softness": ("with a soft cozy morning mood", ["cozy morning", "soft intimacy"]),
}

_ADULT_LIGHTING_PARTS = {
    "warm bedside light": ("under warm bedside lighting", ["warm bedside light"]),
    "low-key shadow": ("under low-key shadowed lighting", ["low-key lighting", "soft shadow"]),
    "soft window backlight": ("with soft window backlight", ["soft window backlight"]),
    "candlelit glow": ("under a candlelit glow", ["candlelit glow"]),
    "studio rim light": ("with controlled studio rim lighting", ["studio rim light"]),
    "neon lounge light": ("under muted neon lounge light", ["neon lounge light"]),
    "steamy bathroom light": ("in soft steamy bathroom light", ["steamy bathroom light"]),
    "sunset backlight": ("with warm sunset backlight", ["sunset backlight"]),
}

_ADULT_SCENE_PROPS_PARTS = {
    "satin sheets": (["satin sheets"], {"bedroom", "hotel room"}),
    "sheer curtains": (["sheer curtains"], {"bedroom", "hotel room", "private studio", "studio backdrop", "cozy living room", "modern apartment"}),
    "bedside lamp": (["bedside lamp"], {"bedroom", "hotel room"}),
    "large mirror": (["large mirror"], {"bedroom", "hotel room", "bathroom", "private studio", "studio backdrop"}),
    "velvet chair": (["velvet chair"], {"bedroom", "hotel room", "private studio", "studio backdrop", "bar / lounge"}),
    "silk fabric": (["silk fabric"], {"bedroom", "hotel room", "private studio", "studio backdrop"}),
    "candles": (["candles"], {"bedroom", "hotel room", "bathroom", "private studio"}),
    "bath steam": (["bath steam"], {"bathroom"}),
    "pool reflection": (["pool reflections"], {"poolside"}),
    "studio softbox": (["studio softbox"], {"private studio", "studio backdrop"}),
    "curtains and pillows": (["curtains", "pillows"], {"bedroom", "hotel room", "cozy living room", "modern apartment"}),
}

_ADULT_BODY_FOCUS_PARTS = {
    "face and expression": ("with attention to face and expression", ["face focus", "expressive face"]),
    "upper body elegance": ("with tasteful upper-body elegance", ["upper body elegance"]),
    "full body silhouette": ("with a tasteful full-body silhouette", ["full body silhouette"]),
    "legs-focused fashion framing": ("with legs-focused fashion framing", ["legs-focused fashion framing"]),
    "back and shoulder silhouette": ("with a back-and-shoulder silhouette", ["back silhouette", "shoulder silhouette"]),
    "hands and fabric detail": ("with attention to hands and fabric detail", ["hands and fabric detail"]),
    "non-graphic body line": ("with non-graphic body-line emphasis", ["non-graphic body line"]),
}

_ADULT_EXPOSURE_SCENE = {
    "clothed sensual": ("with sensual styling", "clothed sensual", "mild"),
    "revealing outfit": ("in a revealing fashion outfit", "revealing outfit", "fashion"),
    "lingerie / underwear": ("in lingerie", "lingerie", "intimate"),
    "swimwear": ("in swimwear", "swimwear", "swimwear"),
    "implied nude / covered": ("with implied nudity covered by fabric", "implied nude", "intimate"),
    "sheet-covered nude": ("covered by sheets in a nude implied style", "sheet-covered nude", "intimate"),
    "nude": ("nude", "nude", "high"),
    "topless": ("topless", "topless", "high"),
    "wet look swimwear": ("in wet-look swimwear", "wet look swimwear", "swimwear"),
    "bodycon fashion": ("in bodycon fashion styling", "bodycon fashion", "fashion"),
}

# Additional standalone-builder content expansion.
# These updates intentionally use existing generation paths: dropdown values stay
# simple canonical phrases, while the maps below keep natural-language output from
# becoming awkward when new expressions, poses, places, or props are selected.
_STANDALONE_PUBLIC_LOCATIONS.update({
    "museum", "theater stage", "hotel lobby", "corridor hallway", "elevator lobby", "convenience store", "supermarket",
    "bakery", "flower shop", "salon", "gym", "yoga studio", "airport terminal", "riverside walkway", "bridge",
    "night market", "laundromat", "parking garage",
})
_STANDALONE_OUTDOOR_LOCATIONS.update({
    "traditional Korean courtyard", "riverside walkway", "bridge", "lake shore", "mountain trail", "campsite", "night market",
})
_STANDALONE_PRIVATE_LOCATIONS.update({
    "hanok room", "dressing room", "makeup room", "photo studio", "hotel lobby", "corridor hallway", "elevator lobby",
    "convenience store", "supermarket", "bakery", "flower shop", "salon", "gym", "yoga studio", "airport terminal",
    "indoor pool", "laundromat",
})
_STANDALONE_WATER_LOCATIONS.update({"lake shore", "indoor pool"})
_STANDALONE_WINDOW_LOCATIONS.update({
    "hanok room", "greenhouse", "museum", "hotel lobby", "corridor hallway", "dressing room", "makeup room", "photo studio",
    "convenience store", "supermarket", "bakery", "flower shop", "salon", "gym", "yoga studio", "airport terminal",
    "riverside walkway", "indoor pool", "laundromat",
})

_SUBJECT_OUTFIT_PARTS.update({
    "blouse and jeans": ("wearing a blouse and jeans", "blouse, jeans"),
    "cardigan and skirt": ("wearing a cardigan and skirt", "cardigan, skirt"),
    "oversized knit sweater": ("wearing an oversized knit sweater", "oversized sweater"),
    "blazer and jeans": ("wearing a blazer and jeans", "blazer, jeans"),
    "leather jacket outfit": ("wearing a leather jacket outfit", "leather jacket"),
    "long coat outfit": ("wearing a long coat outfit", "long coat"),
    "cropped jacket outfit": ("wearing a cropped jacket outfit", "cropped jacket"),
    "pleated skirt outfit": ("wearing a pleated skirt outfit", "pleated skirt"),
    "denim shorts and blouse": ("wearing denim shorts and a blouse", "denim shorts, blouse"),
    "linen shirt and trousers": ("wearing a linen shirt and trousers", "linen shirt, trousers"),
    "floral dress": ("wearing a floral dress", "floral dress"),
    "satin blouse and skirt": ("wearing a satin blouse and skirt", "satin blouse, skirt"),
    "evening gown": ("wearing an evening gown", "evening gown"),
    "cocktail dress": ("wearing a cocktail dress", "cocktail dress"),
    "business casual outfit": ("wearing a business-casual outfit", "business casual"),
    "streetwear outfit": ("wearing a streetwear outfit", "streetwear"),
    "casual athleisure": ("wearing casual athleisure", "athleisure"),
    "yoga outfit": ("wearing a yoga outfit", "yoga outfit"),
    "raincoat outfit": ("wearing a raincoat outfit", "raincoat"),
    "apron dress": ("wearing an apron dress", "apron dress"),
    "modern hanbok": ("wearing a modern hanbok", "modern hanbok"),
    "pajamas / loungewear": ("wearing soft loungewear", "loungewear"),
})
_STANDALONE_MULTI_WARDROBE_PHRASES.update({
    "wearing a blouse and jeans": "wearing blouses and jeans",
    "wearing a cardigan and skirt": "wearing cardigans and skirts",
    "wearing an oversized knit sweater": "wearing oversized knit sweaters",
    "wearing a blazer and jeans": "wearing blazers and jeans",
    "wearing a leather jacket outfit": "wearing leather jacket outfits",
    "wearing a long coat outfit": "wearing long coat outfits",
    "wearing a cropped jacket outfit": "wearing cropped jacket outfits",
    "wearing a pleated skirt outfit": "wearing pleated skirt outfits",
    "wearing denim shorts and a blouse": "wearing denim shorts and blouses",
    "wearing a linen shirt and trousers": "wearing linen shirts and trousers",
    "wearing a floral dress": "wearing floral dresses",
    "wearing a satin blouse and skirt": "wearing satin blouses and skirts",
    "wearing an evening gown": "wearing evening gowns",
    "wearing a cocktail dress": "wearing cocktail dresses",
    "wearing a business-casual outfit": "wearing business-casual outfits",
    "wearing a streetwear outfit": "wearing streetwear outfits",
    "wearing casual athleisure": "wearing casual athleisure outfits",
    "wearing a yoga outfit": "wearing yoga outfits",
    "wearing a raincoat outfit": "wearing raincoat outfits",
    "wearing an apron dress": "wearing apron dresses",
    "wearing a modern hanbok": "wearing modern hanboks",
    "wearing soft loungewear": "wearing soft loungewear",
})

_STANDALONE_EXPRESSION_NATURAL_PHRASES = {
    "natural expression": "with a natural expression",
    "gentle smile": "with a gentle smile",
    "broad smile": "with a broad smile",
    "bright happy smile": "with a bright happy smile",
    "laughing face": "with a laughing face",
    "soft closed-mouth smile": "with a soft closed-mouth smile",
    "shy smile": "with a shy smile",
    "playful wink": "with a playful wink",
    "confident smile": "with a confident smile",
    "tearful eyes": "with tearful eyes",
    "crying face": "with a crying face",
    "pouting face": "with a pouting face",
    "embarrassed blush": "with an embarrassed blush",
    "calm blank expression": "with a calm blank expression",
}

_STANDALONE_POSE_ACTION_MAP = {
    "standing": ("standing", "standing"),
    "sitting": ("sitting", "sitting"),
    "leaning": ("leaning", "leaning"),
    "walking": ("walking", "walking"),
    "looking back": ("looking back", "looking back"),
    "reclining": ("reclining", "reclining"),
    "lying down": ("lying down", "lying down"),
    "standing with arms crossed": ("standing with arms crossed", "arms crossed"),
    "standing with hands on hips": ("standing with hands on hips", "hands on hips"),
    "standing with one hand in pocket": ("standing with one hand in a pocket", "hand in pocket"),
    "hand near face": ("posing with one hand near the face", "hand near face"),
    "hand on cheek": ("posing with one hand on the cheek", "hand on cheek"),
    "sitting cross-legged": ("sitting cross-legged", "sitting cross-legged"),
    "seated sideways": ("seated sideways", "seated sideways"),
    "crouching": ("crouching", "crouching"),
    "kneeling": ("kneeling", "kneeling"),
    "running": ("running", "running"),
    "dancing": ("dancing", "dancing"),
    "jumping lightly": ("jumping lightly", "jumping"),
    "stretching": ("stretching", "stretching"),
    "reaching upward": ("reaching upward", "reaching upward"),
    "turning sideways": ("turning sideways", "sideways pose"),
    "side profile pose": ("posed in side profile", "side profile"),
}

_STANDALONE_ACTION_EXTRA_MAP = {
    "opening curtains": ("opening the curtains", "opening curtains"),
    "cooking in kitchen": ("cooking in the kitchen", "cooking"),
    "writing in a notebook": ("writing in a notebook", "writing"),
    "sketching in a notebook": ("sketching in a notebook", "sketching"),
    "applying makeup": ("applying makeup", "makeup"),
    "brushing hair": ("brushing the hair", "brushing hair"),
    "watering plants": ("watering plants", "watering plants"),
    "arranging flowers": ("arranging flowers", "arranging flowers"),
    "browsing bookshelves": ("browsing bookshelves", "browsing books"),
    "browsing a shop display": ("browsing a shop display", "shopping"),
    "taking a photo": ("taking a photo", "camera"),
    "holding an umbrella": ("holding an umbrella", "umbrella"),
    "carrying a suitcase": ("carrying a suitcase", "suitcase"),
    "playing guitar": ("playing a guitar", "guitar"),
    "dancing": ("dancing", "dancing"),
    "jogging": ("jogging", "jogging"),
    "riding a bicycle": ("riding a bicycle", "bicycle"),
    "stretching on a mat": ("stretching on a mat", "stretching"),
    "fixing hair": ("fixing the hair", "fixing hair"),
    "adjusting glasses": ("adjusting glasses", "adjusting glasses"),
    "tying shoelaces": ("tying shoelaces", "tying shoelaces"),
    "looking down thoughtfully": ("looking down thoughtfully", "looking down"),
    "smiling at someone": ("smiling toward someone nearby", "smiling"),
    "talking with another person": ("talking with another person", "conversation"),
    "waiting under rain": ("waiting under the rain", "rain"),
    "sitting by the window": ("sitting by the window", "sitting by window"),
}

_STANDALONE_KREA2_POSE_EXTRA_MAP = {
    "standing with arms crossed": "Show a stable standing posture with arms crossed, relaxed shoulders, and clear body direction",
    "standing with hands on hips": "Show a confident standing posture with both hands on the hips and visible weight shift",
    "standing with one hand in pocket": "Show a relaxed standing posture with one hand in a pocket and the other arm naturally placed",
    "hand near face": "Show one hand near the face without covering the key facial features",
    "hand on cheek": "Show one hand resting lightly on the cheek while keeping the face readable",
    "sitting cross-legged": "Show a cross-legged seated posture with clear leg placement and balanced torso angle",
    "seated sideways": "Show the body seated sideways with face direction and torso angle clearly separated",
    "crouching": "Show a crouching posture with bent knees, balanced weight, and readable hands",
    "kneeling": "Show a kneeling posture with knee contact, torso angle, and hand placement visible",
    "running": "Show running motion with one leg leading, body momentum, and natural arm swing",
    "dancing": "Show dance movement with body rhythm, hand placement, and foot direction visible",
    "jumping lightly": "Show a small jump with lifted feet, balanced body position, and natural motion",
    "stretching": "Show a stretching pose with extended limbs and clear body line",
    "reaching upward": "Show an upward-reaching gesture with arms raised and face direction readable",
    "turning sideways": "Show the torso turning sideways while keeping the face and body direction clear",
    "side profile pose": "Show a clean side-profile pose with the face contour and body direction readable",
}

_STANDALONE_KREA2_ACTION_EXTRA_MAP = {
    "opening curtains": "Show the hands interacting with the curtains and the window light entering the room",
    "cooking in kitchen": "Show the kitchen counter, cooking gesture, hand placement, and nearby utensils",
    "writing in a notebook": "Show the notebook, pen, hand position, and gaze directed toward the page",
    "sketching in a notebook": "Show the sketchbook, drawing hand, and focused gaze toward the page",
    "applying makeup": "Show the makeup tool, mirror or hand position, and face remaining readable",
    "brushing hair": "Show the brush, hair direction, hand placement, and visible facial expression",
    "watering plants": "Show the watering gesture, plant placement, and hand-object relationship",
    "arranging flowers": "Show the flowers, hand placement, and table or vase relationship",
    "browsing bookshelves": "Show the shelf depth, hand reaching toward books, and gaze direction",
    "browsing a shop display": "Show the display shelves, carried items, and browsing gesture",
    "taking a photo": "Show the camera or phone held toward the subject or scene with clear hand placement",
    "holding an umbrella": "Show the umbrella handle, arm position, and rain or outdoor spacing when relevant",
    "carrying a suitcase": "Show the suitcase handle, arm angle, and walking or waiting posture",
    "playing guitar": "Show the guitar body, hand placement on the strings, and seated or standing balance",
    "dancing": "Show the dance pose, body rhythm, hand placement, and foot direction",
    "jogging": "Show jogging movement with natural stride, arm swing, and outdoor direction",
    "riding a bicycle": "Show bicycle contact points, seated balance, and forward direction",
    "stretching on a mat": "Show the mat, extended limbs, and body alignment clearly",
    "fixing hair": "Show the hands touching or arranging the hair while keeping the face visible",
    "adjusting glasses": "Show the fingers touching the glasses frame and the face direction clearly",
    "tying shoelaces": "Show the crouched or bent posture, shoe area, and hand placement",
    "looking down thoughtfully": "Show the downward gaze, head angle, and quiet body posture",
    "smiling at someone": "Aim the face and gaze toward someone just outside or within the scene",
    "talking with another person": "Show the conversational spacing, face directions, and relative placement between people",
    "waiting under rain": "Show the waiting posture, rainy surface, and believable shelter or umbrella relation",
    "sitting by the window": "Place the subject beside the window with clear gaze direction and room depth",
}

# Action/location and pose/action repair helpers for the expanded standalone data.
# The dropdowns intentionally allow many combinations, but the final prompt should
# not describe mutually impossible body states such as "sitting and jogging" or
# location contradictions such as "opening the curtains in a park".
_STANDALONE_KITCHEN_LIKE_LOCATIONS = {"kitchen", "restaurant", "cafe", "bakery"}
_STANDALONE_SHOP_DISPLAY_LOCATIONS = {"shopping street", "city street", "night market", "convenience store", "supermarket", "bakery", "flower shop", "bookstore", "salon", "museum"}
_STANDALONE_BOOKSHELF_LOCATIONS = {"library", "bookstore", "cozy living room", "modern apartment", "office", "bedroom", "study"}
_STANDALONE_ACTIVE_BICYCLE_LOCATIONS = {"city street", "shopping street", "park", "garden", "riverside walkway", "bridge", "lake shore", "mountain trail", "campsite"}
_STANDALONE_ACTIVE_JOGGING_LOCATIONS = _STANDALONE_ACTIVE_BICYCLE_LOCATIONS | {"gym", "yoga studio", "beach", "rooftop"}
_STANDALONE_RAIN_WAIT_LOCATIONS = _STANDALONE_OUTDOOR_LOCATIONS | {"city street", "shopping street", "alley", "park", "garden", "beach", "rooftop", "balcony", "train station", "subway platform"}

_STANDALONE_POSE_FAMILY = {
    "standing": "stand", "standing with arms crossed": "stand_locked", "standing with hands on hips": "stand_locked",
    "standing with one hand in pocket": "stand_locked", "sitting": "sit", "sitting cross-legged": "sit",
    "seated sideways": "sit", "reclining": "recline", "lying down": "recline", "crouching": "crouch",
    "kneeling": "kneel", "walking": "walk", "running": "run", "dancing": "dance", "jumping lightly": "jump",
    "stretching": "stretch", "reaching upward": "reach", "leaning": "lean", "looking back": "look",
    "hand near face": "hand", "hand on cheek": "hand", "turning sideways": "turn", "side profile pose": "profile",
}
_STANDALONE_ACTION_FAMILY = {
    "standing still": "stand", "sitting at a table": "sit", "walking naturally": "walk", "resting on a bed": "recline",
    "standing in water": "stand", "waiting at a station": "stand", "shopping on a street": "walk", "opening curtains": "hand_task",
    "cooking in kitchen": "hand_task", "writing in a notebook": "hand_task", "sketching in a notebook": "hand_task",
    "applying makeup": "hand_task", "brushing hair": "hand_task", "watering plants": "hand_task", "arranging flowers": "hand_task",
    "browsing bookshelves": "hand_task", "browsing a shop display": "walk", "taking a photo": "hand_task",
    "holding an umbrella": "hand_task", "carrying a suitcase": "walk", "playing guitar": "hand_task", "dancing": "dance",
    "jogging": "run", "riding a bicycle": "ride", "stretching on a mat": "stretch", "fixing hair": "hand_task",
    "adjusting glasses": "hand_task", "tying shoelaces": "crouch", "looking down thoughtfully": "look", "smiling at someone": "look",
    "talking with another person": "talk", "waiting under rain": "stand", "sitting by the window": "sit",
}
_STANDALONE_LOCATION_REPAIR_DETAILS = {
    "opening curtains": "Show a calm pose near the available light source, with believable hand placement",
    "cooking in kitchen": "Show a simple food or drink-related gesture that fits the selected location",
    "browsing bookshelves": "Show the book or display interaction in a way that fits the selected location",
    "browsing a shop display": "Show a natural looking-around gesture and nearby environmental details",
    "holding an umbrella": "Show relaxed hand placement without forcing an impossible indoor umbrella scene",
    "riding a bicycle": "Show the bicycle as a nearby prop with the subject placed beside it",
    "jogging": "Show natural walking movement that fits the selected location",
    "waiting under rain": "Show a quiet waiting posture appropriate to the selected location",
    "sitting by the window": "Show a seated posture that fits the selected location",
}


def _standalone_repair_action_for_location(act: str, nat: str, tag: str, loc: str) -> Tuple[str, str, bool]:
    """Return a location-safe action phrase, preserving intent when possible."""
    if act == "opening curtains" and loc not in _STANDALONE_WINDOW_LOCATIONS:
        return "standing near the available light", "standing near light", True
    if act == "cooking in kitchen" and loc not in _STANDALONE_KITCHEN_LIKE_LOCATIONS:
        return "holding a cup" if loc in _STANDALONE_PRIVATE_LOCATIONS else "standing naturally", "cup" if loc in _STANDALONE_PRIVATE_LOCATIONS else "standing", True
    if act == "browsing bookshelves" and loc not in _STANDALONE_BOOKSHELF_LOCATIONS:
        return "reading a book", "reading", True
    if act == "browsing a shop display" and loc not in _STANDALONE_SHOP_DISPLAY_LOCATIONS:
        return "looking around naturally", "looking around", True
    if act == "holding an umbrella" and loc in _STANDALONE_PRIVATE_LOCATIONS:
        return "standing naturally", "standing", True
    if act == "riding a bicycle" and loc not in _STANDALONE_ACTIVE_BICYCLE_LOCATIONS:
        return "standing beside a bicycle", "bicycle", True
    if act == "jogging" and loc not in _STANDALONE_ACTIVE_JOGGING_LOCATIONS:
        return "walking naturally", "walking", True
    if act == "waiting under rain" and loc not in _STANDALONE_RAIN_WAIT_LOCATIONS:
        return "waiting quietly", "waiting", True
    if act == "sitting by the window" and loc not in _STANDALONE_WINDOW_LOCATIONS:
        return "sitting naturally", "sitting", True
    return nat, tag, False

def _standalone_pose_conflicts_with_action(pose: str, action: str, action_nat: str) -> bool:
    pf = _STANDALONE_POSE_FAMILY.get(pose)
    af = _STANDALONE_ACTION_FAMILY.get(action)
    if not pf or not af:
        return False
    if pf == af:
        return False
    # Eye/head/hand pose cues can combine with most actions unless the action
    # already occupies the same hands/body in an incompatible way.
    if pf in {"look", "turn", "profile", "lean", "reach", "hand"} and af not in {"run", "ride", "jump", "crouch"}:
        return False
    if pf == "stand_locked" and af in {"look", "talk"}:
        return False
    if pf in {"stand", "walk"} and af in {"hand_task", "talk", "look"}:
        return False
    if pf in {"sit"} and af in {"hand_task", "talk", "look"}:
        return False
    if pf in {"crouch", "kneel"} and af in {"hand_task", "look"}:
        return False
    if pf in {"stretch"} and af in {"look", "talk"}:
        return False
    return True

def _standalone_krea2_repaired_action_detail(action: str, loc: str) -> str:
    act = _safe_ui_value(action, "subject_action")
    loc = _safe_ui_value(loc, "location_type")
    if act == "opening curtains" and loc not in _STANDALONE_WINDOW_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "cooking in kitchen" and loc not in _STANDALONE_KITCHEN_LIKE_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "browsing bookshelves" and loc not in _STANDALONE_BOOKSHELF_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "browsing a shop display" and loc not in _STANDALONE_SHOP_DISPLAY_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "holding an umbrella" and loc in _STANDALONE_PRIVATE_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "riding a bicycle" and loc not in _STANDALONE_ACTIVE_BICYCLE_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "jogging" and loc not in _STANDALONE_ACTIVE_JOGGING_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "waiting under rain" and loc not in _STANDALONE_RAIN_WAIT_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    if act == "sitting by the window" and loc not in _STANDALONE_WINDOW_LOCATIONS:
        return _STANDALONE_LOCATION_REPAIR_DETAILS[act]
    return ""

_LOCATION_PHRASES.update({
    "hanok room": "inside a traditional Korean hanok room",
    "traditional Korean courtyard": "in a traditional Korean courtyard",
    "greenhouse": "inside a greenhouse",
    "museum": "inside a museum",
    "theater stage": "on a theater stage",
    "dressing room": "inside a dressing room",
    "makeup room": "inside a makeup room",
    "photo studio": "inside a photo studio",
    "hotel lobby": "inside a hotel lobby",
    "corridor hallway": "in a corridor hallway",
    "elevator lobby": "inside an elevator lobby",
    "convenience store": "inside a convenience store",
    "supermarket": "inside a supermarket",
    "bakery": "inside a bakery",
    "flower shop": "inside a flower shop",
    "salon": "inside a salon",
    "gym": "inside a gym",
    "yoga studio": "inside a yoga studio",
    "airport terminal": "inside an airport terminal",
    "riverside walkway": "on a riverside walkway",
    "bridge": "on a bridge",
    "lake shore": "by a lake shore",
    "mountain trail": "on a mountain trail",
    "campsite": "at a campsite",
    "parking garage": "inside a parking garage",
    "night market": "in a night market",
    "indoor pool": "beside an indoor pool",
    "laundromat": "inside a laundromat",
})
_LOCATION_TAGS.update({
    "hanok room": ["hanok room", "traditional korean interior", "indoor"],
    "traditional Korean courtyard": ["traditional korean courtyard", "outdoors"],
    "greenhouse": ["greenhouse", "indoor plants", "indoor"],
    "museum": ["museum", "indoor"],
    "theater stage": ["theater stage", "stage"],
    "dressing room": ["dressing room", "indoor"],
    "makeup room": ["makeup room", "indoor"],
    "photo studio": ["photo studio", "studio lighting", "indoor"],
    "hotel lobby": ["hotel lobby", "indoor"],
    "corridor hallway": ["corridor", "hallway", "indoor"],
    "elevator lobby": ["elevator lobby", "indoor"],
    "convenience store": ["convenience store", "indoor"],
    "supermarket": ["supermarket", "indoor"],
    "bakery": ["bakery", "indoor"],
    "flower shop": ["flower shop", "indoor"],
    "salon": ["salon", "indoor"],
    "gym": ["gym", "indoor"],
    "yoga studio": ["yoga studio", "indoor"],
    "airport terminal": ["airport terminal", "indoor"],
    "riverside walkway": ["riverside walkway", "outdoors"],
    "bridge": ["bridge", "outdoors"],
    "lake shore": ["lake shore", "outdoors"],
    "mountain trail": ["mountain trail", "outdoors"],
    "campsite": ["campsite", "outdoors"],
    "parking garage": ["parking garage", "indoor"],
    "night market": ["night market", "outdoors"],
    "indoor pool": ["indoor pool", "indoor"],
    "laundromat": ["laundromat", "indoor"],
})
_LOCATION_DETAIL_PHRASES.update({
    "cozy warm": "with a cozy, warm atmosphere",
    "cinematic": "with a cinematic atmosphere",
    "soft romantic": "with a soft romantic atmosphere",
    "moody low-key": "with a moody low-key atmosphere",
    "rainy urban": "with a rainy urban atmosphere",
    "rustic worn": "with a rustic, worn-in atmosphere",
    "cluttered lived-in": "with a lived-in, gently cluttered atmosphere",
    "clean minimal": "with a clean minimal atmosphere",
    "premium hotel": "with a polished premium-hotel atmosphere",
    "traditional Korean": "with a traditional Korean atmosphere",
    "industrial": "with an industrial atmosphere",
    "futuristic neon": "with a futuristic neon atmosphere",
    "soft pastel": "with a soft pastel atmosphere",
    "high-contrast dramatic": "with a high-contrast dramatic atmosphere",
})
_LOCATION_DETAIL_TAGS.update({
    "cozy warm": ["cozy", "warm atmosphere"],
    "cinematic": ["cinematic atmosphere"],
    "soft romantic": ["soft romantic atmosphere"],
    "moody low-key": ["low-key atmosphere", "moody"],
    "rainy urban": ["rainy urban atmosphere"],
    "rustic worn": ["rustic", "worn texture"],
    "cluttered lived-in": ["lived-in", "cluttered interior"],
    "clean minimal": ["clean minimal"],
    "premium hotel": ["premium hotel atmosphere"],
    "traditional Korean": ["traditional korean atmosphere"],
    "industrial": ["industrial atmosphere"],
    "futuristic neon": ["futuristic neon atmosphere"],
    "soft pastel": ["soft pastel atmosphere"],
    "high-contrast dramatic": ["high contrast", "dramatic atmosphere"],
})
_TIME_PHRASES.update({
    "late afternoon": "in the late afternoon",
    "sunset": "at sunset",
    "late night": "late at night",
})
_WEATHER_PHRASES.update({
    "golden hour sunlight": "in golden-hour sunlight",
    "sunset backlight": "with warm sunset backlight",
    "moonlight": "under moonlight",
    "neon lights": "under neon lights",
    "window light": "with soft window light",
    "strong sunlight": "under strong sunlight",
    "overcast soft light": "under soft overcast light",
    "backlit silhouette": "with backlit silhouette lighting",
    "low-key lighting": "with low-key lighting",
    "rim light": "with rim lighting",
    "candlelight": "under candlelight",
    "fluorescent indoor light": "under fluorescent indoor light",
    "streetlights": "under streetlights",
    "rainy neon reflections": "with rainy neon reflections",
})
_AUTO_PROPS_BY_LOCATION.update({
    "hanok room": ["wooden floor", "paper window panels", "low table", "woven mat", "soft fabric"],
    "traditional Korean courtyard": ["stone path", "wooden eaves", "potted plants", "courtyard wall"],
    "greenhouse": ["glass panels", "potted plants", "hanging greenery", "wet leaves"],
    "museum": ["display cases", "gallery labels", "soft museum lighting"],
    "theater stage": ["stage curtains", "spotlights", "wooden stage floor"],
    "dressing room": ["vanity mirror", "clothing rack", "makeup table"],
    "makeup room": ["vanity lights", "makeup tools", "mirror"],
    "photo studio": ["softbox lights", "backdrop stand", "studio floor"],
    "hotel lobby": ["lounge chairs", "marble floor", "warm lobby lights"],
    "corridor hallway": ["long hallway depth", "wall lights", "floor reflections"],
    "elevator lobby": ["elevator doors", "wall panels", "soft ceiling lights"],
    "convenience store": ["shelves", "cooler lights", "product displays"],
    "supermarket": ["aisles", "shopping cart", "display shelves"],
    "bakery": ["bread displays", "warm lights", "wooden shelves"],
    "flower shop": ["flower buckets", "green leaves", "display shelves"],
    "salon": ["salon chair", "mirror", "hair tools"],
    "gym": ["exercise equipment", "mirrors", "floor mats"],
    "yoga studio": ["yoga mats", "wood floor", "soft window light"],
    "airport terminal": ["large windows", "signage", "suitcase"],
    "riverside walkway": ["river railing", "water reflections", "walking path"],
    "bridge": ["bridge railing", "city view", "open air depth"],
    "lake shore": ["lake water", "shoreline", "distant trees"],
    "mountain trail": ["trail path", "rocks", "trees", "distant slope"],
    "campsite": ["tent", "camp chair", "soft lantern"],
    "parking garage": ["concrete pillars", "painted lines", "overhead lights"],
    "night market": ["vendor stalls", "sign lights", "crowd-free walkway"],
    "indoor pool": ["pool water", "tile reflections", "soft ceiling lights"],
    "laundromat": ["washing machines", "folding table", "fluorescent lights"],
})
_AUTO_SCENE_QUALITY_BY_LOCATION.update({
    "hanok room": ["coherent traditional room layout", "wood-and-paper interior texture", "soft background depth"],
    "traditional Korean courtyard": ["clear courtyard depth", "traditional architectural texture", "balanced open-air atmosphere"],
    "greenhouse": ["layered plant depth", "glasshouse texture", "soft humid atmosphere"],
    "museum": ["clean exhibit spacing", "subtle display texture", "balanced interior depth"],
    "theater stage": ["clear stage layout", "curtain and floor texture", "controlled theatrical depth"],
    "dressing room": ["coherent vanity layout", "soft fabric and mirror texture", "balanced backstage depth"],
    "makeup room": ["clean vanity layout", "mirror-light texture", "balanced close interior depth"],
    "photo studio": ["clean studio layout", "controlled equipment spacing", "balanced foreground-background depth"],
    "hotel lobby": ["clear lobby layout", "polished interior texture", "soft premium depth"],
    "corridor hallway": ["strong hallway perspective", "subtle wall texture", "deep linear background"],
    "elevator lobby": ["clean lobby geometry", "panel texture", "balanced indoor depth"],
    "convenience store": ["clear aisle layout", "shelf texture", "balanced fluorescent depth"],
    "supermarket": ["clear aisle perspective", "display shelf texture", "balanced interior depth"],
    "bakery": ["warm display layout", "bread and wood texture", "soft shop depth"],
    "flower shop": ["layered flower-display depth", "leaf and petal texture", "soft shop atmosphere"],
    "salon": ["clean salon layout", "mirror and chair texture", "balanced indoor depth"],
    "gym": ["clear equipment layout", "mat and mirror texture", "balanced workout-space depth"],
    "yoga studio": ["clean floor layout", "mat and wood texture", "calm studio depth"],
    "airport terminal": ["clear terminal perspective", "signage and glass texture", "open interior depth"],
    "riverside walkway": ["clear walkway perspective", "water-reflection texture", "open-air background depth"],
    "bridge": ["clear bridge perspective", "railing texture", "open city or landscape depth"],
    "lake shore": ["clear shoreline depth", "water and foliage texture", "soft open-air atmosphere"],
    "mountain trail": ["clear trail perspective", "rock and forest texture", "natural depth"],
    "campsite": ["clear campsite layout", "fabric and outdoor texture", "soft night or outdoor depth"],
    "parking garage": ["clear concrete perspective", "subtle reflective floor texture", "moody indoor depth"],
    "night market": ["clear stall layout", "sign and fabric texture", "lively night depth"],
    "indoor pool": ["clear poolside layout", "tile and reflection texture", "soft humid depth"],
    "laundromat": ["clear machine-row layout", "metal and tile texture", "balanced fluorescent depth"],
})
_PROP_PHRASES.update({
    "window": ["window", "window light"],
    "curtains": ["curtains"],
    "sofa": ["sofa"],
    "chair": ["chair"],
    "desk": ["desk"],
    "bed": ["bed"],
    "bookshelf": ["bookshelf"],
    "picture frames": ["picture frames"],
    "potted plants": ["potted plants"],
    "vase": ["vase"],
    "flowers": ["flowers"],
    "notebook and pen": ["notebook", "pen"],
    "art supplies": ["art supplies"],
    "makeup tools": ["makeup tools"],
    "perfume bottle": ["perfume bottle"],
    "blanket / fabric": ["blanket", "soft fabric"],
    "pillows": ["pillows"],
    "street signs": ["street signs"],
    "neon signs": ["neon signs"],
    "bench": ["bench"],
    "bicycle": ["bicycle"],
    "food / dessert": ["food", "dessert"],
    "display shelves": ["display shelves"],
    "shopping cart": ["shopping cart"],
    "luggage": ["luggage"],
    "train doors": ["train doors"],
    "guitar": ["guitar"],
    "microphone": ["microphone"],
})
_PROP_ALLOWED_LOCATIONS.update({
    "window": None,
    "curtains": {"cozy living room", "modern apartment", "bedroom", "hotel room", "private studio", "hanok room", "dressing room", "makeup room"},
    "sofa": {"cozy living room", "modern apartment", "hotel room", "hotel lobby", "bar / lounge", "private studio"},
    "chair": None,
    "desk": {"office", "library", "bookstore", "bedroom", "modern apartment", "photo studio", "makeup room"},
    "bed": {"bedroom", "hotel room"},
    "bookshelf": {"cozy living room", "modern apartment", "library", "bookstore", "office"},
    "picture frames": None,
    "potted plants": None,
    "vase": None,
    "flowers": {"flower shop", "garden", "park", "cafe", "bedroom", "hotel room", "private studio", "studio backdrop"},
    "notebook and pen": None,
    "art supplies": {"art gallery", "private studio", "photo studio", "cozy living room", "modern apartment"},
    "makeup tools": {"makeup room", "dressing room", "bathroom", "bedroom", "hotel room", "photo studio"},
    "perfume bottle": {"makeup room", "dressing room", "bathroom", "bedroom", "hotel room", "photo studio"},
    "blanket / fabric": {"bedroom", "hotel room", "cozy living room", "modern apartment", "private studio", "studio backdrop"},
    "pillows": {"bedroom", "hotel room", "cozy living room", "modern apartment"},
    "street signs": {"city street", "shopping street", "alley", "night market", "riverside walkway"},
    "neon signs": {"city street", "shopping street", "alley", "bar / lounge", "night market"},
    "bench": {"park", "garden", "riverside walkway", "museum", "airport terminal"},
    "bicycle": {"city street", "park", "riverside walkway", "bridge", "mountain trail"},
    "food / dessert": {"cafe", "restaurant", "kitchen", "bakery", "cozy living room", "modern apartment"},
    "display shelves": {"bookstore", "convenience store", "supermarket", "bakery", "flower shop", "museum"},
    "shopping cart": {"supermarket", "convenience store"},
    "luggage": {"hotel room", "hotel lobby", "airport terminal", "train station", "subway platform", "city street"},
    "train doors": {"train station", "subway platform"},
    "guitar": {"bedroom", "cozy living room", "modern apartment", "private studio", "studio backdrop", "theater stage"},
    "microphone": {"private studio", "studio backdrop", "photo studio", "theater stage", "bar / lounge"},
})

_ADULT_SCENE_MOOD_PARTS.update({
    "after-bath softness": ("with soft after-bath privacy", ["after-bath mood", "soft private mood"]),
    "midnight hotel intimacy": ("with a midnight hotel-room intimate mood", ["midnight hotel mood", "intimate mood"]),
    "soft lingerie editorial": ("with a soft lingerie editorial mood", ["lingerie editorial", "soft sensual mood"]),
    "warm sheet-covered mood": ("with a warm sheet-covered private mood", ["sheet-covered mood", "warm private mood"]),
    "fine-art nude calm": ("with a calm fine-art nude mood", ["fine-art nude mood", "calm intimate mood"]),
    "private dressing-room mood": ("with a private dressing-room mood", ["dressing room mood", "private moment"]),
    "mirror-lit sensuality": ("with mirror-lit restrained sensuality", ["mirror-lit mood", "restrained sensuality"]),
    "rainy-window intimacy": ("with rainy-window private intimacy", ["rainy window mood", "private intimacy"]),
    "candlelit romantic privacy": ("with candlelit romantic privacy", ["candlelit romance", "private mood"]),
    "glossy fashion sensuality": ("with glossy fashion sensuality", ["glossy sensual fashion", "editorial sensuality"]),
    "quiet teasing mood": ("with a quiet teasing mood", ["teasing mood", "quiet sensuality"]),
})
_ADULT_POSE_EXTRA_MAP = {
    "seated on floor": ("seated on the floor", "seated on floor"),
    "kneeling portrait pose": ("kneeling in a portrait pose", "kneeling"),
    "sitting by window": ("sitting by a window", "sitting by window"),
    "lying on stomach": ("lying on the stomach", "lying on stomach"),
    "stretching on bed": ("stretching on a bed", "stretching on bed"),
    "hands in hair": ("posing with hands in the hair", "hands in hair"),
    "covering with sheet": ("covered by a sheet", "covered by sheet"),
    "holding robe closed": ("holding a robe closed", "holding robe"),
    "side-profile silhouette": ("posed in a side-profile silhouette", "side profile silhouette"),
    "seated mirror pose": ("seated near a mirror", "seated mirror pose"),
    "one leg bent pose": ("posed with one leg bent", "one leg bent"),
    "soft arched pose": ("in a soft arched pose", "arched pose"),
    "hands near collarbone": ("posing with hands near the collarbone", "hands near collarbone"),
    "looking down softly": ("looking down softly", "looking down"),
    "turning away with glance": ("turning away while glancing back", "glancing back"),
}
_ADULT_LIGHTING_PARTS.update({
    "warm window glow": ("with warm window glow", ["warm window glow"]),
    "moonlit room": ("in soft moonlit room light", ["moonlit room"]),
    "rainy window light": ("with rainy window light", ["rainy window light"]),
    "bathroom mirror light": ("under bathroom mirror light", ["bathroom mirror light"]),
    "soft vanity lights": ("under soft vanity lights", ["soft vanity lights"]),
    "hotel lamp glow": ("under a warm hotel lamp glow", ["hotel lamp glow"]),
    "silhouette backlight": ("with tasteful silhouette backlight", ["silhouette backlight"]),
    "high-key studio glamour": ("under high-key studio glamour lighting", ["high-key studio light"]),
    "softbox glow": ("under a softbox glow", ["softbox glow"]),
    "colored gel rim light": ("with colored gel rim lighting", ["colored rim light"]),
})
_ADULT_SCENE_PROPS_PARTS.update({
    "robe": (["robe"], {"bedroom", "hotel room", "bathroom", "private studio", "studio backdrop", "makeup room", "dressing room"}),
    "towel": (["towel"], {"bathroom", "bedroom", "hotel room", "indoor pool", "poolside"}),
    "vanity table": (["vanity table"], {"bedroom", "hotel room", "makeup room", "dressing room", "private studio"}),
    "makeup mirror": (["makeup mirror"], {"bedroom", "hotel room", "bathroom", "makeup room", "dressing room", "private studio"}),
    "perfume bottle": (["perfume bottle"], {"bedroom", "hotel room", "bathroom", "makeup room", "dressing room", "private studio"}),
    "glass shower": (["glass shower"], {"bathroom"}),
    "bathtub edge": (["bathtub edge"], {"bathroom"}),
    "lace curtains": (["lace curtains"], {"bedroom", "hotel room", "private studio", "studio backdrop", "cozy living room", "modern apartment"}),
    "soft rug": (["soft rug"], {"bedroom", "hotel room", "private studio", "studio backdrop", "cozy living room", "modern apartment"}),
    "dressing screen": (["dressing screen"], {"bedroom", "hotel room", "makeup room", "dressing room", "private studio", "studio backdrop"}),
    "window curtains": (["window curtains"], {"bedroom", "hotel room", "cozy living room", "modern apartment", "private studio", "makeup room", "dressing room"}),
    "silk pillow": (["silk pillow"], {"bedroom", "hotel room", "private studio"}),
    "jewelry tray": (["jewelry tray"], {"bedroom", "hotel room", "makeup room", "dressing room", "private studio"}),
    "floor cushion": (["floor cushion"], {"bedroom", "hotel room", "private studio", "studio backdrop", "hanok room"}),
})
_ADULT_BODY_FOCUS_PARTS.update({
    "face with hands": ("with attention to the face and hands", ["face and hands"],),
    "neckline and shoulders": ("with tasteful neckline-and-shoulder framing", ["neckline and shoulders"]),
    "waist silhouette": ("with a tasteful waist silhouette", ["waist silhouette"]),
    "fabric-covered form": ("with fabric-covered form emphasis", ["fabric-covered form"]),
    "profile body line": ("with profile body-line emphasis", ["profile body line"]),
    "hair and shoulder line": ("with attention to hair and shoulder line", ["hair and shoulder line"]),
    "mirror reflection focus": ("with mirror reflection focus", ["mirror reflection focus"]),
})


# Broader semantic safety helpers for the expanded standalone menu.  These are
# deliberately applied late, after all location/prop expansion maps are loaded,
# so newly added menu entries are covered without needing every older rule to be
# manually duplicated.
_STANDALONE_INDOOR_LOCATIONS = {
    loc for loc, tags in _LOCATION_TAGS.items()
    if any("indoor" in str(tag).lower() or "studio" in str(tag).lower() for tag in tags)
}
_STANDALONE_INDOOR_LOCATIONS.update({
    loc for loc, phrase in _LOCATION_PHRASES.items()
    if str(phrase).startswith("inside") or "against a studio backdrop" in str(phrase)
})
_STANDALONE_INDOOR_LOCATIONS.update({"theater stage", "indoor pool"})
_STANDALONE_WINDOW_OR_GLASS_LOCATIONS = set(_STANDALONE_WINDOW_LOCATIONS) | {
    "greenhouse", "city street", "shopping street", "night market", "alley", "hotel lobby", "airport terminal"
}
_STANDALONE_SHOP_INTERIOR_LOCATIONS = {"convenience store", "supermarket", "bakery", "flower shop", "bookstore", "night market"}
_STANDALONE_SEATING_LOCATIONS = _STANDALONE_INDOOR_LOCATIONS | {"park", "garden", "beach", "poolside", "balcony", "rooftop", "campsite", "riverside walkway", "lake shore"}
_STANDALONE_DECOR_INTERIOR_LOCATIONS = _STANDALONE_INDOOR_LOCATIONS | {"balcony", "rooftop", "traditional Korean courtyard", "garden"}
_STANDALONE_TABLE_SURFACE_LOCATIONS = _STANDALONE_INDOOR_LOCATIONS | {"cafe", "restaurant", "bookstore", "library", "balcony", "rooftop", "campsite", "poolside"}

# Tighten only the props whose literal object commonly becomes absurd when the
# menu is expanded.  Free handheld props such as smartphone/handbag remain global.
_PROP_ALLOWED_LOCATIONS.update({
    "window": _STANDALONE_WINDOW_OR_GLASS_LOCATIONS,
    "picture frames": _STANDALONE_DECOR_INTERIOR_LOCATIONS | {"art gallery", "museum"},
    "vase": _STANDALONE_DECOR_INTERIOR_LOCATIONS | {"flower shop", "garden", "traditional Korean courtyard"},
    "chair": _STANDALONE_SEATING_LOCATIONS,
    "potted plants": _STANDALONE_DECOR_INTERIOR_LOCATIONS | {"greenhouse", "flower shop", "cafe", "restaurant"},
    "desk": _STANDALONE_TABLE_SURFACE_LOCATIONS | {"office", "makeup room", "dressing room", "photo studio"},
    "bed": {"bedroom", "hotel room"},
    "bookshelf": {"cozy living room", "modern apartment", "library", "bookstore", "office", "bedroom", "hanok room"},
    "shopping cart": {"supermarket", "convenience store"},
    "display shelves": _STANDALONE_SHOP_INTERIOR_LOCATIONS | {"museum", "salon"},
    "train doors": {"train station", "subway platform"},
    "microphone": {"private studio", "studio backdrop", "photo studio", "theater stage", "bar / lounge"},
    "studio lighting": {"studio backdrop", "private studio", "photo studio", "theater stage"},
    "luxury interior details": _STANDALONE_INDOOR_LOCATIONS | {"bar / lounge"},
    "laptop": {"office", "library", "bookstore", "cafe", "modern apartment", "cozy living room", "hotel room", "airport terminal"},
    "tableware": {"restaurant", "cafe", "kitchen", "cozy living room", "modern apartment", "bakery"},
    "makeup tools": {"makeup room", "dressing room", "bathroom", "bedroom", "hotel room", "photo studio", "salon"},
    "perfume bottle": {"makeup room", "dressing room", "bathroom", "bedroom", "hotel room", "photo studio", "salon"},
    "sofa": {"cozy living room", "modern apartment", "hotel room", "hotel lobby", "bar / lounge", "private studio", "photo studio"},
})

_PROP_LOCATION_SAFE_FALLBACKS = {
    "window": {
        "forest": ["filtered light through trees"],
        "park": ["open-air light"],
        "garden": ["open-air light"],
        "beach": ["bright open-air light"],
        "mountain trail": ["filtered mountain light"],
        "bridge": ["open-air light"],
        "riverside walkway": ["water reflections"],
        "lake shore": ["water reflections"],
    },
    "curtains": {"default": []},
    "sofa": {"default": []},
    "desk": {"campsite": ["camp table"], "poolside": ["small side table"], "default": []},
    "bed": {"beach": ["beach blanket"], "campsite": ["camp blanket"], "forest": ["picnic blanket"], "park": ["picnic blanket"], "garden": ["picnic blanket"], "default": []},
    "bookshelf": {"convenience store": ["display shelves"], "supermarket": ["display shelves"], "bakery": ["display shelves"], "flower shop": ["display shelves"], "default": []},
    "picture frames": {"museum": ["framed artwork"], "art gallery": ["framed artwork"], "default": []},
    "vase": {"park": ["flowers"], "garden": ["flowers"], "forest": ["natural foliage"], "default": []},
    "shopping cart": {"default": []},
    "train doors": {"default": []},
    "microphone": {"default": []},
    "studio lighting": {"default": []},
}

def _standalone_prop_fallback_for_location(prop: str, loc: str) -> List[str]:
    mapping = _PROP_LOCATION_SAFE_FALLBACKS.get(prop, {})
    if loc in mapping:
        return list(mapping[loc])
    if "default" in mapping:
        return list(mapping["default"])
    return []

def _standalone_indoor_weather_phrase(weather: str, loc: str) -> str:
    has_window = loc in _STANDALONE_WINDOW_OR_GLASS_LOCATIONS
    if loc == "theater stage":
        return {
            "rainy": "with theatrical rain-like lighting",
            "snowy": "with cool theatrical stage atmosphere",
            "foggy": "with soft theatrical haze",
            "streetlights": "with streetlight-like stage lighting",
            "rainy neon reflections": "with neon stage reflections",
        }.get(weather, "")
    if weather == "clear":
        return "with soft window light" if has_window else "with clean ambient indoor light"
    if weather == "cloudy":
        return "with soft diffused indoor light"
    if weather == "rainy":
        return "with rainy-day window light" if has_window else "with muted rainy-day indoor light"
    if weather == "snowy":
        return "with cool diffused window light" if has_window else "with cool diffused indoor light"
    if weather == "foggy":
        return "with soft diffused haze"
    if weather == "streetlights":
        return "with streetlight glow through the windows" if has_window else "with warm night ambient light"
    if weather == "rainy neon reflections":
        return "with rainy neon reflections on the windows" if has_window else "with soft neon reflections"
    if weather == "moonlight":
        return "with moonlight through the window" if has_window else "with cool moonlit ambient light"
    return ""

_PUBLIC_SAFE_ADULT_REPLACEMENT = ("", "", "")


def _standalone_is_adult_active(adult_tone: str, adult_wardrobe: str, adult_exposure_level: str) -> bool:
    tone = _safe_ui_value(adult_tone, "adult_tone")
    wardrobe = _safe_ui_value(adult_wardrobe, "adult_wardrobe")
    exposure = _safe_ui_value(adult_exposure_level, "adult_exposure_level")
    return tone in {"romantic non-explicit", "suggestive", "sensual", "bold sensual", "nsfw", "explicit nsfw"} or wardrobe != "auto" or exposure != "auto"


def _standalone_extra_adult_active(*values: Any) -> bool:
    for value in values:
        try:
            text = _clean_text(value)
        except Exception:
            text = ""
        if text and text not in {"auto", "essential", "professional"}:
            return True
    return False

def _standalone_adult_context_active(
    adult_tone: str,
    adult_wardrobe: str,
    adult_exposure_level: str,
    adult_pose_style: str = "auto",
    adult_scene_mood: str = "auto",
    adult_lighting: str = "auto",
    adult_scene_props: str = "auto",
    adult_body_focus: str = "auto",
) -> bool:
    # Professional-only adult pose choices are explicit scene signals too.
    # Without this, adult_pose_style could only work after another adult field
    # had already activated the adult context.
    return (
        _standalone_is_adult_active(adult_tone, adult_wardrobe, adult_exposure_level)
        or _safe_ui_value(adult_pose_style, "adult_pose_style") != "auto"
        or _standalone_extra_adult_active(
            adult_scene_mood,
            adult_lighting,
            adult_scene_props,
            adult_body_focus,
        )
    )

def _standalone_is_explicit_adult(adult_tone: str, adult_wardrobe: str, adult_exposure_level: str) -> bool:
    tone = _safe_ui_value(adult_tone, "adult_tone")
    wardrobe = _safe_ui_value(adult_wardrobe, "adult_wardrobe")
    exposure = _safe_ui_value(adult_exposure_level, "adult_exposure_level")
    if tone in {"nsfw", "explicit nsfw"}:
        return True
    if wardrobe in {"nude", "topless", "lingerie", "lace lingerie set", "black lace lingerie", "satin lingerie", "strappy lingerie", "lace bralette set", "robe and lingerie", "sheer nightgown", "sheer robe", "transparent robe", "sheer bodysuit", "garter belt", "stockings and garter", "fishnet outfit", "wet shirt"}:
        return True
    if exposure in {"lingerie / underwear", "implied nude / covered", "sheet-covered nude", "nude", "topless"}:
        return True
    return False

def _standalone_kind(subject_profile: str) -> str:
    profile = _safe_ui_value(subject_profile, "subject_profile")
    if profile == "background only":
        return "environment"
    if profile == "product / object":
        return "product"
    if profile == "small adult group":
        return "group"
    if profile in {"adult couple", "two adult women", "two adult men"}:
        return "multi"
    return "person"

_ENGLISH_VOWEL_SOUND_PREFIXES = (
    "adult", "elderly", "east", "asian", "african", "indoor", "outdoor", "nsfw",
    "old", "older", "ordinary", "intimate", "elegant", "empty", "object", "upper",
    "open", "oversized", "off",
    # Standalone expression fallback vocabulary. Keep this explicit instead of
    # relying on first-letter vowel checks, because words such as one-sided,
    # uniform, and european-style begin with vowel letters but take "a".
    "agitated", "alert", "aloof", "angry", "annoyed", "anxious",
    "awkward", "amused", "ashamed", "awed", "awesome", "affectionate",
    "earnest", "eerie", "ecstatic", "embarrassed", "emotional",
    "enigmatic", "erotic", "evasive", "exhausted", "explicit", "expressive",
    "innocent",
    "intense", "irritated", "ironic", "ominous", "obvious", "ultra",
    "uneasy", "unamused", "understated", "unhappy", "unimpressed", "upset",
    "overwhelmed", "open-mouthed",
)

def _english_article(phrase: str) -> str:
    s = _clean_text(phrase)
    if not s:
        return "a"
    prefix_pattern = "|".join(re.escape(x) for x in _ENGLISH_VOWEL_SOUND_PREFIXES)
    return "an" if re.match(rf"(?i)^({prefix_pattern})(?:\b|[-/])", s) else "a"

def _with_article(phrase: str) -> str:
    p = _clean_text(phrase)
    if not p:
        return ""
    if re.match(r"(?i)^(a|an|the|two|three|several|small group)\b", p):
        return p
    return f"{_english_article(p)} {p}"


def _standalone_effective_subject_age(value: str, profile: str, adult_active: bool) -> str:
    age = _safe_ui_value(value, "subject_age")
    # The all-auto standalone default should be clear enough for image models,
    # but explicit subject profiles keep the older neutral behavior unless the
    # user chooses an age band.
    if age == "auto" and _safe_ui_value(profile, "subject_profile") == "auto":
        return "20s"
    if age == "auto" and adult_active:
        return "adult"
    return "" if age == "auto" else age


def _standalone_effective_ethnicity(value: str, profile: str, family: str = "natural") -> str:
    eth = _safe_ui_value(value, "subject_ethnicity")
    if eth == "auto" and _safe_ui_value(profile, "subject_profile") == "auto":
        eth = "Korean"
    if eth == "auto":
        return ""
    if family == "tag":
        return eth.lower().replace("-looking", "")
    return eth.replace("-looking", "")


def _standalone_appearance_phrase(value: str, family: str = "natural") -> str:
    app = _safe_ui_value(value, "subject_appearance")
    if app == "auto":
        return ""
    if family == "tag":
        return {
            "natural-looking": "natural-looking",
            "cute": "cute",
            "beautiful": "beautiful",
            "elegant": "elegant",
            "glamorous": "glamorous",
            "ordinary-looking": "ordinary-looking",
            "simple-looking": "simple-looking",
            "less conventionally attractive": "plain-looking",
            "distinctive-looking": "distinctive-looking",
        }.get(app, app)
    return app


def _standalone_age_natural_parts(age: str, subject_profile: str) -> Tuple[str, str]:
    profile = _safe_ui_value(subject_profile, "subject_profile")
    feminine = profile in {"auto", "adult woman", "two adult women"}
    masculine = profile in {"adult man", "two adult men"}
    plural = profile in {"adult couple", "two adult women", "two adult men", "small adult group"}
    if plural:
        pronoun = "their"
    elif masculine:
        pronoun = "his"
    elif feminine:
        pronoun = "her"
    else:
        pronoun = "their"
    if age == "20s":
        if profile == "small adult group":
            prefix = "young"
        else:
            prefix = "young adult"
        suffix = "mostly in their early twenties" if profile == "small adult group" else f"in {pronoun} early twenties"
        return prefix, suffix
    if age == "30s":
        suffix = "mostly in their thirties" if profile == "small adult group" else f"in {pronoun} thirties"
        return "", suffix
    if age == "40s":
        suffix = "mostly in their forties" if profile == "small adult group" else f"in {pronoun} forties"
        return "", suffix
    if age == "50s":
        suffix = "mostly in their fifties" if profile == "small adult group" else f"in {pronoun} fifties"
        return "middle-aged", suffix
    if age == "60s+":
        suffix = "mostly in their sixties or older" if profile == "small adult group" else f"in {pronoun} sixties or older"
        return "older", suffix
    if age == "adult":
        return "adult", ""
    return age, ""


def _standalone_age_tag_parts(age: str) -> List[str]:
    return {
        "20s": ["young adult", "early 20s"],
        "30s": ["30s"],
        "40s": ["40s"],
        "50s": ["middle-aged", "50s"],
        "60s+": ["older adult", "60s"],
        "adult": [],
    }.get(age, [age] if age else [])


def _standalone_join_core(parts: List[str]) -> str:
    return re.sub(r"\s+", " ", " ".join([p for p in parts if _clean_text(p)])).strip()


def _standalone_subject_phrase(subject_profile: str, subject_age: str, subject_ethnicity: str, subject_appearance: str = "auto", adult_active: bool = False, family: str = "natural") -> Tuple[str, List[str]]:
    profile = _safe_ui_value(subject_profile, "subject_profile")
    if profile in {"background only", "product / object"}:
        return "", []
    age = _standalone_effective_subject_age(subject_age, profile, adult_active)
    eth = _standalone_effective_ethnicity(subject_ethnicity, profile, family="natural")
    appearance = _standalone_appearance_phrase(subject_appearance, family=family)

    if family == "tag":
        if profile == "adult man":
            tags = ["1boy", "adult man"]
        elif profile == "adult couple":
            tags = ["1girl", "1boy", "adult couple"]
        elif profile == "two adult women":
            tags = ["2girls", "adult women"]
        elif profile == "two adult men":
            tags = ["2boys", "adult men"]
        elif profile == "small adult group":
            tags = ["group", "adults"]
        else:
            tags = ["1girl", "adult woman"]
        tags.extend(_standalone_age_tag_parts(age))
        if eth:
            tags.append(eth.lower())
        if appearance:
            tags.append(appearance)
        return "", tags

    age_prefix, age_suffix = _standalone_age_natural_parts(age, profile)
    app_part = appearance
    eth_part = eth

    if profile == "adult man":
        core = _standalone_join_core([app_part, age_prefix, eth_part, "man"])
        if not age_prefix and not age_suffix and not eth and not appearance:
            core = "adult man"
        phrase = _with_article(core)
    elif profile == "adult couple":
        couple_noun = "couple" if age_prefix in {"adult", "young adult", "middle-aged", "older"} else "adult couple"
        core = _standalone_join_core([app_part, age_prefix, eth_part, couple_noun])
        phrase = _with_article(core)
    elif profile == "two adult women":
        core = _standalone_join_core(["two", app_part, age_prefix, eth_part, "women"])
        if not age_prefix and not age_suffix and not eth and not appearance:
            core = "two adult women"
        phrase = core
    elif profile == "two adult men":
        core = _standalone_join_core(["two", app_part, age_prefix, eth_part, "men"])
        if not age_prefix and not age_suffix and not eth and not appearance:
            core = "two adult men"
        phrase = core
    elif profile == "small adult group":
        core = _standalone_join_core(["a small group of", app_part, eth_part, "adults"])
        phrase = core
    else:
        core = _standalone_join_core([app_part, age_prefix, eth_part, "woman"])
        if not age_prefix and not age_suffix and not eth and not appearance:
            core = "adult woman"
        phrase = _with_article(core)
    if age_suffix:
        phrase = f"{phrase} {age_suffix}"
    return re.sub(r"\s+", " ", phrase).strip(), []

def _standalone_resolve_location(location_type: str, adult_privacy: str, adult_high: bool, kind: str) -> str:
    loc = _safe_ui_value(location_type, "location_type")
    privacy = _safe_ui_value(adult_privacy, "adult_scene_privacy")
    if kind == "product":
        return loc if loc not in {"auto", "beach", "forest", "park", "city street", "alley"} else "studio backdrop"
    if kind == "environment":
        return loc if loc != "auto" else "cozy living room"
    if privacy == "bedroom / hotel room":
        return loc if loc in {"bedroom", "hotel room"} else "bedroom"
    if privacy == "boudoir bedroom":
        return "bedroom"
    if privacy == "luxury hotel suite":
        return "hotel room"
    if privacy == "private lounge":
        return "bar / lounge"
    if privacy == "studio":
        return loc if loc in {"private studio", "studio backdrop"} else "private studio"
    if privacy == "dressing room":
        return "private studio"
    if privacy == "bathroom":
        return "bathroom"
    if privacy == "spa / bath":
        return "bathroom"
    if privacy == "poolside / beach":
        return loc if loc in {"poolside", "beach"} else "poolside"
    if privacy == "private indoor" and loc in {"auto"} | _STANDALONE_PUBLIC_LOCATIONS:
        return "bedroom"
    if loc == "auto":
        return "bedroom" if adult_high else "cozy living room"
    return loc

def _standalone_detail_phrase(location_detail: str) -> str:
    detail = _safe_ui_value(location_detail, "location_detail")
    return "" if detail == "auto" else _LOCATION_DETAIL_PHRASES.get(detail, "")

def _standalone_detail_tags(location_detail: str) -> List[str]:
    detail = _safe_ui_value(location_detail, "location_detail")
    return [] if detail == "auto" else list(_LOCATION_DETAIL_TAGS.get(detail, []))

def _standalone_action(action: str, pose: str, loc: str, adult_pose_style: str, adult_active: bool, family: str = "natural") -> Tuple[str, List[str]]:
    adult_pose = _safe_ui_value(adult_pose_style, "adult_pose_style")
    act = _safe_ui_value(action, "subject_action")
    p = _safe_ui_value(pose, "subject_pose")
    tags: List[str] = []

    if adult_active and adult_pose != "auto":
        mapping = {
            "relaxed sensual pose": ("in a relaxed sensual pose", "sensual pose"),
            "reclining sensual pose": ("reclining in a sensual pose", "reclining"),
            "seated sensual pose": ("seated in a sensual pose", "seated"),
            "standing confident pose": ("standing in a confident pose", "confident pose"),
            "looking over shoulder": ("looking over the shoulder", "looking back"),
            "intimate portrait pose": ("posed for an intimate adult portrait", "intimate portrait"),
            "sitting on bed edge": ("sitting on the edge of a bed", "sitting on bed"),
            "lying on side": ("lying on one side", "lying on side"),
            "wrapped in sheets": ("wrapped in sheets", "wrapped in sheets"),
            "standing by mirror": ("standing beside a mirror", "mirror pose"),
            "leaning against wall": ("leaning against a wall", "leaning against wall"),
            "adjusting robe": ("adjusting a robe", "adjusting robe"),
            "poolside lounging": ("lounging by the pool", "poolside lounging"),
            "back turned silhouette": ("turned away in a tasteful silhouette", "back turned silhouette"),
        }
        mapping.update(_ADULT_POSE_EXTRA_MAP)
        nat, tag = mapping.get(adult_pose, ("", ""))
        return nat, [tag] if tag else []

    if act == "auto":
        if p == "auto":
            return "", []
        pose_nat, pose_tag = _STANDALONE_POSE_ACTION_MAP.get(p, (p, p.replace(" ", "_")))
        return pose_nat, [pose_tag] if pose_tag else []

    action_map = {
        "standing still": ("standing still", "standing"),
        "sitting at a table": ("sitting at a table", "sitting at table"),
        "walking naturally": ("walking naturally", "walking"),
        "looking out the window": ("looking out the window", "looking out window"),
        "looking at the camera": ("looking at the camera", "looking at viewer"),
        "reading a book": ("reading a book", "reading"),
        "using a phone": ("using a phone", "smartphone"),
        "working on a laptop": ("working on a laptop", "laptop"),
        "drinking from a cup": ("drinking from a cup", "drinking"),
        "holding a flower bouquet": ("holding a flower bouquet", "flower bouquet"),
        "carrying a handbag": ("carrying a handbag", "handbag"),
        "taking a selfie": ("taking a selfie", "selfie"),
        "listening to music": ("listening to music", "headphones"),
        "looking in a mirror": ("looking into a mirror", "mirror"),
        "resting on a bed": ("resting on a bed", "on bed"),
        "standing in water": ("standing in shallow water", "standing in water"),
        "waiting at a station": ("waiting at a station", "waiting at station"),
        "shopping on a street": ("shopping on a street", "shopping"),
    }
    action_map.update(_STANDALONE_ACTION_EXTRA_MAP)
    nat, tag = action_map.get(act, ("", ""))
    repaired_generic = False
    if act == "looking out the window" and loc not in _STANDALONE_WINDOW_LOCATIONS:
        nat, tag = "looking into the distance", "looking away"
        repaired_generic = True
    if act == "resting on a bed" and loc not in {"bedroom", "hotel room"}:
        nat, tag = "reclining in a relaxed pose", "reclining"
        repaired_generic = True
    if act == "standing in water" and loc not in _STANDALONE_WATER_LOCATIONS:
        nat, tag = "standing still", "standing"
        repaired_generic = True
    if act == "working on a laptop" and loc not in {"office", "library", "bookstore", "cafe", "modern apartment", "cozy living room", "hotel room"}:
        nat, tag = "using a phone", "smartphone"
        repaired_generic = True
    if act == "sitting at a table" and loc not in {"cafe", "restaurant", "office", "library", "bookstore", "kitchen", "cozy living room", "modern apartment", "hotel room"}:
        nat, tag = "sitting", "sitting"
        repaired_generic = True
    if act == "waiting at a station" and loc not in {"train station", "subway platform"}:
        nat, tag = "standing still", "standing"
        repaired_generic = True
    # loc in {"train station", "subway platform"}: action_map value kept as-is
    if act == "shopping on a street" and loc not in {"shopping street", "city street"}:
        nat, tag = "walking naturally", "walking"
        repaired_generic = True
    nat, tag, repaired_extra = _standalone_repair_action_for_location(act, nat, tag, loc)
    repaired_generic = repaired_generic or repaired_extra
    if p != "auto" and nat:
        pose_nat, pose_tag = _STANDALONE_POSE_ACTION_MAP.get(p, (p, p.replace(" ", "_")))
        if _standalone_pose_conflicts_with_action(p, act, nat):
            if repaired_generic and pose_nat:
                return pose_nat, [pose_tag] if pose_tag else []
        elif pose_nat and pose_nat not in nat and p not in nat:
            nat = f"{pose_nat}, {nat}"
            if pose_tag:
                tags.append(pose_tag)
    if tag:
        tags.append(tag)
    return nat, tags

def _standalone_props(scene_props: str, loc: str, kind: str, family: str = "natural") -> List[str]:
    prop = _safe_ui_value(scene_props, "scene_props")
    if prop in {"auto", "none"}:
        return []
    if kind == "product":
        return ["sleek cosmetic bottle"] if prop == "cosmetic product" else _PROP_PHRASES.get(prop, [prop])
    allowed = _PROP_ALLOWED_LOCATIONS.get(prop)
    if allowed is not None and loc not in allowed:
        # Expanded dropdowns make impossible literal props easy to combine with
        # unrelated locations. Preserve the user's rough intent only when a
        # natural local substitute exists; otherwise omit the prop rather than
        # emitting contradictions like "bed in a forest" or "window on a beach".
        return _standalone_prop_fallback_for_location(prop, loc)
    return list(_PROP_PHRASES.get(prop, [prop]))

def _standalone_wardrobe(adult_tone: str, adult_wardrobe: str, adult_exposure_level: str, loc: str, kind: str, family: str = "natural") -> Tuple[str, str, float, str]:
    if kind in {"environment", "product"}:
        return "", "", 1.0, ""
    tone = _safe_ui_value(adult_tone, "adult_tone")
    wardrobe = _safe_ui_value(adult_wardrobe, "adult_wardrobe")
    exposure = _safe_ui_value(adult_exposure_level, "adult_exposure_level")
    nat = tag = level = ""
    weight = 1.0
    if wardrobe != "auto" and wardrobe in _ADULT_WARDROBE_SCENE:
        nat, tag, weight, level = _ADULT_WARDROBE_SCENE[wardrobe]
    elif exposure != "auto" and exposure in _ADULT_EXPOSURE_SCENE:
        nat, tag, level = _ADULT_EXPOSURE_SCENE[exposure]
        weight = 1.14 if level in {"intimate", "high"} else 1.08
    elif tone in {"suggestive", "sensual", "bold sensual", "nsfw", "explicit nsfw"}:
        nat, tag, level = ("with sensual styling", "sensual styling", "mild")

    return nat, tag, weight, level

def _standalone_time_weather(time_of_day: str, weather_light: str, loc: str) -> List[str]:
    out = []
    tod = _safe_ui_value(time_of_day, "time_of_day")
    weather = _safe_ui_value(weather_light, "weather_light")
    if tod != "auto":
        out.append(_TIME_PHRASES.get(tod, ""))
    if weather != "auto":
        if loc in _STANDALONE_OUTDOOR_LOCATIONS and weather in {"indoor lighting only", "soft indoor lighting"}:
            out.append("with soft ambient light")
        elif loc in _STANDALONE_INDOOR_LOCATIONS:
            indoor_phrase = _standalone_indoor_weather_phrase(weather, loc)
            out.append(indoor_phrase if indoor_phrase else _WEATHER_PHRASES.get(weather, ""))
        else:
            out.append(_WEATHER_PHRASES.get(weather, ""))
    return [x for x in out if x]


def _standalone_auto_extra_props(loc: str, level: str) -> List[str]:
    level = _safe_ui_value(level, "auto_extra_detail")
    if level == "auto":
        return []
    # Keep prop insertion modest. Richness is mainly handled by safe scene-quality
    # phrases below, not by long object lists that can distract the model.
    count = {"light auto fill": 1, "balanced auto fill": 2, "rich auto fill": 3}.get(level, 0)
    return list(_AUTO_PROPS_BY_LOCATION.get(loc, []))[:count]

def _standalone_auto_extra_time_weather(level: str, loc: str) -> List[str]:
    level = _safe_ui_value(level, "auto_extra_detail")
    if level == "auto":
        return []
    if loc in _STANDALONE_PRIVATE_LOCATIONS:
        return ["under soft indoor lighting"]
    if loc in _STANDALONE_OUTDOOR_LOCATIONS:
        return ["under soft ambient light"]
    return ["under natural light"]

def _standalone_auto_extra_scene_quality(loc: str, level: str) -> List[str]:
    level = _safe_ui_value(level, "auto_extra_detail")
    if level == "auto":
        return []
    items = list(_AUTO_SCENE_QUALITY_BY_LOCATION.get(loc, []))
    if not items:
        items = ["coherent background layout", "subtle environmental texture", "balanced scene depth"]
    count = {"light auto fill": 1, "balanced auto fill": 2, "rich auto fill": 3}.get(level, 0)
    return items[:count]

def _standalone_auto_extra_scene_quality_tags(loc: str, level: str) -> List[str]:
    return [str(x).replace("-", " ") for x in _standalone_auto_extra_scene_quality(loc, level)]

def _standalone_cap_sentence(text: str) -> str:
    s = _clean_text(text)
    if not s:
        return ""
    return s[0].upper() + s[1:]


def _standalone_natural_action_predicate(action_nat: str, kind: str, subject_profile: str = "auto") -> str:
    action = _clean_text(action_nat)
    profile = _safe_ui_value(subject_profile, "subject_profile")
    plural_subject = kind in {"group", "multi"} and profile != "adult couple"
    verb = "are" if plural_subject else "is"
    if not action:
        return "are arranged" if plural_subject else "is posed"
    if ", " in action:
        first, rest = action.split(", ", 1)
        return f"{verb} {first} and {rest}"
    return f"{verb} {action}"


def _standalone_join_english_list(items: List[str]) -> str:
    clean = [_clean_text(x) for x in items if _clean_text(x)]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return ", ".join(clean[:-1]) + f", and {clean[-1]}"


def _standalone_natural_modifiers(*items: str) -> str:
    clean = [_clean_text(x) for x in items if _clean_text(x)]
    if not clean:
        return ""
    lead: List[str] = []
    with_parts: List[str] = []
    for item in clean:
        if item.lower().startswith("with "):
            with_parts.append(item[5:])
        else:
            lead.append(item)
    out = ""
    if lead:
        out += " " + " ".join(lead)
    if with_parts:
        out += " with " + _standalone_join_english_list(with_parts)
    return out


def _standalone_followup_sentence(
    subject_label: str,
    props: List[str],
    time_weather: List[str],
    custom_text: str = "",
    scene_quality: Optional[List[str]] = None,
) -> str:
    prop_text = _standalone_join_english_list(props)
    tw = [_clean_text(x) for x in time_weather if _clean_text(x)]
    quality_text = _standalone_join_english_list(scene_quality or [])
    sentences: List[str] = []
    if prop_text:
        sentence = "the scene includes " + prop_text
        if tw:
            sentence += " " + " ".join(tw)
        sentences.append(sentence)
    elif tw:
        sentences.append("the scene is set " + " ".join(tw))
    if quality_text:
        sentences.append("the background shows " + quality_text)
    if custom_text:
        sentences.append(_clean_text(custom_text))
    if not sentences:
        return ""
    return " ".join(_sentence(_standalone_cap_sentence(s)) for s in sentences)




def _standalone_adult_lighting_parts(adult_lighting: str, loc: str) -> Tuple[str, List[str]]:
    lighting = _safe_ui_value(adult_lighting, "adult_lighting")
    if lighting == "auto":
        return "", []
    bedroom_locs = {"bedroom", "hotel room"}
    bath_locs = {"bathroom"}
    studio_locs = {"private studio", "studio backdrop"}
    lounge_locs = {"bar / lounge", "private studio", "studio backdrop", "hotel room"}
    sunset_locs = {"beach", "poolside", "balcony", "rooftop", "city street", "shopping street", "garden", "park"}

    outdoor_loc = loc in _STANDALONE_OUTDOOR_LOCATIONS
    if lighting == "warm bedside light" and loc not in bedroom_locs:
        return ("under warm localized ambient light" if outdoor_loc else "under soft warm ambient lighting"), ["soft warm light"]
    if lighting == "steamy bathroom light" and loc not in bath_locs:
        return ("under soft diffused ambient light" if outdoor_loc else "under soft diffused lighting"), ["soft diffused light"]
    if lighting == "studio rim light" and loc not in studio_locs:
        return "with soft rim lighting", ["soft rim light"]
    if lighting == "neon lounge light" and loc not in lounge_locs:
        return "under muted colored accent lighting", ["muted accent light"]
    if lighting == "sunset backlight" and loc not in sunset_locs:
        return "with warm soft backlight", ["warm backlight"]

    return _ADULT_LIGHTING_PARTS.get(lighting, ("", []))

def _standalone_adult_scene_props(adult_scene_props: str, loc: str) -> List[str]:
    prop = _safe_ui_value(adult_scene_props, "adult_scene_props")
    if prop == "auto":
        return []
    items, allowed = _ADULT_SCENE_PROPS_PARTS.get(prop, ([], None))
    if allowed is not None and loc not in allowed:
        return []
    return list(items)

def _standalone_adult_detail_parts(
    adult_scene_mood: str,
    adult_lighting: str,
    adult_scene_props: str,
    adult_body_focus: str,
    loc: str,
) -> Tuple[List[str], List[str], List[str], List[str]]:
    notes: List[str] = []
    lights: List[str] = []
    props: List[str] = []
    tags: List[str] = []

    mood = _safe_ui_value(adult_scene_mood, "adult_scene_mood")
    if mood != "auto":
        nat, mood_tags = _ADULT_SCENE_MOOD_PARTS.get(mood, ("", []))
        if nat:
            notes.append(nat)
        tags.extend(mood_tags)

    lighting = _safe_ui_value(adult_lighting, "adult_lighting")
    if lighting != "auto":
        nat, light_tags = _standalone_adult_lighting_parts(lighting, loc)
        if nat:
            lights.append(nat)
        tags.extend(light_tags)

    body_focus = _safe_ui_value(adult_body_focus, "adult_body_focus")
    if body_focus != "auto":
        nat, body_tags = _ADULT_BODY_FOCUS_PARTS.get(body_focus, ("", []))
        if nat:
            notes.append(nat)
        tags.extend(body_tags)

    props.extend(_standalone_adult_scene_props(adult_scene_props, loc))
    tags.extend([p.replace("_", " ") for p in props])
    return notes, lights, props, tags

def _standalone_adult_followup_sentence(notes: List[str]) -> str:
    clean = [_clean_text(x) for x in notes if _clean_text(x)]
    if not clean:
        return ""
    clean = [re.sub(r"^with\s+", "", x, flags=re.I) for x in clean]
    return _sentence("The adult styling uses " + _standalone_join_english_list(clean))

def _standalone_krea2_readable_action_detail(
    *,
    kind: str,
    subject_pose: str,
    subject_action: str,
    subject_expression: str,
    scene_props: str,
    loc: str,
    location_phrase: str = "",
) -> str:
    """Krea2-specific concrete scene guidance for standalone natural prompts.

    Krea2 tends to benefit from explicit, visualizable instructions.  Keep this
    helper narrow and descriptive: it should clarify pose/space/interaction
    without changing other model profiles or adding vague quality prose.
    """
    pose = _safe_ui_value(subject_pose, "subject_pose")
    action = _safe_ui_value(subject_action, "subject_action")
    expression = _safe_ui_value(subject_expression, "subject_expression")
    prop = _safe_ui_value(scene_props, "scene_props")

    if kind == "environment":
        return _sentence("Show the room layout, foreground objects, background depth, and light direction")
    if kind == "product":
        return _sentence("Describe the product placement, material surface, surrounding props, and how the light falls across the object")

    if kind in {"multi", "group"}:
        base = "Show each person's pose, spacing, facing direction, and relative placement"
        if location_phrase:
            base += " within the scene"
        return _sentence(base)

    if kind != "person":
        return ""

    pose_map = {
        "standing": "Show a stable standing posture with relaxed shoulders, visible weight shift, and natural arm placement",
        "sitting": "Show a seated posture with the torso angle, hand position, and nearby surface placement",
        "leaning": "Show the body leaning against the nearby surface, with visible contact point and balanced weight",
        "walking": "Show a natural walking step with one leg leading, body momentum, and relaxed arm placement",
        "looking back": "Show the head and shoulders turned back while the body keeps its original facing direction",
        "reclining": "Show a relaxed reclining posture with the torso, legs, and support surface arranged in view",
        "lying down": "Show the body lying down with the head, shoulders, and surrounding surface relationship visible",
    }
    pose_map.update(_STANDALONE_KREA2_POSE_EXTRA_MAP)
    action_map = {
        "standing still": "Use a calm grounded stance, believable hand placement, and a defined body direction",
        "sitting at a table": "Place the hands and upper body naturally near the tabletop",
        "walking naturally": "Show walking direction, body movement, natural stride, and relaxed arms",
        "looking out the window": "Turn the head and gaze toward the window, with the window positioned in relation to the subject",
        "looking at the camera": "Point the gaze and face direction toward the camera",
        "reading a book": "Show the book held or placed naturally, with the gaze and hands directed toward it",
        "using a phone": "Show the phone in the hand, with gaze or hand position connected to the device",
        "working on a laptop": "Show laptop placement, hand position, and seated or leaning posture",
        "drinking from a cup": "Show the cup, hand, and mouth-level gesture without hiding the face",
        "holding a flower bouquet": "Show the bouquet held naturally in the hands, with the flowers visible and connected to the pose",
        "carrying a handbag": "Show the handbag carried naturally, with visible strap or hand contact",
        "taking a selfie": "Show the raised phone, face direction, and selfie arm gesture",
        "listening to music": "Show the headphones or listening gesture, with head and hand placement connected to the action",
        "looking in a mirror": "Set the gaze and reflection direction toward the mirror",
        "resting on a bed": "Show the bed surface supporting the body, with relaxed posture and nearby bedding",
        "standing in water": "Show the waterline around the legs and the standing balance",
        "waiting at a station": "Show a calm waiting posture with platform or station elements around the subject",
        "shopping on a street": "Show the shopping movement, street direction, and carried items",
    }
    action_map.update(_STANDALONE_KREA2_ACTION_EXTRA_MAP)
    detail = _standalone_krea2_repaired_action_detail(action, loc)
    if not detail and action != "auto" and action in action_map:
        detail = action_map[action]
    elif not detail and pose != "auto" and pose in pose_map:
        detail = pose_map[pose]
    elif not detail:
        detail = "Show the pose, body direction, hand placement, and surrounding spatial relationship"

    additions: List[str] = []
    if expression != "auto":
        additions.append("include the facial expression")
    if prop not in {"auto", "none"}:
        additions.append("place any selected prop in the hands or nearby space when relevant")
    if loc in _STANDALONE_WINDOW_LOCATIONS and action in {"auto", "standing still", "looking out the window"}:
        additions.append("include the window or room depth relation")
    if additions:
        detail += ", and " + _standalone_join_english_list(additions)
    return _sentence(detail)




_STANDALONE_EXPRESSION_ARTICLED_NOUN_SUFFIXES = (
    "smile", "face", "blush", "wink", "look", "gaze", "glance", "stare",
    "frown", "scowl", "smirk", "grin", "grimace", "tear",
)
_STANDALONE_EXPRESSION_BARE_PLURAL_SUFFIXES = ("eyes", "tears")

def _standalone_expression_modifier(expression: str) -> str:
    expr = _safe_ui_value(expression, "subject_expression")
    if expr == "auto":
        return ""
    mapped = _STANDALONE_EXPRESSION_NATURAL_PHRASES.get(expr)
    if mapped:
        return mapped
    expr_clean = _clean_text(expr)
    expr_base = re.sub(r"(?i)\s+expression$", "", expr_clean).strip()
    if expr_base in {"natural"}:
        return "with a natural expression"
    if expr_base.endswith(_STANDALONE_EXPRESSION_BARE_PLURAL_SUFFIXES):
        return f"with {expr_base}"
    if expr_base.endswith(_STANDALONE_EXPRESSION_ARTICLED_NOUN_SUFFIXES):
        return f"with {_with_article(expr_base)}"
    return f"with {_with_article(f'{expr_base} expression')}"

def _standalone_build_scene_natural(
    *,
    model_profile: str = "",
    subject_profile: str,
    subject_age: str,
    subject_appearance: str,
    subject_ethnicity: str,
    subject_hair: str,
    subject_outfit: str,
    subject_expression: str,
    subject_pose: str,
    subject_action: str,
    location_type: str,
    location_detail: str,
    time_of_day: str,
    weather_light: str,
    scene_props: str,
    auto_extra_detail: str,
    adult_tone: str,
    adult_wardrobe: str,
    adult_exposure_level: str,
    adult_pose_style: str,
    adult_scene_privacy: str,
    adult_scene_mood: str = "auto",
    adult_lighting: str = "auto",
    adult_scene_props: str = "auto",
    adult_body_focus: str = "auto",
    custom_text: str = "",
) -> Tuple[str, str]:
    kind = _standalone_kind(subject_profile)
    adult_active = _standalone_adult_context_active(
        adult_tone,
        adult_wardrobe,
        adult_exposure_level,
        adult_pose_style,
        adult_scene_mood,
        adult_lighting,
        adult_scene_props,
        adult_body_focus,
    )
    adult_high = _standalone_is_explicit_adult(adult_tone, adult_wardrobe, adult_exposure_level)
    loc = _standalone_resolve_location(location_type, adult_scene_privacy, adult_high, kind)
    detail = _standalone_detail_phrase(location_detail)
    props = _standalone_props(scene_props, loc, kind, family="natural")
    if not props:
        props = _standalone_auto_extra_props(loc, auto_extra_detail)
    adult_notes, adult_lights, adult_props, _adult_tags = _standalone_adult_detail_parts(
        adult_scene_mood, adult_lighting, adult_scene_props, adult_body_focus, loc
    ) if adult_active and kind not in {"environment", "product"} else ([], [], [], [])
    props.extend([p for p in adult_props if p not in props])
    time_weather = _standalone_time_weather(time_of_day, weather_light, loc)
    if not time_weather:
        time_weather = _standalone_auto_extra_time_weather(auto_extra_detail, loc)
    time_weather.extend([x for x in adult_lights if x not in time_weather])
    wardrobe_nat, _, _, _ = _standalone_wardrobe(adult_tone, adult_wardrobe, adult_exposure_level, loc, kind, family="natural")
    wardrobe_nat = _standalone_pluralize_wardrobe_for_multi(wardrobe_nat, kind)
    location_phrase = _LOCATION_PHRASES.get(loc, "")
    scene_quality = _standalone_auto_extra_scene_quality(loc, auto_extra_detail)

    if kind == "environment":
        main = "An empty environment scene with no people"
        if location_phrase:
            main += f" is shown {location_phrase}"
        else:
            main += " is shown"
        if detail:
            main += f" {detail}"
        sentences = [_sentence(main)]
        if _model_key(model_profile) == "krea2":
            krea_detail = _standalone_krea2_readable_action_detail(
                kind=kind,
                subject_pose=subject_pose,
                subject_action=subject_action,
                subject_expression=subject_expression,
                scene_props=scene_props,
                loc=loc,
                location_phrase=location_phrase,
            )
            if krea_detail:
                sentences.append(krea_detail)
        follow = _standalone_followup_sentence("environment", props, time_weather, custom_text, scene_quality)
        if follow:
            sentences.append(follow)
        return " ".join(sentences), kind

    if kind == "product":
        main = "A carefully arranged product still life"
        if location_phrase:
            main += f" is set {location_phrase}"
        else:
            main += " is set in a clean composition"
        if detail:
            main += f" {detail}"
        sentences = [_sentence(main)]
        if _model_key(model_profile) == "krea2":
            krea_detail = _standalone_krea2_readable_action_detail(
                kind=kind,
                subject_pose=subject_pose,
                subject_action=subject_action,
                subject_expression=subject_expression,
                scene_props=scene_props,
                loc=loc,
                location_phrase=location_phrase,
            )
            if krea_detail:
                sentences.append(krea_detail)
        follow = _standalone_followup_sentence("product", props, time_weather, custom_text, scene_quality)
        if follow:
            sentences.append(follow)
        return " ".join(sentences), kind

    subject, _ = _standalone_subject_phrase(subject_profile, subject_age, subject_ethnicity, subject_appearance, adult_active, family="natural")
    hair = _safe_ui_value(subject_hair, "subject_hair")
    outfit = _safe_ui_value(subject_outfit, "subject_outfit")
    expr = _safe_ui_value(subject_expression, "subject_expression")
    modifiers: List[str] = []
    if wardrobe_nat:
        modifiers.append(wardrobe_nat)
    elif outfit != "auto":
        outfit_nat, _outfit_tag = _SUBJECT_OUTFIT_PARTS.get(outfit, ("", ""))
        outfit_nat = _standalone_pluralize_wardrobe_for_multi(outfit_nat, kind)
        if outfit_nat:
            modifiers.append(outfit_nat)
    if kind not in {"group"}:
        if hair != "auto":
            modifiers.append(f"with {hair}")
        elif _safe_ui_value(subject_profile, "subject_profile") == "auto":
            modifiers.append("with long dark hair")
    if kind not in {"group"} and expr != "auto":
        expr_modifier = _standalone_expression_modifier(expr)
        if expr_modifier:
            modifiers.append(expr_modifier)

    action_nat, _ = _standalone_action(subject_action, subject_pose, loc, adult_pose_style, adult_active, family="natural")
    if (
        not action_nat
        and kind == "person"
        and _safe_ui_value(subject_profile, "subject_profile") == "auto"
        and _safe_ui_value(subject_action, "subject_action") == "auto"
        and _safe_ui_value(subject_pose, "subject_pose") == "auto"
    ):
        if _safe_ui_value(subject_appearance, "subject_appearance") == "natural-looking":
            action_nat = "standing in a relaxed pose"
        else:
            action_nat = "standing naturally"
    predicate = _standalone_natural_action_predicate(action_nat, kind, subject_profile)

    main = _standalone_cap_sentence(subject + _standalone_natural_modifiers(*modifiers))
    main += f" {predicate}"
    if location_phrase:
        main += f" {location_phrase}"
    if detail:
        main += f" {detail}"
    sentences = [_sentence(main)]
    if _model_key(model_profile) == "krea2":
        krea_detail = _standalone_krea2_readable_action_detail(
            kind=kind,
            subject_pose=subject_pose,
            subject_action=subject_action,
            subject_expression=subject_expression,
            scene_props=scene_props,
            loc=loc,
            location_phrase=location_phrase,
        )
        if krea_detail:
            sentences.append(krea_detail)
    follow = _standalone_followup_sentence(subject, props, time_weather, custom_text, scene_quality)
    if follow:
        sentences.append(follow)
    adult_follow = _standalone_adult_followup_sentence(adult_notes)
    if adult_follow:
        sentences.append(adult_follow)
    return " ".join(sentences), kind

def _standalone_build_scene_tags(**kwargs) -> Tuple[str, str]:
    kind = _standalone_kind(kwargs.get("subject_profile", "auto"))
    adult_active = _standalone_adult_context_active(
        kwargs.get("adult_tone", "default"),
        kwargs.get("adult_wardrobe", "auto"),
        kwargs.get("adult_exposure_level", "auto"),
        kwargs.get("adult_pose_style", "auto"),
        kwargs.get("adult_scene_mood", "auto"),
        kwargs.get("adult_lighting", "auto"),
        kwargs.get("adult_scene_props", "auto"),
        kwargs.get("adult_body_focus", "auto"),
    )
    adult_high = _standalone_is_explicit_adult(kwargs.get("adult_tone", "default"), kwargs.get("adult_wardrobe", "auto"), kwargs.get("adult_exposure_level", "auto"))
    loc = _standalone_resolve_location(kwargs.get("location_type", "auto"), kwargs.get("adult_scene_privacy", "auto"), adult_high, kind)
    tags: List[str] = []
    if kind == "environment":
        tags += ["no humans", "empty scene"]
    elif kind == "product":
        tags += ["product photography", "still life"]
    else:
        _, subject_tags = _standalone_subject_phrase(kwargs.get("subject_profile", "auto"), kwargs.get("subject_age", "auto"), kwargs.get("subject_ethnicity", "auto"), kwargs.get("subject_appearance", "auto"), adult_active, family="tag")
        tags += subject_tags
        _, ward_tag, ward_weight, _ = _standalone_wardrobe(kwargs.get("adult_tone", "default"), kwargs.get("adult_wardrobe", "auto"), kwargs.get("adult_exposure_level", "auto"), loc, kind, family="tag")
        if ward_tag:
            tags.append(f"({ward_tag}:{ward_weight:.2f})" if ward_weight != 1.0 else ward_tag)
        hair = _safe_ui_value(kwargs.get("subject_hair", "auto"), "subject_hair")
        outfit = _safe_ui_value(kwargs.get("subject_outfit", "auto"), "subject_outfit")
        expr = _safe_ui_value(kwargs.get("subject_expression", "auto"), "subject_expression")
        if kind != "group" and hair != "auto":
            tags.append(hair)
        elif kind != "group" and _safe_ui_value(kwargs.get("subject_profile", "auto"), "subject_profile") == "auto":
            tags.append("long dark hair")
        if outfit != "auto" and not ward_tag:
            _outfit_nat, outfit_tag = _SUBJECT_OUTFIT_PARTS.get(outfit, ("", outfit))
            tags.append(outfit_tag)
        if kind != "group" and expr != "auto":
            tags.append(expr)
        _, action_tags = _standalone_action(kwargs.get("subject_action", "auto"), kwargs.get("subject_pose", "auto"), loc, kwargs.get("adult_pose_style", "auto"), adult_active, family="tag")
        if (
            not action_tags
            and kind == "person"
            and _safe_ui_value(kwargs.get("subject_profile", "auto"), "subject_profile") == "auto"
            and _safe_ui_value(kwargs.get("subject_action", "auto"), "subject_action") == "auto"
            and _safe_ui_value(kwargs.get("subject_pose", "auto"), "subject_pose") == "auto"
        ):
            action_tags.append("standing")
        tags += action_tags

    tags += _LOCATION_TAGS.get(loc, [])
    tags += _standalone_detail_tags(kwargs.get("location_detail", "auto"))
    tod = _safe_ui_value(kwargs.get("time_of_day", "auto"), "time_of_day")
    weather = _safe_ui_value(kwargs.get("weather_light", "auto"), "weather_light")
    if tod != "auto":
        tags.append(tod)
    if weather != "auto":
        if loc in _STANDALONE_OUTDOOR_LOCATIONS and weather in {"indoor lighting only", "soft indoor lighting"}:
            tags.append("soft ambient light")
        elif loc in _STANDALONE_PRIVATE_LOCATIONS and weather in {"clear", "cloudy", "snowy"}:
            tags.append("soft window light")
        else:
            tags.append(weather.replace(" only", ""))
    elif tod == "auto":
        for extra_light in _standalone_auto_extra_time_weather(kwargs.get("auto_extra_detail", "auto"), loc):
            tags.append(extra_light)
    tag_props = _standalone_props(kwargs.get("scene_props", "auto"), loc, kind, family="tag")
    if not tag_props:
        tag_props = _standalone_auto_extra_props(loc, kwargs.get("auto_extra_detail", "auto"))
    for p in tag_props:
        tags.append(str(p).replace("_", " "))
    tags += _standalone_auto_extra_scene_quality_tags(loc, kwargs.get("auto_extra_detail", "auto"))
    if adult_active and kind not in {"environment", "product"}:
        _adult_notes, adult_lights, adult_props, adult_tags = _standalone_adult_detail_parts(
            kwargs.get("adult_scene_mood", "auto"),
            kwargs.get("adult_lighting", "auto"),
            kwargs.get("adult_scene_props", "auto"),
            kwargs.get("adult_body_focus", "auto"),
            loc,
        )
        # adult_lights contains natural-language fragments such as
        # "with soft window backlight".  Tag-style standalone prompts already
        # receive the corresponding clean tag from adult_tags, so do not append
        # the natural fragment here; otherwise outputs become
        # "with soft window backlight, soft window backlight".
        for prop in adult_props:
            tags.append(prop)
        tags.extend(adult_tags)
    custom = _clean_text(kwargs.get("custom_text", ""))
    if custom:
        tags.append(custom)
    return _join_unique_tags(tags), kind


def _compact_mixed_tag_scene_age_terms(tag_scene: str, subject_age: str) -> str:
    """Remove redundant standalone age tokens from the tag half of mixed prompts.

    Mixed prompts already append a natural-language scene sentence that carries the
    precise age wording. Keeping the profile/adult tag while removing the extra
    tag-side age tokens avoids outputs such as "adult woman, young adult, early
    20s" without changing pure tag models.
    """
    scene = _clean_text(tag_scene)
    if not scene:
        return ""
    age = _safe_ui_value(subject_age, "subject_age")
    remove = {_normalize_tag_identity(x).lower() for x in _standalone_age_tag_parts(age)}
    if not remove:
        return scene
    kept: List[str] = []
    for part in _split_prompt_tags(scene):
        cleaned = _clean_text(part)
        if not cleaned:
            continue
        if _normalize_tag_identity(cleaned).lower() in remove:
            continue
        kept.append(cleaned)
    return _join_comma(kept)


def _build_standalone_scene_mixed(
    model_profile: str,
    subject_profile: str,
    subject_age: str,
    subject_appearance: str,
    subject_ethnicity: str,
    subject_hair: str,
    subject_outfit: str,
    subject_expression: str,
    subject_pose: str,
    subject_action: str,
    location_type: str,
    location_detail: str,
    time_of_day: str,
    weather_light: str,
    scene_props: str,
    auto_extra_detail: str,
    adult_tone: str,
    adult_wardrobe: str,
    adult_exposure_level: str,
    adult_pose_style: str,
    adult_scene_privacy: str,
    adult_scene_mood: str = "auto",
    adult_lighting: str = "auto",
    adult_scene_props: str = "auto",
    adult_body_focus: str = "auto",
    custom_text: str = "",
) -> Tuple[str, str]:
    kwargs = dict(
        subject_profile=subject_profile,
        subject_age=subject_age,
        subject_appearance=subject_appearance,
        subject_ethnicity=subject_ethnicity,
        subject_hair=subject_hair,
        subject_outfit=subject_outfit,
        subject_expression=subject_expression,
        subject_pose=subject_pose,
        subject_action=subject_action,
        location_type=location_type,
        location_detail=location_detail,
        time_of_day=time_of_day,
        weather_light=weather_light,
        scene_props=scene_props,
        auto_extra_detail=auto_extra_detail,
        adult_tone=adult_tone,
        adult_wardrobe=adult_wardrobe,
        adult_exposure_level=adult_exposure_level,
        adult_pose_style=adult_pose_style,
        adult_scene_privacy=adult_scene_privacy,
        adult_scene_mood=adult_scene_mood,
        adult_lighting=adult_lighting,
        adult_scene_props=adult_scene_props,
        adult_body_focus=adult_body_focus,
        custom_text=custom_text,
    )
    tag_scene, tag_kind = _standalone_build_scene_tags(**kwargs)
    natural_scene, natural_kind = _standalone_build_scene_natural(**kwargs)
    kind = tag_kind or natural_kind
    if _is_anima_mixed_profile(model_profile) and tag_scene and natural_scene:
        adult_active = _standalone_adult_context_active(
            adult_tone,
            adult_wardrobe,
            adult_exposure_level,
            adult_pose_style,
            adult_scene_mood,
            adult_lighting,
            adult_scene_props,
            adult_body_focus,
        )
        effective_age = _standalone_effective_subject_age(subject_age, subject_profile, adult_active)
        tag_scene = _compact_mixed_tag_scene_age_terms(tag_scene, effective_age)
    if tag_scene and natural_scene:
        return f"{tag_scene}. {natural_scene}", kind
    return tag_scene or natural_scene, kind

def _build_standalone_scene(
    model_profile: str,
    subject_profile: str,
    subject_age: str,
    subject_appearance: str,
    subject_ethnicity: str,
    subject_hair: str,
    subject_outfit: str,
    subject_expression: str,
    subject_pose: str,
    subject_action: str,
    location_type: str,
    location_detail: str,
    time_of_day: str,
    weather_light: str,
    scene_props: str,
    auto_extra_detail: str,
    adult_tone: str,
    adult_wardrobe: str,
    adult_exposure_level: str,
    adult_pose_style: str,
    adult_scene_privacy: str,
    adult_scene_mood: str = "auto",
    adult_lighting: str = "auto",
    adult_scene_props: str = "auto",
    adult_body_focus: str = "auto",
    custom_text: str = "",
) -> Tuple[str, str]:
    family = _model_family(model_profile)
    kind = _standalone_kind(subject_profile)
    effective_adult_scene_privacy = adult_scene_privacy
    if kind not in {"environment", "product"} and _standalone_public_exposure_softened(
        location_type,
        adult_scene_privacy,
        adult_wardrobe,
        adult_exposure_level,
    ):
        effective_adult_scene_privacy = "studio"
    kwargs = dict(
        subject_profile=subject_profile,
        subject_age=subject_age,
        subject_appearance=subject_appearance,
        subject_ethnicity=subject_ethnicity,
        subject_hair=subject_hair,
        subject_outfit=subject_outfit,
        subject_expression=subject_expression,
        subject_pose=subject_pose,
        subject_action=subject_action,
        location_type=location_type,
        location_detail=location_detail,
        time_of_day=time_of_day,
        weather_light=weather_light,
        scene_props=scene_props,
        auto_extra_detail=auto_extra_detail,
        adult_tone=adult_tone,
        adult_wardrobe=adult_wardrobe,
        adult_exposure_level=adult_exposure_level,
        adult_pose_style=adult_pose_style,
        adult_scene_privacy=effective_adult_scene_privacy,
        adult_scene_mood=adult_scene_mood,
        adult_lighting=adult_lighting,
        adult_scene_props=adult_scene_props,
        adult_body_focus=adult_body_focus,
        custom_text=custom_text,
    )
    if family == "mixed":
        return _build_standalone_scene_mixed(
            model_profile=model_profile,
            subject_profile=subject_profile,
            subject_age=subject_age,
            subject_appearance=subject_appearance,
            subject_ethnicity=subject_ethnicity,
            subject_hair=subject_hair,
            subject_outfit=subject_outfit,
            subject_expression=subject_expression,
            subject_pose=subject_pose,
            subject_action=subject_action,
            location_type=location_type,
            location_detail=location_detail,
            time_of_day=time_of_day,
            weather_light=weather_light,
            scene_props=scene_props,
            auto_extra_detail=auto_extra_detail,
            adult_tone=adult_tone,
            adult_wardrobe=adult_wardrobe,
            adult_exposure_level=adult_exposure_level,
            adult_pose_style=adult_pose_style,
            adult_scene_privacy=effective_adult_scene_privacy,
            adult_scene_mood=adult_scene_mood,
            adult_lighting=adult_lighting,
            adult_scene_props=adult_scene_props,
            adult_body_focus=adult_body_focus,
            custom_text=custom_text,
        )
    if family == "tag":
        return _standalone_build_scene_tags(**kwargs)
    return _standalone_build_scene_natural(model_profile=model_profile, **kwargs)

def _resolve_prompt_source_mode(prompt_source_mode: str, external_positive_in: Any) -> str:
    mode = _safe_ui_value(prompt_source_mode, "prompt_source_mode")
    if mode == "Style Only":
        return "style_only"
    if mode == "External Prompt Composer":
        return "external"
    if mode == "Standalone Scene Builder":
        return "standalone"
    return "external" if _clean_text(external_positive_in) else "standalone"


def _standalone_should_render_base_only(
    *,
    mood_family: str,
    style_dna: str,
    scene_framing: str,
    lens_preset: str,
    adult_tone: str,
    adult_wardrobe: str,
    adult_exposure_level: str,
    adult_pose_style: str,
    adult_framing_bias: str,
    auto_extra_detail: str,
    adult_scene_mood: str = "auto",
    adult_lighting: str = "auto",
    adult_scene_props: str = "auto",
    adult_body_focus: str = "auto",
    custom_text: str = "",
    kind: str,
) -> bool:
    if kind in {"environment", "product"}:
        # Background/product modes intentionally ignore person/adult-only controls.
        # Keep base-only behavior stable when those hidden/irrelevant controls still
        # carry saved values from another mode.
        adult_tone = "default"
        adult_wardrobe = "auto"
        adult_exposure_level = "auto"
        adult_pose_style = "auto"
        adult_framing_bias = "auto"
        adult_scene_mood = "auto"
        adult_lighting = "auto"
        adult_scene_props = "auto"
        adult_body_focus = "auto"
    return (
        _safe_ui_value(mood_family, "mood_family") == "Default / None"
        and _safe_ui_value(style_dna, "style_dna") in {"Auto by Mood", "Neutral / Minimal Carryover"}
        and _safe_ui_value(scene_framing, "scene_framing") == "auto"
        and _safe_ui_value(lens_preset, "lens_preset") == "auto"
        and _safe_ui_value(adult_tone, "adult_tone") in {"default", "safe"}
        and _safe_ui_value(adult_wardrobe, "adult_wardrobe") == "auto"
        and _safe_ui_value(adult_exposure_level, "adult_exposure_level") == "auto"
        and _safe_ui_value(adult_pose_style, "adult_pose_style") == "auto"
        and _safe_ui_value(adult_framing_bias, "adult_framing_bias") == "auto"
        and _safe_ui_value(adult_scene_mood, "adult_scene_mood") == "auto"
        and _safe_ui_value(adult_lighting, "adult_lighting") == "auto"
        and _safe_ui_value(adult_scene_props, "adult_scene_props") == "auto"
        and _safe_ui_value(adult_body_focus, "adult_body_focus") == "auto"
        and not _clean_text(custom_text)
    )

def _environment_safe_scene_framing_terms(scene_terms: List[str]) -> List[str]:
    """Convert portrait/body-centric framing wording into environment-safe terms.

    Background-only prompts must not carry subject/body/figure instructions such
    as "full figure visible".  Keep the user's broad composition intent, but
    express it as spatial/environment framing.
    """
    replacements = {
        "wide framing": "wide environmental framing",
        "subject smaller within the frame": "broad view of the setting",
        "subject small within the frame": "broad view of the setting",
        "full figure visible": "full spatial layout visible",
        "space around the entire body": "generous surrounding space",
        "full-body framing": "full environmental framing",
        "full-body framing with extra space": "wide environmental framing with extra space",
        "full-length composition": "full spatial composition",
        "entire figure visible": "complete environment visible",
        "entire figure fully visible": "complete environment fully visible",
        "space above the head and below the feet": "balanced space above and below the setting",
        "feet visible in frame": "floor area visible in frame",
        "overhead portrait view": "overhead environmental view",
        "downward portrait framing": "downward environmental framing",
        "top-down portrait perspective": "top-down spatial perspective",
        "high-angle portrait": "high-angle environmental view",
        "gentle downward framing": "gentle downward environmental framing",
        "environmental portrait": "environmental scene composition",
        "subject integrated with surroundings": "setting integrated with surroundings",
        "seated full body shot": "seated-area environmental view",
        "full figure seated framing": "full seating-area framing",
    }
    out: List[str] = []
    for term in scene_terms or []:
        cleaned = _clean_text(term)
        if not cleaned:
            continue
        mapped = replacements.get(cleaned.lower(), cleaned)
        mapped = re.sub(r"\bportrait\b", "environmental view", mapped, flags=re.I)
        mapped = re.sub(r"\bsubject\b", "setting", mapped, flags=re.I)
        mapped = re.sub(r"\bfigure\b", "environment", mapped, flags=re.I)
        mapped = re.sub(r"\bbody\b", "environment", mapped, flags=re.I)
        mapped = re.sub(r"\bhead\b", "upper setting", mapped, flags=re.I)
        mapped = re.sub(r"\bfeet\b", "floor area", mapped, flags=re.I)
        mapped = _clean_text(mapped)
        if mapped:
            out.append(mapped)
    return _unique(out)


def _environment_safe_camera_terms(camera_terms: List[str]) -> List[str]:
    """Convert subject-shot camera wording into background-safe camera wording."""
    replacements = {
        "medium shot": "medium environmental view",
        "close framing": "close environmental detail framing",
        "tight portrait framing": "tight environmental detail framing",
        "portrait framing": "environmental view framing",
        "anamorphic widescreen character": "anamorphic widescreen environment",
        "product-display close framing": "display-scene close framing",
        "controlled studio depth": "controlled setting depth",
        "soft background separation": "soft environmental depth separation",
        "low-angle shot": "low-angle environmental view",
        "natural full-body perspective": "natural spatial perspective",
    }
    out: List[str] = []
    for term in camera_terms or []:
        cleaned = _clean_text(term)
        if not cleaned:
            continue
        mapped = replacements.get(cleaned.lower(), cleaned)
        mapped = re.sub(r"\bportrait\b", "environmental view", mapped, flags=re.I)
        mapped = re.sub(r"\bcharacter\b", "environment", mapped, flags=re.I)
        mapped = _clean_text(mapped)
        if mapped:
            out.append(mapped)
    return _unique(out)


def _krea2_compact_long_prompt(text: Any, *, threshold: int = 1650, soft_margin: int = 80) -> str:
    """Krea2-only soft length guard.

    This is not a hard prompt trimmer.  Krea2 benefits from concrete visual
    detail, and user-provided custom/external sentences must not be removed
    just because they contain words such as "keep", "clear", or "well".

    When the prompt is already long, this guard only performs non-destructive
    cleanup of generated scaffolding: compact overlong generated list-style
    sentences, shorten known auto-anchor phrases, and collapse a few exact
    duplicated auto reminders.  It may still return a long prompt if the
    length comes from unique user details.
    """
    s = _clean_text(text)
    # Avoid a one-character cliff: tiny wording fixes such as a/an changes must
    # not suddenly remove many style or mood details.  The margin keeps prompts
    # near the threshold intact and reserves stronger compaction for genuinely
    # overlong Krea2 prompts.
    if len(s) <= threshold + max(0, int(soft_margin)):
        return s

    def compact_list_phrase(phrase: str, max_items: int) -> str:
        phrase = _clean_text(phrase)
        if not phrase:
            return ""
        items = [_clean_text(x) for x in re.split(r",\s*", phrase) if _clean_text(x)]
        if len(items) <= max_items:
            return phrase
        return ", ".join(items[:max_items])

    def compact_known_auto_anchor(sentence: str) -> str:
        sentence = _clean_text(sentence)
        replacements = [
            (
                r"\bKeep the same subject, outfit, pose, setting, composition, and listed objects as closely as possible\b",
                "Keep subject, outfit, pose, setting, composition, and listed objects recognizable",
            ),
            (
                r"\bKeep the same subject, outfit, pose, setting, composition, and listed objects recognizable\b",
                "Keep subject, outfit, pose, setting, composition, and listed objects recognizable",
            ),
            (
                r"\bKeep the same subject, outfit, pose, setting, composition, and listed objects\b",
                "Keep subject, outfit, pose, setting, composition, and listed objects",
            ),
            (
                r"\bUse the same subject, visible styling, pose, setting, composition, and important objects as anchors\b",
                "Use subject, styling, pose, setting, composition, and important objects as anchors",
            ),
            (
                r"\bUse visible subject count, facial identity, main outfit idea, pose, setting, and important scene objects as anchors\b",
                "Use subject count, facial identity, outfit, pose, setting, and key scene objects as anchors",
            ),
            (
                r"\bUse visible subject count, facial identity, outfit idea, pose, setting, and key scene details as anchors\b",
                "Use subject count, facial identity, outfit, pose, setting, and key scene details as anchors",
            ),
        ]
        for pattern, repl in replacements:
            sentence = re.sub(pattern, repl, sentence, flags=re.I)
        return sentence

    def compact_sentence(sentence: str) -> str:
        sentence = compact_known_auto_anchor(sentence)
        if len(sentence) <= 260:
            return sentence
        prefix = "Describe the scene with "
        if sentence.startswith(prefix):
            body = sentence[len(prefix):].rstrip(".")
            mood = ""
            if " while keeping a mood of " in body:
                body, mood = body.split(" while keeping a mood of ", 1)
            body = compact_list_phrase(body, 6)
            if mood:
                mood = compact_list_phrase(mood, 2)
                return _sentence(f"{prefix}{body}, while keeping a mood of {mood}")
            return _sentence(f"{prefix}{body}")
        prefix = "Describe the framing with "
        if sentence.startswith(prefix):
            body = sentence[len(prefix):].rstrip(".")
            # These suffixes are generated by the Krea2 framing helper; keep them
            # as semantic suffixes instead of letting comma-list compaction drop
            # pieces such as spatial depth.
            framing_suffix = ""
            suffix_match = re.search(
                r",\s*including\s+((?:body direction, subject scale|scene orientation, environmental scale|object orientation, product scale),\s+and\s+spatial depth)$",
                body,
                flags=re.I,
            )
            if suffix_match:
                framing_suffix = suffix_match.group(1)
                body = body[:suffix_match.start()]
            body = re.sub(r",\s*(?:keeping|with)\s+[^,.]*(?:readable|clear)[^,.]*$", "", body, flags=re.I)
            compacted_body = compact_list_phrase(body, 4)
            if framing_suffix:
                return _sentence(f"{prefix}{compacted_body}, including {framing_suffix}")
            return _sentence(f"{prefix}{compacted_body}")
        return sentence

    pieces = [x for x in re.split(r"(?<=[.!?])\s+", s) if _clean_text(x)]
    compacted = [compact_sentence(x) for x in pieces]

    # Collapse only exact duplicate auto-generated reminders that carry no
    # unique subject/scene detail.  Do not dedupe arbitrary user sentences.
    auto_repeat_once = {
        "Do not satisfy the style with plain raindrops alone.",
    }
    seen_auto = set()
    kept = []
    for sentence in compacted:
        clean_sentence = _clean_text(sentence)
        if clean_sentence in auto_repeat_once:
            key = clean_sentence.lower()
            if key in seen_auto:
                continue
            seen_auto.add(key)
        kept.append(sentence)

    s = " ".join(kept)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _krea2_protect_user_input_segments(text: Any, *, custom_text: Any = "", external_text: Any = "", external_location: str = "") -> Tuple[str, List[Tuple[str, str]]]:
    """Temporarily hide user-authored prompt text from Krea2 cleanup passes.

    Krea2 context/monochrome/length postprocessors rewrite generated scaffolding
    such as style anchor, framing, lighting, and product/environment wording.  They
    must not silently rewrite custom_text or an external prompt, because the user
    can naturally type phrases that resemble internal generated cues.
    """
    out = str(text or "")
    protected_pairs: List[Tuple[str, str]] = []
    used_segments = set()

    def make_token(index: int) -> str:
        return f"__UPS_KREA2_USER_TEXT_PROTECTED_{index}__"

    def protection_replacement(seg: str, token: str) -> Tuple[str, str]:
        """Hide user text without erasing sentence-boundary punctuation.

        Krea2 cleanup passes split generated text into sentences.  If a protected
        custom/external sentence consumes its terminal punctuation, the neighboring
        generated sentence can merge with the token and bypass sentence-scoped
        cleanup.  Keep final .!? outside the token while mapping the visible
        token+punctuation back to the exact original user segment.
        """
        m = re.search(r"([.!?]+)$", seg)
        if not m:
            return token, token
        punct = m.group(1)
        return token + punct, token + punct

    def protect_exact(segment: str, *, occurrence: str = "all") -> None:
        nonlocal out
        seg = _clean_text(segment)
        if not seg or seg in used_segments or seg not in out:
            return
        used_segments.add(seg)
        token = make_token(len(protected_pairs))
        replacement, restore_key = protection_replacement(seg, token)
        if occurrence == "first":
            idx = out.find(seg)
            if idx < 0:
                return
            out = out[:idx] + replacement + out[idx + len(seg):]
        elif occurrence == "last":
            idx = out.rfind(seg)
            if idx < 0:
                return
            out = out[:idx] + replacement + out[idx + len(seg):]
        else:
            out = out.replace(seg, replacement)
        protected_pairs.append((restore_key, seg))

    custom_clean = _clean_text(custom_text)
    custom_note = _external_custom_note(custom_clean)
    for custom_segment in (custom_note, custom_clean):
        if custom_segment:
            # Custom notes are rendered as standalone sentences inside the generated
            # natural insert.  Protect the full sentence form first so short user
            # phrases such as "elegant posture" do not also shield generated style
            # scaffolding that happens to contain the same words.
            protect_exact(_sentence(custom_segment), occurrence="all")
    for custom_segment in (custom_note, custom_clean):
        if custom_segment and len(custom_segment) >= 24:
            protect_exact(custom_segment, occurrence="all")

    external_clean = _clean_text(external_text)
    if external_clean and external_location in {"first", "last"}:
        # External prompts appear as one prompt block: first in append mode, last
        # in style-first/reference mode.  Protect only that rendered occurrence;
        # otherwise a very short external phrase could accidentally protect an
        # unrelated generated style phrase.
        protect_exact(external_clean, occurrence=external_location)
        if len(external_clean) >= 24:
            protect_exact(_sentence(external_clean), occurrence=external_location)

    return out, protected_pairs


def _krea2_restore_user_input_segments(text: Any, protected_pairs: List[Tuple[str, str]]) -> str:
    out = str(text or "")
    for token, segment in reversed(protected_pairs):
        out = out.replace(token, segment)
    return out

KREA2_RELAX_MARKER_RE = re.compile(
    r"__UPS_KREA2_RELAX_BEGIN_\d+__(.*?)__UPS_KREA2_RELAX_END_\d+__",
    re.DOTALL,
)


def _krea2_unwrap_relax_markers(text: Any) -> str:
    return KREA2_RELAX_MARKER_RE.sub(lambda m: m.group(1), str(text or ""))


def _krea2_cleanup_generated_handrendered_residue(text: Any) -> str:
    """Clean only Krea2 non-photo residue actually created by cleanup rules.

    The external prompt may already contain internal-looking phrases typed by the
    user.  Therefore this function only rewrites phrases wrapped by
    _apply_style_conflict_replacements_tracked(), i.e. text that
    _relax_style_conflicting_external_prompt() generated during the current pass.
    Unmarked identical wording is treated as user-authored and preserved.
    """
    out = str(text or "")
    marked_quality = (
        r"__UPS_KREA2_RELAX_BEGIN_\d+__clear\s+hand-rendered\s+subject\s+quality"
        r"__UPS_KREA2_RELAX_END_\d+__"
    )
    marked_edges = (
        r"__UPS_KREA2_RELAX_BEGIN_\d+__clear\s+hand-rendered\s+edges"
        r"__UPS_KREA2_RELAX_END_\d+__"
    )
    def collapse_marked_plain_duplicate(current: str, marked_pattern: str, plain_pattern: str) -> str:
        """Remove only the generated side of an adjacent exact duplicate.

        A user can type the same phrase that style_conflict_cleanup may generate.
        When a marked generated phrase lands directly next to an identical
        unmarked user phrase, keep the unmarked phrase and drop the marked one.
        This runs before marker unwrapping so it never performs broad n-gram
        cleanup on arbitrary user text.
        """
        separator = r"\s*(?:,\s*(?:and\s+)?|\band\b\s+|\bwith\b\s+)"
        plain_group = f"({plain_pattern})"
        current = re.sub(
            rf"{marked_pattern}{separator}{plain_group}",
            r"\1",
            current,
            flags=re.I,
        )
        current = re.sub(
            rf"{plain_group}{separator}{marked_pattern}",
            r"\1",
            current,
            flags=re.I,
        )
        return current

    plain_quality = r"clear\s+hand-rendered\s+subject\s+quality"
    plain_edges = r"clear\s+hand-rendered\s+edges"
    out = collapse_marked_plain_duplicate(out, marked_quality, plain_quality)
    out = collapse_marked_plain_duplicate(out, marked_edges, plain_edges)

    marked_quality_group = f"({marked_quality})"
    marked_edges_group = f"({marked_edges})"
    out = re.sub(
        rf"{marked_quality_group}(?:\s*(?:,|and|with)\s*{marked_quality})+",
        r"\1",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"{marked_edges_group}(?:\s*(?:,|and|with)\s*{marked_edges})+",
        r"\1",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b(?:photorealistic|photo[-\s]?realistic|photoreal|photographic|ultra[-\s]?realistic|hyper[-\s]?realistic)\s+(?={marked_quality}\b)",
        "",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\brealistic\s+camera\s+{marked_quality}\b",
        "hand-rendered spatial-depth treatment",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b(cinematic\s+)?realistic\s+{marked_quality}\s+(?:photo|photograph)\s+of\b",
        r"\1hand-rendered depiction of",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b(cinematic\s+)?realistic\s+{marked_quality}\b",
        r"\1clear hand-rendered",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\bcinematic\s+{marked_quality}\s+(?:photo|photograph)\s+of\b",
        "cinematic hand-rendered depiction of",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\bcinematic\s+{marked_quality}\b",
        "cinematic clear hand-rendered",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b{marked_quality}\s+(?=(?:close-up|portrait|image|depiction|scene|shot)\b)",
        "clear hand-rendered ",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b{marked_quality}\s+of\b",
        "clear hand-rendered subject depiction of",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b{marked_quality}\s+(?:photo|photograph)\s+of\b",
        "clear hand-rendered subject depiction of",
        out,
        flags=re.I,
    )
    out = re.sub(
        rf"\b{marked_edges}\s+(?=(?:portrait|image|depiction)\s+of\b)",
        "clear hand-rendered ",
        out,
        flags=re.I,
    )
    return _krea2_unwrap_relax_markers(out)

def _postprocess_krea2_context_positive(positive: Any, kind: str) -> str:
    """Krea2-only cleanup for standalone background/product prompts.

    Keep this separate from the shared standalone postprocess so Z-Image, Qwen,
    Flux, and tag/mixed profiles remain byte-stable.
    """
    text = _krea2_cleanup_generated_handrendered_residue(positive)
    if kind == "environment":
        text = re.sub(
            r"\bUse the same environment,\s*environmental appearance,\s*environmental detail,\s*setting,\s*composition,\s*and important objects as anchors\.",
            "Use the same setting, spatial layout, atmosphere, composition, and important environmental details as anchors.",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"Describe the framing with ([^.]+?), including body direction, subject scale, and spatial depth\.",
            r"Describe the framing with \1, including scene orientation, environmental scale, and spatial depth.",
            text,
            flags=re.I,
        )
        replacements = [
            (r"Keep the core subject, environmental detail, and scene idea\.", "Keep the core setting, spatial layout, and scene idea."),
            (r"Keep the core subject, pose, and scene idea\.", "Keep the core setting, spatial layout, and scene idea."),
            (r"Keep the core subject and scene idea\.", "Keep the core setting and scene idea."),
            (r"controlled beauty lighting", "controlled studio scene lighting"),
            (r"elegant beauty-editorial posture", "elegant spatial arrangement"),
            (r"elegant posture", "elegant spatial arrangement"),
        ]
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text, flags=re.I)
    elif kind == "product":
        text = re.sub(
            r"\bUse the same product,\s*material appearance,\s*product arrangement,\s*setting,\s*composition,\s*and important objects as anchors\.",
            "Use the same product identity, material, arrangement, setting, composition, and important scene details as anchors.",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"Describe the framing with ([^.]+?), including body direction, subject scale, and spatial depth\.",
            r"Describe the framing with \1, including object orientation, product scale, and spatial depth.",
            text,
            flags=re.I,
        )
        replacements = [
            (r"Keep the core subject, product arrangement, and scene idea\.", "Keep the core product identity, material appearance, arrangement, and scene idea."),
            (r"Keep the core subject, pose, and scene idea\.", "Keep the core product identity, material appearance, arrangement, and scene idea."),
            (r"Keep the core subject and scene idea\.", "Keep the core product and scene idea."),
            (r"controlled beauty lighting", "controlled product studio lighting"),
            (r"elegant beauty-editorial posture", "elegant product arrangement"),
            (r"elegant posture", "elegant product arrangement"),
        ]
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text, flags=re.I)
    text = _dedupe_classical_glamour_context_echo(text, kind)
    return _clean_text(text)


def _postprocess_standalone_positive(positive: str, kind: str, protected_text: str = "") -> str:
    text = str(positive or "")
    protected = _clean_text(protected_text)
    protected_token = "__UPS_PROTECTED_CUSTOM_TEXT__"
    has_protected = False
    if protected and protected in text:
        text = text.replace(protected, protected_token)
        has_protected = True
    text = re.sub(r"\badult adult\b", "adult", text, flags=re.I)
    if kind == "environment":
        text = re.sub(r"subject small within the frame", "wide environmental space", text, flags=re.I)
        replacements = [
            ("detailed subject", "detailed environment"),
            ("clear subject", "clear environment"),
            ("coherent image, well-defined scene", "coherent environment, well-defined scene"),
            ("Keep the original subject, pose, outfit, setting, scene layout, and listed objects recognizable.", "Keep the original setting, spatial layout, atmosphere, and environmental details recognizable."),
            ("Preserve: subject identity, clothing, pose, setting, composition, and listed objects in a recognizable way.", "Preserve: setting, spatial layout, atmosphere, composition, and environmental details in a recognizable way."),
            ("Use upper body shot, upper body framing.", "Use wide environmental framing."),
            ("Use waist-up framing.", "Use wide environmental framing."),
            ("Use wide shot, subject small within the frame.", "Use wide environmental shot with generous surrounding space."),
            ("Use 50mm lens, medium shot, and natural perspective for visual framing.", "Use wide environmental composition and natural spatial perspective."),
            ("Use 50mm lens and medium shot for visual framing.", "Use 50mm lens and medium environmental view for visual framing."),
            ("Use medium shot for visual framing.", "Use medium environmental view for visual framing."),
        ]
        for a, b in replacements:
            text = text.replace(a, b)
        text = re.sub(r"\bvisible styling\b", "environmental appearance", text, flags=re.I)
        text = re.sub(r"\b(outfit|clothing|pose)\b", "environmental detail", text)
        text = re.sub(r"\bKeep the same subject,\s*environmental detail,\s*setting,\s*composition,\s*and listed objects\.",
                      "Keep the same setting, spatial layout, atmosphere, composition, and listed environmental details.", text, flags=re.I)
        text = re.sub(r"\bPreserve:\s*subject identity,\s*environmental detail,\s*setting,\s*composition,\s*and listed objects\.",
                      "Preserve: setting identity, spatial layout, atmosphere, composition, and listed environmental details.", text, flags=re.I)
        text = re.sub(r"\bKeep the original subject,\s*environmental detail,\s*setting,\s*scene layout,\s*and listed objects unchanged\.",
                      "Keep the original setting, spatial layout, atmosphere, scene layout, and listed environmental details unchanged.", text, flags=re.I)
        text = re.sub(r"\bsame subject\b", "same environment", text, flags=re.I)
        text = re.sub(r"\bsubject identity\b", "setting identity", text, flags=re.I)
        text = re.sub(r"\boriginal subject\b", "original setting", text, flags=re.I)
        text = re.sub(
            r"(?:Preserve|Keep)(?: the)? visible subject count,\s*(?:core )?facial identity,\s*main environmental detail idea,\s*environmental detail,\s*setting,\s*(?:window,\s*)?and important (?:indoor and outdoor )?scene (?:details|objects)\.",
            "Preserve the setting, spatial layout, atmosphere, composition, and important environmental details.",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"Preserve: visible subject count,\s*(?:core )?facial identity,\s*main environmental detail idea,\s*environmental detail,\s*setting,\s*(?:window,\s*)?and important (?:indoor and outdoor )?scene (?:details|objects)\.",
            "Preserve: setting, spatial layout, atmosphere, composition, and important environmental details.",
            text,
            flags=re.I,
        )
        text = re.sub(r"Let the chibi style clearly restyle the people while keeping the surrounding scene readable\.", "Let the chibi style clearly restyle the empty environment while keeping the surrounding scene readable.", text, flags=re.I)
        text = re.sub(r"Restyle the people in a chibi illustration style while keeping the surrounding scene readable\.", "Restyle the empty environment in a chibi illustration style while keeping the surrounding scene readable.", text, flags=re.I)
        text = re.sub(r"Restyle every visible person [^.]+\.\s*", "Restyle the empty environment with the selected stylized visual language. ", text, flags=re.I)
        text = re.sub(r"with slightly oversized heads, compact bodies, simplified facial features, and short simplified limbs when visible", "with rounded simplified forms, cute scale, and playful environmental shapes", text, flags=re.I)
        text = re.sub(
            r"Keep the original subject,\s*environmental detail,\s*(?:environmental detail,\s*)?setting,\s*scene layout,\s*and listed objects as close as possible to the source prompt\.",
            "Keep the original setting, spatial layout, atmosphere, and environmental details as close as possible to the source prompt.",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"Keep the original subject,\s*environmental detail,\s*(?:environmental detail,\s*)?setting,\s*scene layout,\s*and listed objects recognizable\.",
            "Keep the original setting, spatial layout, atmosphere, and environmental details recognizable.",
            text,
            flags=re.I,
        )
        text = re.sub(r"environmental detail or material", "environmental detail", text, flags=re.I)
        text = re.sub(r"environmental detail or arrangement", "spatial arrangement", text, flags=re.I)
        text = re.sub(r"environmental detail,\s*environmental detail", "environmental detail", text, flags=re.I)
        text = re.sub(r"\b(facial identity|facial features)\b", "environmental features", text, flags=re.I)
        text = re.sub(r"Keep the presentation in an? [^.]+ adult [^.]+ direction\.\s*", "", text, flags=re.I)
        env_replacements = [
            (r"cute chibi character illustration", "cute simplified environment illustration"),
            (r"chibi super-deformed character style", "cute simplified environment style"),
            (r"large-head small-body proportions", "rounded playful environmental proportions"),
            (r"super-deformed character composition", "playful simplified scene composition"),
            (r"oversized head", "rounded playful forms"),
            (r"tiny compact body", "compact simplified forms"),
            (r"short simplified limbs when visible", "simple rounded environmental shapes"),
            (r"super-deformed chibi proportions", "cute simplified scene proportions"),
            (r"big expressive eyes", "expressive rounded details"),
            (r"soft rosy cheeks", "soft cheerful accents"),
            (r"toy-like character staging", "toy-like environmental staging"),
            (r"collectible figure presentation", "small display-scene presentation"),
            (r"stylized 3D collectible figure render", "stylized 3D display-scene render"),
            (r"collectible toy palette", "clean resin model palette"),
            (r"painted figure colors", "painted model-set colors"),
            (r"small figure centered layout", "centered small-scale scene layout"),
        ]
        for a, b in env_replacements:
            text = re.sub(a, b, text, flags=re.I)
        text = re.sub(r"Render the subject as a stylized 3D collectible figure with toy-like material, simplified form, and clean display lighting\.", "Render the empty environment as a stylized 3D display scene with toy-like material, simplified forms, and clean display lighting.", text, flags=re.I)
        text = re.sub(r"Preserve the core subject, pose, and scene idea\.", "Preserve the core setting, spatial layout, and scene idea.", text, flags=re.I)
        text = re.sub(r"Preserve the core subject and scene idea\.", "Preserve the core setting and scene idea.", text, flags=re.I)
        text = re.sub(r"Preserve: core subject, pose, and scene idea\.", "Preserve: core setting, spatial layout, and scene idea.", text, flags=re.I)
        text = re.sub(r"Preserve: core subject and scene idea\.", "Preserve: core setting and scene idea.", text, flags=re.I)
        text = re.sub(r"with the main subject, props, furniture, and environment all appearing as miniature scale-model elements", "with the props, furniture, and environment all appearing as miniature scale-model elements", text, flags=re.I)
        text = re.sub(r"the main subject appears as a miniature figure", "the key scene elements appear as miniature objects", text, flags=re.I)
        text = re.sub(r"miniature figure", "miniature scene element", text, flags=re.I)
        text = re.sub(r"miniature scene element subject", "miniature scene element", text, flags=re.I)
        text = re.sub(r"stylized 3d figure", "stylized 3d display object", text, flags=re.I)
        text = re.sub(r"3d anime figure", "3d display object", text, flags=re.I)
        text = re.sub(r"anime figurine", "anime-style display object", text, flags=re.I)
        text = re.sub(r"PVC figure", "PVC display object", text, flags=re.I)
        text = re.sub(r"collectible figures", "display objects", text, flags=re.I)
        text = re.sub(r"collectible figure", "display object", text, flags=re.I)
        text = re.sub(r"painted figure tones", "painted model-set tones", text, flags=re.I)
        text = re.sub(r"painted figure colors", "painted model-set colors", text, flags=re.I)
        text = re.sub(r"classic old-Hollywood studio glamour portrait", "classic old-Hollywood studio glamour interior scene", text, flags=re.I)
        text = re.sub(r"controlled portrait lighting", "controlled studio scene lighting", text, flags=re.I)
        text = re.sub(r"vintage portrait", "vintage studio scene", text, flags=re.I)
        text = re.sub(r"glamour portrait", "glamour studio scene", text, flags=re.I)
    elif kind == "product":
        text = re.sub(r"tight portrait framing", "tight product close-up framing", text, flags=re.I)
        text = re.sub(r"portrait framing", "product close-up framing", text, flags=re.I)
        replacements = [
            ("detailed subject", "detailed product"),
            ("clear subject", "clear product detail"),
            ("Keep the original subject, pose, outfit, setting, scene layout, and listed objects recognizable.", "Keep the original product, material, setting, composition, scene layout, and listed objects recognizable."),
            ("Preserve: subject identity, clothing, pose, setting, composition, and listed objects in a recognizable way.", "Preserve: product identity, material, setting, composition, and listed objects in a recognizable way."),
            ("Use upper body shot, upper body framing.", "Use product close-up framing."),
            ("Use waist-up framing.", "Use product close-up framing."),
            ("Use close-up, tight portrait framing.", "Use product close-up framing."),
            ("tight portrait framing", "tight product close-up framing"),
            ("Use 50mm lens, medium shot, and natural perspective for visual framing.", "Use product-focused close-up composition and natural perspective."),
            ("Use 50mm lens and medium shot for visual framing.", "Use product-focused close-up composition and natural perspective for visual framing."),
            ("Use medium shot for visual framing.", "Use product-focused close-up composition for visual framing."),
        ]
        for a, b in replacements:
            text = text.replace(a, b)
        text = re.sub(r"\bvisible styling\b", "material appearance", text, flags=re.I)
        text = re.sub(r"\b(outfit|clothing|pose)\b", "product arrangement", text)
        text = re.sub(r"product arrangement or material", "material", text, flags=re.I)
        text = re.sub(r"product arrangement or arrangement", "arrangement", text, flags=re.I)
        text = re.sub(
            r"(?:Preserve|Keep)(?: the)? visible subject count,\s*(?:core )?facial identity,\s*main product arrangement idea,\s*product arrangement,\s*setting,\s*(?:window,\s*)?and important (?:indoor and outdoor )?scene (?:details|objects)\.",
            "Preserve the product identity, material, arrangement, setting, composition, and important scene details.",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"Preserve: visible subject count,\s*(?:core )?facial identity,\s*main product arrangement idea,\s*product arrangement,\s*setting,\s*(?:window,\s*)?and important (?:indoor and outdoor )?scene (?:details|objects)\.",
            "Preserve: product identity, material, arrangement, setting, composition, and important scene details.",
            text,
            flags=re.I,
        )
        text = re.sub(r"Let the chibi style clearly restyle the people while keeping the surrounding scene readable\.", "Let the chibi style clearly restyle the product still life while keeping the product arrangement readable.", text, flags=re.I)
        text = re.sub(r"Restyle the people in a chibi illustration style while keeping the surrounding scene readable\.", "Restyle the product still life in a chibi illustration style while keeping the product arrangement readable.", text, flags=re.I)
        text = re.sub(r"Restyle every visible person [^.]+\.\s*", "Restyle the product still life with the selected stylized visual language. ", text, flags=re.I)
        text = re.sub(r"with slightly oversized heads, compact bodies, simplified facial features, and short simplified limbs when visible", "with rounded simplified product forms, cute scale, and playful product shapes", text, flags=re.I)
        text = re.sub(
            r"Keep the original subject,\s*product arrangement,\s*(?:product arrangement,\s*)?setting,\s*scene layout,\s*and listed objects as close as possible to the source prompt\.",
            "Keep the original product, material, arrangement, setting, scene layout, and listed objects as close as possible to the source prompt.",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"Keep the original subject,\s*product arrangement,\s*(?:product arrangement,\s*)?setting,\s*scene layout,\s*and listed objects recognizable\.",
            "Keep the original product, material, arrangement, setting, scene layout, and listed objects recognizable.",
            text,
            flags=re.I,
        )
        text = re.sub(r"\b(facial identity|facial features)\b", "product features", text, flags=re.I)
        text = re.sub(r"\bKeep the same subject,\s*product arrangement,\s*setting,\s*composition,\s*and listed objects\.",
                      "Keep the same product, material, arrangement, setting, composition, and listed objects.", text, flags=re.I)
        text = re.sub(r"\bsame subject\b", "same product", text, flags=re.I)
        text = re.sub(r"\bsubject identity\b", "product identity", text, flags=re.I)
        text = re.sub(r"\boriginal subject\b", "original product", text, flags=re.I)
        text = re.sub(r"Keep the presentation in an? [^.]+ adult [^.]+ direction\.\s*", "", text, flags=re.I)
        product_replacements = [
            (r"\bfigurine\b", "resin product"),
            (r"\bcollectible figure\b", "display object"),
            (r"cute chibi character illustration", "cute simplified product illustration"),
            (r"chibi super-deformed character style", "cute simplified product style"),
            (r"large-head small-body proportions", "rounded playful product proportions"),
            (r"super-deformed character composition", "playful simplified product composition"),
            (r"oversized head", "rounded playful product forms"),
            (r"tiny compact body", "compact simplified product forms"),
            (r"short simplified limbs when visible", "simple rounded product shapes"),
            (r"super-deformed chibi proportions", "cute simplified product proportions"),
            (r"big expressive eyes", "expressive rounded product details"),
            (r"soft rosy cheeks", "soft cheerful material accents"),
            (r"stylized 3D collectible figure render", "stylized 3D display-object render"),
            (r"collectible figure presentation", "display-object presentation"),
            (r"toy-like character staging", "product display staging"),
            (r"small figure centered layout", "centered product layout"),
            (r"painted figure colors", "painted material colors"),
            (r"collectible toy palette", "clean resin product palette"),
        ]
        for a, b in product_replacements:
            text = re.sub(a, b, text, flags=re.I)
        text = re.sub(r"Render the subject as a stylized 3D collectible figure with toy-like material, simplified form, and clean display lighting\.", "Render the product as a stylized 3D display object with toy-like material, simplified form, and clean display lighting.", text, flags=re.I)
        text = re.sub(r"Preserve the core subject, pose, and scene idea\.", "Preserve the core product identity, material appearance, arrangement, and scene idea.", text, flags=re.I)
        text = re.sub(r"Preserve the core subject and scene idea\.", "Preserve the core product and scene idea.", text, flags=re.I)
        text = re.sub(r"Preserve: core subject, pose, and scene idea\.", "Preserve: core product identity, material appearance, arrangement, and scene idea.", text, flags=re.I)
        text = re.sub(r"Preserve: core subject and scene idea\.", "Preserve: core product and scene idea.", text, flags=re.I)
        text = re.sub(r"with the main subject, props, furniture, and environment all appearing as miniature scale-model elements", "with the main product, props, furniture, and environment all appearing as miniature scale-model elements", text, flags=re.I)
        text = re.sub(r"the main subject appears as a miniature figure", "the main product appears as a miniature display object", text, flags=re.I)
        text = re.sub(r"miniature figure", "miniature display object", text, flags=re.I)
        text = re.sub(r"miniature display object subject", "miniature display object", text, flags=re.I)
        text = re.sub(r"classic old-Hollywood studio glamour portrait", "classic old-Hollywood studio glamour product presentation", text, flags=re.I)
        text = re.sub(r"controlled portrait lighting", "controlled product studio lighting", text, flags=re.I)
        text = re.sub(r"vintage portrait", "vintage studio product presentation", text, flags=re.I)
        text = re.sub(r"glamour portrait", "glamour product presentation", text, flags=re.I)
        text = re.sub(r"timeless glamour product presentation composition", "glamour product presentation", text, flags=re.I)
    text = re.sub(r"\bproduct,\s*product arrangement(?:,\s*product arrangement)?\b", "product, material, arrangement", text, flags=re.I)
    text = re.sub(r"\bmaterial,\s*arrangement,\s*product arrangement\b", "material, arrangement", text, flags=re.I)
    text = re.sub(r"\bproduct arrangement,\s*product arrangement\b", "product arrangement", text, flags=re.I)
    text = re.sub(
        r"Render the subject and scene as pixel art with visible square pixels and a limited palette\.\s*"
        r"Render the subject and scene as pixel art with visible square pixels, blocky edges, and a limited palette\.",
        "Render the subject and scene as pixel art with visible square pixels, blocky edges, and a limited palette.",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"Render the subject and scene as clear pixel art with visible square pixels and a limited palette\.\s*"
        r"Render the subject and scene as clear pixel art with visible square pixels, blocky edges, and a limited palette\.",
        "Render the subject and scene as clear pixel art with visible square pixels, blocky edges, and a limited palette.",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+", " ", text).strip()
    if has_protected:
        text = text.replace(protected_token, protected)
    return text


def _standalone_public_exposure_softened(location_type: str, adult_scene_privacy: str, adult_wardrobe: str, adult_exposure_level: str) -> bool:
    loc = _safe_ui_value(location_type, "location_type")
    privacy = _safe_ui_value(adult_scene_privacy, "adult_scene_privacy")
    wardrobe = _safe_ui_value(adult_wardrobe, "adult_wardrobe")
    exposure = _safe_ui_value(adult_exposure_level, "adult_exposure_level")
    if privacy != "auto":
        return False
    if loc not in _STANDALONE_PUBLIC_LOCATIONS:
        return False
    if wardrobe in {"nude", "topless", "lingerie", "lace lingerie set", "black lace lingerie", "satin lingerie", "strappy lingerie", "lace bralette set", "robe and lingerie", "sheer nightgown", "sheer robe", "transparent robe", "sheer bodysuit", "garter belt", "stockings and garter", "fishnet outfit", "wet shirt"}:
        return True
    if exposure in {"nude", "topless", "lingerie / underwear", "implied nude / covered", "sheet-covered nude"}:
        return True
    return False

def _negative_policy_for_standalone(negative: str, adult_tone: str, adult_wardrobe: str, adult_exposure_level: str, kind: str) -> str:
    text = str(negative or "")
    if kind in {"environment", "product"}:
        text = re.sub(r"\bunderage appearance,?\s*", "", text, flags=re.I)
        text = re.sub(r"\bchildish appearance,?\s*", "", text, flags=re.I)
    if _standalone_is_explicit_adult(adult_tone, adult_wardrobe, adult_exposure_level):
        # Keep minor/school/anatomy blockers, but do not negate the selected adult-only content itself.
        remove_terms = [
            "explicit sexual act",
            "explicit sexual action",
            "pornographic staging",
            "pornographic",
            "nude",
            "topless",
        ]
        parts = [p.strip() for p in re.split(r",\s*", text) if p.strip()]
        kept = []
        for p in parts:
            key = p.lower().strip()
            if key in remove_terms:
                continue
            kept.append(p)
        text = ", ".join(kept)
    return _clean_negative_text(text)



def _minimized_generated_negative(model_profile: str, adult_tone: str = "default", kind: str = "") -> str:
    """Return a deliberately light built-in negative prompt.

    The node is often used with turbo / low-CFG workflows where heavy built-in
    negatives either do nothing or can over-constrain non-turbo models. Keep the
    generated negative compact and low-impact, while still preserving a minimal
    underage/school-style safety guard for human subjects. User-provided external
    negative text is merged separately and remains untouched.
    """
    family = _model_family(model_profile)
    if str(kind or "") in {"environment", "product"}:
        return ""
    if family == "natural":
        base = ["underage appearance", "school uniform"]
        if _adult_tone_group(adult_tone) not in {"nsfw", "explicit"}:
            base.insert(1, "childish appearance")
        return _clean_negative_text(", ".join(base))
    base = ["underage", "schoolgirl", "school uniform"]
    if _adult_tone_group(adult_tone) not in {"nsfw", "explicit"}:
        base.insert(1, "childish")
    return _clean_negative_text(", ".join(base))


def _apply_model_quality_to_standalone_base(scene_text: str, model_profile: str, adult_tone: str = "default") -> str:
    """Attach model-profile quality tags to base standalone prompts for tag/mixed families.

    Standalone base-only mode intentionally skips style inserts, but tag-oriented
    models still benefit from their profile quality/source/rating prefix.
    Natural-language models keep the raw standalone sentence.
    """
    scene_text = _clean_text(scene_text)
    if not scene_text:
        return ""
    family = _model_family(model_profile)
    if family == "tag":
        return _join_unique_tags([_tag_quality_for_model(model_profile, adult_tone), scene_text])
    if family == "mixed":
        first, sep, rest = scene_text.partition(". ")
        tag_block = _join_unique_tags([_tag_quality_for_model(model_profile, adult_tone), first])
        return _join_mixed_prompt(tag_block, rest)
    return scene_text


class UltraPromptComposer:
    """Compact PromptComposer node.

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
                "prompt_source_mode": (_ui_options("prompt_source_mode", STANDALONE_OPTIONS["prompt_source_mode"]), {"default": "Auto"}),
                "builder_detail_mode": (_ui_options("builder_detail_mode", STANDALONE_OPTIONS["builder_detail_mode"]), {"default": "simple"}),
                "external_prompt_mode": (_ui_options("external_prompt_mode", [
                    "Append style after external prompt",
                    "Prepend style before external prompt",
                    "Output style only",
                ]), {"default": "Prepend style before external prompt"}),
                "subject_profile": (_ui_options("subject_profile", STANDALONE_OPTIONS["subject_profile"]), {"default": "auto"}),
                "subject_age": (_ui_options("subject_age", STANDALONE_OPTIONS["subject_age"]), {"default": "auto"}),
                "subject_appearance": (_ui_options("subject_appearance", STANDALONE_OPTIONS["subject_appearance"]), {"default": "auto"}),
                "subject_ethnicity": (_ui_options("subject_ethnicity", STANDALONE_OPTIONS["subject_ethnicity"]), {"default": "auto"}),
                "subject_hair": (_ui_options("subject_hair", STANDALONE_OPTIONS["subject_hair"]), {"default": "auto"}),
                "subject_outfit": (_ui_options("subject_outfit", STANDALONE_OPTIONS["subject_outfit"]), {"default": "auto"}),
                "subject_expression": (_ui_options("subject_expression", STANDALONE_OPTIONS["subject_expression"]), {"default": "auto"}),
                "subject_pose": (_ui_options("subject_pose", STANDALONE_OPTIONS["subject_pose"]), {"default": "auto"}),
                "subject_action": (_ui_options("subject_action", STANDALONE_OPTIONS["subject_action"]), {"default": "auto"}),
                "location_type": (_ui_options("location_type", STANDALONE_OPTIONS["location_type"]), {"default": "auto"}),
                "location_detail": (_ui_options("location_detail", STANDALONE_OPTIONS["location_detail"]), {"default": "auto"}),
                "time_of_day": (_ui_options("time_of_day", STANDALONE_OPTIONS["time_of_day"]), {"default": "auto"}),
                "weather_light": (_ui_options("weather_light", STANDALONE_OPTIONS["weather_light"]), {"default": "auto"}),
                "scene_props": (_ui_options("scene_props", STANDALONE_OPTIONS["scene_props"]), {"default": "auto"}),
                "auto_extra_detail": (_ui_options("auto_extra_detail", STANDALONE_OPTIONS["auto_extra_detail"]), {"default": "auto"}),
                "adult_menu_level": (_ui_options("adult_menu_level", STANDALONE_OPTIONS["adult_menu_level"]), {"default": "essential"}),
                "adult_exposure_level": (_ui_options("adult_exposure_level", STANDALONE_OPTIONS["adult_exposure_level"]), {"default": "auto"}),
                "adult_scene_privacy": (_ui_options("adult_scene_privacy", STANDALONE_OPTIONS["adult_scene_privacy"]), {"default": "auto"}),
                "adult_scene_mood": (_ui_options("adult_scene_mood", STANDALONE_OPTIONS["adult_scene_mood"]), {"default": "auto"}),
                "adult_pose_style": (_ui_options("adult_pose_style", STANDALONE_OPTIONS["adult_pose_style"]), {"default": "auto"}),
                "adult_lighting": (_ui_options("adult_lighting", STANDALONE_OPTIONS["adult_lighting"]), {"default": "auto"}),
                "adult_scene_props": (_ui_options("adult_scene_props", STANDALONE_OPTIONS["adult_scene_props"]), {"default": "auto"}),
                "adult_body_focus": (_ui_options("adult_body_focus", STANDALONE_OPTIONS["adult_body_focus"]), {"default": "auto"}),
                "adult_framing_bias": (_ui_options("adult_framing_bias", STANDALONE_OPTIONS["adult_framing_bias"]), {"default": "auto"}),
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
            "external_prompt_mode", "prompt_source_mode", "builder_detail_mode",
            "subject_profile", "subject_age", "subject_appearance", "subject_ethnicity", "subject_hair", "subject_outfit", "subject_expression",
            "subject_pose", "subject_action", "location_type", "location_detail", "time_of_day",
            "weather_light", "scene_props", "auto_extra_detail", "adult_menu_level",
            "adult_exposure_level", "adult_scene_privacy", "adult_scene_mood",
            "adult_pose_style", "adult_lighting", "adult_scene_props", "adult_body_focus",
            "adult_framing_bias",
            "seed", "custom_text",
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
        prompt_source_mode: str = "Auto",
        builder_detail_mode: str = "simple",
        external_prompt_mode: str = "Prepend style before external prompt",
        subject_profile: str = "auto",
        subject_age: str = "auto",
        subject_appearance: str = "auto",
        subject_ethnicity: str = "auto",
        subject_hair: str = "auto",
        subject_outfit: str = "auto",
        subject_expression: str = "auto",
        subject_pose: str = "auto",
        subject_action: str = "auto",
        location_type: str = "auto",
        location_detail: str = "auto",
        time_of_day: str = "auto",
        weather_light: str = "auto",
        scene_props: str = "auto",
        auto_extra_detail: str = "auto",
        adult_menu_level: str = "essential",
        adult_exposure_level: str = "auto",
        adult_scene_privacy: str = "auto",
        adult_scene_mood: str = "auto",
        adult_pose_style: str = "auto",
        adult_lighting: str = "auto",
        adult_scene_props: str = "auto",
        adult_body_focus: str = "auto",
        adult_framing_bias: str = "auto",
        seed: int = 0,
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
        prompt_source_mode = _safe_ui_value(prompt_source_mode, "prompt_source_mode")
        builder_detail_mode = _safe_ui_value(builder_detail_mode, "builder_detail_mode")
        subject_profile = _safe_ui_value(subject_profile, "subject_profile")
        subject_age = _safe_ui_value(subject_age, "subject_age")
        subject_appearance = _safe_ui_value(subject_appearance, "subject_appearance")
        subject_ethnicity = _safe_ui_value(subject_ethnicity, "subject_ethnicity")
        subject_hair = _safe_ui_value(subject_hair, "subject_hair")
        subject_outfit = _safe_ui_value(subject_outfit, "subject_outfit")
        subject_expression = _safe_ui_value(subject_expression, "subject_expression")
        subject_pose = _safe_ui_value(subject_pose, "subject_pose")
        subject_action = _safe_ui_value(subject_action, "subject_action")
        location_type = _safe_ui_value(location_type, "location_type")
        location_detail = _safe_ui_value(location_detail, "location_detail")
        time_of_day = _safe_ui_value(time_of_day, "time_of_day")
        weather_light = _safe_ui_value(weather_light, "weather_light")
        scene_props = _safe_ui_value(scene_props, "scene_props")
        auto_extra_detail = _safe_ui_value(auto_extra_detail, "auto_extra_detail")
        adult_menu_level = _safe_ui_value(adult_menu_level, "adult_menu_level")
        adult_exposure_level = _safe_ui_value(adult_exposure_level, "adult_exposure_level")
        adult_scene_privacy = _safe_ui_value(adult_scene_privacy, "adult_scene_privacy")
        adult_scene_mood = _safe_ui_value(adult_scene_mood, "adult_scene_mood")
        adult_pose_style = _safe_ui_value(adult_pose_style, "adult_pose_style")
        adult_lighting = _safe_ui_value(adult_lighting, "adult_lighting")
        adult_scene_props = _safe_ui_value(adult_scene_props, "adult_scene_props")
        adult_body_focus = _safe_ui_value(adult_body_focus, "adult_body_focus")
        adult_framing_bias = _safe_ui_value(adult_framing_bias, "adult_framing_bias")
        adult_pose_style, adult_lighting, adult_scene_props, adult_body_focus, adult_framing_bias = _apply_adult_menu_level_to_pro_fields(
            adult_menu_level,
            adult_pose_style,
            adult_lighting,
            adult_scene_props,
            adult_body_focus,
            adult_framing_bias,
        )
        subject_age, subject_appearance, subject_ethnicity, subject_hair, subject_outfit, subject_expression, location_detail, time_of_day, weather_light, scene_props = _apply_builder_detail_mode_to_advanced_fields(
            builder_detail_mode,
            subject_age,
            subject_appearance,
            subject_ethnicity,
            subject_hair,
            subject_outfit,
            subject_expression,
            location_detail,
            time_of_day,
            weather_light,
            scene_props,
        )

        external_positive_in = _safe_free_text_input(external_positive_in)
        external_negative_in = _safe_free_text_input(external_negative_in)
        custom_text = _safe_free_text_input(custom_text)

        source_mode = _resolve_prompt_source_mode(prompt_source_mode, external_positive_in)
        standalone_scene = ""
        standalone_kind = ""
        standalone_active = source_mode == "standalone"
        if standalone_active:
            standalone_scene, standalone_kind = _build_standalone_scene(
                model_profile=model_profile,
                subject_profile=subject_profile,
                subject_age=subject_age,
                subject_appearance=subject_appearance,
                subject_ethnicity=subject_ethnicity,
                subject_hair=subject_hair,
                subject_outfit=subject_outfit,
                subject_expression=subject_expression,
                subject_pose=subject_pose,
                subject_action=subject_action,
                location_type=location_type,
                location_detail=location_detail,
                time_of_day=time_of_day,
                weather_light=weather_light,
                scene_props=scene_props,
                auto_extra_detail=auto_extra_detail,
                adult_tone=adult_tone,
                adult_wardrobe=adult_wardrobe,
                adult_exposure_level=adult_exposure_level,
                adult_pose_style=adult_pose_style,
                adult_scene_privacy=adult_scene_privacy,
                adult_scene_mood=adult_scene_mood,
                adult_lighting=adult_lighting,
                adult_scene_props=adult_scene_props,
                adult_body_focus=adult_body_focus,
                custom_text="",
            )

        bp_adult_tone = adult_tone
        bp_adult_wardrobe = adult_wardrobe
        bp_scene_framing = scene_framing
        if standalone_active and standalone_kind in {"environment", "product"}:
            bp_adult_tone = "default"
            bp_adult_wardrobe = "auto"
            bp_scene_framing = "wide shot" if standalone_kind == "environment" else "close-up"
        # Text-only composer policy: keep user-selected adult tone/wardrobe as
        # written.  A narrow location safeguard may move auto-privacy public
        # exposure scenes into a private studio during standalone scene building;
        # environment/product modes still suppress adult styling because those
        # modes intentionally contain no adult subject.
        elif standalone_active and adult_framing_bias != "auto":
            framing_map = {
                "portrait safe": "upper body",
                "close portrait": "close-up",
                "upper body": "upper body",
                "waist-up": "waist-up",
                "full body": "full body (head to toe)",
                "tasteful silhouette": "full shot (full body + extra space)",
                "editorial full body": "full body (head to toe)",
                "fabric detail close-up": "close-up",
                "body-focused non-graphic": "three-quarter body",
            }
            bp_scene_framing = framing_map.get(adult_framing_bias, bp_scene_framing)

        effective_adult_tone_for_text = _resolve_adult_tone_for_wardrobe(bp_adult_tone, bp_adult_wardrobe)
        active_positive_text = standalone_scene if standalone_active else external_positive_in
        external_positive = _sanitize_minor_conflict_text(active_positive_text, effective_adult_tone_for_text)
        external_negative = _clean_negative_text(external_negative_in)

        bp = PromptComposerCore.build_blueprint(
            model_profile=model_profile,
            mood_family=mood_family,
            style_dna=style_dna,
            adult_wardrobe=bp_adult_wardrobe,
            scene_framing=bp_scene_framing,
            lens_preset=lens_preset,
            explicitness=bp_adult_tone,
            custom_notes=custom_text,
            seed=seed,
            style_strength=style_strength,
        )
        if standalone_active and standalone_kind == "environment":
            bp.scene_framing = _environment_safe_scene_framing_terms(bp.scene_framing)
            bp.camera = _environment_safe_camera_terms(bp.camera)
        if standalone_active:
            bp.krea_framing_context = standalone_kind
        custom_text = bp.custom_notes

        external_style_cleanup_applied = False
        if source_mode == "external" and _should_cleanup_external_prompt(bp, style_conflict_cleanup, external_prompt_mode):
            external_positive = _relax_style_conflicting_external_prompt(
                external_positive,
                bp,
                style_conflict_cleanup,
                track_krea2_generated_fragments=(_model_key(bp.model_profile) == "krea2"),
            )
            external_style_cleanup_applied = True

        if external_style_cleanup_applied and _model_key(bp.model_profile) == "krea2":
            # The explicit style_conflict_cleanup option may transform a user
            # external prompt into generated non-photo residue such as
            # "realistic clear hand-rendered subject quality ...".  Clean that
            # residue before the external block is protected from broader Krea2
            # context rewrites, so user-authored phrases like "elegant posture"
            # still remain untouched later.
            external_positive = _krea2_cleanup_generated_handrendered_residue(external_positive)

        negative_context_sources = [custom_text]
        if source_mode != "style_only":
            negative_context_sources.insert(0, external_positive)

        generated_negative = _minimized_generated_negative(
            bp.model_profile,
            adult_tone=bp.adult_tone,
            kind=standalone_kind if standalone_active else "",
        )
        generated_negative = _harmonize_negative_with_user_positive(
            generated_negative,
            *negative_context_sources,
            adult_tone=effective_adult_tone_for_text,
        )
        generated_negative = _harmonize_negative_with_model_tone(
            generated_negative,
            bp.model_profile,
            bp.adult_tone,
        )
        if standalone_active:
            generated_negative = _negative_policy_for_standalone(
                generated_negative,
                adult_tone=adult_tone,
                adult_wardrobe=adult_wardrobe,
                adult_exposure_level=adult_exposure_level,
                kind=standalone_kind,
            )

        if source_mode == "style_only":
            positive = PromptComposerCore.render_external_style_only(bp)
        elif standalone_active and external_positive and _standalone_should_render_base_only(
            mood_family=mood_family,
            style_dna=style_dna,
            scene_framing=scene_framing,
            lens_preset=lens_preset,
            adult_tone=adult_tone,
            adult_wardrobe=adult_wardrobe,
            adult_exposure_level=adult_exposure_level,
            adult_pose_style=adult_pose_style,
            adult_framing_bias=adult_framing_bias,
            adult_scene_mood=adult_scene_mood,
            adult_lighting=adult_lighting,
            adult_scene_props=adult_scene_props,
            adult_body_focus=adult_body_focus,
            auto_extra_detail=auto_extra_detail,
            custom_text=custom_text,
            kind=standalone_kind,
        ):
            positive = _apply_model_quality_to_standalone_base(external_positive, bp.model_profile, bp.adult_tone)
            positive = _postprocess_standalone_positive(positive, standalone_kind, protected_text=custom_text)
        elif not external_positive:
            positive = PromptComposerCore.render_external_style_only(bp)
        elif standalone_active:
            if _should_force_transformative_style_first(bp, "Prepend style before external prompt"):
                positive = PromptComposerCore.render_prepend_style(bp, external_positive)
            else:
                positive = PromptComposerCore.render_external_positive(bp, external_positive)
            positive = _postprocess_standalone_positive(positive, standalone_kind, protected_text=custom_text)
        elif external_prompt_mode == "Output style only":
            positive = PromptComposerCore.render_external_style_only(bp)
        elif external_prompt_mode == "Prepend style before external prompt" or _should_force_transformative_style_first(bp, external_prompt_mode):
            positive = PromptComposerCore.render_prepend_style(bp, external_positive)
        else:
            positive = PromptComposerCore.render_external_positive(bp, external_positive)


        if _model_key(bp.model_profile) == "krea2":
            external_user_location = ""
            external_user_text = ""
            if source_mode == "external" and external_prompt_mode != "Output style only" and external_positive:
                external_user_text = external_positive
                if external_prompt_mode == "Prepend style before external prompt" or _should_force_transformative_style_first(bp, external_prompt_mode):
                    external_user_location = "last"
                else:
                    external_user_location = "first"
            positive, _krea2_user_restore_pairs = _krea2_protect_user_input_segments(
                positive,
                custom_text=custom_text,
                external_text=external_user_text,
                external_location=external_user_location,
            )
            positive = _postprocess_krea2_context_positive(positive, standalone_kind if standalone_active else "")
            if _is_monochrome_output_context(bp.mood_family, bp.style_name, positive):
                if standalone_active:
                    positive = _krea2_monochrome_safe_generated_wardrobe_sentence(positive)
                positive = _krea2_monochrome_safe_positive_text(positive)
            positive = _krea2_compact_long_prompt(positive)
            positive = _krea2_restore_user_input_segments(positive, _krea2_user_restore_pairs)

        family = _model_family(bp.model_profile)
        positive = _sanitize_prompt_output(positive, family)
        negative = _sanitize_prompt_output(_merge_negative_prompt_parts(generated_negative, external_negative), "tag")

        return (positive, negative)


NODE_CLASS_MAPPINGS = {
    "UltraPromptComposer": UltraPromptComposer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltraPromptComposer": "Ultra Tools Prompt Composer",
}

