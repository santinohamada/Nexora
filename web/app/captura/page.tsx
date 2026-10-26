"use client";

import { useCallback, useRef, useState } from "react";
import { CaptureMode } from "../../components/capture/CaptureMode";
import { useMediaPipeTasks } from "../../hooks/useMediaPipeTasks";
import { Frame } from "../../types";

export default function CapturaPage() {
  const captureHandlerRef = useRef<((f: Frame, blendshapes?: number[]) => void) | null>(null);
  const [showSkeleton, setShowSkeleton] = useState(true);

  const handleFrame = useCallback((frameData: Frame, blendshapes?: number[]) => {
    captureHandlerRef.current?.(frameData, blendshapes);
  }, []);

  const { videoRef, canvasRef, status, setStatus } = useMediaPipeTasks({
    onFrame: handleFrame,
    drawLandmarksOnCanvas: showSkeleton,
  });

  return (
    <CaptureMode
      videoRef={videoRef}
      canvasRef={canvasRef}
      status={status}
      setStatus={setStatus}
      captureHandlerRef={captureHandlerRef}
      showSkeleton={showSkeleton}
      onShowSkeletonChange={setShowSkeleton}
    />
  );
}
