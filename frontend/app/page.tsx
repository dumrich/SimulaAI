'use client'; // This directive is necessary for React hooks

// Removed all @react-three/fiber and THREE imports
import React, { useState, useEffect, useRef } from 'react';
// Import 'recharts' for graphs
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Play, Pause, RotateCcw, Bot, PanelLeft, PanelRight, Send, BrainCircuit } from 'lucide-react';

// This is the shape of the simulation object we'll get from your API
interface Simulation {
  simulation_id: string;
  model_xml: string;
}

/**
 * Main application page.
 */
export default function Home() {
  // This state will hold the simulation details from your API
  const [simulation, setSimulation] = useState<Simulation | null>(null);

  // This callback now receives the API response
  const handleChatSubmit = (apiResponse: Simulation) => {
    setSimulation(apiResponse);
  };

  return (
    <main className="flex h-screen w-screen flex-col items-center justify-center bg-gray-900 text-white font-sans">
      {/* We now pass the 'simulation' object to the layout.
        If 'simulation' is null, show Chatbot. If it has data, show Layout.
      */}
      {simulation ? (
        <SimulationLayout simulation={simulation} />
      ) : (
        <ChatbotEntry onChatSubmit={handleChatSubmit} />
      )}
    </main>
  );
}

// ------------------------------------------------------------------
// 1. Chatbot entry component (Now calls your API)
// ------------------------------------------------------------------
function ChatbotEntry({ onChatSubmit }: { onChatSubmit: (sim: Simulation) => void }) {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsLoading(true);
    setError('');

    try {
      // *** THIS NOW CALLS YOUR FASTAPI ENDPOINT ***
      // NOTE: Assumes your FastAPI is running on http://localhost:8000
      const response = await fetch('http://localhost:8000/simulation/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const simulationData: Simulation = await response.json();
      
      // Pass the simulation data back to the parent to switch views
      onChatSubmit(simulationData);

    } catch (err: any) {
      setError(err.message);
      console.error("Error generating simulation:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-full h-full p-4">
      <div className="w-full max-w-2xl text-center">
        <h1 className="text-6xl font-bold text-white mb-4 flex items-center justify-center gap-4">
          <BrainCircuit size={60} /> SimulaAI
        </h1>
        <p className="text-xl text-gray-400 mb-10">
          Start by describing the robot simulation you want to build.
        </p>
        
        <form onSubmit={handleSubmit} className="w-full">
          <div className="relative flex w-full">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., 'Start training a bipedal walker'"
              className="w-full pl-6 pr-20 py-5 bg-gray-800 border border-gray-700 text-white rounded-full text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              disabled={isLoading}
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-3 rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="w-6 h-6 border-2 border-t-transparent border-white rounded-full animate-spin" />
              ) : (
                <Send size={24} />
              )}
            </button>
          </div>
          {error && <p className="text-red-400 mt-4">{error}</p>}
        </form>
      </div>
    </div>
  );
}


// ------------------------------------------------------------------
// 2. Main simulation layout (Now renders DashboardContainer)
// ------------------------------------------------------------------
function SimulationLayout({ simulation }: { simulation: Simulation }) {
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);

  // This state will hold the most recent model_xml from the /refine endpoint
  const [currentModelXml, setCurrentModelXml] = useState(simulation.model_xml);
  const [isSimRunning, setIsSimRunning] = useState(true);
  const [resetTrigger, setResetTrigger] = useState(0);

  // This handler calls your /simulation/refine endpoint
  const handleRefineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const input = form.elements.namedItem('prompt') as HTMLInputElement;
    const prompt = input.value;
    if (!prompt) return;

    try {
      const response = await fetch('http://localhost:8000/simulation/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          simulation_id: simulation.simulation_id,
          model_xml: currentModelXml, // Send the *current* XML
        }),
      });

      if (!response.ok) throw new Error(`API Error: ${response.statusText}`);

      const newSimData: Simulation = await response.json();
      // Update the state with the new XML returned from the backend
      setCurrentModelXml(newSimData.model_xml);
      input.value = ''; // Clear input

    } catch (err) {
      console.error("Error refining simulation:", err);
    }
  };


  return (
    <div className="flex h-full w-full">
      
      {/* Left Sidebar (Inspector) */}
      {isLeftSidebarOpen && (
        <div className="w-72 h-full bg-gray-800 border-r border-gray-700 p-4">
          <InspectorPanel />
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full relative bg-gray-900">
        {/* Top Header/Toolbar */}
        <div className="flex items-center justify-between w-full h-14 bg-gray-800 border-b border-gray-700 px-4">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setIsLeftSidebarOpen(!isLeftSidebarOpen)}
              className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700"
              title={isLeftSidebarOpen ? "Hide Inspector" : "Show Inspector"}
            >
              <PanelLeft size={18} />
            </button>
          </div>
          
          {/* Simulation Controls */}
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSimRunning(true)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors text-sm ${
                isSimRunning 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-white hover:bg-gray-600'
              }`}
            >
              <Play size={16} /> <span>Run Training</span>
            </button>
            <button 
              onClick={() => setIsSimRunning(false)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors text-sm ${
                !isSimRunning 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-white hover:bg-gray-600'
              }`}
            >
              <Pause size={16} /> <span>Pause Training</span>
            </button>
            <button 
              onClick={() => setResetTrigger(v => v + 1)} // Increment trigger
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors text-sm"
            >
              <RotateCcw size={16} /> <span>Reset</span>
            </button>
          </div>
          
          <div className="flex items-center gap-1">
            <button 
              onClick={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
              className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700"
              title={isRightSidebarOpen ? "Hide LLM Panel" : "Show LLM Panel"}
            >
              <PanelRight size={18} />
            </button>
          </div>
        </div>

        {/* ******* NEW: Main Dashboard Area ******* */}
        <div className="flex-1 w-full h-full overflow-y-auto p-4">
          <DashboardContainer
            simulationId={simulation.simulation_id}
            isRunning={isSimRunning}
            resetTrigger={resetTrigger}
          />
        </div>

        {/* Overlay Chat Bar - Now wired to your API */}
        <form 
          className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4"
          onSubmit={handleRefineSubmit}
        >
          <div className="relative flex w-full">
            <input
              type="text"
              name="prompt"
              placeholder="Refine the training... (e.g., 'Increase learning rate')"
              className="w-full pl-6 pr-16 py-4 bg-gray-800 bg-opacity-80 backdrop-blur-md border border-gray-700 text-white rounded-full text-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2.5 rounded-full hover:bg-blue-700 transition-colors"
            >
              <Send size={20} />
            </button>
          </div>
        </form>
      </div>

      {/* Right Sidebar (LLM) */}
      {isRightSidebarOpen && (
        <div className="w-80 h-full bg-gray-800 border-l border-gray-700 p-4">
          <LLMPanel />
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// 3. Re-usable components
// ------------------------------------------------------------------

const getInitialData = () => [
  { episode: 0, reward: 0, length: 0 },
];

/**
 * NEW: The main dashboard for showing graphs.
 * This component now connects to a WebSocket for live data.
 */
function DashboardContainer({ simulationId, isRunning, resetTrigger }: {
  simulationId: string;
  isRunning: boolean;
  resetTrigger: number;
}) {
  const [data, setData] = useState(getInitialData());

  // This effect connects to the WebSocket for live data
  useEffect(() => {
    if (!simulationId) return;

    // Connect to the WebSocket (assumes FastAPI is on port 8000)
    // Your API guy needs to build this endpoint
    console.log(`Connecting to WebSocket: ws://localhost:8000/ws/train/${simulationId}`);
    const ws = new WebSocket(`ws://localhost:8000/ws/train/${simulationId}`);

    ws.onopen = () => {
      console.log("WebSocket connected");
      // Tell the backend to start/pause training
      ws.send(JSON.stringify({ command: isRunning ? "run" : "pause" }));
    };

    // This is where new graph data arrives
    ws.onmessage = (event) => {
      try {
        const newDataPoint = JSON.parse(event.data);
        // Expect data like: { "episode": 1, "reward": 10.5, "length": 150 }
        if (newDataPoint.episode !== undefined) {
          setData(currentData => [...currentData, newDataPoint]);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
    };

    // Cleanup: close the connection when the component unmounts
    return () => {
      ws.close();
    };
  }, [simulationId]); // Reconnect if the simulationId changes

  // This effect sends run/pause commands to the WebSocket
  useEffect(() => {
    // We can just log this for now, as the WebSocket isn't real yet.
    // In a real app, you'd send a message:
    // ws.send(JSON.stringify({ command: isRunning ? "run" : "pause" }));
    console.log("Training state changed:", isRunning ? "RUNNING" : "PAUSED");
  }, [isRunning]);

  // This effect handles resetting the graphs
  useEffect(() => {
    if (resetTrigger > 0) {
      setData(getInitialData());
      // In a real app, you'd send a "reset" command:
      // ws.send(JSON.stringify({ command: "reset" }));
      console.log("Resetting training data");
    }
  }, [resetTrigger]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      {/* Chart 1: Cumulative Reward */}
      <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
        <h3 className="text-white text-lg font-semibold mb-4">Cumulative Reward per Episode</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            margin={{ top: 5, right: 20, left: -10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#4a5568" />
            <XAxis dataKey="episode" stroke="#a0aec0" />
            <YAxis stroke="#a0aec0" />
            <Tooltip
              contentStyle={{ backgroundColor: '#2d3748', border: 'none' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend wrapperStyle={{ color: '#e2e8f0' }} />
            <Line
              type="monotone"
              dataKey="reward"
              stroke="#4299e1" // Blue line
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 2: Episode Length */}
      <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
        <h3 className="text-white text-lg font-semibold mb-4">Episode Length</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            margin={{ top: 5, right: 20, left: -10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#4a5568" />
            <XAxis dataKey="episode" stroke="#a0aec0" />
            <YAxis stroke="#a0aec0" />
            <Tooltip
              contentStyle={{ backgroundColor: '#2d3748', border: 'none' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend wrapperStyle={{ color: '#e2e8f0' }} />
            <Line
              type="monotone"
              dataKey="length"
              stroke="#38b2ac" // Teal line
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


/**
 * Left Sidebar Panel (Inspector)
 */
function InspectorPanel() {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">RL Parameters</h3>
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 block">Learning Rate</label>
          <input 
            type="text" 
            defaultValue="0.001" 
            className="w-full p-2 bg-gray-700 rounded-md text-white text-sm border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" 
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 block">Discount Factor (Gamma)</label>
          <input 
            type="text" 
            defaultValue="0.99" 
            className="w-full p-2 bg-gray-700 rounded-md text-white text-sm border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" 
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Right Sidebar Panel (LLM) - Now calls your API
 */
function LLMPanel() {
  const [prompt, setPrompt] = useState('You are an RL agent optimizing a humanoid walker...');
  const [isUpdating, setIsUpdating] = useState(false);

  const handlePromptUpdate = async () => {
    setIsUpdating(true);
    try {
      // *** THIS NOW CALLS YOUR FASTAPI ENDPOINT ***
      const response = await fetch('http://localhost:8000/config/system_prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt }),
      });
      if (!response.ok) throw new Error("Failed to update prompt");
      const result = await response.json();
      if (result.status === true) {
        console.log("System prompt updated successfully");
      }
    } catch (err) {
      console.error("Error updating prompt:", err);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">LLM Agent</h3>
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 block">System Prompt</label>
          <textarea 
            rows={5}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full p-2 bg-gray-700 rounded-md text-white text-sm border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" 
          />
        </div>
        <button 
          onClick={handlePromptUpdate}
          disabled={isUpdating}
          className="w-full py-2 bg-blue-600 rounded-md text-white font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {isUpdating ? "Updating..." : "Update Prompt"}
        </button>
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 block">Agent Log</label>
          <div className="w-full h-48 p-2 bg-gray-900 rounded-md text-gray-400 text-xs font-mono overflow-y-auto">
            <p>Waiting for training to start...</p>
            {/* This log could also be populated by WebSocket messages */}
          </div>
        </div>
      </div>
    </div>
  );
}