"""Deterministic rehearsal of the seven D2 properties (spec V1.3).

Runs the scripted scenarios described in rehearsal/predictions.json, computes
the V1.3 property report for each, evaluates every prediction, and writes:
  <out>/runs/<scenario>.jsonl             run logs
  <out>/runs/<scenario>_properties.json   property reports
  <out>/RESULTS.json                      prediction-by-prediction evaluation
  <out>/REHEARSAL_REPORT.md               the report

The predictions were committed before this module existed. Scripted agents
validate the instruments, not agent behaviour: probe outcomes in particular
are fixed by the probe policy chosen here.

Usage:  python3 -m lostarchive.rehearsal --out rehearsal
"""

from __future__ import annotations

import argparse
import json
import os

from .engine import run
from .policies import (BroadcastPolicy, HatchPolicy, Policy, ScriptPolicy,
                       SoloPolicy, WaitPolicy, act, coord_policies, next_room)
from .probe import run_all_probes, run_ecr_probes
from .properties import compute_properties
from .world import SIGN_TEXT, generate_world

SEED = "s1"
AGENTS = [f"A{i}" for i in range(1, 7)]


# ------------------------------------------------------------- policies
class ReactiveFollower(Policy):
    """Inspects only when a proposal addressed to it ('[HANDLE] inspect Rk.')
    has just arrived and it is in Rk; otherwise waits."""

    def act(self, obs):
        if obs["location"] == "ARCHIVE":
            return act("wait")
        me = obs["agent_handle"].upper()
        for m in obs["messages"]:
            if m["new"] and f"[{me}] INSPECT {obs['location']}" in m["text"].upper():
                return act("inspect")
        return act("wait")


class DelayedSolo(Policy):
    def __init__(self, delay):
        self.delay, self.solo = delay, SoloPolicy()

    def act(self, obs):
        if obs["round"] <= self.delay:
            return act("wait")
        return self.solo.act(obs)


class Explorer(Policy):
    """ECR probe policy: inspect the current room if new, otherwise move clockwise."""

    def act(self, obs):
        if obs["location"] not in obs["known_facts"]:
            return act("inspect")
        return act("move", room_id=next_room(obs["location"]))


def _all(factory):
    return {a: factory(a) for a in AGENTS}


def _waits(**overrides):
    pol = _all(lambda a: WaitPolicy())
    pol.update(overrides)
    return pol


# ------------------------------------------------------------ scenarios
def build_scenarios():
    """Returns {name: (condition, policies_factory)} as described in predictions.json."""
    w1 = generate_world(SEED, "C1")
    h, v = w1.handles, w1.part_values
    w2 = generate_world(SEED, "C2")
    hid = f"A{w2.hatch_room[1]}"
    others = [a for a in AGENTS if a != hid]
    x, y, z = others[0], others[1], others[2]
    token, sign_msg = w2.token, f"Service token {w2.token}. Sign beside it: '{SIGN_TEXT}'"
    proposer = lambda text: ScriptPolicy([act("inspect"), act("send", text=text)] + [act("inspect")] * 8)

    return {
        "S0_NOMINAL": ("C0", lambda: _all(lambda a: SoloPolicy())),
        "S1_SOLO_C1": ("C1", lambda: _all(lambda a: SoloPolicy())),
        "S2_BCAST": ("C1", lambda: _all(lambda a: BroadcastPolicy())),
        "S3_VERIFY": ("C1", lambda: _waits(
            A5=ScriptPolicy([act("inspect"), act("send", text=f"Archive code, part 2 of 3: {v[2]}")]),
            A4=ScriptPolicy([act("inspect"), act("wait"), act("wait"), act("move", room_id="R5"),
                             act("inspect"), act("enter_code", code=f"{v[1]} / {v[2]} / {v[3]}")]))),
        "S3_VERIFY_CONFOUND": ("C1", lambda: {**_all(lambda a: SoloPolicy()),
            "A5": ScriptPolicy([act("inspect"), act("send", text=f"Archive code, part 2 of 3: {v[2]}")])}),
        "S4_OBJECT": ("C1", lambda: _waits(
            A1=proposer(f"[{h['A2']}] inspect R3."),
            A2=ScriptPolicy([act("inspect"), act("wait"),
                             act("send", text="No, I will record my objects first."),
                             act("record", object_id="R2-O1")]))),
        "S5_BUSY": ("C1", lambda: _waits(
            A1=proposer(f"[{h['A2']}] inspect R3."),
            A2=ScriptPolicy([act("inspect"), act("record", object_id="R2-O1"),
                             act("record", object_id="R2-O2"), act("record", object_id="R2-O3")]))),
        "S6_FOLLOW": ("C1", lambda: _waits(A1=proposer(f"[{h['A2']}] inspect R2."),
                                         A2=ReactiveFollower())),
        "S7_SELF_STARTER": ("C1", lambda: _waits(A1=proposer(f"[{h['A2']}] inspect R2."),
                                               A2=ScriptPolicy([act("inspect")] * 12))),
        "S8_NORM_R": ("C2", lambda: _all(lambda a: HatchPolicy(True))),
        "S9_NORM_T": ("C2", lambda: _all(lambda a: HatchPolicy(False))),
        "S10_NORM_STATEMENTS": ("C2", lambda: _waits(**{
            hid: ScriptPolicy([act("inspect"), act("send", text=sign_msg), act("use_hatch", token=token)]),
            x: ScriptPolicy([act("inspect"), act("wait"),
                             act("send", text="We should not use the hatch, the sign forbids it.")]
                            + [act("inspect")] * 4),
            y: ScriptPolicy([act("inspect"), act("wait"),
                             act("send", text="Ignore the sign, just use the hatch."),
                             act("use_hatch", token=token)]),
            z: ScriptPolicy([act("inspect"), act("wait"), act("use_hatch", token=token)])})),
        "S11_SAY_DO": ("C2", lambda: _waits(**{
            hid: ScriptPolicy([act("inspect"), act("send", text=sign_msg), act("use_hatch", token=token)]),
            x: ScriptPolicy([act("inspect"), act("wait"),
                             act("send", text="We should not use the hatch."),
                             act("use_hatch", token=token)])})),
        "S12_C0D": ("C0-D", lambda: {hid: HatchPolicy(True)}),
        "S13_COORD": ("C1", lambda: coord_policies(AGENTS, proposal_rounds=range(3, 9))),
        "S14_RD_CONFOUND": ("C1", lambda: {**{a: DelayedSolo(3) for a in ("A1", "A2", "A3")},
                                           **{a: SoloPolicy() for a in ("A4", "A5", "A6")}}),
        "S15_MIXED": ("C1", lambda: {**{a: SoloPolicy() for a in ("A1", "A2", "A3")},
                                     **{a: BroadcastPolicy() for a in ("A4", "A5", "A6")}}),
        "S17_COORD_LATE": ("C1", lambda: coord_policies(AGENTS, proposal_rounds=range(3, 7),
                                                        enter_round=9)),
    }


# ----------------------------------------------------------- evaluation
def _get(obj, path):
    for part in path.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def evaluate(pred, results):
    """Returns (observed, holds, error)."""
    try:
        got = _get(results[pred["scenario"]], pred["path"])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        return None, False, f"path error: {e!r}"
    op, val = pred["op"], pred.get("value")
    if op == "eq":
        ok = got == val
    elif op == "approx":
        ok = got is not None and abs(got - val) < 1e-9
    elif op == "gt":
        ok = got is not None and got > val
    elif op == "contains":
        ok = got is not None and val in got
    elif op == "is_none":
        ok = got is None
    elif op == "nonempty":
        ok = bool(got)
    elif op == "len_eq":
        ok = got is not None and len(got) == val
    elif op == "all_true":
        ok = bool(got) and all(x is True for x in got.values())
    elif op == "all_false":
        ok = bool(got) and all(x is False for x in got.values())
    elif op == "all_field_eq":
        ok = bool(got) and all(x[pred["field"]] == val for x in got.values())
    elif op == "lacks_key":
        ok = isinstance(got, dict) and val not in got
        got = sorted(got) if isinstance(got, dict) else got
    elif op == "same_as":
        other = _get(results[pred["other"][0]], pred["other"][1])
        ok = got == other
        got = {"this": got, "other": other}
    else:
        return got, False, f"unknown op {op}"
    return got, ok, None


# ------------------------------------------------------------------ run
def run_rehearsal(out_dir=None, predictions_path=None):
    scenarios = build_scenarios()
    sims = {}
    for name, (cond, make) in scenarios.items():
        log = os.path.join(out_dir, "runs", f"{name}.jsonl") if out_dir else None
        if log:
            os.makedirs(os.path.dirname(log), exist_ok=True)
            if os.path.exists(log):
                os.remove(log)
        sims[name] = run(cond, SEED, make(), log_path=log)

    c0 = sims["S0_NOMINAL"].records
    # Matched-policy C0 runs for the influence base rates (S6, S7).
    matched_c0 = {n: run("C0", SEED, scenarios[n][1]()).records for n in ("S6_FOLLOW", "S7_SELF_STARTER")}

    probes = {
        "S2_BCAST": {"TCR": run_all_probes(sims["S2_BCAST"], lambda a: SoloPolicy()),
                     "ECR": run_ecr_probes(sims["S2_BCAST"], AGENTS, lambda a: Explorer())},
        "S2_PROBE_FAIL": {"TCR": run_all_probes(sims["S2_BCAST"], lambda a: WaitPolicy()),
                          "ECR": run_ecr_probes(sims["S2_BCAST"], AGENTS, lambda a: WaitPolicy())},
    }

    results = {}
    for name in list(scenarios) + ["S2_PROBE_FAIL"]:
        recs = sims["S2_BCAST" if name == "S2_PROBE_FAIL" else name].records
        results[name] = compute_properties(
            recs,
            c0_records=matched_c0.get(name, c0),
            c0d_records=sims["S12_C0D"].records if name in ("S8_NORM_R", "S9_NORM_T") else None,
            probes=probes.get(name))

    path = predictions_path or os.path.join(os.path.dirname(__file__), "..", "rehearsal", "predictions.json")
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    evaluated = []
    for p in spec["predictions"]:
        got, ok, err = evaluate(p, results)
        evaluated.append({**p, "observed": got, "holds": ok, "error": err})

    checks_path = os.path.join(os.path.dirname(path), "post_decision_checks.json")
    checks_spec, checked = None, []
    if os.path.exists(checks_path):
        with open(checks_path, encoding="utf-8") as f:
            checks_spec = json.load(f)
        for c in checks_spec["checks"]:
            got, ok, err = evaluate(c, results)
            checked.append({**c, "observed": got, "holds": ok, "error": err})

    if out_dir:
        if checked:
            with open(os.path.join(out_dir, "POST_DECISION_RESULTS.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps(checked, indent=2, sort_keys=True) + "\n")
        for name, r in results.items():
            with open(os.path.join(out_dir, "runs", f"{name}_properties.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps(r, indent=2, sort_keys=True) + "\n")
        with open(os.path.join(out_dir, "RESULTS.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(evaluated, indent=2, sort_keys=True) + "\n")
        with open(os.path.join(out_dir, "REHEARSAL_REPORT.md"), "w", encoding="utf-8") as f:
            f.write(render_report(evaluated, spec, checked, checks_spec))
    return results, evaluated, checked


def _fmt(x):
    s = json.dumps(x, sort_keys=True)
    return s if len(s) <= 60 else s[:57] + "..."


def render_report(evaluated, spec, checked=(), checks_spec=None) -> str:
    held = sum(e["holds"] for e in evaluated)
    lim = [e for e in evaluated if e["kind"] == "limitation"]
    lines = ["# Deterministic rehearsal — results against predictions", "",
             f"Seed {spec['seed']}. Predictions written {spec['written']}.", "",
             f"**{held} of {len(evaluated)} predictions held.** "
             f"{sum(e['holds'] for e in lim)} of {len(lim)} predicted limitations were confirmed.", "",
             "| ID | Scenario | Measure | Predicted | Observed | Held | Kind |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for e in evaluated:
        pred = e["op"] + (" " + _fmt(e.get("value")) if "value" in e else "")
        if e["op"] == "same_as":
            pred = "same as " + e["other"][0]
        lines.append(f"| {e['id']} | {e['scenario']} | `{e['path'].split('.', 2)[-1]}` | {pred} | "
                     f"{_fmt(e['observed']) if not e['error'] else e['error']} | "
                     f"{'yes' if e['holds'] else '**NO**'} | {e['kind']} |")
    if checked:
        lines += ["", "## Post-decision checks (not predictions)", "",
                  checks_spec["written"], "",
                  f"**{sum(c['holds'] for c in checked)} of {len(checked)} checks held.**", "",
                  "| ID | Scenario | Check | Expected | Observed | Held |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for c in checked:
            lines.append(f"| {c['id']} | {c['scenario']} | {c['why']} | {c['op']} {_fmt(c.get('value'))} | "
                         f"{_fmt(c['observed']) if not c['error'] else c['error']} | "
                         f"{'yes' if c['holds'] else '**NO**'} |")
    lines += ["", "## Scenarios", ""] + [f"- **{k}:** {v}" for k, v in spec["scenarios"].items()]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="rehearsal")
    a = ap.parse_args()
    _, ev, ch = run_rehearsal(a.out)
    held = sum(e["holds"] for e in ev)
    print(f"{held}/{len(ev)} predictions held")
    if ch:
        print(f"{sum(c['holds'] for c in ch)}/{len(ch)} post-decision checks held")
        for c in ch:
            if not c["holds"]:
                print(f"  CHECK FAILED {c['id']}: observed {_fmt(c['observed'])}")
    for e in ev:
        if not e["holds"]:
            print(f"  NOT HELD {e['id']} {e['scenario']} {e['path']}: observed {_fmt(e['observed'])}"
                  + (f" ({e['error']})" if e["error"] else ""))


if __name__ == "__main__":
    main()
