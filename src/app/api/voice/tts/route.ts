import { NextRequest, NextResponse } from 'next/server';
import { textToSpeech } from '@/lib/services/elevenlabs';
import { TextToSpeechRequest } from '@/lib/types';

export async function POST(request: NextRequest) {
  try {
    const body: TextToSpeechRequest = await request.json();

    if (!body.text) {
      return NextResponse.json(
        { error: 'Invalid request: text is required' },
        { status: 400 }
      );
    }

    // Get API key and voice ID from environment variables
    const apiKey = process.env.ELEVENLABS_API_KEY;
    const voiceId = process.env.ELEVENLABS_VOICE_ID || 'C3FusDjPequ6qFchqpzu';

    if (!apiKey) {
      return NextResponse.json(
        { error: 'ElevenLabs API key is not configured' },
        { status: 500 }
      );
    }

    // Convert text to speech
    const audioBuffer = await textToSpeech(body.text, {
      apiKey,
      voiceId: body.voice || voiceId
    });

    // Return the audio data
    return new NextResponse(audioBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Length': audioBuffer.byteLength.toString(),
      },
    });
  } catch (error) {
    console.error('Error in text-to-speech API route:', error);

    return NextResponse.json(
      { error: 'Failed to process text-to-speech request' },
      { status: 500 }
    );
  }
}
