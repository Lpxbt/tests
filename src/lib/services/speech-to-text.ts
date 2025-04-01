import { blobToBase64 } from '../utils';

interface SpeechToTextOptions {
  apiKey?: string;
  language?: string;
}

const defaultOptions: SpeechToTextOptions = {
  apiKey: process.env.OPENAI_API_KEY || '',
  language: 'ru'
};

export async function speechToText(audioBlob: Blob, options: SpeechToTextOptions = {}): Promise<string> {
  const mergedOptions = { ...defaultOptions, ...options };

  if (!mergedOptions.apiKey) {
    throw new Error('OpenAI API key is required for speech-to-text');
  }

  try {
    // Convert audio to format accepted by OpenAI
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.wav');
    formData.append('model', 'whisper-1');
    if (mergedOptions.language) {
      formData.append('language', mergedOptions.language);
    }

    const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${mergedOptions.apiKey}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`Speech-to-text API error: ${errorData.error?.message || response.statusText}`);
    }

    const data = await response.json();
    return data.text || '';
  } catch (error) {
    console.error('Error in speech-to-text service:', error);
    throw error;
  }
}
