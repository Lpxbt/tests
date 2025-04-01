import React, { useState, useRef, useEffect } from 'react';
import { Message } from '@/lib/types';
import { generateId, formatDate } from '@/lib/utils';

interface ChatContainerProps {
  initialMessages: Message[];
  onSendMessage: (content: string) => Promise<Message>;
  onTextToSpeech: (text: string) => Promise<void>;
  onStartRecording: () => void;
  onStopRecording: () => Promise<string | null>;
  isRecording: boolean;
  isProcessing: boolean;
}

export function ChatContainer({
  initialMessages,
  onSendMessage,
  onTextToSpeech,
  onStartRecording,
  onStopRecording,
  isRecording,
  isProcessing
}: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Handle sending a message
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isProcessing) return;
    
    // Create user message
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };
    
    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    
    try {
      // Get response from AI
      const assistantMessage = await onSendMessage(inputValue);
      
      // Add assistant message to chat
      setMessages(prev => [...prev, assistantMessage]);
      
      // Convert response to speech
      await onTextToSpeech(assistantMessage.content);
    } catch (error) {
      console.error('Error in chat flow:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: 'Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    }
  };
  
  // Handle voice recording
  const handleVoiceRecording = async () => {
    if (isRecording) {
      // Stop recording and get transcription
      const text = await onStopRecording();
      
      if (text) {
        setInputValue(text);
        
        // Auto-send if we got text
        setTimeout(() => {
          handleSendMessage();
        }, 500);
      }
    } else {
      // Start recording
      onStartRecording();
    }
  };
  
  // Handle key press in textarea
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <h3 className="text-lg font-semibold mb-2">Добро пожаловать в Business Trucks</h3>
            <p className="text-muted-foreground mb-4">
              Я Анна, ваш персональный консультант по выбору грузовиков. Чем я могу вам помочь сегодня?
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-md">
              <button
                onClick={() => setInputValue('Какие модели грузовиков у вас есть?')}
                className="p-2 border rounded-md text-sm hover:bg-muted"
              >
                Какие модели грузовиков у вас есть?
              </button>
              <button
                onClick={() => setInputValue('Расскажите о ценах на грузовики')}
                className="p-2 border rounded-md text-sm hover:bg-muted"
              >
                Расскажите о ценах на грузовики
              </button>
              <button
                onClick={() => setInputValue('Какие условия лизинга вы предлагаете?')}
                className="p-2 border rounded-md text-sm hover:bg-muted"
              >
                Какие условия лизинга вы предлагаете?
              </button>
              <button
                onClick={() => setInputValue('Мне нужен грузовик для перевозки строительных материалов')}
                className="p-2 border rounded-md text-sm hover:bg-muted"
              >
                Нужен грузовик для стройматериалов
              </button>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                <div className="mb-1 text-sm opacity-70">
                  {message.role === 'user' ? 'Вы' : 'Анна'} • {formatDate(new Date(message.timestamp))}
                </div>
                <div className="whitespace-pre-wrap">{message.content}</div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <div className="border-t p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Введите сообщение..."
              className="w-full border rounded-md p-3 pr-10 min-h-[80px] max-h-[200px] resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isProcessing}
            />
          </div>
          
          <button
            onClick={handleVoiceRecording}
            className={`p-3 rounded-full ${
              isRecording
                ? 'bg-red-500 text-white animate-pulse'
                : 'bg-muted hover:bg-muted/80'
            }`}
            disabled={isProcessing}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
          </button>
          
          <button
            onClick={handleSendMessage}
            className="p-3 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            disabled={!inputValue.trim() || isProcessing}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6"
            >
              <path d="m22 2-7 20-4-9-9-4Z" />
              <path d="M22 2 11 13" />
            </svg>
          </button>
        </div>
        
        {isProcessing && (
          <div className="mt-2 text-sm text-muted-foreground flex items-center">
            <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
            Анна печатает...
          </div>
        )}
      </div>
    </div>
  );
}
