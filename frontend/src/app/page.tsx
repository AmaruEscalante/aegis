'use client';

import { useChat } from 'ai/react';
import { useRef, useState } from 'react';
import { ShieldCheck, ShieldAlert, Send, FileCode, CheckCircle, XCircle } from 'lucide-react';
import clsx from 'clsx';
import Image from 'next/image';

export default function Chat() {
  const { messages, input, handleInputChange, handleSubmit, setInput, isLoading } = useChat({
    api: 'http://localhost:8000/api/chat',
  });
  
  // Ref for hidden file input
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      // Read file content
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        // Append file content to the input message
        const fileMsg = `[FILE: ${file.name}]\n${content}\n\nAnalyze this file.`;
        setInput(fileMsg);
      };
      reader.readAsText(file);
    }
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col w-full max-w-3xl mx-auto h-screen py-8 px-4 bg-zinc-50 dark:bg-zinc-900 font-sans">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
            <ShieldCheck className="w-8 h-8 text-emerald-500" />
            <div>
                <h1 className="text-2xl font-bold text-zinc-800 dark:text-zinc-100">Aegis</h1>
                <p className="text-sm text-zinc-500">Local Privacy Layer</p>
            </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono bg-zinc-100 dark:bg-zinc-800 px-3 py-1 rounded-full">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            LOCAL: FunctionGemma
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2 scrollbar-thin scrollbar-thumb-zinc-300 dark:scrollbar-thumb-zinc-700">
        {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-zinc-400 opacity-50">
                <ShieldAlert className="w-16 h-16 mb-4" />
                <p>Ready to inspect sensitive data.</p>
            </div>
        )}
        
        {messages.map(m => (
          <div key={m.id} className={clsx(
            "flex w-full mb-4",
            m.role === 'user' ? "justify-end" : "justify-start"
          )}>
            <div className={clsx(
                "max-w-[80%] rounded-2xl px-5 py-3 shadow-sm",
                m.role === 'user' 
                    ? "bg-blue-600 text-white rounded-br-none" 
                    : "bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200 rounded-bl-none"
            )}>
              <div className="text-sm font-medium mb-1 opacity-75 flex items-center gap-2">
                {m.role === 'user' ? 'You' : (
                    <>
                        <ShieldCheck className="w-3 h-3 text-emerald-500" /> Aegis
                    </>
                )}
              </div>
              <div className="whitespace-pre-wrap leading-relaxed text-sm">
                {m.content}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
            <div className="flex w-full justify-start mb-4">
                 <div className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-2xl rounded-bl-none px-5 py-3 shadow-sm flex items-center gap-3">
                    <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-sm text-zinc-500 animate-pulse">Deep scanning for PII...</span>
                 </div>
            </div>
        )}
      </div>

      {/* Input Area */}
      <div className="relative">
        {fileName && (
            <div className="absolute -top-10 left-0 bg-zinc-100 dark:bg-zinc-800 px-3 py-1 text-xs rounded-t-lg flex items-center gap-2 border border-b-0 border-zinc-200 dark:border-zinc-700">
                <FileCode className="w-3 h-3" />
                {fileName}
                <button onClick={() => {setFileName(null); setInput('');}} className="hover:text-red-500 ml-2">
                    <XCircle className="w-3 h-3" />
                </button>
            </div>
        )}
        
        <form onSubmit={handleSubmit} className="relative flex items-center shadow-lg rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800">
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden" 
            />
            
            <button 
                type="button"
                onClick={handleFileClick}
                className="p-4 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-400 transition-colors border-r border-zinc-100 dark:border-zinc-700"
                title="Upload file for analysis"
            >
                <FileCode className="w-5 h-5" />
            </button>

            <input
            className="flex-1 p-4 bg-transparent outline-none text-zinc-800 dark:text-zinc-100 placeholder:text-zinc-400"
            value={input}
            onChange={handleInputChange}
            placeholder="Paste text or upload file to analyze..."
            />
            
            <button 
                type="submit"
                disabled={isLoading || (!input && !fileName)}
                className="p-4 bg-emerald-600 hover:bg-emerald-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Send className="w-5 h-5" />
            </button>
        </form>
        <div className="text-center mt-2 text-xs text-zinc-400">
            Secured by FunctionGemma & Cactus Compute
        </div>
      </div>
    </div>
  );
}
