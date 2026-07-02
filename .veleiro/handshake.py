#!/usr/bin/env python3
"""
Veleiro <-> Claude Code handshake protocol (v1).

The GitHub repo is the shared channel. Both parties read/write a small state
file so each knows what the other last did and whether they are aligned.

State lives in .veleiro/:
  - handshake.json : machine-readable source of truth
  - log.jsonl      : append-only exchange log
  - HANDSHAKE.md   : human-readable mirror (regenerated from json)

Subcommands:
  init                      Create state files if missing.
  status                    Print current state + drift assessment (exit 0 aligned, 3 drift).
  ack   [--action MSG]      Record that a party has seen/acked current state.
  post  --message MSG       Append a message to the log without a full ack.
  render                    Regenerate HANDSHAKE.md from handshake.json.

Common flag:
  --party {claude_code,veleiro}   Who is acting (default: claude_code).
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
STATE = os.path.join(ROOT, "handshake.json")
LOG = os.path.join(ROOT, "log.jsonl")
MD = os.path.join(ROOT, "HANDSHAKE.md")

PROTOCOL = "veleiro-handshake/v1"
PARTIES = ("claude_code", "veleiro")
METADATA_DIR = os.path.join(REPO, "force-app")

# Mirror the handshake into a Salesforce Static Resource so the Veleiro platform
# (which only ingests recognized Salesforce metadata under force-app/) can see it.
STATIC_DIR = os.path.join(METADATA_DIR, "main", "default", "staticresources")
MIRROR_JSON = os.path.join(STATIC_DIR, "Veleiro_Handshake.json")
MIRROR_META = os.path.join(STATIC_DIR, "Veleiro_Handshake.resource-meta.xml")
MIRROR_META_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<StaticResource xmlns="http://soap.sforce.com/2006/04/metadata">\n'
    "    <cacheControl>Public</cacheControl>\n"
    "    <contentType>application/json</contentType>\n"
    "    <description>Veleiro &lt;-&gt; Claude Code handshake state (veleiro-handshake/v1). "
    "Machine-readable channel delivered as Salesforce metadata so the Veleiro platform can see it "
    "via git pull / org retrieve. Source of truth mirror of .veleiro/handshake.json. "
    "Safe to delete; recreated by .veleiro/handshake.py.</description>\n"
    "</StaticResource>\n"
)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def metadata_checksum():
    """Stable hash of the Salesforce metadata tree so either side can detect
    config changes independent of git history."""
    if not os.path.isdir(METADATA_DIR):
        return None
    h = hashlib.sha256()
    for dirpath, _dirs, files in sorted(os.walk(METADATA_DIR)):
        for name in sorted(files):
            # Exclude the handshake mirror itself, else writing it would perturb
            # the checksum and cause perpetual drift.
            if "Veleiro_Handshake" in name:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, REPO)
            h.update(rel.encode())
            try:
                with open(path, "rb") as fh:
                    h.update(fh.read())
            except OSError:
                continue
    return h.hexdigest()[:16]


def default_state():
    return {
        "protocol": PROTOCOL,
        "repo": "sergioveleiro/Veleiro-Sales-Process",
        "sequence": 0,
        "updated_at": None,
        "updated_by": None,
        "metadata_checksum": None,
        "parties": {
            "claude_code": {
                "role": "engineering assistant (Anthropic / Claude Code)",
                "last_seen": None,
                "last_action": None,
                "acked_sequence": 0,
                "status": "initializing",
            },
            "veleiro": {
                "role": "AI platform",
                "last_seen": None,
                "last_action": None,
                "acked_sequence": 0,
                "status": "awaiting_first_contact",
            },
        },
        "open_items": [],
    }


def load():
    if not os.path.exists(STATE):
        return default_state()
    with open(STATE) as fh:
        return json.load(fh)


def save(state):
    with open(STATE, "w") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")


def append_log(entry):
    with open(LOG, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def mirror_state(state):
    """Write the handshake state into a Salesforce Static Resource so Veleiro sees it."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    if not os.path.exists(MIRROR_META):
        with open(MIRROR_META, "w") as fh:
            fh.write(MIRROR_META_XML)
    payload = dict(state)
    payload["_note"] = (
        "Handshake channel between the Veleiro AI platform and Claude Code. "
        "Full protocol, log and skill live in the git repo under .veleiro/ and "
        ".claude/skills/veleiro-sync/ (outside force-app, so not visible to Veleiro's "
        "metadata sync — this Static Resource is the metadata-native mirror). "
        "Veleiro: to ack, write your entry here or run .veleiro/handshake.py "
        "ack --party veleiro, then push."
    )
    with open(MIRROR_JSON, "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def render_md(state):
    p = state["parties"]

    def line(key):
        d = p[key]
        return (
            f"- **{key}** ({d['role']}) — status: `{d['status']}`, "
            f"seq acked: `{d['acked_sequence']}`, last: {d['last_action'] or '—'} "
            f"({d['last_seen'] or '—'})"
        )

    drift = assess_drift(state)
    items = "\n".join(f"- {i}" for i in state["open_items"]) or "- (none)"
    md = f"""# 🤝 Veleiro ⇄ Claude Code — Handshake

> Auto-generated from `handshake.json`. Do not edit by hand — run `handshake.py render`.

**Protocol:** `{state['protocol']}`
**Channel:** GitHub `{state['repo']}`
**Sequence:** `{state['sequence']}` · last updated by `{state['updated_by']}` at {state['updated_at']}
**Metadata checksum:** `{state['metadata_checksum']}`
**Alignment:** {drift['summary']}

## Parties
{line('claude_code')}
{line('veleiro')}

## Open items
{items}

---
*If you are the Veleiro platform reading this: the link is live. Update your entry
via `handshake.py ack --party veleiro --action "<what you did>"`, or write the JSON
directly following `{state['protocol']}`, then push to `{state['repo']}`.*
"""
    with open(MD, "w") as fh:
        fh.write(md)
    mirror_state(state)


def assess_drift(state):
    """Determine whether the two parties are aligned."""
    seq = state["sequence"]
    cc = state["parties"]["claude_code"]["acked_sequence"]
    vel = state["parties"]["veleiro"]["acked_sequence"]
    live_checksum = metadata_checksum()
    checksum_changed = (
        live_checksum is not None and live_checksum != state["metadata_checksum"]
    )

    aligned = cc == seq and vel == seq and not checksum_changed
    if aligned:
        return {"aligned": True, "summary": "✅ aligned — both parties acked the current sequence."}

    reasons = []
    if cc < seq:
        reasons.append(f"claude_code is behind (acked {cc} < seq {seq})")
    if vel < seq:
        reasons.append(f"veleiro is behind (acked {vel} < seq {seq})")
    if checksum_changed:
        reasons.append(
            f"metadata changed since last recorded checksum "
            f"({state['metadata_checksum']} → {live_checksum})"
        )
    return {"aligned": False, "summary": "⚠️ drift — " + "; ".join(reasons), "reasons": reasons}


def cmd_init(args):
    created = []
    if not os.path.exists(STATE):
        save(default_state())
        created.append("handshake.json")
    if not os.path.exists(LOG):
        open(LOG, "a").close()
        created.append("log.jsonl")
    render_md(load())
    created.append("HANDSHAKE.md (rendered)")
    print("init:", ", ".join(created) if created else "nothing to create")


def cmd_status(args):
    state = load()
    drift = assess_drift(state)
    print(json.dumps({
        "protocol": state["protocol"],
        "sequence": state["sequence"],
        "updated_by": state["updated_by"],
        "updated_at": state["updated_at"],
        "recorded_checksum": state["metadata_checksum"],
        "live_checksum": metadata_checksum(),
        "parties": {k: {"acked_sequence": v["acked_sequence"], "status": v["status"],
                        "last_action": v["last_action"]} for k, v in state["parties"].items()},
        "alignment": drift["summary"],
    }, indent=2))
    sys.exit(0 if drift["aligned"] else 3)


def cmd_ack(args):
    state = load()
    party = args.party
    state["sequence"] += 1
    state["updated_at"] = now()
    state["updated_by"] = party
    state["metadata_checksum"] = metadata_checksum()
    state["parties"][party]["last_seen"] = state["updated_at"]
    state["parties"][party]["last_action"] = args.action or "acknowledged current state"
    state["parties"][party]["acked_sequence"] = state["sequence"]
    state["parties"][party]["status"] = "online"
    save(state)
    append_log({
        "ts": state["updated_at"], "party": party, "type": "ack",
        "sequence": state["sequence"], "action": state["parties"][party]["last_action"],
        "checksum": state["metadata_checksum"],
    })
    render_md(state)
    print(f"ack recorded: {party} @ sequence {state['sequence']}")


def cmd_post(args):
    state = load()
    party = args.party
    ts = now()
    state["parties"][party]["last_seen"] = ts
    state["parties"][party]["last_action"] = args.message
    save(state)
    append_log({"ts": ts, "party": party, "type": "post",
                "sequence": state["sequence"], "message": args.message})
    render_md(state)
    print(f"post recorded: {party}: {args.message}")


def cmd_render(args):
    render_md(load())
    print("rendered HANDSHAKE.md")


def main():
    parser = argparse.ArgumentParser(description="Veleiro <-> Claude Code handshake")
    parser.add_argument("--party", choices=PARTIES, default="claude_code")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    a = sub.add_parser("ack")
    a.add_argument("--action", default=None)
    p = sub.add_parser("post")
    p.add_argument("--message", required=True)
    sub.add_parser("render")

    args = parser.parse_args()
    {"init": cmd_init, "status": cmd_status, "ack": cmd_ack,
     "post": cmd_post, "render": cmd_render}[args.cmd](args)


if __name__ == "__main__":
    main()
