'use client'; // This directive is necessary for React hooks

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
  xml_key: string; 
}

/**
 * Main application page.
 */
export default function Home() {
  const [simulation, setSimulation] = useState<Simulation | null>(null);

  const handleChatSubmit = (apiResponse: Simulation) => {
    setSimulation(apiResponse);
  };

  return (
    <main className="flex h-screen w-screen flex-col items-center justify-center bg-gray-900 text-white font-sans">
      {simulation ? (
        <SimulationLayout simulation={simulation} />
      ) : (
        <ChatbotEntry onChatSubmit={handleChatSubmit} />
      )}
    </main>
  );
}

// ------------------------------------------------------------------
// 1. Chatbot entry component
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
      const response = await fetch('http://localhost:8000/simulation/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(`API Error: ${err.detail || response.statusText}`);
      }

      const simulationData: Simulation = await response.json();
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
// 2. Main simulation layout
// ------------------------------------------------------------------
function SimulationLayout({ simulation }: { simulation: Simulation }) {
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);

  const [currentSim, setCurrentSim] = useState(simulation);
  const [isSimRunning, setIsSimRunning] = useState(true);
  const [resetTrigger, setResetTrigger] = useState(0);
  const [isRefining, setIsRefining] = useState(false);

  const handleRefineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const input = form.elements.namedItem('prompt') as HTMLInputElement;
    const prompt = input.value;
    if (!prompt || isRefining) return;

    setIsRefining(true);

    try {
      console.log(`Planning edits for ${currentSim.xml_key} with prompt: ${prompt}`);
      const planResponse = await fetch('http://localhost:8000/simulation/plan_edits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          xml_key: currentSim.xml_key, 
        }),
      });

      if (!planResponse.ok) throw new Error('Failed to plan edits.');
      const plan = await planResponse.json();
      console.log("Received edit plan:", plan.edits);

      if (!plan.edits || plan.edits.length === 0) {
        console.log("No edits planned by LLM.");
        input.value = ''; 
        setIsRefining(false);
        return;
      }

      console.log(`Applying ${plan.edits.length} edits...`);
      const applyResponse = await fetch('http://localhost:8000/simulation/apply_edits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          xml_key: currentSim.xml_key, 
          edits: plan.edits,
        }),
      });

      if (!applyResponse.ok) throw new Error('Failed to apply edits.');
      
      const newSimData = await applyResponse.json();

      setCurrentSim({
        simulation_id: newSimData.simulation_id,
        model_xml: newSimData.model_xml,
        xml_key: currentSim.xml_key,
      });
      
      setResetTrigger(v => v + 1); // Trigger a reset on the graphs/WS
      input.value = '';

    } catch (err) {
      console.error("Error refining simulation:", err);
    } finally {
      setIsRefining(false);
    }
  };


  return (
    <div className="flex h-full w-full">
      
      {isLeftSidebarOpen && (
        <div className="w-72 h-full bg-gray-800 border-r border-gray-700 p-4">
          <InspectorPanel />
        </div>
      )}

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
              onClick={() => setResetTrigger(v => v + 1)}
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

        <div className="flex-1 w-full h-full overflow-y-auto p-4">
          <DashboardContainer
            simulationId={currentSim.simulation_id}
            isRunning={isSimRunning}
            resetTrigger={resetTrigger}
            // Pass a function to update the running state
            setIsRunning={setIsSimRunning} 
          />
        </div>

        <form 
          className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4"
          onSubmit={handleRefineSubmit}
        >
          <div className="relative flex w-full">
            <input
              type="text"
              name="prompt"
              placeholder="Refine the training... (e.g., 'Make the legs stronger')"
              className="w-full pl-6 pr-16 py-4 bg-gray-800 bg-opacity-80 backdrop-blur-md border border-gray-700 text-white rounded-full text-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              disabled={isRefining}
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2.5 rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50"
              disabled={isRefining}
            >
              {isRefining ? (
                <div className="w-5 h-5 border-2 border-t-transparent border-white rounded-full animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
        </form>
      </div>

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

function DashboardContainer({ simulationId, isRunning, resetTrigger, setIsRunning }: {
  simulationId: string;
  isRunning: boolean;
  resetTrigger: number;
  setIsRunning: (isRunning: boolean) => void;
}) {
  const [data, setData] = useState(getInitialData());
  const ws = useRef<WebSocket | null>(null);
  const [statusMessage, setStatusMessage] = useState("Connecting to training server...");

  useEffect(() => {
    if (!simulationId) return;
    if (ws.current) ws.current.close(); 
    
    setData(getInitialData()); 
    setStatusMessage("Connecting to training server...");

    const newWs = new WebSocket(`ws://localhost:8000/ws/train/${simulationId}`);

    newWs.onopen = () => {
      console.log("WebSocket connected");
      setStatusMessage("Training started...");
      newWs.send(JSON.stringify({ command: isRunning ? "run" : "pause" }));
    };

    newWs.onmessage = (event) => {
      try {
        const newDataPoint = JSON.parse(event.data);
        if (newDataPoint.episode !== undefined) {
          setData(currentData => [...currentData, newDataPoint]);
          setStatusMessage(`Training... Episode: ${newDataPoint.episode}`);
        }
        else if (newDataPoint.status === "complete") {
          setStatusMessage("Training Complete!");
          setIsRunning(false); // Update parent state
        }
        else if (newDataPoint.error) {
          setStatusMessage(`Error: ${newDataPoint.error}`);
          setIsRunning(false); // Update parent state
        }

      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    newWs.onerror = (err) => {
      console.error("WebSocket error:", err);
      setStatusMessage("Connection error. Is the server running?");
    };

    newWs.onclose = () => {
      console.log("WebSocket disconnected");
      if (statusMessage.startsWith("Training")) {
        setStatusMessage("Training connection lost.");
      }
    };

    ws.current = newWs;
    return () => newWs.close();
  }, [simulationId, resetTrigger]); // Reconnect if sim_id or resetTrigger changes

  useEffect(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ command: isRunning ? "run" : "pause" }));
    }
  }, [isRunning]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
        <h3 className="text-white text-lg font-semibold mb-2">Cumulative Reward per Episode</h3>
        <p className="text-gray-400 text-sm mb-4">{statusMessage}</p>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
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
              stroke="#4299e1"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
        <h3 className="text-white text-lg font-semibold mb-2">Episode Length</h3>
        <p className="text-gray-400 text-sm mb-4">Total episodes: {data.length - 1}</p>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
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
              stroke="#38b2ac"
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

function LLMPanel() {
  const [prompt, setPrompt] =useState('You are an RL agent optimizing a humanoid walker...');
  const [isUpdating, setIsUpdating] = useState(false);

  const handlePromptUpdate = async () => {
    setIsUpdating(true);
    try {
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
          </div>
        </div>
      </div>
    </div>
  );
}