import { NextRequest, NextResponse } from 'next/server';
import { sendChatRequest } from '@/lib/services/openrouter';
import { ChatRequest, ChatResponse } from '@/lib/types';

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    
    if (!body.messages || !Array.isArray(body.messages)) {
      return NextResponse.json(
        { error: 'Invalid request: messages array is required' },
        { status: 400 }
      );
    }
    
    // Get API key from environment variable
    const apiKey = process.env.OPENROUTER_API_KEY;
    
    if (!apiKey) {
      return NextResponse.json(
        { error: 'OpenRouter API key is not configured' },
        { status: 500 }
      );
    }
    
    // Send request to OpenRouter
    const message = await sendChatRequest(body.messages, { apiKey });
    
    // Return the response
    const response: ChatResponse = { message };
    return NextResponse.json(response);
  } catch (error) {
    console.error('Error in chat API route:', error);
    
    return NextResponse.json(
      { error: 'Failed to process chat request' },
      { status: 500 }
    );
  }
}
