- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-installable-frost-alert-package.md`
  summary: Move `uv sync` / `uv run pytest` in `AGENTS.md` outside the managed `bmad:context` block so a context refresh cannot overwrite them.
  evidence: The commands were added inside the refresh-replaced markers, as the file itself instructs preserving text outside those markers. Fixing it means editing an agent-context file, which this review defers.
