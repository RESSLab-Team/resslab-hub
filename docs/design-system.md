# Design system

What the app looks like, and where each value comes from. Read this before
you write CSS, pick a colour, or fight a Vuetify component. The dashboard
engine that uses it is in [dashboard-architecture.md](dashboard-architecture.md).

The short version: the values live in one token file, the rules live in five
sheets stacked in cascade layers, and you almost never need `!important`.

## Where the design comes from

Two Claude Design projects, in Pierre's claude.ai account:

- **"EPFL Design System"** (0.1.0, June 2026) is the heritage: the official
  EPFL web charter (`epfl-si/elements`) turned into tokens, Suisse Int'l and
  a web UI kit. The four handoff screens for the hub (dashboard, tool pages,
  specimen drawer, chart library) were drawn on it. That bundle is not in
  git. It sits, untracked, in the sibling checkout `../resslab-hub-redesign/`:
  `design_handoff_resslab_hub/README.md` (the spec and the softer-contrast
  pass), `screens/screenshots/*.png`, `screens/_ds/.../colors_and_type.css`
  (what `epfl-tokens.css` was first copied from), and
  `handoff_tool_layout/LAYOUT-SPEC.md` (the rail + stage system behind
  `tool-pages.css`).
- **"RESSLab Hub - Design System"** (1.0.0, 2026-08-24) goes the other way:
  it was extracted from this code, from the `stage` branch. It carries the
  same tokens and title roles, the ECharts theme, the `rl` icons, the marks,
  and an app UI kit (sidebar, buttons, key numbers, tiles, filter rail, data
  table, chart cells, hero) whose class names match `app.css` one to one.
  Use it to make mocks and new screens with the brand. It has no dark mode,
  on purpose.

The code is the source. When a token changes here, re-sync the RESSLab Hub
project (the `DesignSync` tool in Claude Code reads and writes it), or the
next mock will be drawn with stale values.

Where the app departs from the EPFL heritage, all on purpose:

|                      | EPFL system                                                        | App                                                               |
| -------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| brand red            | `--epfl-red` is web red `#ff0000`, `--epfl-red-print` is `#e30713` | only the print red, as `--epfl-red`                               |
| structural hairlines | soft black in the first screens                                    | `#cfcfcf` (`--epfl-gray-150`), and table gridlines lighter still  |
| series colours       | red, canard, blue, grey                                            | Okabe-Ito, red never a series                                     |
| links                | underlined                                                         | never underlined                                                  |
| icons                | Feather                                                            | Material Design Icons through Vuetify, plus the `rl` database set |
| dark mode            | none                                                               | `body.theme-dark` re-assigns the decisions                        |

Where the RESSLab Hub mirror is ahead of the code, as of 1.0.0: it publishes
the chart ink and the eight series as `--chart-*` custom properties (here they
are constants in `plugins/echarts-theme.ts` and `utils/palette.ts`), it has
`--space-1` to `--space-6`, status intents (`--success`, `--info`,
`--warning`, `--danger`), a `.tnum` utility for tabular figures, and a 2px
red `:focus-visible` outline on buttons. None of those exist here yet, except
`--warning` (orange, for the unverified rows of #253: a rule or a tint, never
text, the orange is too light to read). Add the others to `epfl-tokens.css`
if a component needs them, do not invent a different name.

## Where it lives

Everything is under `frontend/src/assets/styles/`, plus two plugins:

| File                                          | What it holds                                                              |
| --------------------------------------------- | -------------------------------------------------------------------------- |
| `styles/index.css`                            | the only sheet `main.ts` imports. Declares the layers, pulls the others in |
| `styles/epfl-tokens.css`                      | every custom property, light and dark                                      |
| `styles/fonts.css`                            | the five `@font-face` for Suisse Int'l                                     |
| `styles/base.css`                             | element defaults and the five title roles                                  |
| `styles/vuetify-overrides.css`                | the broad rules that restyle Vuetify components                            |
| `styles/app.css`                              | the shell, the home page, the dashboards, the drawer                       |
| `styles/tool-pages.css`                       | the rail + stage layout of the model and fragility pages                   |
| `plugins/vuetify.ts`                          | the Vuetify theme colours, as hex                                          |
| `plugins/echarts-theme.ts`                    | the chart chrome, as hex and font strings                                  |
| `utils/palette.ts`, `utils/categoryColors.ts` | the categorical series colours                                             |

`src/settings.scss` is not a stylesheet, it configures Vuetify's SASS build:
it turns cascade layers on, drops the Material colour pack, and trims the
utility classes down to the groups we actually use. If a Vuetify utility class
(`ma-4`, `text-right`, ...) does nothing, its group is switched off there.
Re-enable the group, do not write the rule by hand.

Rules of thumb, the rest of this page explains them:

- In a component, write decisions (`--bg`, `--fg`, `--border`, `--primary`),
  never a raw option or a hex value. If the decision you need is missing, add
  it to the token file.
- A new page or component styles itself in its own `<style scoped>`, with the
  tokens. `app.css` holds the pages that came with the handoff, prefer not to
  grow it.
- A rule on a Vuetify class (`.v-card`, `.v-field`, ...) that applies app-wide
  goes in `vuetify-overrides.css`. Inside one component, write it there with
  `:deep()`.
- Never `!important` to beat Vuetify. It sits in a lower layer, a plain
  selector wins.

## Options, decisions, components

Three tiers, the vocabulary the EPFL co2-calculator docs use.

**Options** are the raw values. They name a colour or a size, not a use. Do not
put them in a component: `var(--epfl-gray-600)` says nothing about why.

| Option                             | Value                 |                                                       |
| ---------------------------------- | --------------------- | ----------------------------------------------------- |
| `--epfl-red`                       | `#e30713`             | the brand red, print red rather than screen `#ff0000` |
| `--epfl-red-dark`                  | `#b51f1f`             | hover                                                 |
| `--epfl-leman`, `--epfl-canard`    | `#00a79f`, `#007480`  | the EPFL secondary hues                               |
| `--epfl-white`                     | `#ffffff`             |                                                       |
| `--epfl-gray-100 … -600`           | `#e6e6e6` → `#707070` | five neutrals, plus `-150` for hairlines              |
| `--epfl-black`                     | `#212121`             | soft black, never pure                                |
| `--epfl-blue`, `-orange`, `-green` |                       | status only                                           |
| `--fs-h1 … --fs-xs`                | `3rem` → `0.75rem`    | the type scale, as in the EPFL handoff                |
| `--w-light … --w-bold`             | `300` → `700`         |                                                       |
| `--lh-tight … --lh-relaxed`        | `1.1` → `1.5`         |                                                       |

**Decisions** map an option to a use. This is what you write in a component.
Change one here and the whole app follows.

| Decision                                       | Resolves to               | Use it for                                                   |
| ---------------------------------------------- | ------------------------- | ------------------------------------------------------------ |
| `--bg`                                         | white                     | a card, a panel, anything raised off the page                |
| `--bg-app`                                     | `#fcfcfc`                 | the page ground behind the cards                             |
| `--bg-subtle`                                  | `#f5f5f5`                 | hover and selected fills, table head bands                   |
| `--bg-muted`                                   | gray-100                  | a filled, inactive area                                      |
| `--fg`                                         | soft black                | body text                                                    |
| `--fg-muted`                                   | gray-600                  | secondary text, axis names, captions                         |
| `--fg-subtle`                                  | gray-500                  | the quietest text that is still text                         |
| `--fg-disabled`                                | gray-300                  |                                                              |
| `--border`                                     | gray-200                  | the standard hairline                                        |
| `--border-subtle`                              | gray-100                  | a hairline that should barely show                           |
| `--border-strong`                              | gray-500                  | a border that reads as a line, not a seam                    |
| `--table-gridline`, `--table-row-stripe`       | `#ededed`, `#fafafa`      | data tables only, tuned lighter than the hairline on purpose |
| `--primary`, `--primary-hover`, `--on-primary` | red, dark red, white      | the primary action                                           |
| `--link`, `--link-hover`                       | black, red                |                                                              |
| `--font-sans`, `--font-mono`                   | Suisse Int'l, system mono |                                                              |
| `--radius`, `--radius-lg`, `--radius-sm`       | `0`                       | see "square corners" below                                   |
| `--focus-ring`                                 | red at 25%                | keyboard focus                                               |
| `--t-fast`, `--t-base`                         | `0.15s`, `0.2s`           | transitions                                                  |

**Component classes** are the shapes built from those. The five title roles in
`base.css` are the ones you will use most:

| Class        | Role                                       |
| ------------ | ------------------------------------------ |
| `.t-page`    | the per-view H1, large and regular weight  |
| `.t-card`    | a chart, table or carousel card heading    |
| `.t-panel`   | an uppercase control or data panel heading |
| `.t-eyebrow` | the small red category line above a title  |
| `.t-subhead` | a small ruled field-group label            |

Each is driven by its own `--title-*` tokens, so the five treatments stay
uniform across the app. `.ey-red` and `.ey-mut` split an eyebrow into its red
segment and its muted qualifier (`EyebrowText.vue` does this for you).

The page-level scaffolds are `DashboardShell.vue`, `PageHeader.vue` and
`ToolShell.vue` in `components/commons/`. None of them carries its own
`<style>`, they consume the classes in `app.css`.

## The decisions, and why

- **Suisse Int'l**, self-hosted in `public/fonts` as woff2, weights 300 to 700.
  It is a commercial face licensed to EPFL properties, so only bundle it in
  EPFL-operated deployments. `--font-sans` falls back to Arial, and the app
  still reads correctly there.
- **Soft black, never pure.** `#212121` for ink, greys down from it. Pure black
  next to the red looks harsh on a white ground.
- **Square corners everywhere.** `--radius` is `0`, and one rule in
  `vuetify-overrides.css` flattens Vuetify's cards, buttons, fields, chips,
  menus, tooltips and alerts. The radius tokens are kept rather than deleted
  from every caller, so the whole app can be un-flattened from one line. Real
  circles (legend dots, slider thumbs) set `border-radius: 50%` themselves and
  are not matched by that rule.
- **No shadows.** Depth comes from hairlines. The `--shadow*` tokens survive for
  the popover over the filter rail and the toggle thumb in `ToolSwitch.vue`,
  nothing else uses them.
- **Sentence case.** Titles and buttons in sentence case. Uppercase only for
  eyebrows and panel labels. No emoji, no gradients.
- **Numbers in mono.** IDs, units, values and axis ticks use `--font-mono`
  with tabular figures, so columns line up.
- **Links are never underlined.** The EPFL system underlines them, the redesign
  does not. Underline only where you opt back in.
- **Red is reserved.** The primary action, the active nav item, the eyebrow, and
  chart brush bands. It is never a series colour.
- **Categorical chart colours** come from the Okabe-Ito slots in
  `utils/palette.ts`, handed out once per field by
  `useDataset(...).colorFor(field)`. Never colour a series from its position in
  the filtered data. The full rule is in
  [dashboard-architecture.md](dashboard-architecture.md).

## The same value, three times

A brand value exists in three files and has to. The token is the source, but
Vuetify's theme wants plain hex (it splits it into the rgb triplet behind
`--v-theme-*`), and ECharts draws on a canvas where `var(--epfl-red)` resolves
to nothing.

| Meaning     | Token             | `plugins/vuetify.ts` | `plugins/echarts-theme.ts` |
| ----------- | ----------------- | -------------------- | -------------------------- |
| brand red   | `--epfl-red`      | `primary`            | `RED`                      |
| leman       | `--epfl-leman`    | `accent`             |                            |
| soft black  | `--epfl-black`    |                      | `INK`                      |
| hairline    | `--epfl-gray-300` |                      | `AXIS`                     |
| tick ink    | `--epfl-gray-500` |                      | `TICK`                     |
| dark ground | dark `--bg`       | dark `background`    |                            |
| brand face  | `--font-sans`     |                      | `SANS`                     |

Change one, change the others. `plugins/__tests__/designTokens.spec.ts` reads
the token file and fails if they drift, so you will find out at test time
rather than by looking at a chart next to a button.

## Dark mode

Two mechanisms, toggled together in `App.vue`'s `applyTheme()`: `theme.change()`
for Vuetify, and a `theme-dark` class on `<body>` for the tokens. The token
file re-assigns fifteen custom properties under `body.theme-dark`, so
anything written with decisions follows automatically.

Only reach for the class in JavaScript when a canvas needs a colour it cannot
inherit, the way `DistributionBrush.vue` does:

```ts
const dark = document.body.classList.contains("theme-dark");
```

## Cascade layers

`index.css` declares the order once:

```css
@layer vuetify, tokens, base, overrides, app;
```

Lowest priority first:

| Layer       | Holds                                           |
| ----------- | ----------------------------------------------- |
| `vuetify`   | everything Vuetify emits, in its own sub-layers |
| `tokens`    | the custom properties                           |
| `base`      | element defaults, the title roles               |
| `overrides` | the broad rules that restyle Vuetify components |
| `app`       | the shell, the pages, the tool pages            |

Vuetify is layered by `$layers: true` in `src/settings.scss` (its stylesheets)
and `theme: { layers: true }` in `plugins/vuetify.ts` (the runtime theme sheet).
Both matter: without them Vuetify's CSS is unlayered and beats every layer
here.

Two rules follow from this:

1. **A component's `<style>` block is unlayered, and unlayered beats every
   layer.** A component always wins over the page. That is on purpose.
2. **Never `!important` to beat Vuetify.** A plain selector in `overrides` or
   `app` already wins. If your rule does not apply, the problem is the layer or
   the element, not the specificity.

Two places in the global sheets still use `!important`, both for a reason:
`tool-pages.css` kills transitions under `prefers-reduced-motion`, and
`app.css` strips the border off the dashboard table card. That second one
fights `SimpleTable.vue`'s own scoped `.stbl` border, which is unlayered and so
outranks the page. The clean fix is a variant prop on `SimpleTable`, not a
louder rule.

One trap: for `!important` declarations the layer order is
reversed, so Vuetify's `!important` utilities (`.elevation-*`,
`.font-weight-*`, `.text-h1` and friends) still beat our normal rules. Prefer
the `.t-*` roles over Vuetify's typography utilities.

## Use cases

**A button.** Vuetify's is already square and flat, so pass a colour and stop:

```vue
<v-btn color="primary" variant="outlined">Download</v-btn>
```

Do not set `rounded` or `elevation`. For a plain button outside Vuetify, the
app classes are `.btn` with `.btn-primary`, `.btn-secondary` or `.btn-ghost`.

**A card or a panel.** Hairline, white ground, square. The title takes a role:

```vue
<div class="my-panel">
  <h3 class="t-panel">Filters</h3>
</div>

<style scoped>
.my-panel {
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 16px;
}
</style>
```

**A page head.** Use the scaffold rather than rebuilding it:

```vue
<PageHeader>
  <template #eyebrow><EyebrowText text="Columns · Model" /></template>
  ...
</PageHeader>
```

**A chart.** The theme is provided app-wide in `main.ts`, so `<v-chart>` picks
up the axes, the square markers and the tooltip chrome by itself. Take the
series colour from the dataset, never from a literal:

```ts
const color = useDataset(...).colorFor('connection_type')
```

**Restyling one Vuetify component inside yours.** Write it in the component's
own `<style scoped>` with a plain selector. No `.v-application` chain, no
`!important`:

```vue
<style scoped>
.my-filter :deep(.v-field) {
  font-size: 14px;
}
</style>
```

## Changing a token

1. Edit `styles/epfl-tokens.css`.
2. If it is one of the values in the table above, update
   `plugins/vuetify.ts` and `plugins/echarts-theme.ts` too.
3. `pnpm run test:unit`, `designTokens.spec.ts` catches a copy you missed.
4. Look at home, one dashboard, one tool page and a detail drawer, in light and
   dark. Those four cover most of the app.
5. Re-sync the "RESSLab Hub - Design System" project in Claude Design, so
   mocks keep the new value.

## Known gaps

- The Vuetify theme and the ECharts theme copy their colours by hand. Feeding
  both from one TypeScript source would remove the copies, and the guard test
  with them.
- `app.css` still sets some sizes in raw px (`.hero-title` 44px,
  `.keynum-num` 56px, `.section-title` 32px) instead of the `--fs-*` scale.
- Vuetify's own SASS variables are untouched, so the square corners come from
  an override rule rather than from `$border-radius-root: 0`. Setting it at the
  source would drop the rule, but it moves every rounded size map at once and
  needs its own visual pass.
