'use client'; // This directive is necessary for React hooks

import React, { useState, useEffect, useRef, Suspense } from 'react'; // Import React hooks
import * as THREE from 'three'; // <-- FIX 1: Import the THREE namespace
// Import R3F and Drei components
import { Canvas, useFrame } from '@react-three/fiber'; // Import useFrame for the render loop
import { OrbitControls, Grid } from '@react-three/drei';
import { Play, Pause, RotateCcw, Bot, PanelLeft, PanelRight, Send, BrainCircuit } from 'lucide-react';

/**
 * Main application page.
 * Uses state to show either the Chatbot entry
 * page or the full Simulation layout.
 */
export default function Home() {
  const [showSimulation, setShowSimulation] = useState(false);

  // Callback function to switch to the simulation view
  const handleChatSubmit = () => {
    // Here you would eventually send the chat to the backend.
    // For now, we just switch the view.
    setShowSimulation(true);
  };

  return (
    <main className="flex h-screen w-screen flex-col items-center justify-center bg-gray-900 text-white font-sans">
      {showSimulation ? (
        <SimulationLayout />
      ) : (
        <ChatbotEntry onChatSubmit={handleChatSubmit} />
      )}
    </main>
  );
}

// ------------------------------------------------------------------
// 1. NEW: The initial chatbot entry component
// ------------------------------------------------------------------
function ChatbotEntry({ onChatSubmit }: { onChatSubmit: () => void }) {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim()) {
      onChatSubmit(); // Call the callback to switch views
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
              placeholder="e.g., 'Create a bipedal robot and make it walk'"
              className="w-full pl-6 pr-20 py-5 bg-gray-800 border border-gray-700 text-white rounded-full text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-3 rounded-full hover:bg-blue-700 transition-colors"
            >
              <Send size={24} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// ------------------------------------------------------------------
// 2. UPDATED: The full simulation layout
// ------------------------------------------------------------------

/**
 * The main 3-panel simulation layout.
 * This component now also includes the overlay chat bar.
 */
function SimulationLayout() {
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);

  // NEW: State to control the simulation
  const [isSimRunning, setIsSimRunning] = useState(true); // Start running by default
  // NEW: State to trigger a reset. We just increment the number.
  const [resetTrigger, setResetTrigger] = useState(0);

  return (
    <div className="flex h-full w-full">
      
      {/* Left Sidebar (Inspector) */}
      {isLeftSidebarOpen && (
        <div className="w-72 h-full bg-gray-800 border-r border-gray-700 p-4">
          <InspectorPanel />
        </div>
      )}

      {/* Main Content Area (Viewport + Top Bar + Overlay Chat) */}
      <div className="flex-1 flex flex-col h-full relative">
        {/* Top Header/Toolbar */}
        <div className="flex items-center justify-between w-full h-14 bg-gray-800 border-b border-gray-700 px-4">
          {/* Left-side controls (Sidebar Toggles) */}
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setIsLeftSidebarOpen(!isLeftSidebarOpen)}
              className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700"
              title={isLeftSidebarOpen ? "Hide Inspector" : "Show Inspector"}
            >
              <PanelLeft size={18} />
            </button>
          </div>
          
          {/* Simulation Controls - NOW WIRED UP */}
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSimRunning(true)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors text-sm ${
                isSimRunning 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-white hover:bg-gray-600'
              }`}
            >
              <Play size={16} /> <span>Run</span>
            </button>
            <button 
              onClick={() => setIsSimRunning(false)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors text-sm ${
                !isSimRunning 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-white hover:bg-gray-600'
              }`}
            >
              <Pause size={16} /> <span>Pause</span>
            </button>
            <button 
              onClick={() => setResetTrigger(v => v + 1)} // Increment trigger
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors text-sm"
            >
              <RotateCcw size={16} /> <span>Reset</span>
            </button>
          </div>
          
          {/* Right-side controls (Sidebar Toggle) */}
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

        {/* Main 3D Viewport Area - NOW PASSING PROPS */}
        <div className="flex-1 w-full h-full bg-black overflow-hidden">
          <SimulationViewport 
            isRunning={isSimRunning}
            resetTrigger={resetTrigger}
          />
        </div>

        {/* NEW: Overlay Chat Bar */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
          <div className="relative flex w-full">
            <input
              type="text"
              placeholder="Refine the simulation... (e.g., 'Make the box heavier')"
              className="w-full pl-6 pr-16 py-4 bg-gray-800 bg-opacity-80 backdrop-blur-md border border-gray-700 text-white rounded-full text-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2.5 rounded-full hover:bg-blue-700 transition-colors"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
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
// 3. Re-usable components (Placeholders for now)
// ------------------------------------------------------------------

// <-- FIX 2: Correct URL for the model file -->
// This points to 'frontend/public/model.xml'
const MODEL_XML_URL = '/model.xml';

// This is the CDN link for the mujoco.js library
const MUJOCO_SCRIPT_URL = 'https://cdn.jsdelivr.net/gh/zalo/mujoco_wasm@main/mujoco.js'; // Changed to 'main' branch


/**
 * UPDATED: The 3D simulation viewport.
 * This component now *only* renders the Canvas.
 * The actual 3D scene and physics logic are in <PhysicsScene />
 */
function SimulationViewport({ isRunning, resetTrigger }: { isRunning: boolean, resetTrigger: number }) {
  return (
    <Canvas 
      camera={{ position: [5, 5, 5], fov: 60 }} // Set initial camera position
      className="w-full h-full"
    >
      {/* Suspense is a React feature that lets us show a fallback
        (like a loading spinner) while child components are loading.
        This is good practice for 3D scenes.
      */}
      <Suspense fallback={null}>
        {/* We pass the control props down to the component
          that is *inside* the Canvas. This component can
          now safely use R3F hooks like useFrame.
        */}
        <PhysicsScene 
          isRunning={isRunning}
          resetTrigger={resetTrigger}
        />
      </Suspense>
    </Canvas>
  );
}

/**
 * NEW: Physics and 3D Scene Component
 * This component lives *inside* the Canvas and can safely use
 * R3F hooks like useFrame. It contains all the logic
 * that was previously in SimulationViewport.
 */
function PhysicsScene({ isRunning, resetTrigger }: { isRunning: boolean, resetTrigger: number }) {
  // <-- FIX 1 (continued): Use the imported THREE namespace for the type -->
  const boxRef = useRef<THREE.Mesh>(null); // A React ref to get direct access to the 3D mesh
  
  // State to hold the initialized MuJoCo instances
  // We use 'any' for now as we don't have the types for the MuJoCo module
  const [mujoco, setMujoco] = useState<any>(null);
  const [physicsModel, setPhysicsModel] = useState<any>(null);
  const [physicsData, setPhysicsData] = useState<any>(null);

  // 1. Load the Mujoco library and the physics model (XML)
  useEffect(() => {
    // Function to load the external mujoco.js script
    const loadScript = (src: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        // Prevent loading the script multiple times
        if (document.querySelector(`script[src="${src}"]`)) {
          resolve();
          return;
        }
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = (err) => reject(err);
        document.body.appendChild(script);
      });
    };

    // Function to initialize the physics engine
    const initPhysics = async () => {
      try {
        // Load the mujoco.js script
        await loadScript(MUJOCO_SCRIPT_URL);
        console.log("Mujoco script loaded.");

        // The 'Mujoco' function is now available on the window object
        if (!(window as any).Mujoco) {
          throw new Error("Mujoco function not found on window. Ensure script loaded.");
        }

        // Wait for the Wasm module to be ready
        const mujocoInstance = await (window as any).Mujoco();
        setMujoco(mujocoInstance);
        console.log("Mujoco Wasm module initialized.");

        // Fetch the model XML file
        const response = await fetch(MODEL_XML_URL); // This now fetches '/model.xml'
        if (!response.ok) {
          throw new Error(`Failed to fetch model: ${response.statusText}`);
        }
        const modelXML = await response.text();
        console.log("Model XML fetched.");

        // Write the model to the virtual filesystem (VFS)
        mujocoInstance.FS.writeFile('model.xml', modelXML);

        // Load the model into the physics engine
        const model = mujocoInstance.loadModel('model.xml');
        // Initialize the simulation data structure
        const data = mujocoInstance.initData(model);
        
        setPhysicsModel(model);
        setPhysicsData(data);
        
        console.log("%cPhysics simulation is ready!", "color: #00FF00; font-weight: bold;");

      } catch (error) {
        console.error("Error initializing physics:", error);
      }
    };

    initPhysics();

    // Cleanup function
    return () => {
      const script = document.querySelector(`script[src="${MUJOCO_SCRIPT_URL}"]`);
      if (script) {
        // In a real app, you'd handle cleanup
      }
    };
  }, []); // Empty dependency array ensures this runs only once on mount

  // 2. Effect to handle simulation reset
  useEffect(() => {
    if (resetTrigger > 0 && mujoco && physicsModel && physicsData) {
      console.log("Resetting physics simulation state...");
      mujoco.resetData(physicsModel, physicsData);
    }
  }, [resetTrigger, mujoco, physicsModel, physicsData]); // Dependencies

  // 3. The Animation/Physics Loop
  useFrame(() => {
    // This hook is now safely inside the Canvas context
    if (isRunning && mujoco && physicsModel && physicsData && boxRef.current) {
      
      // --- PHYSICS ---
      mujoco.step(physicsModel, physicsData);

      // --- VISUALS ---
      // Get the position and orientation of the box from the physics simulation.
      // MuJoCo qpos for free joint: [pos.x, pos.y, pos.z, quat.w, quat.x, quat.y, quat.z]
      const [x, y, z, w, qx, qy, qz] = physicsData.qpos; // <-- TYPO FIX (was ql)

      // Update the 3D model's position in the Three.js scene
      boxRef.current.position.set(x, y, z);
      
      // Update the 3D model's rotation (orientation)
      // THREE.Quaternion.set expects (x, y, z, w)
      boxRef.current.quaternion.set(qx, qy, qz, w); // <-- CORRECTED ORDER
    }
  });

  // This component returns the 3D objects, not the canvas
  return (
    <>
      {/* Basic lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />

      {/* A simple red box. */}
      <mesh ref={boxRef} position={[0, 0, 1]}>
        {/* The geom in the XML is size "0.1 0.1 0.1", which is radius.
          boxGeometry uses full width/height/depth, so "0.2 0.2 0.2".
        */}
        <boxGeometry args={[0.2, 0.2, 0.2]} />
        <meshStandardMaterial color="red" />
      </mesh>

      {/* A grid on the XZ plane. */}
      <Grid 
        infiniteGrid 
        sectionColor={"#555555"} 
        sectionSize={10} 
        fadeDistance={50} 
        fadeStrength={5}
        position={[0, -0.01, 0]} // Position grid slightly below the physics plane
      />

      {/* OrbitControls allows you to control the camera with the mouse */}
      <OrbitControls makeDefault />
    </>
  );
}


/**
 * Left Sidebar Panel (Inspector)
 * This is a placeholder for your UI.
 */
function InspectorPanel() {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">Inspector</h3>
      <div className="space-y-4">
        <div className="text-gray-400 text-sm">
          <p className="font-medium text-white mb-1">Selected: (none)</p>
          <p>Select an object in the scene to see its properties.</p>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 block">Gravity</label>
          <input 
            type="text" 
            defaultValue="-9.81" 
            className="w-full p-2 bg-gray-700 rounded-md text-white text-sm border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" 
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Right Sidebar Panel (LLM)
 * This is a placeholder for your UI.
 */
function LLMPanel() {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">LLM Controls</h3>
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 block">System Prompt</label>
          <textarea 
            rows={5}
            defaultValue="You are a helpful assistant for MuJoCo physics simulations..."
            className="w-full p-2 bg-gray-700 rounded-md text-white text-sm border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" 
          />
        </div>
        <button className="w-full py-2 bg-blue-600 rounded-md text-white font-medium hover:bg-blue-700 transition-colors">
          Update Prompt
        </button>
      </div>
    </div>
  );
}