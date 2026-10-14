# Known Issues

Issues found by reading the code (see [ARCHITECTURE.md](ARCHITECTURE.md) for how the pieces
fit together). All twelve have been fixed in the code; issue 1 still needs manual action
outside the repository (see [Follow-ups](#follow-ups)).

Severity: 🔴 high · 🟠 medium · 🟡 low

| # | Severity | Area | Summary | Status |
| --- | --- | --- | --- | --- |
| 1 | 🔴 | Security | Third-party API credentials committed in a template | Fixed in code; **revoke keys** |
| 2 | 🟠 | Security / config | Hard-coded `SECRET_KEY` and reCAPTCHA key | Fixed |
| 3 | 🟠 | Renderer | Only about half of the requested harmonics are animated | Fixed |
| 4 | 🟠 | Renderer | Trails and animation time are not reset between plots | Fixed |
| 5 | 🟠 | SVG parsing | `<polyline>` / `<polygon>` handling is broken | Fixed |
| 6 | 🟡 | SVG parsing | Transforms and basic shapes are ignored | Fixed |
| 7 | 🟡 | Layout | Client canvas size ignored; magic `+1500i` offset | Fixed |
| 8 | 🟡 | CLI | `python fourier.py file.svg N` crashes | Fixed |
| 9 | 🟡 | Performance | Slow, synchronous coefficient computation | Fixed |
| 10 | 🟡 | Maintenance | Duplicate entry points (`app.py` / `main.py`) | Fixed |
| 11 | 🟡 | Maintenance | Debug leftovers, unused imports, committed bytecode | Fixed |
| 12 | 🟡 | UX | File picker accepts `image/*` but only `.svg` is valid | Fixed |

---

## How each issue was fixed

1. **Credentials in `templates/fourier.html`.** The commented-out CloudConvert JWT and
   ConvertApi secret, and the dead conversion code around them, were deleted. They remain in
   git history, so they must be revoked (see below).
2. **Hard-coded config.** `SECRET_KEY` is read from the environment. If it's missing, the app
   logs a warning and uses a random per-process key. The unused reCAPTCHA key was removed, and
   so was `flask-appconfig`: it pins `Flask<1.0`, which can't import modern Jinja2, so a fresh
   `pip install -r requirements.txt` produced an app that wouldn't start.
3. **Missing harmonics.** `draw()` now chains all `2N − 2` rotating vectors per path. The
   slider value is parsed with `parseInt` and captured at submit time, so moving the slider
   during a request can no longer mis-slice the response.
4. **Stale trails.** `init_fourier` resets `wave` and `time`.
5. **Polylines / polygons.** `svg2paths_ext.py` was removed; parsing now uses
   `svgpathtools.Document`, which converts polylines and polygons correctly.
6. **Transforms and shapes.** `Document(...).paths()` applies element and group transforms and
   reads `<rect>`, `<circle>` and `<ellipse>`. Example: the kiwi's ellipse shadow now appears.
   The renderer's Y-axis flip was removed. It only compensated for potrace's ignored
   `scale(0.1,-0.1)` group transform, and it drew SVGs without that transform upside down.
7. **Layout.** The server fits the bounding box of all paths into the canvas size the client
   sends (centred, 20 px margin). The `/10`, `+1500i`, `r/2` and `(150, 150)` constants are gone.
8. **CLI.** `python fourier.py file.svg N` works and prints JSON for a 600×600 canvas.
9. **Performance.** Each path is sampled once (vectorised per segment) and all coefficients come
   from one FFT. The examples are 100–250× faster (e.g. `img1.svg` at N=101: 5.8 s → 0.06 s),
   and accuracy improved too, since high frequencies are no longer under-sampled. `N` is capped
   at 1000 on the server.
10. **Duplicate entry points.** `main.py` was deleted; `app.py` takes the port from `$PORT`
    (default 8002).
11. **Leftovers.** Removed `print`/`console.log` calls (including the per-frame one), dead
    code, the unused `request.files['file']` upload, and unused imports along with their
    requirements (`matplotlib`, `svgutils`, `scipy`, `flask-appconfig`, the `itsdangerous`
    pin). Added `.gitignore` and untracked `__pycache__/`. The shadowed loop variable went
    with the rewrite.
12. **File picker / errors.** The picker accepts `.svg,image/svg+xml`. Validation and parse
    failures return HTTP 400 with `{"errors": {...}}`, and the page shows them in an alert.

## Follow-ups

- **Revoke the leaked credentials (issue 1).** The CloudConvert API JWT and the ConvertApi
  secret are still in this repository's git history, and in the upstream repository's. Revoke
  them with the providers. Rewriting history (`git filter-repo` / BFG, then a force-push) only
  hides them afterwards, and only in repositories you control.
- **Set `SECRET_KEY` in production**, especially with more than one gunicorn worker.
- The remaining design limitations (one chain per `<path>`, large responses for detailed SVGs,
  fixed canvas size) are listed in [ARCHITECTURE.md](ARCHITECTURE.md#known-limitations).
