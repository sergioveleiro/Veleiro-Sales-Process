---
name: veleiro-sync
description: Keep Claude Code and the Veleiro AI platform aligned via a GitHub-based handshake. Use whenever working in the Veleiro-Sales-Process repo, when the user mentions Veleiro, handshake, sync, or alignment, or after Claude Code changes repo/Salesforce metadata — to detect what Veleiro changed, reconcile, and record Claude's side. Propose-and-confirm before pushing.
---

# Veleiro ⇄ Claude Code sync

You are collaborating with **Veleiro**, which is two things: (1) this Salesforce
org (whose metadata lives in this repo) and (2) an **AI platform**. The two of you
stay aligned through a **handshake protocol** where the **GitHub repo is the shared
channel**: you write and push; Veleiro pulls and interprets, and vice-versa.

The goal is a seamless, always-current handshake so neither side drifts — whether
Veleiro changed something or you did.

## Ground rules

- **Autonomy = propose-and-confirm.** You may run the read-only steps (pull, status)
  freely, but **show the user what changed and ask before committing/pushing** the
  handshake update.
- The source of truth is `.veleiro/handshake.json`. Never hand-edit it — always go
  through `.veleiro/handshake.py` so the sequence, log, and rendered `HANDSHAKE.md`
  stay consistent.
- You act as party `claude_code`. Veleiro acts as party `veleiro`.

## When this skill triggers

Trigger at the start of substantive work in this repo, when the user mentions
Veleiro / handshake / sync / alignment, and **after you change repo or Salesforce
metadata** (so Veleiro learns about it).

## Procedure

1. **Fetch the other side.** `git pull --ff-only origin main` (report, don't force,
   if it can't fast-forward — Veleiro may have diverged; reconcile with the user).

2. **Check alignment.**
   ```
   python3 .veleiro/handshake.py status
   ```
   Exit `0` = aligned (both parties acked current sequence and metadata is unchanged).
   Exit `3` = drift. Read the `alignment` line to see why.

3. **Interpret drift:**
   - *Veleiro moved* (`updated_by: veleiro`, its `acked_sequence` ahead / new log
     entries): read `.veleiro/log.jsonl` tail and any changed metadata to understand
     what Veleiro did, then summarize it for the user.
   - *Metadata changed* (`live_checksum` ≠ recorded): someone changed Salesforce
     config. Summarize the diff (`git log`, `git diff`).
   - *You are behind*: you have unacked changes to record.

4. **Reconcile & record your side** (after summarizing to the user):
   ```
   python3 .veleiro/handshake.py ack --action "<concise description of what you did / acknowledged>"
   ```
   This bumps the sequence, refreshes the metadata checksum, appends to the log, and
   re-renders `HANDSHAKE.md`.

5. **Propose the push.** Show the user the updated `handshake.py status` and the diff
   of `.veleiro/`. On approval:
   ```
   git add .veleiro/ && git commit -m "handshake: <summary>" && git push origin main
   ```

## Leaving a message for Veleiro

To hand Veleiro a note without a full ack:
```
python3 .veleiro/handshake.py post --message "<note for Veleiro>"
```

## If Veleiro needs to write back

Veleiro updates its own entry with:
```
python3 .veleiro/handshake.py ack --party veleiro --action "<what Veleiro did>"
```
or by writing `handshake.json` directly per protocol `veleiro-handshake/v1`, then
pushing to `sergioveleiro/Veleiro-Sales-Process`. Next time this skill runs you will
pull that, see Veleiro's `acked_sequence` advance, and reconcile.

## Health check

Alignment is ✅ only when **both** parties' `acked_sequence` equals `sequence` **and**
the live metadata checksum matches the recorded one. Anything else is drift to resolve.
