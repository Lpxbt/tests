import React from 'react';

export function Footer() {
  return (
    <footer className="border-t py-6 md:py-0">
      <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
        <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
          &copy; {new Date().getFullYear()} Business Trucks. Все права защищены.
        </p>
        <div className="flex items-center gap-4">
          <a href="#" className="text-sm text-muted-foreground hover:underline">
            Политика конфиденциальности
          </a>
          <a href="#" className="text-sm text-muted-foreground hover:underline">
            Условия использования
          </a>
        </div>
      </div>
    </footer>
  );
}
