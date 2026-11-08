"""Write one scripted run to a JSONL log, for inspection.

Usage:
    python3 -m lostarchive.demo --condition C1 --seed s1 --policy bcast --out logs/demo.jsonl
"""

import argparse
import json
import os

from .engine import run
from .policies import (BroadcastPolicy, HatchPolicy, RandomPolicy, SoloPolicy,
                       WaitPolicy)
from .world import generate_world

POLICIES = {
    "solo": lambda aid, seed: SoloPolicy(),
    "bcast": lambda aid, seed: BroadcastPolicy(),
    "hatch-r": lambda aid, seed: HatchPolicy(True),
    "hatch-t": lambda aid, seed: HatchPolicy(False),
    "random": lambda aid, seed: RandomPolicy(f"{seed}{aid}"),
    "wait": lambda aid, seed: WaitPolicy(),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--condition", default="C1", choices=["C0", "C1", "C2", "C0-D"])
    p.add_argument("--seed", default="s1")
    p.add_argument("--policy", default="bcast", choices=sorted(POLICIES))
    p.add_argument("--T", type=int, default=16)
    p.add_argument("--out", default="logs/demo.jsonl")
    a = p.parse_args()

    world = generate_world(a.seed, a.condition)
    policies = {aid: POLICIES[a.policy](aid, a.seed) for aid in world.agent_ids}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    sim = run(a.condition, a.seed, policies, T=a.T, log_path=a.out)
    end = sim.records[-1]
    print(json.dumps({"stop_reason": end["stop_reason"], "rounds": end["rounds"],
                      "messages": end["messages_total"], "tu_events": len(end["tu_events"]),
                      "hatch_uses": len(end["hatch_uses"]), "log": a.out}, indent=2))


if __name__ == "__main__":
    main()
