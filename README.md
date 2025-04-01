# Business Trucks AI Web Application

This is the web application for the Business Trucks AI sales agent (Anna). It provides a user-friendly interface for interacting with the AI agent.

## Features

- Chat interface for communicating with the AI agent
- Text-to-speech functionality using ElevenLabs API
- Speech-to-text functionality for voice input
- Russian language support
- Responsive design for desktop and mobile devices

## Technologies Used

- Next.js 14 for the frontend and API routes
- OpenRouter API for AI model access (using Gemini 2.5 Pro)
- ElevenLabs API for high-quality text-to-speech
- TypeScript for type safety
- Tailwind CSS for styling

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create a `.env` file with the following variables:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id
   NEXT_PUBLIC_MODEL=google/gemini-2.5-pro-exp-03-25:free
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Build for production:
   ```bash
   npm run build
   ```

5. Start the production server:
   ```bash
   npm start
   ```

## Deployment

This application can be deployed to Vercel or any other Next.js-compatible hosting service.

## API Routes

- `/api/chat` - Chat API endpoint for communicating with the AI agent
- `/api/voice/tts` - Text-to-speech API endpoint for converting text to speech
- `/api/voice/stt` - Speech-to-text API endpoint for converting speech to text

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.
