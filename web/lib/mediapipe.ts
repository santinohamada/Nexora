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

export function resolveHandSlots(
  landmarks: RawLandmark[][] | undefined,
  handedness: HandednessCategory[][] | undefined
): HandSlots {
  const slots: HandSlots = {};
  if (!landmarks || landmarks.length === 0) return slots;
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

export async function createLandmarkers(visionModule: TasksVisionModule) {
  const { FilesetResolver, PoseLandmarker, HandLandmarker, FaceLandmarker } = visionModule;
  const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_BASE_PATH);
  const [pose, hand, face] = await Promise.all([
    PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: `${MEDIAPIPE_MODELS_BASE_PATH}/pose_landmarker_lite.task`,
        delegate: "CPU",
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
        delegate: "CPU",
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
        delegate: "CPU",
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

const loadedScripts = new Set<string>();

export function loadScript(src: string): Promise<void> {
  if (typeof document === "undefined") {
    return Promise.reject(new Error("document unavailable"));
  }
  if (loadedScripts.has(src)) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
    if (existing) {
      loadedScripts.add(src);
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.onload = () => {
      loadedScripts.add(src);
      resolve();
    };
    script.onerror = () => reject(new Error(`${src} failed to load`));
    document.head.appendChild(script);
  });
}
