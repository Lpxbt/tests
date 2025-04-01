import { ElevenLabsConfig } from '../types';

// Default configuration
const defaultConfig: ElevenLabsConfig = {
  apiKey: process.env.ELEVENLABS_API_KEY || '',
  voiceId: process.env.ELEVENLABS_VOICE_ID || 'C3FusDjPequ6qFchqpzu', // Use configured voice ID or default
  stability: 0.5,
  similarityBoost: 0.75
};

export async function textToSpeech(text: string, config: Partial<ElevenLabsConfig> = {}): Promise<ArrayBuffer> {
  const mergedConfig = { ...defaultConfig, ...config };

  if (!mergedConfig.apiKey) {
    throw new Error('ElevenLabs API key is required');
  }

  try {
    const response = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${mergedConfig.voiceId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'xi-api-key': mergedConfig.apiKey,
        },
        body: JSON.stringify({
          text,
          model_id: 'eleven_multilingual_v2',
          voice_settings: {
            stability: mergedConfig.stability,
            similarity_boost: mergedConfig.similarityBoost,
          },
        }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`ElevenLabs API error: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.arrayBuffer();
  } catch (error) {
    console.error('Error in ElevenLabs service:', error);
    throw error;
  }
}

export async function getVoices(apiKey: string = defaultConfig.apiKey): Promise<any[]> {
  if (!apiKey) {
    throw new Error('ElevenLabs API key is required');
  }

  try {
    const response = await fetch('https://api.elevenlabs.io/v1/voices', {
      method: 'GET',
      headers: {
        'xi-api-key': apiKey,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`ElevenLabs API error: ${errorData.detail?.message || response.statusText}`);
    }

    const data = await response.json();
    return data.voices || [];
  } catch (error) {
    console.error('Error fetching ElevenLabs voices:', error);
    throw error;
  }
}
