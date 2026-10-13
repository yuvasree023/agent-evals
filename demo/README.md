# Saved-evidence demo

The approved responsive dashboard is served from `docs/index.html` on Vercel (Hobby, main branch, root `docs`, Other preset) and GitHub Pages (main branch, /docs).

- Vercel: https://agent-evals-seven.vercel.app/
- GitHub Pages: https://yuvasree023.github.io/agent-evals/ It is a single self-contained static HTML file, with no dependency install, external runtime assets, API keys, model calls or backend.

Views:
- Overview switches between Groq M1 and separate single-trial Gemini diagnostics.
- Trace explorer searches 80 selected v1/v2 review traces, filters versions, and opens exact requests, arguments, raw tool results and final answers. Original v1 labels are preserved; v2 labels remain pending.
- Failure atlas browses all 118 historical smoke-failure audit entries by primary category. Measurement failures are separate from agent errors.
- Evidence explains scope, source paths, judge limitations and open release gates.

Source snapshot: b70c7d3, 2026-10-13. These are synthetic development records, not real customer orders or a production accuracy claim. No human label, policy, frozen judge or holdout result is changed by this visualization.

Open `docs/index.html` locally, or run `python3 -m http.server 8000 --directory docs` from the repository root and open `http://localhost:8000/`. Hash routes work without server rewrite rules. Search/filter selections are temporary; downloads contain only the selected saved trace.

Before updating the snapshot, re-check each source record, label and count. Preserve main/flip identities, version/model/protocol scope, pending labels and caveats. Escape trace data before inserting into HTML. Never add credentials, private context or live evaluation calls to the dashboard.

Current portfolio milestone is wrapped up, not scientifically validated. Further experiments are deferred. Follow `docs/completion-gates.md` before any model rerun or release claim. Vercel production follows future main pushes; review the static snapshot before committing changes. No custom domain, analytics or paid add-on is required.
