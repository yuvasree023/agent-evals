# Saved-evidence demo

The approved responsive dashboard is served from `docs/index.html` by GitHub Pages (main branch, /docs). It is a single self-contained static HTML file, with no dependency install, external runtime assets, API keys, model calls or backend.

Views:
- Overview switches between Groq M1 and separate single-trial Gemini diagnostics.
- Trace explorer searches 80 selected v1/v2 review traces, filters versions, and opens exact requests, arguments, raw tool results and final answers. Original v1 labels are preserved; v2 labels remain pending.
- Failure atlas browses all 118 historical smoke-failure audit entries by primary category. Measurement failures are separate from agent errors.
- Evidence explains scope, source paths, judge limitations and open release gates.

Source snapshot: b70c7d3, 2026-10-13. These are synthetic development records, not real customer orders or a production accuracy claim. No human label, policy, frozen judge or holdout result is changed by this visualization.

Open `docs/index.html` locally or serve the repository with `python3 -m http.server`. Hash routes work without server rewrite rules. Search/filter selections are temporary; downloads contain only the selected saved trace.

Before updating the snapshot, re-check each source record, label and count. Preserve main/flip identities, version/model/protocol scope, pending labels and caveats. Escape trace data before inserting into HTML. Never add credentials, private context or live evaluation calls to the dashboard.
