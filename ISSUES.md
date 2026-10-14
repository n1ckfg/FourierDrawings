# Known Issues

Issues found by reading the code (see [ARCHITECTURE.md](ARCHITECTURE.md) for how the pieces
fit together). They haven't been reproduced at runtime. Each entry lists where the problem is,
what goes wrong, and a suggested fix.

Severity: 🔴 high · 🟠 medium · 🟡 low

| # | Severity | Area | Summary |
| --- | --- | --- | --- |
| 1 | 🔴 | Security | Third-party API credentials committed in a template |
| 2 | 🟠 | Security / config | Hard-coded `SECRET_KEY` and reCAPTCHA key |
| 3 | 🟠 | Renderer | Only about half of the requested harmonics are animated |
| 4 | 🟠 | Renderer | Trails and animation time are not reset between plots |
| 5 | 🟠 | SVG parsing | `<polyline>` / `<polygon>` handling is broken |
| 6 | 🟡 | SVG parsing | Transforms and basic shapes are ignored |
| 7 | 🟡 | Layout | Client canvas size ignored; magic `+1500i` offset |
| 8 | 🟡 | CLI | `python fourier.py file.svg N` crashes |
| 9 | 🟡 | Performance | Slow, synchronous coefficient computation |
| 10 | 🟡 | Maintenance | Duplicate entry points (`app.py` / `main.py`) |
| 11 | 🟡 | Maintenance | Debug leftovers, unused imports, committed bytecode |
| 12 | 🟡 | UX | File picker accepts `image/*` but only `.svg` is valid |

---

## 1. 🔴 Third-party API credentials committed in a template

**Where:** [templates/fourier.html](templates/fourier.html#L65-L86)

Commented-out code contains a full **CloudConvert API JWT** (line 66) and a **ConvertApi
secret** (line 78). Commented-out code still ships in the HTML sent to every visitor, and the
values are in git history.

**Fix:** Revoke both credentials with their providers, delete the dead code, and if needed
scrub history (`git filter-repo` / BFG). Any future image→SVG conversion should run
server-side with keys read from environment variables.

## 2. 🟠 Hard-coded `SECRET_KEY` and reCAPTCHA key

**Where:** [app.py](app.py#L17-L20) (same in [main.py](main.py#L17-L20))

`SECRET_KEY = 'devkey'` signs sessions and CSRF tokens; a known value makes CSRF protection
pointless. The reCAPTCHA public key is also hard-coded (and unused).

**Fix:** Load config from the environment (e.g. `os.environ["SECRET_KEY"]`) or through the
already-installed Flask-AppConfig, and remove the unused reCAPTCHA setting.

## 3. 🟠 Only about half of the requested harmonics are animated

**Where:** [static/js/fourier.js](static/js/fourier.js#L141-L144)

The server returns `2N − 1` coefficients per path (`c_0, c_1, c_−1, …, c_±(N−1)`), but the
draw loop iterates `i = 1 … N−1` within each path's slice, so only the first `N − 1` rotating
vectors (roughly frequencies up to `±N/2`) are drawn. The rest are computed and sent, then never
used.

**Fix:** Loop `i = 1 … 2N−2` (i.e. `i < 2 * n - 1`), or have the server compute only what the
client draws. Also parse the slider value as a number (`parseInt`) rather than relying on
implicit string coercion of `n`.

## 4. 🟠 Trails and animation time are not reset between plots

**Where:** [static/js/fourier.js](static/js/fourier.js#L52-L75), [L177](static/js/fourier.js#L177)

`init_fourier` pushes new empty arrays onto the global `wave` but never clears it, so after a
re-plot `wave[j]` still holds the previous drawing's trail (and extra arrays pile up). `time`
also keeps growing across plots.

**Fix:** At the start of `init_fourier`, set `wave = []` and `time = 0`.

## 5. 🟠 `<polyline>` / `<polygon>` handling is broken

**Where:** [svg2paths_ext.py](svg2paths_ext.py#L56-L66)

`svg2paths(pl['points'])` is called with a points string, but `svg2paths` expects a file path
and returns `(paths, attributes)`, not a `d` string. SVGs containing these elements will raise
or produce garbage; for polygons, the code then tries to append `'z'` to a tuple.

**Fix:** Use `svgpathtools.polyline2pathd(points)` / `polygon2pathd(points)` (or build
`"M x0,y0 L x1,y1 …"` manually).

## 6. 🟡 Transforms and basic shapes are ignored

**Where:** [svg2paths_ext.py](svg2paths_ext.py)

Only `<path>`, `<polyline>`, `<polygon>` and `<line>` are read. `<circle>`, `<ellipse>`,
`<rect>` are dropped, and `transform="…"` attributes (including on parent `<g>` elements) are
not applied, so many real-world SVGs render incomplete or misplaced.

**Fix:** Use `svgpathtools.Document(...).paths()` (applies group transforms) or a library such
as `svgelements` that flattens shapes and transforms.

## 7. 🟡 Client canvas size ignored; magic `+1500i` offset

**Where:** [fourier.py](fourier.py#L114-L117), [L143](fourier.py#L143);
[templates/fourier.html](templates/fourier.html#L131-L138)

The client sends `canvas_width` / `canvas_height`, but `calculate_fourier_for_path` overwrites
them with "bbox extent / 10". The `c_0` term adds a constant `1500i`, which only lines up with
the hard-coded 1500×1650 px canvas and the Y-axis flip in `init_fourier`. The renderer also
halves every radius (`r / 2`) and starts every path from a fixed `(150, 150)`. Together, the
drawing's size and position depend on the input SVG's units, not on the canvas.

**Fix:** Compute one scale factor and offset from the global bbox and the real canvas size
(with a margin), apply it to all paths, and drop the magic constants (`/10`, `+1500i`, `r/2`,
`(150, 150)`).

## 8. 🟡 `python fourier.py file.svg N` crashes

**Where:** [fourier.py](fourier.py#L74-L76), [L167-L170](fourier.py#L167-L170)

`calculate_fourier_for_svg_path` calls `calculate_fourier_for_path(paths[count], count, 600, 600)`:
the `form` argument is missing, a single `Path` is passed where a list is expected, and the
path is indexed by `count`.

**Fix:** Call `calculate_fourier_for_path(None, paths, count, 600, 600)` and remove the unused
`form` parameter from the function signature.

## 9. 🟡 Slow, synchronous coefficient computation

**Where:** [fourier.py](fourier.py#L84-L86), [L139-L146](fourier.py#L139-L146)

For every path and every frequency, `fixed_quad` evaluates `path.point(t)` at 500 points through
`np.vectorize` (a Python loop). The cost is `paths × (2N−1) × 500` point evaluations inside one
request. With the slider maximum of 1000 and a detailed SVG, this can take a very long time or
hit worker timeouts under gunicorn.

**Fix:** Sample each path once (`t = linspace(0, 1, M)`, `path.point(t)` is vectorised in
recent svgpathtools), then get all coefficients at once with `np.fft.fft(samples) / M`. Cap `N`
on the server as well.

## 10. 🟡 Duplicate entry points

**Where:** [app.py](app.py), [main.py](main.py)

The two files are identical apart from the dev-server port (8002 vs 8000), so they can drift
apart.

**Fix:** Keep one (e.g. `app.py`), take the port from an env var or CLI flag, and delete the other.

## 11. 🟡 Debug leftovers, unused imports, committed bytecode

**Where:**
- `print(...)` calls in [fourier.py](fourier.py#L33) and [L112-L128](fourier.py#L112-L128)
- `console.log` in [templates/fourier.html](templates/fourier.html#L45-L62)
- **`console.log` on every animation frame** in [static/js/fourier.js](static/js/fourier.js#L129) (measurable slowdown)
- Unused imports in [fourier.py](fourier.py#L6-L16): `matplotlib`, `svgutils`, `parse`,
  `os`, `secure_filename`, `smoothed_path`; `request.files['file']` is read only to print it
  (and `canvas_width`/`canvas_height` are sent by the client only to be overwritten, see #7)
- Unused imports in [svg2paths_ext.py](svg2paths_ext.py#L4-L5)
- Large blocks of commented-out code in `fourier.js`, `fourier.py`, `fourier.html`
- `__pycache__/` committed to git; no `.gitignore`
- `matplotlib` and `svgutils` in [requirements.txt](requirements.txt) only because of the unused imports
- Inner loop variable `i` in `calculate_fourier_for_path` shadows the outer `enumerate` index

**Fix:** Switch to `current_app.logger`, remove dead code and unused imports and their
requirements, add a `.gitignore`, and `git rm -r --cached __pycache__`.

## 12. 🟡 File picker accepts `image/*` but only `.svg` is valid

**Where:** [templates/fourier.html](templates/fourier.html#L12)

The input offers any image type, but `FileAllowed(['svg'])` rejects everything except SVG.
On failure the endpoint returns `{"data": {...errors}}` with HTTP 200, the client passes it to
`init_fourier` as if it were coefficients, and the user sees nothing.

**Fix:** Use `accept=".svg,image/svg+xml"`, return a 400 status on validation errors, and show
the error in the UI.
