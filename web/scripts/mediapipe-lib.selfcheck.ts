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

const slotsUnmirrored = resolveHandSlots([leftHand, rightHand], [[{ categoryName: "Left" }], [{ categoryName: "Right" }]]);
assert.equal(slotsUnmirrored.right, leftHand, "Tasks 'Left' must map to the right output slot (unmirrored input)");
assert.equal(slotsUnmirrored.left, rightHand, "Tasks 'Right' must map to the left output slot (unmirrored input)");

const slotsCollision = resolveHandSlots([leftHand, rightHand], [[{ categoryName: "Left" }], [{ categoryName: "Left" }]]);
assert.equal(slotsCollision.right, leftHand, "first hand claims its wanted slot");
assert.equal(slotsCollision.left, rightHand, "second hand on a slot collision takes the remaining free slot");

assert.deepEqual(extractBlendshapes(undefined), new Array(52).fill(0), "missing face must yield 52 zeros");
assert.deepEqual(extractBlendshapes([{ score: 0.3 }]), [0.3], "blendshapes must be extracted in category order");

console.log("mediapipe-lib.selfcheck: all assertions passed");
