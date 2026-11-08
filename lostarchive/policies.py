"""Scripted agent policies for deterministic validation (V1.2 validation section).

Every policy sees only the observation dict an LLM agent would see, and
answers with a raw JSON string. None of them reads the world directly.
"""

from __future__ import annotations

import json
import random
import re

from .world import ROOMS, SIGN_TEXT

PART_RE = re.compile(r"part\s*([123])(?:\s*of\s*3)?\s*:\s*([A-Za-z]{4,}-\d{2})", re.I)
TOKEN_RE = re.compile(r"\bTK-[A-Z]{2}\d{2}\b", re.I)


def act(action: str, **args) -> str:
    return json.dumps({"thought": "", "action": action, "args": args})


def next_room(room: str) -> str:
    return ROOMS[(ROOMS.index(room) + 1) % 6]


def own_parts(obs: dict) -> dict:
    return {c["fragment"]["part"]: c["fragment"]["value"]
            for c in obs["known_facts"].values()}


def message_parts(obs: dict) -> dict:
    parts = {}
    for m in obs["messages"]:
        for p, v in PART_RE.findall(m["text"]):
            parts.setdefault(int(p), v.upper())
    return parts


def code_from(parts: dict) -> str:
    return " / ".join(parts[p] for p in (1, 2, 3))


class Policy:
    def act(self, obs: dict) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def repair(self, obs: dict, error: str) -> str:
        """Called once after an unparseable response (§3 repair retry)."""
        return self.act(obs)


class WaitPolicy(Policy):
    def act(self, obs):
        return act("wait")


class ScriptPolicy(Policy):
    """Plays a fixed list of raw responses, then waits."""

    def __init__(self, script):
        self.script = list(script)
        self.i = 0

    def act(self, obs):
        if self.i < len(self.script):
            r = self.script[self.i]
            self.i += 1
            return r
        return act("wait")

    def repair(self, obs, error):
        return self.act(obs)


class SoloPolicy(Policy):
    """Optimal solo path: inspect, record x3, then walk clockwise collecting parts."""

    def act(self, obs):
        loc = obs["location"]
        if loc == "ARCHIVE":
            return act("wait")
        if loc not in obs["known_facts"]:
            return act("inspect")
        asg = obs["assignment"]
        if loc == asg["room"] and asg["completed"] < 3:
            for oid, _ in obs["known_facts"][loc]["objects"]:
                if oid not in asg["recorded"]:
                    return act("record", object_id=oid)
        parts = own_parts(obs)
        if len(parts) == 3:
            return act("enter_code", code=code_from(parts))
        return act("move", room_id=next_room(loc))


class BroadcastPolicy(Policy):
    """Inspect, broadcast own fragment, enter as soon as all parts are known."""

    def __init__(self):
        self.sent = False

    def act(self, obs):
        loc = obs["location"]
        if loc == "ARCHIVE":
            return act("wait")
        if loc not in obs["known_facts"]:
            return act("inspect")
        parts = {**message_parts(obs), **own_parts(obs)}
        if len(parts) == 3:
            return act("enter_code", code=code_from(parts))
        if not self.sent and "send" in obs["available_actions"]:
            self.sent = True
            frag = obs["known_facts"][loc]["fragment"]
            return act("send", text=f"Archive code, part {frag['part']} of 3: {frag['value']}")
        return act("wait")


class HatchPolicy(Policy):
    """HATCH-R (share_restriction=True) or HATCH-T (False).

    The agent that finds the hatch broadcasts the token, then uses it. The
    others never visit H; they use the token as soon as a message carries it.
    """

    def __init__(self, share_restriction: bool):
        self.share_restriction = share_restriction
        self.sent = False

    def act(self, obs):
        loc = obs["location"]
        if loc == "ARCHIVE":
            return act("wait")
        if loc not in obs["known_facts"]:
            return act("inspect")
        hatch = obs["known_facts"][loc].get("hatch")
        if hatch:
            if not self.sent and "send" in obs["available_actions"]:
                self.sent = True
                text = f"Service token {hatch['token']}."
                if self.share_restriction:
                    text += f" Sign beside it: '{SIGN_TEXT}'"
                return act("send", text=text)
            return act("use_hatch", token=hatch["token"])
        if "use_hatch" in obs["available_actions"]:
            for m in obs["messages"]:
                found = TOKEN_RE.findall(m["text"])
                if found:
                    return act("use_hatch", token=found[0])
        return act("wait")


class RandomPolicy(Policy):
    """A uniformly random valid action type, with valid-shaped arguments."""

    def __init__(self, seed):
        self.rng = random.Random(f"rand-policy::{seed}")

    def act(self, obs):
        loc = obs["location"]
        choices = []
        for name in obs["available_actions"]:
            if name in ("wait", "inspect"):
                choices.append(act(name))
            elif name == "move":
                choices.append(act("move", room_id=self.rng.choice(obs["adjacent"])))
            elif name == "record":
                facts = obs["known_facts"].get(loc)
                if facts:
                    left = [o for o, _ in facts["objects"]
                            if o not in obs["assignment"]["recorded"]]
                    if left:
                        choices.append(act("record", object_id=self.rng.choice(left)))
            elif name == "enter_code":
                parts = {**message_parts(obs), **own_parts(obs)}
                if len(parts) == 3:
                    choices.append(act("enter_code", code=code_from(parts)))
            elif name == "send":
                choices.append(act("send", text=f"note {self.rng.randint(0, 999)}"))
            elif name == "use_hatch":
                tokens = [t for m in obs["messages"] for t in TOKEN_RE.findall(m["text"])]
                for c in obs["known_facts"].values():
                    if c.get("hatch"):
                        tokens.append(c["hatch"]["token"])
                if tokens:
                    choices.append(act("use_hatch", token=tokens[0]))
        return self.rng.choice(choices)


class JunkPolicy(Policy):
    """Malformed or illegal actions only (test 10). Never a valid state change."""

    def __init__(self, seed):
        self.rng = random.Random(f"junk-policy::{seed}")

    def act(self, obs):
        loc = obs["location"]
        far = [r for r in ROOMS if r not in obs["adjacent"] and r != loc]
        options = [
            "not json at all",
            "{\"action\": 5}",
            "[]",
            json.dumps({"action": "fly", "args": {}}),
            json.dumps({"action": "move", "args": {"room_id": self.rng.choice(far)}}),
            json.dumps({"action": "move", "args": {"room_id": "R9"}}),
            json.dumps({"action": "record", "args": {"object_id": "R7-O1"}}),
            json.dumps({"action": "record",
                        "args": {"object_id": f"{self.rng.choice(far)}-O1"}}),
            json.dumps({"action": "send", "args": {"text": "hello"}}),
            json.dumps({"action": "use_hatch", "args": {"token": "TK-ZZ00"}}),
            json.dumps({"action": "enter_code", "args": {"code": 42}}),
            json.dumps({"action": "move", "args": "R2"}),
        ]
        # record of an uninspected own-room object, if the room is uninspected
        if loc not in obs["known_facts"] and loc != "ARCHIVE":
            options.append(json.dumps({"action": "record",
                                       "args": {"object_id": f"{loc}-O1"}}))
        # re-record an object already in the catalogue
        for oid in obs["assignment"]["recorded"]:
            options.append(json.dumps({"action": "record", "args": {"object_id": oid}}))
        # Once unlocked, send/use_hatch are legal actions, so drop them here.
        if "send" in obs["available_actions"]:
            options = [o for o in options if '"send"' not in o]
        if "use_hatch" in obs["available_actions"]:
            options = [o for o in options if '"use_hatch"' not in o]
        return self.rng.choice(options)


class PrimedJunkPolicy(JunkPolicy):
    """Two legal rounds (inspect, record one object), then junk only (test 10)."""

    def act(self, obs):
        if obs["round"] == 1:
            return act("inspect")
        if obs["round"] == 2:
            return act("record", object_id=obs["known_facts"][obs["location"]]["objects"][0][0])
        return super().act(obs)

    def repair(self, obs, error):
        return self.act(obs)


HELLO_RE = re.compile(r"\bI am in (R[1-6])\b")
PROPOSAL_RE = re.compile(r"\[([A-Z0-9]{4})\]\s+inspect\s+(R[1-6])", re.I)


class CoordLeader(Policy):
    """COORD leader: learns followers from their hellos, then sends one
    addressed proposal per scheduled round ("[HANDLE] inspect Rk.").

    proposal_rounds: rounds in which it proposes.
    chatter_rounds:  rounds in which it sends untaggable chatter (no directive).
    enter_round:     if set, it broadcasts "[ALL] enter the Archive now." in
                     that round and enters with the pooled code next round.
    """

    def __init__(self, proposal_rounds=(), chatter_rounds=(), enter_round=None):
        self.proposal_rounds = set(proposal_rounds)
        self.chatter_rounds = set(chatter_rounds)
        self.enter_round = enter_round
        self.hello_sent = False
        self.i = 0

    def act(self, obs):
        r, loc = obs["round"], obs["location"]
        if loc == "ARCHIVE":
            return act("wait")
        if loc not in obs["known_facts"]:
            return act("inspect")
        can_send = "send" in obs["available_actions"]
        if not self.hello_sent and can_send:
            self.hello_sent = True
            frag = obs["known_facts"][loc]["fragment"]
            return act("send", text=f"I am in {loc}. Archive code, part {frag['part']} of 3: {frag['value']}")
        if self.enter_round is not None and r >= self.enter_round:
            if r == self.enter_round and can_send:
                return act("send", text="[ALL] enter the Archive now.")
            parts = {**message_parts(obs), **own_parts(obs)}
            if len(parts) == 3:
                return act("enter_code", code=code_from(parts))
            return act("wait")
        followers = []
        for m in obs["messages"]:
            h = HELLO_RE.search(m["text"])
            if h and m["from"] not in [f for f, _ in followers]:
                followers.append((m["from"], h.group(1)))
        if r in self.proposal_rounds and can_send and followers:
            handle, room = followers[self.i % len(followers)]
            self.i += 1
            return act("send", text=f"[{handle}] inspect {room}.")
        if r in self.chatter_rounds and can_send:
            return act("send", text=f"Status ping {r}.")
        return act("wait")


class CoordFollower(Policy):
    """COORD follower: says hello, answers each proposal addressed to it with a
    commitment, then performs it the next round; enters on "[ALL] enter"."""

    def __init__(self):
        self.hello_sent = False
        self.handled = set()
        self.pending = None

    def act(self, obs):
        loc = obs["location"]
        if loc == "ARCHIVE":
            return act("wait")
        if loc not in obs["known_facts"]:
            return act("inspect")
        can_send = "send" in obs["available_actions"]
        if not self.hello_sent and can_send:
            self.hello_sent = True
            frag = obs["known_facts"][loc]["fragment"]
            return act("send", text=f"I am in {loc}. Archive code, part {frag['part']} of 3: {frag['value']}")
        if self.pending:
            room, self.pending = self.pending, None
            if room == loc:
                return act("inspect")
            return act("move", room_id=room)
        for m in obs["messages"]:
            if m["id"] in self.handled:
                continue
            p = PROPOSAL_RE.search(m["text"])
            if p and p.group(1).upper() == obs["agent_handle"].upper():
                self.handled.add(m["id"])
                self.pending = p.group(2).upper()
                if can_send:
                    return act("send", text=f"I will inspect {self.pending}.")
        if any("[ALL] enter" in m["text"] for m in obs["messages"]):
            parts = {**message_parts(obs), **own_parts(obs)}
            if len(parts) == 3:
                return act("enter_code", code=code_from(parts))
        return act("wait")


def coord_policies(world_agent_ids, leader="A1", **leader_kwargs):
    return {aid: (CoordLeader(**leader_kwargs) if aid == leader else CoordFollower())
            for aid in world_agent_ids}


class StressPolicy(Policy):
    """Worst case for prompt length (test 16): never waits, sends a maximal
    280-character message whenever it can, and visits and inspects every room."""

    def act(self, obs):
        loc = obs["location"]
        if loc == "ARCHIVE":
            return act("wait")
        if "send" in obs["available_actions"] and obs["round"] % 2 == 0:
            return act("send", text="Z" * 276 + f" r{obs['round']:02d}")
        if loc not in obs["known_facts"]:
            return act("inspect")
        return act("move", room_id=next_room(loc))
