# Writing Guide — auto-scribe Medium articles

The editorial and format specification every article in this repo must
follow. Machine-checkable rules are enforced by `_validate_html`
(`generator.py:73`) and the LLM prompt (`SYSTEM_PROMPT_TEMPLATE`,
`generator.py:25`) — keep all three in sync (see AGENTS.md rule 7).

**Style exemplar:** `ai-coding-agents-explained.html`
(https://rezer-bleede.github.io/auto-scribe/ai-coding-agents-explained.html)

---

## 1. Voice & audience

- **Who:** developers and technical readers on Medium — assume competence,
  explain nothing condescendingly.
- **Tone:** clear expert, conversational but credible. Short declaratives
  over throat-clearing. Read-aloud test: if a sentence wouldn't survive
  being said in a stand-up, rewrite it.
- Second person sparingly; present tense for how-things-work.
- **No marketing fluff:** ban hype adjectives (*revolutionary, cutting-edge,
  game-changing, unprecedented*). Concrete claims beat vibes:
  - Don't write: "AI agents are incredibly powerful and transformative."
  - Do write: "An agent loops until its tests pass; capability is bounded
    by the quality of your suite."
- Em-dashes welcome, one per sentence max. Oxford comma. One space after
  periods.

## 2. Structure & length

| Requirement | Rule |
|-------------|------|
| Length | 600–900 words |
| Heading | exactly one `<h1>`, matching the `<title>` |
| Intro | hook paragraph, ≤ 4 sentences — the first 300 words decide Medium readers |
| Body | 3–6 `<h2>` sections, each 1–3 short paragraphs (2–4 sentences) |
| List | at least one `<ul>`; bullets are parallel in grammar |
| Code | optional single `<pre><code>` block, ≤ 12 lines, realistic not toy |
| Close | takeaway paragraph that ends on a claim, never "In conclusion" |
| Footer | every article must end with the LinkedIn footer paragraph (section 5) |

## 3. Medium-specific constraints — and why they exist

- **Canonical link is mandatory.** The `<head>` must contain
  `<link rel="canonical" href="https://rezer-bleede.github.io/auto-scribe/{slug}.html">`.
  Medium's importer reads it to credit the original source; without it (or
  with a wrong URL) the imported story risks duplicate-content penalties
  and misattribution.
- **Simple semantic HTML only.** Medium's scraper silently drops `div`s,
  inline CSS, classes, and scripts. What survives is semantic tags — so
  layout you build with them is layout Medium can actually render. Fancy
  HTML is not just rejected, it is *mangled*, which is worse.
- **Skimmability.** Medium readers scan on phones: `h2` sections every
  100–150 words, real lists, bold for terms on first use.

## 4. HTML format spec

Allowed body tags:

```
<h1> <h2> <p> <ul> <li> <strong> <em> <blockquote>
<pre> <code>  (and <figure> <img> <figcaption> if used)
```

Forbidden — the validator rejects these outright:

```
<div> <span> <style> <script> <iframe>  any style="..." attribute
any class="..." or id="..."  relative URLs  <link> to stylesheets
```

Head requirements:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{engaging title, ≤ 70 chars}</title>
<link rel="canonical" href="https://rezer-bleede.github.io/auto-scribe/{slug}.html">
</head>
```

## 5. Images policy

- Images are **optional**. Zero is a valid, often better, choice.
- Max 2 per article. Every `src` must be an absolute `https://` URL —
  the validator rejects relative paths, Medium's scraper rejects anything
  it cannot fetch.
- **Never fabricate Unsplash photo IDs.** An unverifiable image URL is
  worse than no image: it renders as a broken placeholder on Medium
  permanently. If unsure, drop the image. Always include `alt`.
- **Verify before publishing.** Every image URL must return HTTP 200 with
  an `image/*` content type (check with `curl -I <url>`). Wikimedia
  Commons (`upload.wikimedia.org`) is a good source of stable, freely
  licensed URLs; strip any `?utm_*` tracking params from the `src`.

## 6. Footer (mandatory)

Every article must end with this exact footer paragraph, as the last
element of `<body>` (plain text URL — `<a>` is not an allowed tag, and
Medium auto-links bare URLs):

```html
<p>I'd love to keep the conversation going. If you found this article insightful or have thoughts, experiences, and ideas to share, let's connect on LinkedIn! https://www.linkedin.com/in/remisharoon/</p>
```

The validator enforces the LinkedIn URL; do not paraphrase or reorder.

## 7. Do / don't examples

Don't — layout markup Medium will strip:

```html
<div class="hero" style="font-size: 2em">
  <span>Key insight</span>
</div>
```

Do — semantic structure Medium renders faithfully:

```html
<blockquote>Key insight: the model is not the risk. The loop without
verification is the risk.</blockquote>
```

Don't — hedged filler: "It could maybe be argued that agents sometimes
might help developers in some cases."
Do — a claim: "Agents made review, not typing, the bottleneck skill."

## 8. Slugs & filenames

- Lowercase kebab-case: `[a-z0-9-]`, no leading/trailing/consecutive
  hyphens, ≤ 60 chars (enforced in `generate_html_article`).
- The filename is exactly `{slug}.html` at the repo root — it *is* the
  Pages URL path. Choose it as if the article already ranks.
- Re-publishing a slug updates the article in place (idempotent).

## 9. Pre-publish checklist

- [ ] Topic + slug chosen; slug is kebab-case, ≤ 60 chars
- [ ] `<!DOCTYPE html>` and `<html lang="en">` present
- [ ] `<title>` engaging, ≤ 70 chars, `<h1>` matches it
- [ ] Canonical link exact: `https://rezer-bleede.github.io/auto-scribe/{slug}.html`
- [ ] 600–900 words; 3–6 `h2` sections; ≥ 1 `ul`; close on a claim
- [ ] No `div`/`span`/inline CSS/classes/ids/scripts anywhere
- [ ] Any images: absolute `https://`, verified HTTP 200 `image/*`, ≤ 2, with `alt`
- [ ] Footer paragraph present as the last element, LinkedIn URL exact
- [ ] Passes `_validate_html` (`from generator import _validate_html`)
- [ ] Published via `publisher.push_to_github`, URL polled to HTTP 200
