# Brief: sign-in email for RESSLab Hub

Design the HTML sign-in email for RESSLab Hub, an open-access research
database from the RESSLab at EPFL. Today the mail is plain text only and it
reads like a script wrote it. It should read like mail from an established
academic institution.

## What the mail does

One transactional mail, sent when someone asks to sign in. It carries a
six-digit code and a magic link that does the same thing. The code is for
when the mailbox is on another device, the link for when it is the same one.
Both die after 10 minutes and both are single use.

Recipients are structural engineering researchers and PhD students, in
Europe, the US and Japan. Many will see this mail before they have ever seen
the site, because a colleague sent them a link to a dataset. So the mail is
often the first impression of the project.

## Current text, to rewrite as well as redesign

Subject: `123456 is your RESSLab Hub sign-in code`

```
Hello,

Your sign-in code for RESSLab Hub is: 123456

Type it in the tab where you asked for it, or open this link on this device:

https://resslab-hub.epfl.ch/login/verify?challenge=...&token=...

The code and the link both stop working in 10 minutes, and each of them can
only be used once.

If you did not ask to sign in, you can ignore this mail.
```

Keep every piece of information above. The tone should stay plain and direct,
not corporate and not chatty. No exclamation marks, no "Welcome aboard", no
marketing voice. Short sentences, common words. Write for a reader whose
English is good but not native.

## Identity

- Name: **RESSLab Hub**. "RESSLab" in the page ink, "Hub" in EPFL red.
- Tagline: "Steel structures research · EPFL".
- Footer line used on the site: "Open-access databases and models for design
  and assessment of steel structures."
- Logo: an isometric braced steel skeleton drawn as a technical drawing.
  Double-line members, butted joints, red hairline X braces on the two visible
  faces, bolt dots, dashed footings. Files in `frontend/public/logo/`,
  `resslab-hub-mark-iso.svg` is the primary one.
- The lab sits at EPFL. The EPFL logo belongs in the footer, not the header.

## House style, already set by the app

- **EPFL red** `#e30713`, dark red `#b51f1f`.
- Ink is a soft black `#212121`, never pure black. Muted grey `#6b6b6b`,
  hairline borders `rgba(33,33,33,0.1)`, page ground `#fcfcfc`, cards white.
- **Square corners everywhere.** The app forces `border-radius: 0` globally.
  A rounded button would look foreign.
- **No shadows.** The app forces `box-shadow: none`. Depth comes from
  hairlines, not from blur.
- Typeface is Suisse Int'l, self-hosted on the site. Mail clients will not
  load it, so design on a stack of Arial and Helvetica and make sure the
  layout survives the substitution.
- The overall feel is a Swiss technical drawing: flat, precise, generous
  white space, rules instead of boxes.

## Technical constraints, these are hard

1. **Table-based layout, inline styles.** No flexbox, no grid, no `<style>`
   block you depend on. Outlook renders with Word.
2. **Max width 600px**, single column, readable at 320px.
3. **No web fonts, no JavaScript, no external CSS.**
4. **No images that must load.** Half of the recipients block images by
   default, and a code they cannot read is a broken sign-in. The logo has to
   be inline SVG or, better, drawn in table cells and borders, and the mail
   must still work with every image off. If you use an image, the code and
   the button must be live text, never a picture.
5. **Dark mode.** Apple Mail and Outlook invert colours on their own. Pick
   colours that survive inversion, and test the red on a dark ground.
6. **The code must be selectable text**, large, with generous letter spacing,
   easy to copy on a phone. Not an image, not split across elements.
7. **The link appears twice**: as a button and as the raw URL underneath, for
   clients that strip the button. The URL is long, it must wrap without
   breaking the layout.
8. **Plain text alternative** stays in the mail as the fallback part. Write
   that version too, and make it good on its own.
9. No tracking pixel, no unsubscribe link. This is transactional mail, and we
   do not track opens.

## What to deliver

1. The HTML part, ready to paste into a Python f-string or a template file.
   Placeholders: `{code}`, `{link}`, `{ttl_minutes}`.
2. The plain text part, same placeholders.
3. A subject line. The current one puts the code first so it shows in the
   phone notification, which is worth keeping unless you have a better idea.
4. A screenshot or preview of light and dark rendering.

## Things to decide, tell me what you chose

- Does the mail explain what RESSLab Hub is, for the first-time reader, or
  does it stay strictly transactional? I lean towards one short line in the
  footer.
- The site is bilingual, English and French. The mail is English only today.
  Say whether the design would survive longer French strings, since French
  runs about 20 percent longer.
- Whether the security line ("if you did not ask to sign in") belongs near
  the code or in the footer.
