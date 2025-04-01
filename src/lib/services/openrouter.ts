import { OpenRouterConfig } from '../types';
import { generateId } from '../utils';

// Default configuration
const defaultConfig: OpenRouterConfig = {
  apiKey: process.env.OPENROUTER_API_KEY || '',
  model: process.env.NEXT_PUBLIC_MODEL || 'google/gemini-2.5-pro-exp-03-25:free',
  systemPrompt: `Ты Анна, русскоговорящий AI-агент по продажам грузовиков компании Business Trucks.
  Твоя задача - помогать клиентам выбрать подходящий грузовик, отвечать на их вопросы о характеристиках,
  ценах и условиях покупки. Всегда отвечай на русском языке, будь вежлива, профессиональна и информативна.
  Предлагай конкретные модели грузовиков на основе потребностей клиента.`
};

export async function sendChatRequest(messages: any[], config: Partial<OpenRouterConfig> = {}) {
  const mergedConfig = { ...defaultConfig, ...config };

  if (!mergedConfig.apiKey) {
    throw new Error('OpenRouter API key is required');
  }

  const systemMessage = {
    role: 'system',
    content: mergedConfig.systemPrompt
  };

  const allMessages = [systemMessage, ...messages];

  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${mergedConfig.apiKey}`,
        'HTTP-Referer': 'https://businesstrucks.com',
        'X-Title': 'Business Trucks Sales Agent'
      },
      body: JSON.stringify({
        model: mergedConfig.model,
        messages: allMessages,
        temperature: 0.7,
        max_tokens: 1024,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`OpenRouter API error: ${errorData.error?.message || response.statusText}`);
    }

    const data = await response.json();

    return {
      id: generateId(),
      role: 'assistant' as const,
      content: data.choices[0].message.content,
      timestamp: new Date(),
    };
  } catch (error) {
    console.error('Error in OpenRouter service:', error);
    throw error;
  }
}
