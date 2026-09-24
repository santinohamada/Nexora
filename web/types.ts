export type ChatMessage = {
  id: number;
  role: "PACIENTE" | "RECEPCIONISTA";
  text: string;
  time: string;
  words?: string[];
};

export type PredictionItem = {
  sign: string;
  confidence: number;
};

export type Prediction = {
  sign: string;
  confidence: number;
  top3: PredictionItem[];
};

export type Landmark = [number, number, number, number]; // x, y, z, visibility
export type Frame = Landmark[];
export type Status = "idle" | "loading" | "recording" | "processing" | "done" | "error";
export type PredictionResult = Prediction;
