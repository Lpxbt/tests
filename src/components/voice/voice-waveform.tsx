import React, { useEffect, useRef } from 'react';

interface VoiceWaveformProps {
  isRecording: boolean;
  audioLevel: number;
}

interface AudioVisualizerProps {
  stream: MediaStream;
  onAudioLevel: (level: number) => void;
}

export function VoiceWaveform({ isRecording, audioLevel }: VoiceWaveformProps) {
  return (
    <div className="h-6 w-full flex items-center justify-center">
      {isRecording ? (
        <div className="flex items-center space-x-1">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="bg-red-500 w-1 rounded-full animate-pulse"
              style={{
                height: `${Math.max(4, audioLevel * 24 * (0.5 + Math.sin(i / 2) / 2))}px`,
                animationDelay: `${i * 0.1}s`,
              }}
            />
          ))}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">
          Нажмите на микрофон для записи
        </div>
      )}
    </div>
  );
}

export function AudioVisualizer({ stream, onAudioLevel }: AudioVisualizerProps) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const rafIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!stream) return;

    // Create audio context
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    analyserRef.current = audioContextRef.current.createAnalyser();
    analyserRef.current.fftSize = 32;

    // Connect the stream to the analyser
    const source = audioContextRef.current.createMediaStreamSource(stream);
    source.connect(analyserRef.current);

    // Create data array for frequency data
    const bufferLength = analyserRef.current.frequencyBinCount;
    dataArrayRef.current = new Uint8Array(bufferLength);

    // Start analyzing
    const analyzeAudio = () => {
      if (!analyserRef.current || !dataArrayRef.current) return;

      rafIdRef.current = requestAnimationFrame(analyzeAudio);
      analyserRef.current.getByteFrequencyData(dataArrayRef.current);

      // Calculate average volume level (0-1)
      const average = dataArrayRef.current.reduce((acc, val) => acc + val, 0) / 
                     (dataArrayRef.current.length * 255);
      
      onAudioLevel(average);
    };

    analyzeAudio();

    // Cleanup
    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, onAudioLevel]);

  return null; // This is just for audio processing, no visual component
}
