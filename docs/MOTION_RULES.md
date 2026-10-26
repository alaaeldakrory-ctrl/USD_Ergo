# Motion rules: what every animated operator must respect

Read this **before** you write or change any operator animation, and keep every rule in mind while you build each
step. The person reviewing the animation must never have to say "he is clipping into the bench" or "no human holds
a wrench like that". Those are your checks, not theirs.

Every rule below came from a real mistake that a person had to point out. `tools/motion_check.py` checks most of
them automatically (see the end of this page). The rules it cannot check, you check by looking.

---

## 1. The first rule: nothing passes through anything

A real person can never:

- pass through an object (bench, panel, fixture, machine, shelf, wall);
- pass through **another person**;
- pass through the floor;
- pass through their own body.

This holds for every body part (head, trunk, arms, hands, **legs, knees, feet and toes**) and for everything the
person holds or carries. Legs and feet are where this is broken most often: a knee through a panel while kneeling,
toes inside a cabinet, a foot through a pallet.

If a pose only works by overlapping something, the pose is wrong. Move the **person** (step back, step aside, kneel
somewhere else) or move the **work**. Never accept the overlap.

| Never | Do instead |
|---|---|
| Knee or toes inside the fixture you kneel at | Kneel a little further back, turn the front foot out to the side |
| Hips, belly or chest pushed into a bench edge | Stand 10-15 cm off the edge; bend at the hips, not through the bench |
| Two operators' stations overlapping | At least ~60 cm of clear space between two bodies at every moment |
| Walking path through another operator or a cart | Route around, or time the move so the space is free |
| A carried tool or box passing through the thigh or belly | Carry it at the side, turned out, or tipped down; go around the knee |
| A tool tip pushed through the part it works on | The tip **touches** the bolt or surface, it never goes inside it |
| A hand inside the part it holds | The palm sits on the surface; the fingers wrap around it |

## 2. Hands and grips

- **The hand is on the grip, not near it.** The palm centre is on the handle's surface, about 0.7 cm out from it, never
  on the handle's centre line (the handle would then pass through the palm).
- **Fingers close until they touch.** Each finger joint bends until the finger meets the handle (or the part).
  Fingers are never straight while holding something, and never sunk into it.
- **The right grip for the tool:** a power grip (all fingers round the handle, thumb across) for screwdrivers,
  wrenches, hammers, drivers and handles; a pinch for small parts, screws, connectors and clips. A screwdriver is
  driven with the whole hand round the handle, never between two middle fingers.
- **The tool is held at its handle**, the way the tool is designed to be held, with the working end pointing at the
  work.
- **The off hand does something real**: it steadies the part, braces on the bench or panel near the work, rests on
  the knee when kneeling, or hangs relaxed. It never hovers in the air, floats palm-up or sticks out sideways.

## 3. Arms

- **Arms are never behind the back** while working. An elbow more than ~19 cm behind the shoulder, or a wrist behind
  the shoulder line, does not happen on a line. Turn the body to face the work instead.
- **A free arm hangs relaxed**: elbow bent about 20-30 deg, hand beside the thigh. It is not lifted and bent at 70
  deg like a mannequin. A stiff, raised idle arm is what makes a character look like a zombie.
- **Reach from in front of the body.** Hands work between hip and shoulder height, about 25-50 cm in front of the
  chest. Further away than about 60 cm, the person steps closer: they do not stretch the arm straight or fold the
  trunk to get there.
- **Wrists:** keep bending near neutral. Up to ~55 deg up or down and ~30 deg sideways while working; 90 deg and 45
  deg are physical limits that are never reached.
- **Elbows** never bend backwards, and never past ~160 deg.

## 4. Trunk, neck and head

- **Don't fold the trunk to reach.** If the work is low or far, the person squats, kneels or steps closer. A trunk
  bent 40-60 deg to reach something you could walk up to is wrong.
- **Bending is shared** by the hips and the lower back. It does not happen all at the hips (a stiff, hinged back) or
  all in the spine (a hunch).
- **Never lean back** to work in front of you.
- **The head looks at the hands or the work** during each step; the neck bends at most ~20-25 deg to do it.
- **Twist and side bend stay small** (under ~20 deg while working). Turn the feet instead of twisting the spine.

## 5. Legs, feet and kneeling

- **Feet are planted.** A standing foot stays fixed until it steps. It never glides along the floor. To change
  position, take a step.
- **Stance:** feet about hip width apart, toes turned out slightly, the weight between the feet.
- **Kneeling on one knee** (low work):
  - the knee on the floor sits a kneecap above it: the knee joint is about 5 cm up, never below the floor;
  - the toes of that foot are tucked under;
  - the hips are over the knee (the thigh is near vertical), not pushed back behind it;
  - the knee on the floor is part of the support: the body balances over the knee and both feet, so the trunk can
    stay upright;
  - the front foot is planted and kept clear of the fixture: turn it out to the side when the work is close;
  - work at about the kneeling person's elbow height (60-70 cm off the floor), about 25-35 cm in front of the chest.
    If the work is lower than that, use a creeper or stool, or work squatting. Don't fold the trunk over the knee.
- **Squatting** keeps the heels down when possible, and the knees over the toes.
- **Knees** never bend backwards.

## 6. Carrying tools and parts

- **The carried thing never goes through the body**: not on the way to the work, not on the way back.
- **Short tools** are carried at the side, hand by the hip, tool pointing down or forward.
- **Long tools** (torque wrenches, bars, long drivers) are carried turned out to the side or tipped down. When
  kneeling, they are never carried across the front thigh. On the way between hip and work, lift the tool over or
  around the knee.
- **Boxes and parts** are held in front of the body, against it, not inside it, with both hands on the sides or the
  bottom.
- **Weight matters**: heavy items are carried close to the body, lifted with bent knees, and never held at arm's
  length.

## 7. Timing

- **No snaps.** Blend between poses over at least 0.2 s. A hand or foot never jumps faster than a person can move it
  (about 6 m/s for a hand, much slower for the hips).
- **Reach, act, return:** each step takes a believable time, about 0.6-1.2 s to reach and the same to return.
  Repetitive actions (turns of a ratchet, screws) have a steady rhythm.
- **Hold the contact** while working: the hand stays on the tool and the tool stays on the work. They do not drift
  apart.

## 8. The character

- **Never change the character's proportions** to make a pose work. Don't scale or stretch bones, and don't move a
  bone's offset. Fix the pose, the position or the work instead.
- **Retargeting** keeps the target character's own bone lengths. The arms and legs are solved so the hands and feet
  land on the right points.
- **Every operator is the same kind of human:** the same rules apply to every character and every body size.

## 9. Between operators (scenes with many people)

- Each station has its own floor space. Bodies, arms and carried items of neighbours never overlap.
- **Shared aisles:** paths are timed so two people are never in the same spot at the same time.
- **Facing:** an operator faces their own work, not the neighbour's.

---

## The gate: check every animation before anyone sees it

After **every** change to an operator's animation, bake it to USD time samples and run:

```
python tools/motion_check.py "<SCENE>.usd" --out="<OUT>/motion_qa" --step=2
```

In Kit's Script Editor:

```python
from ergo_scan import motion_qa as Q
import omni.usd
res = Q.check_stage(omni.usd.get_context().get_stage(), "/World", step=2)
Q.write_report(res, r"<OUT>/motion_qa")
```

- It exits with code **1** while any error is left, and **0** when the scene passes.
- `motion_qa.md` lists, per operator, each problem with its frames, its worst value, what it means and how to fix it.
- **Fix every error, then run it again.** Repeat until it passes.
- Read the warnings and fix them, or say why they are fine (for example: the hand is holding something the scene
  does not model).
- Only then show the animation, or run the RULA scan on it.

While you build a pose in Python, you can check it before writing it: `Q.check_pose(J)` takes the joint positions
(role names as in `scan.py`, Y-up, cm) and returns the rules that pose breaks.

### What the check catches, and what you still check by eye

| Check (code) | Automatic | What it means |
|---|---|---|
| `inside_equipment` | yes | a body part (legs and feet included) inside static scene geometry |
| `operators_overlap` | yes | one operator's body inside another's |
| `through_floor` | yes | a knee, the hips or a foot below the floor |
| `held_object_in_body` | yes | something being carried or held passing through the trunk or legs |
| `arm_behind_back` | yes | an elbow or wrist behind the back |
| `joint_range` | yes | elbow, wrist, forearm, shoulder rotation, trunk, neck or knee past what a person can do; hand inside the torso |
| `snap` | yes | a joint jumping faster than a person can move |
| `foot_slide` (warning) | yes | a planted foot gliding |
| `arm_held_up` (warning) | yes | an idle arm held up and bent |
| grip and fingers | **by eye** | the hand on the handle, fingers closed onto it, the right grip type |
| tool tip on the work | **by eye** | the tip touches the part, never passes through it |
| posture choice | **by eye** | stepping closer instead of folding the trunk; kneeling or squatting for low work |
| gaze | **by eye** | the head looks at the work |

For the "by eye" rows, look at the worst frame of each step from two sides (front three-quarter and side), close
enough to see the hands. Do this for every new step you add.
