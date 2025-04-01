'use client';

import React, { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { Message } from '@/lib/types';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0.5);
  const [inputText, setInputText] = useState('');

  const handleSendMessage = async () => {
    if (!inputText.trim() || isProcessing) return;

    // Add user message to chat
    const userMessage: Message = {
      id: Math.random().toString(36).substring(2),
      role: 'user',
      content: inputText,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsProcessing(true);

    try {
      // Call API to get response
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(msg => ({
            role: msg.role,
            content: msg.content,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      // Add assistant message to chat
      setMessages(prev => [...prev, data.message]);

      // Convert to speech
      await handleTextToSpeech(data.message.content);
    } catch (error) {
      console.error('Error:', error);

      // Add error message
      setMessages(prev => [
        ...prev,
        {
          id: Math.random().toString(36).substring(2),
          role: 'assistant',
          content: 'Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTextToSpeech = async (text: string) => {
    try {
      const response = await fetch('/api/voice/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error('Failed to convert text to speech');
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      await new Promise<void>((resolve) => {
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          resolve();
        };
        audio.play();
      });
    } catch (error) {
      console.error('Error in text-to-speech:', error);
    }
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center">
            <Image
              src="/logo.svg"
              alt="Business Trucks Logo"
              width={40}
              height={40}
              className="h-10 w-10"
            />
            <h1 className="ml-2 text-xl font-bold text-gray-900 dark:text-white">Business Trucks</h1>
          </div>
          <nav className="flex space-x-4">
            <a href="#" className="text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white">Главная</a>
            <a href="#" className="text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white">Каталог</a>
            <a href="#" className="text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white">Контакты</a>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Truck Visualization */}
          <div className="hidden md:block md:col-span-1 bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white">Наши грузовики</h2>
            </div>
            <div className="p-4 h-[400px] flex items-center justify-center">
              <Image
                src="/truck.png"
                alt="Truck"
                width={300}
                height={200}
                className="max-w-full h-auto"
              />
            </div>
          </div>

          {/* Chat Interface */}
          <div className="col-span-1 md:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white">Анна - Специалист по продажам</h2>
              {isRecording && (
                <div className="flex space-x-1">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className="h-2 w-1 bg-red-500 rounded-full animate-pulse"
                      style={{ animationDelay: `${i * 0.1}s` }}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="flex-1 p-4 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center p-4">
                  <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Добро пожаловать в Business Trucks</h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">
                    Я Анна, ваш персональный консультант по выбору грузовиков. Чем я могу вам помочь сегодня?
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-md">
                    <button
                      onClick={() => setInputText('Какие модели грузовиков у вас есть?')}
                      className="p-2 border rounded-md text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                    >
                      Какие модели грузовиков у вас есть?
                    </button>
                    <button
                      onClick={() => setInputText('Расскажите о ценах на грузовики')}
                      className="p-2 border rounded-md text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                    >
                      Расскажите о ценах на грузовики
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg p-3 ${
                          message.role === 'user'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                        }`}
                      >
                        <div className="text-xs opacity-70 mb-1">
                          {message.role === 'user' ? 'Вы' : 'Анна'} • {formatTime(message.timestamp)}
                        </div>
                        <div className="whitespace-pre-wrap">{message.content}</div>
                      </div>
                    </div>
                  ))}
                  {isProcessing && (
                    <div className="flex justify-start">
                      <div className="max-w-[80%] rounded-lg p-3 bg-gray-100 dark:bg-gray-700">
                        <div className="flex items-center space-x-2">
                          <div className="h-2 w-2 bg-gray-400 rounded-full animate-pulse"></div>
                          <div className="h-2 w-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                          <div className="h-2 w-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Введите сообщение..."
                  className="flex-1 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isProcessing}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!inputText.trim() || isProcessing}
                  className="rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  Отправить
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="bg-white dark:bg-gray-800 shadow mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-gray-500 dark:text-gray-400">
            &copy; {new Date().getFullYear()} Business Trucks. Все права защищены.
          </p>
        </div>
      </footer>
    </div>
  );
}
