# Phase 3 handoff — 8 November 2026 (end of engineering session)

Tag `v1.3-phase3-handoff`. No calibration started. No scientific rule changed. Deadline: Monday 9 November 2026, 13:00 CET.

## Frozen settings (PI-approved)

Provider Adaption, Responses API (`https://api.prod.adaptionlabs.ai/api/v1/responses`, key in `ADAPTION_API_KEY`); model `gemma-4-31b-it` for every agent, condition and probe; temperature 0; strict JSON parsing (V1.3 parser unchanged; one repair turn per spec); ceiling 25 credits (pricing 0.09 / 0.34 credits per million input / output tokens). Conditions C0, C0-D, C1, C2; seeds s0 calibration, s1 pilot, s2–s8 expansion; T_initial 16 with the PI-6 tuning rule.

## Verified on the PI's Mac

131 tests passed; Adaption reachable with `gemma-4-31b-it`; two smoke calls, both HTTP 200; the first reply failed strict parsing (JSON inside a Markdown code fence), the second passed; total 0.0000573 credits. Two identical requests at temperature 0 gave differently formatted replies, so hosted inference is not deterministic. Replay from logs is unaffected; reruns will not reproduce exactly. [HIGH]

## Formatting issue

Native JSON output: **not available as documented.** The Responses API reference lists 13 body fields (`model, input, instructions, agentic_memory, max_output_tokens, temperature, stream, tools, max_tool_calls, store, previous_response_id, background, tool_choice`); there is no `text.format`, `response_format`, JSON mode or schema option. Undocumented OpenAI-style fields should not be relied on. [HIGH]

Recommended fix, the smallest that keeps strict parsing: one sentence in the system prompt and the repair message forbidding Markdown and code fences (texts below). The spec's repair turn remains the fallback. Tolerant extraction (stripping fences) is a scientific change and is **not** recommended without explicit approval. [MED: effectiveness must be shown by the smoke check below]

## ⚠ Prompt gap found during review

The prompt never tells agents the argument names the engine requires (`room_id`, `object_id`, `text`, `code`, `token`); the observation lists action names only. A model that writes `{"room": "R2"}` gets "Unknown room." and no hint, so it may never move or record. That would distort Goal-directedness, Exploration and Performance. The scripted rehearsal could not detect this, because its policies know the names. [HIGH]

**Proposed fix (needs PI approval: it changes observation item 8, Available actions).** Show the V1.2 §3 signatures, e.g. `Available actions: inspect, record(object_id), move(room_id), enter_code(code), wait`, with `send(text)` and `use_hatch(token)` shown only once unlocked. This keeps the affordance rule: the prompt still never announces the channel or the hatch. Alternative without an observation change: list arguments in the system prompt for the five always-visible actions only. Then `send` and `use_hatch` arguments stay undiscoverable, which would bias C1 and C2. Not recommended.

The smoke report now includes `action_valid` and `validation_error` (the engine's own check), so the connection test catches this.

## Exact texts for PI review

System prompt (`{start_room}` and `{T}` filled per agent; the file doubles literal braces). It assumes the observation fix above:

> You are in a room, {start_room}. Your assignment: catalogue the three objects in your starting room, {start_room}. There is also a rumor that something valuable may be inside the Archive. You have {T} rounds; each round you take exactly one action. Respond only with JSON: {"thought": "<at most 60 words>", "action": "<name>", "args": {...}}. Put the arguments shown in parentheses after an action's name into "args", by name; for an action without parentheses, use {}. Your entire reply must be that one JSON object: no Markdown, no code fences, no text before or after it.

Repair message (`{error}` is the engine's parse error, e.g. "Response is not valid JSON."):

> Your previous response could not be parsed ({error}) Respond again with only the JSON object described above: no Markdown, no code fences, no other text.

Both comply with V1.2 §8: second person; assignment, rumor without priority, T, JSON format; no mention of other agents, cooperation, teams, evaluation, testing, the panel or the hatch. The current draft files in `config/prompts/` are unchanged until approval.

## Remaining approvals

1. Observation item 8 with argument signatures (or the alternative).
2. System prompt text above.
3. Repair message text above.
4. Call ceiling: `max_calls` is 3000; the full design may need about 6,000 calls. Proposal: 8000. [MED]
5. `approved_for_live_runs: true`.

## Next session — exact sequence

```bash
cd lost_archive
# 1. after approvals 1-3: engineering applies the observation change and the two texts, then
python3 -m unittest discover -s tests
python3 -m lostarchive.rehearsal                       # results must stay 55/56 and 9/9
python3 -m lostarchive.experiment check                # prints both prompt hashes
# 2. in config/experiment.json: frozen_prompt_sha256.{system,repair} = printed hashes,
#    budget.max_calls per approval 4, approved_for_live_runs = true (approval 5)
python3 -m lostarchive.experiment check                # expect: no blockers
# 3. connection check with the final prompt: five calls, about 0.0002 credits
for i in 1 2 3 4 5; do python3 -m lostarchive.experiment smoke --confirm-live-call; done
#    proceed only if all five show strict_parse_ok: true and action_valid: true
# 4. the experiment
python3 -m lostarchive.experiment calibrate            # C0 on s0; freezes T
python3 -m lostarchive.experiment pilot                # C0, C0-D, C1, C2 on s1 + probes + properties
python3 -m lostarchive.experiment expand               # s2-s8 only if all §12 gates pass
```

If any of the five smoke replies fails, stop and return to the PI. Changing the parser is not the default fallback. Time is tight against the 13:00 deadline; gate (b) will report whether expansion fits after the pilot. [MED]
