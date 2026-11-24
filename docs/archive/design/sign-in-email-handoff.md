# Handoff: RESSLab Hub sign-in email

## Overview
Transactional HTML email sent when someone asks to sign in to RESSLab Hub. It carries a six-digit code and a magic link that does the same thing. Replaces the current plain-text-only mail. Recipients are researchers in Europe, the US and Japan; for many it is the first contact with the project.

## About the design files
`signin_email.html` and `signin_email.txt` are **finished email templates, not a UI prototype**. Unlike a screen design, an HTML email is shipped as-is: the task is to wire these two files into the backend mailer as the HTML and plain-text parts of a multipart message, fill the three placeholders, and send. Do not port the markup to Vue components or the app's CSS — mail clients render neither.

## Fidelity
High-fidelity. Colours, type stack, spacing and copy are final. Table layout, inline styles and MSO conditionals are deliberate and must stay.

## Placeholders
Both files use the same three tokens:

- `{code}` — six digits, no spaces
- `{link}` — full verify URL, e.g. `https://resslab-hub.epfl.ch/login/verify?challenge=…&token=…`. HTML-escape `&` as `&amp;` in the HTML part (it appears twice: `href` and visible text).
- `{ttl_minutes}` — integer, currently `10`

**Do not use an f-string or `str.format` on the HTML file**: its `<style>` block contains CSS braces. Fill with `str.replace()` in a loop, or `string.Template` after converting the tokens to `$code` etc.

```python
from pathlib import Path
from html import escape

TEMPLATE_DIR = Path(__file__).parent / "templates" / "email"

def render_signin_mail(code: str, link: str, ttl_minutes: int) -> tuple[str, str, str]:
    html = (TEMPLATE_DIR / "signin_email.html").read_text(encoding="utf-8")
    text = (TEMPLATE_DIR / "signin_email.txt").read_text(encoding="utf-8")
    fills_html = {"{code}": escape(code), "{link}": escape(link, quote=True), "{ttl_minutes}": str(ttl_minutes)}
    fills_text = {"{code}": code, "{link}": link, "{ttl_minutes}": str(ttl_minutes)}
    for k, v in fills_html.items():
        html = html.replace(k, v)
    for k, v in fills_text.items():
        text = text.replace(k, v)
    subject = f"{code} is your RESSLab Hub sign-in code"
    return subject, text, html
```

Send as `multipart/alternative` with the text part first, HTML second. Set `Content-Type: text/html; charset=utf-8`. No tracking pixel, no unsubscribe header, no List-Unsubscribe — this is transactional mail.

## Subject line
`{code} is your RESSLab Hub sign-in code` — code first so it shows in phone notifications. The hidden preheader in the HTML adds "Enter the code or open the link. Both stop working in {ttl_minutes} minutes."

## Structure of the HTML part
Single column, full width of the window (no 600px cap, dropped during implementation), centred on a `#fcfcfc` ground. White card, 40px side padding (20px under 480px via media query, which Gmail/Apple Mail honour; Outlook keeps 40px).

1. **Header** — the mark as an attached PNG (`cid:rl-mark-light`, 40×40, with a `cid:rl-mark-dark` twin for dark mode) + wordmark "RESSLab" ink / "Hub" `#e30713`, 20px bold; tagline "Steel structures research · EPFL" 12px `#6b6b6b`. 1px `#e6e6e6` rule below.
2. **Title + lead** — "Sign in to RESSLab Hub" 24/30 bold; lead 16/24.
3. **Code block** — between two 1px rules. Label "YOUR SIGN-IN CODE" 11px, 1.5px tracking, uppercase, grey. Code: one `<div>` containing only `{code}`, `'Courier New',Courier,monospace` 44/56 bold, 10px letter-spacing (36px / 6px under 480px). Line "Type it in the tab where you asked to sign in." 15/22.
4. **Link block** — intro line; bulletproof button (`<td bgcolor="#e30713">` + block `<a>`, 13px 26px padding, 15px bold white, square corners, MSO padding fix inline); "Or copy this address into your browser:" then the raw URL in 12px monospace grey with `word-break:break-all`.
5. **Terms** — above a 1px rule: expiry line and security line, both 14/21 in full ink.
6. **Footer** (outside the card, on the ground) — the EPFL logo as an attached PNG (`cid:rl-epfl`, 62×18, red), one sentence about the project, link to resslab-hub.epfl.ch. 12/18 grey.

## Behaviour in mail clients
- **Images blocked**: the two logos show their alt text, everything else is live text (code, button, URL). The logos travel with the mail as `cid:` parts, so no remote load is needed when images are on.
- **Gmail / Outlook**: strip inline SVG, which is why the logos are PNG parts and not SVG (see "Changes made during implementation").
- **Dark mode**: `color-scheme` meta + `supported-color-schemes` are set. A `prefers-color-scheme: dark` block in `<style>` remaps classes `rl-ground` `#171717`, `rl-card` `#212121`, `rl-ink` `#ececec`, `rl-mut` `#a3a3a3`, `rl-rule` `#3a3a3a`, `rl-red` `#ff4a4a` (brighter red for text on dark), SVG strokes/fills. The button keeps `#e30713` with white text in both modes. Clients that ignore the block (Gmail) apply their own inversion; the palette has no pure `#000`/`#fff` so it survives.
- **Outlook desktop**: `mso-line-height-rule:exactly` on the code; button padding via MSO `<i>` spacers. No width conditional any more (it went with the 600px cap).
- **320px**: single column throughout; the URL wraps with `word-break:break-all`; the code shrinks via media query and still fits (6 digits × ~22px + 5 × 6px).

## Copy (final)
See `signin_email.txt` — the HTML uses identical sentences. Plain English, no exclamation marks, short sentences. French translation will fit: all text blocks wrap, the button label ("Ouvrir RESSLab Hub") fits at 320px.

## Design tokens
- EPFL red `#e30713`, hover `#b51f1f` (button `:hover`, only where `<style>` survives)
- Ink `#212121`, muted `#6b6b6b`, rules `#e6e6e6` (solid stand-in for `rgba(33,33,33,.1)` — Outlook has no alpha)
- Ground `#fcfcfc`, card `#ffffff`
- Dark: ground `#171717`, card `#212121`, ink `#ececec`, muted `#a3a3a3`, rule `#3a3a3a`, red text `#ff4a4a`
- Type stack: `Arial, Helvetica, sans-serif`; code and URL: `'Courier New', Courier, monospace`
- Sizes: 24/30 title · 20/24 wordmark · 16/24 lead · 15/22 body · 14/21 terms · 12/18 small · 11/16 label · 44/56 code
- Square corners, no shadows, no gradients. The only images are the two logos, attached as PNG parts

## Changes made during implementation

- **The marks are attached PNGs, not inline SVG.** Gmail and Outlook strip
  inline SVG, so the handoff's "accepted" fallback meant no logo at all in
  the two most common clients. The real `resslab-hub-mark-iso.svg` is
  rendered to PNG at 2x (80px for a 40px slot) and travels with the mail as
  a `cid:` related part. A hosted URL was rejected because it would not load
  from a laptop serving on `127.0.0.1`, and because Gmail proxies images.
  Two versions of the mark: the white fills in that logo are a masking
  trick, so on a dark card they are remapped to the card colour and the ink
  goes light. They swap in the `prefers-color-scheme` block.
- **No `max-width: 600px`.** Asked for after seeing it on a laptop: the card
  now fills the window. The Outlook conditional that forced 600px went with
  it, since it would have pinned Outlook to the old width.

## Assets
- Header mark: `mark-light.png` and `mark-dark.png` next to the templates, rendered at 2x from `frontend/public/logo/resslab-hub-mark-iso.svg`. Attached by `mailer.py` (`LOGOS`) under the content ids `rl-mark-light` and `rl-mark-dark`; the `prefers-color-scheme` block swaps them.
- Footer: `epfl.png`, same folder, from the official `epfl-logo.svg`, content id `rl-epfl`.

## Files (as implemented)
The two parts live in the backend package, next to the mailer that loads them:

- `backend/resslab_hub/auth/templates/email/signin_email.html`
- `backend/resslab_hub/auth/templates/email/signin_email.txt`

They are filled and assembled by `build_message()` in
`backend/resslab_hub/auth/mailer.py`.
- Preview with sample values, light/dark/320px: `Sign-in Email Preview.html` in the design project (not needed for implementation)

## Test checklist
- Send to Gmail web, Apple Mail (light + dark), Outlook desktop, Outlook.com, iOS Mail at 320px.
- Copy the code on a phone: one long-press selects all six digits.
- Click the button and the raw URL: both hit `/login/verify` with intact `challenge` and `token`.
- Images blocked: the two logos fall back to their alt text, the rest is unchanged.
