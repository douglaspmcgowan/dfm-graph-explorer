# PLAYBOOK_EXTRACTS — what actually applies to this build

Distilled from three source docs Douglas has already written. Rather than link them and hope the future session reads them all, this file extracts the parts that apply to `dfm-graph-explorer` specifically and flags what to skip.

Source docs:
- **`build-playbook.md`** (Content Hub Web App) — Vercel static deploy patterns, Express serverless, 17 pitfalls. Pattern A (markdown hub) and Pattern B (inline HTML research hub).
- **`explainer_site_playbook.md`** (Explainer Site Playbook) — editorial-site aesthetic system. Typography, color, layout, anti-checklist, craft checklist.
- **`Documents\dfm_scraping\BUILD_PLAN_V2.md`** §2-4 — the DFM-KG-Agent rebuild plan. Anti-AI-slop research with sources, RAG/KG-tool UX research, dark technical product aesthetic.

---

## 0. Archetype — what this site IS, and what it is NOT

`dfm-graph-explorer` is a **technical product**, not an editorial essay. The atlas-gui we're forking is dark, dense, controllable — Linear/Cursor/Figma polish bar, not a literary magazine.

This matters because `explainer_site_playbook.md` defaults to **warm editorial** (cream paper, Source Serif 4, rust accent, 65ch measure). **Do not apply those defaults here.** Use the dark-technical-product aesthetic from BUILD_PLAN_V2 §2 instead. The principles transfer; the specific values don't.

The transferable principles from the editorial playbook:

- Single accent used on <5% of pixels
- Hairlines over box borders
- Varied spacing per density, not uniform `py-24`
- Real typographic hierarchy (weight, size, italic, mono-vs-sans)
- `text-wrap: balance` on headings, `text-wrap: pretty` on paragraphs
- `font-optical-sizing: auto`
- `prefers-reduced-motion` honored
- Grain overlay at 3–5% opacity to kill flat-flatness
- Focus ring in accent color, 2px, 3px offset, `:focus-visible` only

What does NOT transfer from the editorial playbook:

- ❌ Warm cream paper (`#FBF8F1`) — this is a dark tool
- ❌ Source Serif 4 as body font — use Geist/Inter for chrome; reserve serif for report content IF we ever render reports inline
- ❌ Rust accent `#A62B1F` — use orange `#ff6b3d` instead (see §3 on indigo)
- ❌ 65ch body measure — force-directed graphs are not body copy
- ❌ Drop cap on opening paragraph
- ❌ Section marks with Roman numerals (we don't have "sections" — we have panels)

---

## 1. Deploy — Vercel static, one command

From `build-playbook.md` plus `explainer_site_playbook.md` §9.

### The happy path

```bash
npx vercel --prod --yes
```

From the project root. First run links the project (accepts defaults; project name comes from folder name). Subsequent runs redeploy. Output includes both a deployment-specific URL and a stable alias like `dfm-graph-explorer-xyz.vercel.app` — share the alias.

### If single-file HTML (atlas-gui clone)

Flat layout. No config needed — Vercel serves static files by default.

```
dfm-graph-explorer/
  index.html            ← the D3 prototype, forked from preview.html
  graph_data.json       ← exported from dfm_scraping (see USER_KG_POINTERS.md §11)
  public/fonts/         ← self-hosted Geist + JetBrains Mono (optional)
```

### If Vite + React (after migration per PLAN.md §6)

```
dfm-graph-explorer/
  vite.config.ts
  index.html
  src/
    main.tsx
    ...
  public/
    graph_data.json
```

Vercel auto-detects Vite and runs `npm run build` → `dist/`. No `vercel.json` needed unless you're customizing routes.

### Naming rules learned the hard way (pitfalls #10, #14 in build-playbook)

- **Pass `--name` with a kebab-case name** if the folder has spaces or awkward characters. This directory has spaces in ancestors ("My Drive (douglaspmcgowan@gmail.com)") — confirm Vercel auto-detects the `dfm-graph-explorer` leaf correctly; if not, `npx vercel --prod --yes --name dfm-graph-explorer`.
- **Check name availability before renaming.** `curl -s -o /dev/null -w "%{http_code}" https://NAME.vercel.app` — 404 means available.
- **Aliases get 401 due to deployment protection.** Rename projects in the Vercel dashboard (Settings → General → Project Name), not via `vercel alias`.

### Verify the deploy

```bash
curl -s -o /dev/null -w "%{http_code}" https://dfm-graph-explorer.vercel.app
# 200 = live. 500 = check logs. 404 = URL mismatch or still building.
npx vercel logs https://dfm-graph-explorer.vercel.app
```

---

## 2. The anti-AI-slop checklist (sourced)

From BUILD_PLAN_V2 §2. Every item below has a 2025-26 practitioner source — not vibes.

### Visual dead-giveaways

- ❌ **`indigo-500` / blue-purple gradient accent.** Adam Wathan (Tailwind creator) apologized Aug 2025 for making `bg-indigo-500` the default: "every AI-generated UI on earth [is] also indigo." → use warm orange `#ff6b3d` instead.
- ❌ **shadcn defaults untouched** — "sidebar on the left, data tables in the center, button groups top right, toasts sliding in bottom-right." → use Radix primitives directly and style them with your own tokens.
- ❌ **8px/16px radii on every surface.** → keep radii ≤10px. `rounded-2xl` is banned.
- ❌ **Uniform 0.1-opacity shadows everywhere.** → use shadows that earn their place; inset hairlines for surface lift.
- ❌ **Lucide icons untouched.** → use Lucide but override stroke/size; or mix with custom SVG for key icons.
- ❌ **Uniform 300ms animation on everything.** → asymmetric timing (120ms in, 240ms out); frequency-based — high-frequency actions get no animation.
- ❌ **Streamlit's `#FF4B4B` primary + 730px centered + top-right spinner.** Every Streamlit tell. → none of these.
- ❌ **Aurora/mesh gradients, glowing radial blobs, `bg-clip-text` gradients on headlines.**
- ❌ **Centered everything.** → varied alignment by density.
- ❌ **Cool slate/zinc grays.** → warm near-blacks (`#0a0a0b` base, not `#0f172a`).

### Structural dead-giveaways

- ❌ 3×3 feature-card grid
- ❌ Emoji in headlines
- ❌ Mixed icon sets (Lucide + Feather + Heroicons in the same UI)
- ❌ Uniform `py-24` on every section
- ❌ Faded grayscale "Trusted by" logo row
- ❌ Inter at one weight across every size (use weight/size/italic to vary)
- ❌ Pure flat surfaces (add grain at 3–5%)

---

## 3. What the polish tier does instead

Also from BUILD_PLAN_V2 §2. Concrete moves, with sources.

- **Token-first palette in a perceptual color space.** Linear rebuilt their theme in LCH/OKLCH in Mar 2026 — "colors with the same lightness appear equally light" — and shifted to warmer, less-saturated grays. North star: "Structure should be felt, not seen." → use OKLCH for the color tokens. Tailwind v4's `@theme` supports this natively.
- **Frequency-based motion.** High-frequency actions (command palette, context menu) appear without animation — novelty diminishes after the hundredth use. Motion conveys spatial structure, not decoration. (Rauno Helander, *Invisible Details*.)
- **Single accent used sparingly** (<5% pixels), hairlines not card outlines, varied spacing per density, real type hierarchy, `prefers-reduced-motion` honored.
- **Design on screenshots, not in Figma.** Saarinen's operating rule at Linear. The real deliverable is the running product.

---

## 4. RAG / knowledge-graph / agent-tool trust patterns

This is the MOST IMPORTANT SECTION of this file. From BUILD_PLAN_V2 §2-4 research. These patterns earn trust in tools where the user is staring at AI-generated or AI-curated output. Every one of them has a source tying it to a real product critique or research paper.

### 4.1 Provenance on every artifact

> "I can't distinguish AI output from real data" — HN on Cursor 1.0, Jun 2025.

Every node and edge in the graph has a provenance story. **Surface it.**

- **Hover-to-see-the-quoted-passage on citations.** NotebookLM's scroll-to-quote + Perplexity's favicon+title+freshness chips. When a user hovers a frame node, show `source_quote` (verbatim), `author_username` + credibility tier, `se_site`, and a click-to-open to the original thread. This is the #1 thing atlas-gui doesn't do that we should.
- **Show the actual source URL on the provenance panel.** Deep-link back to the SE thread.
- **Freshness:** show `post_date` if available.

### 4.2 Show the graph's reasoning, not just the result

For semantic edges specifically: the `reasoning` field in `semantic_edges.json` is human-readable LLM output explaining WHY two frames are connected. **Surface it on edge hover.**

Atlas-gui has no semantic edges. Ours has 4,272 with reasoning. Not showing them is leaving the differentiator on the floor.

### 4.3 Don't hide modes

> "10,000+ Reddit threads forced OpenAI to restore visible 'Auto / Fast / Thinking' within days after GPT-5 launch." — TechCrunch Aug 2025.

If the explorer grows multiple rendering modes (SVG / canvas / WebGL, or structural-only / with-semantic, or filter-by-type), make the toggles visible and named by intent, not by implementation.

Not "Renderer: svg2". Instead: "Layout: Instant (uses pre-computed positions)" vs "Layout: Live (runs force sim in browser)".

### 4.4 Surface uncertainty in first-person

Where the explorer displays LLM-generated text (edge reasoning, main_point), if confidence is low, show it:

- "medium confidence" label on edges flagged `"confidence": "medium"` in `semantic_edges.json` — don't pretend all 4,272 edges are equally certain.
- **Don't add fake confidence bands if they're not calibrated.** Miscalibrated confidence badges actively reduce decision quality (arXiv 2402.07632). If you don't know that "high" means 90% precision, don't label it "high."

### 4.5 Plan-then-execute streaming (if we ever add a search box with backend)

Not required for V1 (static site, no backend). But if V2 adds "ask a question, get traced answer": Perplexity Pro Search streams a plan first, then the steps, then the answer — each step expandable. Much better than opaque "thinking…"

### 4.6 Name modes by intent, not by model

Not "gpt-4.1-mini labels" — "Topic labels (LLM-generated)". Not "forceAtlas2" — "Gephi layout preset."

### 4.7 Treat visible reasoning as "working notes," not ground truth

Anthropic's research: Claude 3.7 references a hinted answer only 25% of the time when shown a hint. CoT is indicative, not faithful. If the explorer ever surfaces LLM chain-of-thought for edge inference, label it "working notes" — don't frame it as verified.

### 4.8 Knowledge-graph specific (Obsidian / Logseq / Roam community consensus)

From the Obsidian forum thread on graph view usage:

- **Start focused (20–50 nodes), not full-graph.** Full-graph hairball views get abandoned. 7,864 nodes at once is worse than useless — it's misleading.
- **Filter-by-type is the #1 win.** Users consistently say the graph view becomes useful only after they filter to a subset. Our `frame_type` / `scope` / `se_site` filters are table stakes.
- **Ego network (1–2 hops around one node) is where the graph earns its keep**, not the whole-graph view.

This is why PLAN.md §5 proposes the three-level hierarchy: 39 topic supernodes → frames within topic → ego network around one frame.

---

## 5. The citation / tooltip pattern (transferable)

From BUILD_PLAN_V2 §2 (referencing `idetc-paper-site/styles.css §1007-1073`). This transfers directly.

### CSS shape

```css
.cite {
  color: var(--accent);
  text-decoration: underline dotted;
  text-underline-offset: 2px;
  cursor: help;
}
.cite:hover + .tip,
.cite:focus + .tip {
  opacity: 1;
  pointer-events: auto;
}
.tip {
  position: absolute;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem 1rem;
  max-width: 28rem;
  opacity: 0;
  pointer-events: none;
  transition: opacity 120ms ease-in, opacity 240ms ease-out;
  box-shadow: var(--shadow-2);
  z-index: 50;
}
.tip .quote {
  font-style: italic;
  color: var(--fg-muted);
  border-left: 2px solid var(--accent);
  padding-left: 0.75rem;
  margin: 0.5rem 0;
}
.tip .meta {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--fg-faint);
}
```

Use this shape for frame node hover cards. `.quote` is the `source_quote`. `.meta` is author + credibility + se_site + date.

---

## 6. Typography — what to actually load

From BUILD_PLAN_V2 §2 (revised) and explainer_site_playbook §2.

For a dark technical tool, NOT warm editorial:

```css
--font-sans: "Geist", "Inter Tight", "Inter", system-ui, sans-serif;
--font-mono: "Geist Mono", "JetBrains Mono", ui-monospace, Menlo, monospace;
```

Self-host both (not Google Fonts, not a CDN) to avoid flash and lock in weight variations. Variable fonts preferred so you pay for one file and get all weights.

### The five things to always turn on

```css
html {
  font-optical-sizing: auto;
  font-feature-settings: "kern" 1, "liga" 1;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { text-wrap: balance; }
p, li { text-wrap: pretty; }
```

Tabular numerals (`font-variant-numeric: tabular-nums`) on any number column (graph statistics, node counts).

### Type scale — dense, not editorial

Tight (1.20 ratio) since this is a tool, not a read:

```
0.72rem  — meta, labels, node IDs
0.82rem  — small UI, chips, keyboard shortcuts
0.95rem  — body / default
1.15rem  — emphasized body, panel headers
1.38rem  — h4
1.66rem  — h3
2.00rem  — h2
2.40rem  — h1 (masthead)
```

### Serif exception

Only inside `.report-body` if we ever render a DFM report inline (V2 feature). Chrome stays sans; reading content stays serif. That's the Stripe Press / Anthropic-docs trick.

---

## 7. Color palette — dark technical product

From BUILD_PLAN_V2 §2. Use this almost verbatim.

```css
:root {
  /* Near-blacks, slightly warm */
  --bg: #0a0a0b;
  --surface: #131316;
  --surface-2: #1c1c20;
  --surface-3: #26262b;

  --border: rgba(255, 255, 255, 0.07);
  --border-strong: rgba(255, 255, 255, 0.12);

  --fg: #ececee;
  --fg-muted: #a0a0a8;
  --fg-faint: #6b6b72;

  /* Accent — orange, NOT indigo (see §2 above) */
  --accent: #ff6b3d;
  --accent-soft: rgba(255, 107, 61, 0.15);
  --accent-fg: #ffffff;

  --good: #4ade80;
  --warn: #fbbf24;
  --bad: #f87171;

  /* Frame-type colors — replace Plotly's Flatly defaults */
  --type-risk:        #f87171;
  --type-heuristic:   #60a5fa;
  --type-principle:   #a78bfa;
  --type-case:        #fbbf24;
  --type-workaround:  #34d399;
  --type-observation: #94a3b8;
  --type-comparison:  #f472b6;
  --type-other:       #6b6b72;

  --radius-sm: 4px;
  --radius: 6px;
  --radius-lg: 10px;  /* NEVER larger — no rounded-2xl */

  --shadow-1: 0 1px 0 rgba(255,255,255,0.04) inset,
              0 1px 2px rgba(0,0,0,0.4);
  --shadow-2: 0 0 0 1px var(--border),
              0 8px 24px rgba(0,0,0,0.5);
}
```

Why orange and not the editorial rust (`#A62B1F`):

1. **Orange sits opposite indigo on the hue wheel** — a designer's choice, not a default.
2. **Manufacturing/DFM has cultural ties to safety orange and CAT yellow** — the accent does domain work.
3. **Rust on cream reads as "literary essay"; orange on near-black reads as "tool."** Right register.

---

## 8. Layout — dense, not spacious

- **No 65ch measure on anything** except generated report text (if any). Graph fills viewport.
- **Sidebar + main + optional right rail** — the three-region pattern from BUILD_PLAN_V2. Left sidebar for navigation/filters, center for graph, right rail opens contextually on citation click.
- **Hairlines between regions** (`1px solid var(--border)`), not card borders.
- **Varied padding per region density.** The graph canvas is edge-to-edge. Filter panels get breathing room. Metadata chips are tight.
- **Grain overlay** at 3–5% opacity is still worth doing even on a dark UI. Flat blacks read as "default shadcn dark mode."

### Grain overlay snippet (from explainer_site_playbook §4)

```css
.grain {
  position: fixed; inset: 0; pointer-events: none; z-index: 1000;
  opacity: 0.035;
  mix-blend-mode: overlay;  /* on dark bg; use "multiply" on light */
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.9 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}
```

First child of `<body>`, `aria-hidden="true"`.

---

## 9. Pitfalls from building before, check these first

From `build-playbook.md` Pitfalls §1-17. The ones most likely to bite this project:

| # | Pitfall | Why it matters here |
|---|---|---|
| 2 | `module.exports` missing for Vercel | Only if we go Express+Node — pure static doesn't hit this. |
| 4 | Inline `onclick` handlers break on mobile | Use data-attributes + addEventListener. Applies to any D3-generated nodes. |
| 5 | Anchor links hide behind sticky header | `scroll-margin-top: 7rem`. Applies if the page has a top bar. |
| 7 | File dates wrong on Vercel | Don't derive node counts or last-updated from `fs.stat` — hardcode or pull from a JSON field. |
| 8 | `--` vs `-` in slugs | Falls out of typography choices; not likely here. |
| 10 | Vercel project name with spaces | Ancestor folder has spaces (`My Drive (...)`) → pass `--name dfm-graph-explorer`. |
| 11 | `showSection()` using implicit `event` | Pass `this` explicitly into handlers. |
| 12 | Vercel CLI can't rename projects | Rename in dashboard. |
| 13 | Vercel alias gets 401 | Rename, don't alias, for `.vercel.app` URL changes. |
| 14 | Name already taken | Check `dfm-graph-explorer.vercel.app` availability before locking in. |
| 15 | Testing on port already in use | Use a unique port for local preview. |

---

## 10. Craft checklist (trimmed to what applies)

Adapted from explainer_site_playbook §5. Items that apply to a dark technical product; italic are the ones that need adjustment from the original.

- [ ] Grain overlay at 3–5% opacity, `mix-blend-mode: overlay`
- [ ] `text-wrap: balance` on headings, `text-wrap: pretty` on paragraphs
- [ ] `font-optical-sizing: auto`
- [ ] Tabular figures (`tnum`) in all data displays (node counts, degree, etc.)
- [ ] *Self-hosted Geist + Geist Mono* (not Source Serif 4; serif only for report body)
- [ ] *Near-black bg* (`#0a0a0b`), warm off-white fg (`#ececee`) — never `#000` on `#FFF`
- [ ] *Single orange accent* (`#ff6b3d`) used on <5% of pixels
- [ ] Hairlines (`rgba(255,255,255,0.07)`) between panels — no box borders
- [ ] Focus ring in accent color, 2px, 3px offset, `:focus-visible` only
- [ ] `prefers-reduced-motion` honored on all transitions and D3 animations
- [ ] Asymmetric hover timing (120ms in, 240ms out) on tooltips and hovers
- [ ] Inline code with `var(--surface-2)` bg + hairline border, not flat tag
- [ ] *Radii ≤10px everywhere* (no `rounded-2xl`)
- [ ] Frame-type color palette (not Plotly Flatly)
- [ ] Citation tooltip pattern (§5 above) on every frame node
- [ ] Semantic-edge `reasoning` visible on edge hover
- [ ] Filter-by-`frame_type` AND filter-by-`scope` AND filter-by-`se_site` all present
- [ ] Start view focused on 20–50 nodes (Level 1: 39 topics), NOT 7,864

---

## 11. The anti-checklist (do not ship with any of these)

Trimmed and adjusted from explainer_site_playbook §6 + BUILD_PLAN_V2 §2:

- Aurora/mesh gradients
- Glowing radial blur blobs
- Gradient text on headlines (`bg-clip-text`)
- `rounded-2xl` on anything
- Default shadcn `shadow-md` everywhere
- Cool slate/zinc grays (must be warm near-black)
- Indigo-500 or blue/purple gradient accent
- Inter at one weight across every size
- Emoji in headlines
- Mixed icon sets
- 3×3 feature-card grid
- Centered everything
- Faded grayscale logo row
- Pure flat surfaces (no grain)
- Uniform `py-24` or any uniform spacing rule
- Streamlit `#FF4B4B` primary, 730px centered layout, top-right spinner
- Full-graph hairball view as the default landing state
- Citations that don't show the quoted passage
- LLM-generated reasoning presented as ground truth (label it)

If a critic scoring the site with this list hits on any item, fix before shipping.

---

## 12. Build order (adapted to this project)

From explainer_site_playbook §8, reshaped for a graph explorer:

1. **Confirm archetype, temperature, accent.** Dark technical product, orange accent. Not warm editorial. Write this at top of scratch doc.
2. **Export the data.** Write the Python script (USER_KG_POINTERS.md §11). Produce `graph_data.json`. This is 30% of the work and it's not optional.
3. **Fork `atlas-gui/preview.html`.** Copy it into repo root as `index.html`. Replace the inline `GRAPH_DATA` or file-picker path so it loads our JSON by default.
4. **Get it rendering something.** 39 topic supernodes first. Then Level 2 drill-down. Then Level 3 ego network.
5. **Paste the tokens from §7.** Swap out atlas-gui's palette for ours. This is where it stops looking like someone else's site.
6. **Add citation tooltips (§5)** and the semantic-edge reasoning on hover.
7. **Layer filters.** `frame_type`, `scope`, `se_site`, credibility tier.
8. **Add grain, hairlines, focus rings.** Polish pass.
9. **Test mobile.** Narrow the viewport. Fix the first three things that look wrong. Do not over-fix.
10. **Deploy.** `npx vercel --prod --yes --name dfm-graph-explorer`. Verify `200`. Share the URL.

Time: 2-4 hours to a rough version that renders the real graph. Another 2-4 for the polish pass and filters.

---

## 13. What to read next

- `PLAN.md` — the full 13-section roadmap for this project.
- `USER_KG_POINTERS.md` — the data layer (schemas, files, counts, export).
- `reference/atlas-gui/preview.html` — the prototype to fork. Read it before writing any new code; it already does 80% of what we need.
- `reference/atlas-gui/PRD.md` — the atlas-gui spec, for the three-level nav architecture we're adapting.

For anything NOT covered here, the source playbooks in `C:\Users\dougl\My Drive (...)\Research\Claude Research Folder\` are authoritative:

- `build-playbook.md` — all 17 Vercel pitfalls, both patterns, full feature checklists.
- `explainer_site_playbook.md` — full editorial aesthetic (for when you build something that IS editorial, not this project).
- `Documents\dfm_scraping\BUILD_PLAN_V2.md` — the 82KB master rebuild plan with every source citation.

Don't re-research what's already in those docs. Read them if you hit something this extract didn't cover.
