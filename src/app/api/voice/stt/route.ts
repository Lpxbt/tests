import { NextRequest, NextResponse } from 'next/server';
import { speechToText } from '@/lib/services/speech-to-text';

export async function POST(request: NextRequest) {
  try {
    // Get form data with audio file
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File | null;
    
    if (!audioFile) {
      return NextResponse.json(
        { error: 'Invalid request: audio file is required' },
        { status: 400 }
      );
    }
    
    // Get API key from environment variable
    const apiKey = process.env.OPENAI_API_KEY;
    
    if (!apiKey) {
      return NextResponse.json(
        { error: 'OpenAI API key is not configured' },
        { status: 500 }
      );
    }
    
    // Convert speech to text
    const text = await speechToText(audioFile, { 
      apiKey,
      language: 'ru' // Set Russian language
    });
    
    // Return the transcribed text
    return NextResponse.json({ text });
  } catch (error) {
    console.error('Error in speech-to-text API route:', error);
    
    return NextResponse.json(
      { error: 'Failed to process speech-to-text request' },
      { status: 500 }
    );
  }
}
