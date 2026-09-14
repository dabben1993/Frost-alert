# Deferred work

- resolved 2026-09-13: `AGENTS.md` install/test commands now sit after `<!-- /bmad:context -->` so a context refresh cannot overwrite them.
- source_spec: `_bmad-output/implementation-artifacts/spec-3-1-schedule-the-check-on-github-actions.md`
  summary: GitHub may disable unused public-repo schedules after 60 days of inactivity.
  evidence: Platform behavior this workflow inherits; 3.3's state commit and 3.5 operator README are the activity/docs path. Docs or a keep-alive policy would settle operator impact.
