export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ChatRequest {
  messages: {
    role: 'user' | 'assistant' | 'system';
    content: string;
  }[];
}

export interface ChatResponse {
  message: Message;
}

export interface TextToSpeechRequest {
  text: string;
  voice?: string;
}

export interface SpeechToTextRequest {
  audio: Blob;
}

export interface SpeechToTextResponse {
  text: string;
}

export interface OpenRouterConfig {
  apiKey: string;
  model: string;
  systemPrompt: string;
}

export interface ElevenLabsConfig {
  apiKey: string;
  voiceId: string;
  stability: number;
  similarityBoost: number;
}
