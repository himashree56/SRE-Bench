# SREBench Fix: Resolve HF Space /reset 404

## Plan Steps:
- [x] 1. Understand codebase and identify issue (local OpenEnv sys.path breaks in HF Space).
- [x] 2. Edit server/app.py: Remove sys.path inserts for ../OpenEnv.
- [x] 3. Edit server/models.py: Remove sys.path inserts for ../OpenEnv.
- [x] 4. Test locally: Run server and curl /reset. (Returned HTTP 200 with valid observation JSON).
- [ ] 5. User re-deploys to HF Space (git add/commit/push → Space rebuilds).
- [x] Added Dockerfile/inference.py fixes for HF Space.
- [ ] 6. Re-run validate-submission.sh to confirm fix.
