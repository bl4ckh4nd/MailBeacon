import React from 'react';
// Remove Box, Container from MUI
import { NavLink } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  // Helper for NavLink classes
  const getNavLinkClass = ({ isActive }: { isActive: boolean }): string => {
    const baseClass = "px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out";
    const activeClass = "bg-sky-700 text-white";
    const inactiveClass = "text-sky-100 hover:bg-sky-500 hover:text-white";
    return `${baseClass} ${isActive ? activeClass : inactiveClass}`;
  };

  return (
    // Main layout container: flex column, min height screen, background
    <div className="flex flex-col min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-sky-600 shadow-md sticky top-0 z-10">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left side: Logo/Title */}
            <div className="flex-shrink-0">
              <span className="text-2xl font-bold text-white tracking-tight">
                MailBeacon
              </span>
            </div>
            {/* Right side: Navigation Links */}
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <NavLink to="/single" className={getNavLinkClass}>
                  Single Finder
                </NavLink>
                <NavLink to="/batch" className={getNavLinkClass}>
                  Batch Finder
                </NavLink>
              </div>
            </div>
            {/* TODO: Add Mobile Menu Button for smaller screens */}
          </div>
        </nav>
      </header>

      {/* Main content area */}
      {/* flex-grow allows this section to take up available space */}
      {/* flex flex-col items-center centers the content horizontally */}
      {/* justify-center attempts vertical center - works best when content is not too tall */}
      <main className="flex-grow flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        {/* Inner container for max-width and consistent padding */}
        <div className="w-full max-w-4xl">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="p-4 bg-gray-200 text-center text-gray-600 text-sm mt-auto">
        © {new Date().getFullYear()} MailBeacon
      </footer>
    </div>
  );
};

export default Layout; 
