import type { Frame, Landmark } from "../types";

export type RawLandmark = { x: number; y: number; z: number; visibility?: number };
export type HandednessCategory = { categoryName?: string };

const POSE_LANDMARKS = 33;
const HAND_LANDMARKS = 21;
const BLENDSHAPE_COUNT = 52;

function padLandmarks(lms: RawLandmark[] | undefined, n: number): Landmark[] {
  if (!lms || lms.length === 0) {
    return Array.from({ length: n }, () => [0, 0, 0, 0] as Landmark);
  }
  return lms.slice(0, n).map((lm) => [lm.x, lm.y, lm.z, lm.visibility ?? 0] as Landmark);
}

export function toFrame(
  pose: RawLandmark[] | undefined,
  left: RawLandmark[] | undefined,
  right: RawLandmark[] | undefined
): Frame {
  const raw: Frame = [
    ...padLandmarks(pose, POSE_LANDMARKS),
    ...padLandmarks(left, HAND_LANDMARKS),
    ...padLandmarks(right, HAND_LANDMARKS),
  ];
  const nose = raw[0];
  if (!nose) return raw;
  return raw.map((lm, i) => {
    const isHand = i >= POSE_LANDMARKS;
    return [lm[0] - nose[0], lm[1] - nose[1], lm[2], isHand ? 0 : lm[3]] as Landmark;
  });
}

export type HandSlots = { left?: RawLandmark[]; right?: RawLandmark[] };

const POSE_LEFT_WRIST = 15;
const POSE_RIGHT_WRIST = 16;

function wristDistance(hand: RawLandmark[], wrist: RawLandmark): number {
  const dx = hand[0].x - wrist.x;
  const dy = hand[0].y - wrist.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function resolveHandSlotsByWrist(
  landmarks: RawLandmark[][],
  leftWrist: RawLandmark,
  rightWrist: RawLandmark
): HandSlots {
  if (landmarks.length === 1) {
    const hand = landmarks[0];
    return wristDistance(hand, leftWrist) <= wristDistance(hand, rightWrist)
      ? { left: hand }
      : { right: hand };
  }
  const [a, b] = landmarks;
  const straight = wristDistance(a, leftWrist) + wristDistance(b, rightWrist);
  const swapped = wristDistance(a, rightWrist) + wristDistance(b, leftWrist);
  return straight <= swapped ? { left: a, right: b } : { left: b, right: a };
}

function resolveHandSlotsByHandedness(
  landmarks: RawLandmark[][],
  handedness: HandednessCategory[][] | undefined
): HandSlots {
  const slots: HandSlots = {};
  for (let i = 0; i < landmarks.length; i++) {
    const label = handedness?.[i]?.[0]?.categoryName;
    const wantsRightSlot = label === "Left";
    const wantsLeftSlot = label === "Right";
    if (wantsRightSlot && slots.right === undefined) {
      slots.right = landmarks[i];
    } else if (wantsLeftSlot && slots.left === undefined) {
      slots.left = landmarks[i];
    } else if (slots.left === undefined) {
      slots.left = landmarks[i];
    } else if (slots.right === undefined) {
      slots.right = landmarks[i];
    }
  }
  return slots;
}

export function resolveHandSlots(
  pose: RawLandmark[] | undefined,
  landmarks: RawLandmark[][] | undefined,
  handedness: HandednessCategory[][] | undefined
): HandSlots {
  if (!landmarks || landmarks.length === 0) return {};
  const leftWrist = pose?.[POSE_LEFT_WRIST];
  const rightWrist = pose?.[POSE_RIGHT_WRIST];
  if (leftWrist && rightWrist) {
    return resolveHandSlotsByWrist(landmarks, leftWrist, rightWrist);
  }
  return resolveHandSlotsByHandedness(landmarks, handedness);
}

export function extractBlendshapes(
  categories: { score: number }[] | undefined
): number[] {
  if (!categories || categories.length === 0) {
    return new Array(BLENDSHAPE_COUNT).fill(0);
  }
  return categories.map((c) => c.score);
}

export function isFaceEligibleTick(eligibleTickCount: number): boolean {
  return eligibleTickCount % 2 === 1;
}

export const MEDIAPIPE_MODELS_BASE_PATH = "/models";
export const MEDIAPIPE_WASM_BASE_PATH = "/mediapipe/wasm";
export const MEDIAPIPE_DETECTION_CONFIDENCE = 0.5;

export type TasksVisionModule = typeof import("@mediapipe/tasks-vision");

// GPU runs ~3x faster (23 vs 8 fps measured); machines without usable WebGL fall back to CPU.
export async function createLandmarkers(visionModule: TasksVisionModule) {
  const vision = await visionModule.FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_BASE_PATH);
  try {
    return await createLandmarkersWith(visionModule, vision, "GPU");
  } catch (e) {
    console.warn("[Nexora] GPU delegate unavailable, falling back to CPU", e);
    return createLandmarkersWith(visionModule, vision, "CPU");
  }
}

async function createLandmarkersWith(
  visionModule: TasksVisionModule,
  vision: Awaited<ReturnType<TasksVisionModule["FilesetResolver"]["forVisionTasks"]>>,
  delegate: "GPU" | "CPU"
) {
  const { PoseLandmarker, HandLandmarker, FaceLandmarker } = visionModule;
  const [pose, hand, face] = await Promise.all([
    PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: `${MEDIAPIPE_MODELS_BASE_PATH}/pose_landmarker_lite.task`,
        delegate,
      },
      runningMode: "VIDEO",
      numPoses: 1,
      minPoseDetectionConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
      minPosePresenceConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
      minTrackingConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
    }),
    HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: `${MEDIAPIPE_MODELS_BASE_PATH}/hand_landmarker.task`,
        delegate,
      },
      runningMode: "VIDEO",
      numHands: 2,
      minHandDetectionConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
      minHandPresenceConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
      minTrackingConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
    }),
    FaceLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: `${MEDIAPIPE_MODELS_BASE_PATH}/face_landmarker.task`,
        delegate,
      },
      runningMode: "VIDEO",
      outputFaceBlendshapes: true,
      minFaceDetectionConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
      minFacePresenceConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
      minTrackingConfidence: MEDIAPIPE_DETECTION_CONFIDENCE,
    }),
  ]);
  return { pose, hand, face };
}

export type MediaPipeLandmarkerSet = Awaited<ReturnType<typeof createLandmarkers>>;
