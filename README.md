# FPS Agent Strategy

A rule-based agent for the AGX FPS competition. This project adapts the supplied FPS optimisation kit into a tactical policy that makes decisions about movement, combat, equipment, and the bomb objective from observations during a match. It also contains a separate experimental roaming agent.

## Approach

The main policy is in [`agent/agent.py`](agent/agent.py). It uses heuristics and information available in the observation rather than a trained neural network. The design aims to balance fighting, staying near cover, and completing the objective:

- **Economy and equipment:** Choose a save, partial buy, or full buy based on cash and the round situation. The policy considers the match score, keeps an existing primary weapon, and can buy armor, a defuse kit, and utility when appropriate.
- **Team and objective:** Attackers initially select the same site; defenders distribute between sites based on their seats. The agent can adjust to teammate positioning and react to a known dropped or planted bomb. It plants or defuses when appropriate and can guard the objective after planting.
- **Navigation and positioning:** Use the public navigation graph and A* route search with distance and risk penalties. The policy considers nearby cover, checks corners with short peeks, aims along the route or toward a recent threat, and attempts to recover when stuck.
- **Combat:** Rank visible opponents using distance and view angle, with opponent facing direction when available. Aim at exposed body parts, handle weapon-specific firing and sniper zoom, reload when safer, and switch weapons when needed.
- **Utility and awareness:** Use observed enemy and teammate events to guide attention. When conditions allow, prime and release available utility with safety checks; flash behavior also attempts to reduce self-blinding. These are heuristics, not guarantees of safe throws.

These behaviors depend on the observation and game mechanics. The policy does not assume direct communication between agents. Its thresholds and tactics are experimental; they should be evaluated against actual match logs rather than treated as proven improvements.

## Experimental roaming agent

[`toy_agent/agent/agent.py`](toy_agent/agent/agent.py) is a separate experiment. It continuously roams without choosing a fixed destination, rotates and jumps while moving, changes heading when stuck or after an interval, and aims at a visible opponent, preferring the head. It pauses the roaming actions to aim and fire. It is distinct from the tactical policy.

## Repository guide

| Path | Purpose |
| --- | --- |
| `agent/agent.py` | Main tactical agent and platform entry points. |
| `agent/agent_baseline.txt` | Original baseline kept for comparison. |
| `agent/agent_previous_v*.txt` | Earlier iterations of the tactical policy. |
| `toy_agent/` | Experimental roaming agent and its supporting files. |
| `data/` | Supplied map data. |
| `tests/` | Local tests for the tactical policy. |
| `calibrate/`, `sim/`, `tools/` | Supplied calibration, approximation, and packaging tools. |
| `submission_tactical_v12.zip` | Packaged tactical v12 submission. |
| `submission_toy_spinner_wander.zip` | Packaged roaming experiment. |
| [KIT_INSTRUCTIONS.md](KIT_INSTRUCTIONS.md) | Original instructions supplied with the optimisation kit. |

## Testing and packaging

The local tests can be run from the repository root:

```sh
python -m unittest discover -s tests
```

To package the current main agent with the supplied tool:

```sh
python tools/pack.py --output submission.zip
```

The platform submission uses the required ZIP structure; consult the [original kit instructions](KIT_INSTRUCTIONS.md) and the platform's current rules for setup, dependencies, and submission details. The local simulator is an approximation, so platform matches are needed to evaluate actual performance.

## Acknowledgment

This project builds on the AGX FPS local optimisation kit and its supplied baseline, map data, and tools. The strategy changes and experimental agent are adaptations developed for the competition.
