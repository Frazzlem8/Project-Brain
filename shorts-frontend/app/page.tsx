'use client';

import { useState, useRef, useEffect } from 'react';

export default function Home() {
  const [videoUrl, setVideoUrl] = useState('');
  const [step, setStep] = useState('all');
  const [output, setOutput] = useState('');
  const [loading, setLoading] = useState(false);
  const outputRef = useRef<HTMLPreElement | null>(null);

  const steps = [
    'all', 'download', 'transcribe', 'find_moments',
    'cut_clips', 'resize', 'label', 'generate_metadata',
    'upload'
  ];

  const handleRun = async () => {
    if (!videoUrl) return;

    setOutput('');
    setLoading(true);

    const eventSource = new EventSource(
      `http://localhost:5000/api/run-script-stream?video_url=${encodeURIComponent(videoUrl)}&step=${step}`
    );

    console.log("EventSource:", eventSource);

    eventSource.onmessage = (event) => {
      setOutput((prev) => prev + event.data + '\n');
    };

    eventSource.addEventListener('done', () => {
      setLoading(false);
      eventSource.close();
    });

    eventSource.onerror = (err) => {
      console.error("Stream error:", err);
      setOutput((prev) => prev + '\n❌ Error in stream');
      setLoading(false);
      eventSource.close();
    };
  };

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  return (
    <>
      {/* Fixed Banner */}
      <div className="fraselabs-banner">
        🚀 FraseLabs Shorts Automation Toolkit
      </div>

      <main className="p-6 max-w-2xl mx-auto mt-20">
        <div className="flex items-center gap-4 mb-6">
          <img
            src="/fraselabs-lava.png"
            alt="FraseLabs Logo"
            className="h-10 w-auto"
          />
          <h1 className="text-3xl font-bold text-accent">
            FraseLabs Shorts Automation
          </h1>
        </div>

        <input
          className="w-full p-2 border border-gray-300 rounded mb-3 focus:outline-none focus:ring-2 focus:ring-accent"
          type="text"
          placeholder="Enter YouTube video URL"
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
        />

        <select
          className="w-full p-2 border border-gray-300 rounded mb-3"
          value={step}
          onChange={(e) => setStep(e.target.value)}
        >
          {steps.map((s) => (
            <option key={s} value={s}>
              {s === 'all' ? 'Run All Steps' : s}
            </option>
          ))}
        </select>
        
        
        <button
          onClick={handleRun}
          disabled={loading}
          className={`w-full text-white py-2 rounded font-semibold transition ${
            loading
              ? 'bg-blue-600 hover:bg-blue-700'
              : 'bg-green-600 hover:bg-green-700'
          }`}
        >
          {loading ? 'Processing...' : 'Run Automation'}
        </button>

        <details open className="mt-6">
          <summary className="cursor-pointer text-sm text-accent mb-2">
            View Output
          </summary>
          <pre
            ref={outputRef}
            className="bg-black text-white p-4 rounded whitespace-pre-wrap overflow-auto max-h-96"
          >
            {output}
          </pre>
        </details>

        <footer className="text-center text-sm text-gray-500 mt-10">
          Built by{' '}
          <a
            href="https://fraselabs.com"
            target="_blank"
            className="text-blue-500 underline"
          >
            FraseLabs
          </a>
        </footer>
      </main>
    </>
  );
}