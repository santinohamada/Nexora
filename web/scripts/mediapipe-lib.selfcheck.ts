import assert from "node:assert/strict";
import { toFrame, resolveHandSlots, extractBlendshapes, isFaceEligibleTick } from "../lib/mediapipe.ts";

let faceFires = 0;
for (let eligibleTick = 1; eligibleTick <= 10; eligibleTick++) {
  if (isFaceEligibleTick(eligibleTick)) faceFires++;
}
assert.equal(faceFires, 5, "face must fire on exactly 5 of 10 eligible ticks (half of hand rate)");

const pose = Array.from({ length: 33 }, (_, i) => ({ x: i === 0 ? 0.5 : 0.6, y: i === 0 ? 0.5 : 0.6, z: 0, visibility: 0.9 }));
const frameNoHands = toFrame(pose, undefined, undefined);
assert.equal(frameNoHands.length, 75, "frame must always be 75 landmarks");
assert.deepEqual(frameNoHands[33], [-0.5, -0.5, 0, 0], "missing left hand must be padded to [-nose.x, -nose.y, 0, 0]");
assert.equal(frameNoHands[0][3], 0.9, "pose visibility must be kept as-is after normalization");
assert.equal(frameNoHands[33][3], 0, "hand visibility must be forced to 0");

const leftHand = Array.from({ length: 21 }, () => ({ x: 0.1, y: 0.1, z: 0, visibility: 0 }));
const rightHand = Array.from({ length: 21 }, () => ({ x: 0.2, y: 0.2, z: 0, visibility: 0 }));

const poseWithWrists = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 }));
poseWithWrists[15] = { x: 0.1, y: 0.1, z: 0, visibility: 0.9 };
poseWithWrists[16] = { x: 0.9, y: 0.9, z: 0, visibility: 0.9 };

const handNearLeftWrist = Array.from({ length: 21 }, () => ({ x: 0.12, y: 0.12, z: 0, visibility: 0 }));
const slotsSingleHand = resolveHandSlots(poseWithWrists, [handNearLeftWrist], [[{ categoryName: "Right" }]]);
assert.equal(slotsSingleHand.left, handNearLeftWrist, "hand near left pose wrist must go to the left slot regardless of the classifier label");
assert.equal(slotsSingleHand.right, undefined, "unclaimed slot stays empty");

const handNearLeft = Array.from({ length: 21 }, () => ({ x: 0.1, y: 0.1, z: 0, visibility: 0 }));
const handNearRight = Array.from({ length: 21 }, () => ({ x: 0.9, y: 0.9, z: 0, visibility: 0 }));
const slotsSameLabel = resolveHandSlots(poseWithWrists, [handNearLeft, handNearRight], [[{ categoryName: "Left" }], [{ categoryName: "Left" }]]);
assert.equal(slotsSameLabel.left, handNearLeft, "wrist distance must win over identical classifier labels");
assert.equal(slotsSameLabel.right, handNearRight, "wrist distance must win over identical classifier labels");

const poseLowRightWrist = poseWithWrists.map((lm) => ({ ...lm }));
poseLowRightWrist[16].visibility = 0.2;
const slotsGated = resolveHandSlots(poseLowRightWrist, [handNearLeft, handNearRight], [[{ categoryName: "Right" }], [{ categoryName: "Left" }]]);
assert.equal(slotsGated.left, handNearLeft, "hand at a visible pose wrist is kept");
assert.equal(slotsGated.right, undefined, "hand at a pose wrist with visibility < 0.5 is dropped, as legacy Holistic never tracked it");

const slotsNoPose =resolveHandSlots(undefined, [leftHand, rightHand], [[{ categoryName: "Left" }], [{ categoryName: "Right" }]]);
assert.equal(slotsNoPose.right, leftHand, "no pose falls back to the handedness label mapping: Tasks 'Left' maps to the right slot");
assert.equal(slotsNoPose.left, rightHand, "no pose falls back to the handedness label mapping: Tasks 'Right' maps to the left slot");

assert.deepEqual(extractBlendshapes(undefined), new Array(52).fill(0), "missing face must yield 52 zeros");
assert.deepEqual(extractBlendshapes([{ score: 0.3 }]), [0.3], "blendshapes must be extracted in category order");

console.log("mediapipe-lib.selfcheck: all assertions passed");
