import { useState, useEffect, useCallback, useRef } from 'react';

// Declarations for TypeScript
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export function useSpeechToText(onResult: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  // One recognition instance for the hook's lifetime: start/stop must act on the same object.
  const recognitionRef = useRef<any>(null);
  const onResultRef = useRef(onResult);
  const finalsRef = useRef("");
  const restartAfterStopRef = useRef(false);

  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return; // isSupported=false is the only signal; the UI shows a single notice

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'es-AR'; // Español Argentina

    rec.onresult = (event: any) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript.trim();
        if (event.results[i].isFinal) {
          finalsRef.current = `${finalsRef.current} ${transcript}`.trim();
        } else {
          interimTranscript = `${interimTranscript} ${transcript}`.trim();
        }
      }
      // Whole dictation of this session: accumulated finals plus the current interim segment
      onResultRef.current(`${finalsRef.current} ${interimTranscript}`.trim());
    };

    rec.onerror = (event: any) => {
      const code = event.error as string;
      if (code === "no-speech" || code === "aborted") return;
      console.error("Speech recognition error:", code);
      setError(code);
      setIsListening(false);
    };

    rec.onend = () => {
      if (restartAfterStopRef.current) {
        restartAfterStopRef.current = false;
        finalsRef.current = "";
        onResultRef.current("");
        try {
          rec.start();
          setIsListening(true);
        } catch {
          setIsListening(false);
        }
        return;
      }
      setIsListening(false);
    };

    recognitionRef.current = rec;
    setIsSupported(true);
    return () => {
      rec.onresult = rec.onerror = rec.onend = null;
      try { rec.abort(); } catch { /* not started */ }
      recognitionRef.current = null;
    };
  }, []);

  const startListening = useCallback(() => {
    const rec = recognitionRef.current;
    if (rec) {
      setError(null);
      finalsRef.current = "";
      try {
        rec.start();
        setIsListening(true);
      } catch (err) {
        console.error(err);
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    // isListening turns false in onend, once the engine has really stopped and can start again
    recognitionRef.current?.stop();
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  /** Clears accumulated dictation; if mic is on, restarts recognition so old finals do not reappear. */
  const resetTranscript = useCallback(() => {
    finalsRef.current = "";
    onResultRef.current("");
    const rec = recognitionRef.current;
    if (!rec || !isListening) return;
    restartAfterStopRef.current = true;
    try {
      rec.stop();
    } catch {
      restartAfterStopRef.current = false;
    }
  }, [isListening]);

  return { isListening, toggleListening, resetTranscript, error, isSupported };
}
