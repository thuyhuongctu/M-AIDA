# Atlas costumes — plan & tracker

Huong in each economy's national dress for the 50-economy atlas
(`asia-atlas.html`). Each economy tile carries four distinctive features:

- 🚩 **Flag** — automatic (Unicode, from the atlas data)
- 👗 **National dress** — a Huong render dropped here (this folder)
- 🏛️ **Symbol** — an emoji (editable default set in the atlas)
- 🎵 **Famous song(s)** — editable defaults (Vietnam shows two)

## File convention

Drop each render as a background-removed PNG named by the economy `key`:

```
assets/img/huong/costume/<key>.png
```

Keys (match the atlas data): `vietnam, japan, korea, china, india, singapore,
taiwan, hongkong, israel, thailand, malaysia, indonesia, philippines,
bangladesh, pakistan, mongolia, fiji, samoa, kiribati, tonga, solomonislands,
vanuatu, papuanewguinea, timorleste, …` (full list in `asia-atlas.html`).

If a file is missing, the atlas automatically shows the default Huong figure
with a "coming soon" note — so renders can be added incrementally, no code
changes needed. Send the render, it is cut out and placed here.

## Priority (economies that headline a paper)

| # | Economy | Paper(s) | Dress | Status |
|---|---------|----------|-------|--------|
| 1 | 🇻🇳 Vietnam | P3 | Ao dai | ✅ done |
| 2 | 🇯🇵 Japan | P10 | Kimono | ⏳ awaiting render |
| 3 | 🇮🇳 India | P9 + book chapter | Sari | ⏳ |
| 4 | 🇸🇬 Singapore | P4 | Sarong kebaya | ⏳ |
| 5 | 🇨🇳 China | P2, P5 | Qipao / Hanfu | ⏳ |
| 6 | 🇫🇯 Fiji + 6 Pacific | P8 | Island dress (sulu/masi, puletasi, ta'ovala, …) | ⏳ |
| 7 | remaining 43 economies | P7 (the 50-economy frame) | see the atlas table | ⏳ |

## Proposed distinctive features — priority economies

Defaults already live in the atlas; refine songs per economy as for Vietnam.

| Economy | Symbol | Dress | Famous song(s) — proposed |
|---------|--------|-------|----------------------------|
| 🇻🇳 Vietnam | 🪷 lotus | Ao dai | *Mua xuan dau tien* (Le Hong Yen, music Van Cao); *Bonjour Vietnam* (Pham Quynh Anh) — **set** |
| 🇯🇵 Japan | 🗻 Fuji | Kimono | *Sakura Sakura* |
| 🇮🇳 India | 🕌 Taj Mahal | Sari | *Vande Mataram* |
| 🇸🇬 Singapore | 🦁 Merlion | Sarong kebaya | *Di Tanjong Katong* |
| 🇨🇳 China | 🐼 panda | Qipao / Hanfu | *Mo Li Hua* (Jasmine Flower) |
| 🇫🇯 Fiji | 🌺 hibiscus | Sulu / Masi | *Isa Lei* |
| 🇼🇸 Samoa | 🌴 | Puletasi | *Minoi Minoi* |
| 🇹🇴 Tonga | 🌺 | Ta'ovala | *Hala Fononga* |
| 🇰🇮 Kiribati | 🐚 | Te tibuta | *Teirake Kaini Kiribati* |
| 🇸🇧 Solomon Is. | 🏝️ | Traditional dress | *God Save Our Solomon Islands* |
| 🇻🇺 Vanuatu | 🌋 | Island dress | *Yumi, Yumi, Yumi* |
| 🇵🇬 Papua N.G. | 🦜 | Meri blouse | *O Arise, All You Sons* |

> Author to review/adjust songs and symbols; author supplies the national-dress
> renders (each economy's own flag on the dress is fine — e.g. the Vietnam ao dai
> carries the Vietnam flag).
