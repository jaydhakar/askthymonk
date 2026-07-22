import * as Speech from "expo-speech";
import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from "expo-speech-recognition";
import { useCallback, useEffect, useRef, useState } from "react";

type Options = {
  /** BCP-47 locale, e.g. "hi-IN". */
  lang: string;
  /** Called with each interim/final transcript so it can stream into the input. */
  onTranscript: (text: string) => void;
  /** Called with a human-readable message on failure or denied permission. */
  onError?: (message: string) => void;
  /** Localized message shown when permission is denied. */
  permissionMessage?: string;
};

/**
 * Wraps expo-speech-recognition into a simple toggle-able hook:
 * - streams interim results into the text input for verification before submit
 * - starting the mic cancels any TTS currently playing
 * - locale follows the selected language (hi-IN / en-IN)
 *
 * Note: this relies on a native module and therefore only works in a custom
 * dev-client build (or a store build), not in Expo Go.
 */
export function useSpeechToText({ lang, onTranscript, onError, permissionMessage }: Options) {
  const [listening, setListening] = useState(false);

  // Keep callbacks in refs so the native event listeners always see the latest.
  const onTranscriptRef = useRef(onTranscript);
  const onErrorRef = useRef(onError);
  const permissionMessageRef = useRef(permissionMessage);
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
    onErrorRef.current = onError;
    permissionMessageRef.current = permissionMessage;
  });

  useSpeechRecognitionEvent("start", () => setListening(true));
  useSpeechRecognitionEvent("end", () => setListening(false));
  useSpeechRecognitionEvent("result", (event) => {
    const transcript = event.results?.[0]?.transcript ?? "";
    if (transcript.length > 0) onTranscriptRef.current(transcript);
  });
  useSpeechRecognitionEvent("error", (event) => {
    setListening(false);
    onErrorRef.current?.(event.message || event.error);
  });

  const start = useCallback(async () => {
    try {
      // Starting the mic cancels any TTS currently playing.
      Speech.stop();

      const permission = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
      if (!permission.granted) {
        onErrorRef.current?.(
          permissionMessageRef.current ??
            "Microphone and speech-recognition permission are needed for voice input."
        );
        return;
      }

      ExpoSpeechRecognitionModule.start({
        lang,
        interimResults: true,
        continuous: false,
        maxAlternatives: 1,
      });
    } catch (e) {
      setListening(false);
      onErrorRef.current?.(e instanceof Error ? e.message : "Could not start voice input.");
    }
  }, [lang]);

  const stop = useCallback(() => {
    try {
      ExpoSpeechRecognitionModule.stop();
    } catch {
      // Ignore — nothing was listening.
    }
  }, []);

  const toggle = useCallback(() => {
    if (listening) {
      stop();
    } else {
      void start();
    }
  }, [listening, start, stop]);

  return { listening, toggle, start, stop };
}
