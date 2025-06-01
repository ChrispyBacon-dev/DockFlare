// src/app/layout.tsx

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css"; 
import Navbar from "@/components/common/Navbar";
import { SWRProvider } from "@/components/SWRProvider"; 

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DockFlare NextUI",
  description: "An experimental, modern UI for managing DockFlare.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark"> 
      <body 
        className={`${inter.className} bg-slate-900 text-slate-100 antialiased`}
      >
        <SWRProvider> 
          <div className="flex flex-col min-h-screen">
            <Navbar />
            <main className="flex-grow container mx-auto p-4 sm:p-6 lg:p-8">
              {children}
            </main>
            <footer className="text-center p-4 text-xs text-slate-400 border-t border-slate-700/50">
              DockFlare NextUI - Experimental © {new Date().getFullYear()}
            </footer>
          </div>
        </SWRProvider>
      </body>
    </html>
  );
}