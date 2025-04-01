import React from 'react';
import Image from 'next/image';

export function Header() {
  return (
    <header className="border-b">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2">
          <Image 
            src="/logo.svg" 
            alt="Business Trucks Logo" 
            width={40} 
            height={40} 
            className="h-10 w-10"
          />
          <span className="text-xl font-bold">Business Trucks</span>
        </div>
        
        <nav className="flex items-center gap-6">
          <a href="#" className="text-sm font-medium hover:underline">Главная</a>
          <a href="#" className="text-sm font-medium hover:underline">Каталог</a>
          <a href="#" className="text-sm font-medium hover:underline">О компании</a>
          <a href="#" className="text-sm font-medium hover:underline">Контакты</a>
        </nav>
        
        <div className="flex items-center gap-4">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
            Войти
          </button>
        </div>
      </div>
    </header>
  );
}
