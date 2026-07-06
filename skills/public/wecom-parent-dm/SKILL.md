---
name: wecom-parent-dm
description: Generate parent-facing WeCom / WeChat private-message scripts for course sales. Use when the user wants 企微私聊话术, 家长沟通, or one-to-one DM copy grounded in KB materials.
allowed-tools:
  - kb_search
  - format_structured_output
---

# WeCom Parent DM Skill

## When to activate

Load when the user wants:

- Enterprise WeChat or WeChat **private chat** scripts for parents
- Short, sendable message blocks (not long articles)
- Copy grounded in uploaded course / training materials

## Workflow

1. **Retrieve** — `kb_search` with the course or training topic (e.g. 超脑阅读, 脑力训练).
2. **Structure** — `format_structured_output` with schema `parent_dm_script` when structured blocks are needed.
3. **Tone** — warm, professional, parent-friendly; each block should be copy-paste ready for WeCom.

## Output format

- Split into 3–6 short messages the operator can send one by one.
- Lead with empathy or a hook, then value, then a soft CTA (试听 / 了解详情).
- Cite KB sources when stating factual training requirements or policies.
- Do not fabricate prices, guarantees, or policies not found in KB results.
