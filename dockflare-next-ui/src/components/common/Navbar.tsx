// src/components/common/Navbar.tsx
import Link from 'next/link';
import AnimatedLogo from './AnimatedLogo';

export default function Navbar() {
  return (
    <nav className="bg-gray-800/50 backdrop-blur-md shadow-lg sticky top-0 z-50">
      <div className="container mx-auto px-6 py-2 flex justify-between items-center h-19"> 
        <div className="flex-1"> {/* This div will take up space, helping to center the middle item */}
        </div>

        <div className="flex-shrink-0"> 
          <Link href="/" aria-label="Go to dashboard"> 
            <AnimatedLogo />
          </Link>
        </div>

        <div className="flex-1 flex justify-end"> 
          <div className="space-x-4">
            <Link href="/" className="text-gray-300 hover:text-white">Dashboard</Link>
            <Link href="/rules" className="text-gray-300 hover:text-white">Rules</Link>
          </div>
        </div>
      </div>
    </nav>
  );
}