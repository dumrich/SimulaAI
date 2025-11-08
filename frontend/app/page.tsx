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

// This points to 'frontend/public/model.xml'
const MODEL_XML_URL = '/model.xml';

// MuJoCo will be loaded directly from public directory to avoid webpack bundling issues
const MUJOCO_WASM_URL = '/mujoco_wasm.js';


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
    // Ensure we're on the client side
    if (typeof window === 'undefined') {
      return;
    }

    // Function to initialize the physics engine
    const initPhysics = async () => {
      try {
        console.log("Starting MuJoCo initialization...");
        
        // Load mujoco_wasm.js directly from public directory using dynamic import
        // This avoids webpack bundling issues
        console.log(`Loading mujoco_wasm.js from: ${MUJOCO_WASM_URL}`);
        let loadMujoco: any;
        try {
          // Use dynamic import to load the ES6 module from public directory
          // Use Function constructor to prevent webpack from trying to bundle it
          const importModule = new Function('url', 'return import(url)');
          const mujocoModule = await importModule(MUJOCO_WASM_URL);
          // The module exports loadMujoco as default
          loadMujoco = mujocoModule.default;
          if (!loadMujoco || typeof loadMujoco !== 'function') {
            throw new Error("loadMujoco not found or is not a function in mujoco_wasm.js module");
          }
          console.log("✓ mujoco_wasm.js loaded successfully.");
        } catch (loadError: any) {
          const errorMsg = loadError instanceof Error ? loadError.message : String(loadError);
          throw new Error(`Failed to load mujoco_wasm.js: ${errorMsg}. Check that the file exists in the public directory.`);
        }

        // Wait for the Wasm module to be ready
        console.log("Initializing MuJoCo Wasm module...");
        const mujocoInstance = await loadMujoco();
        if (!mujocoInstance) {
          throw new Error("Failed to initialize MuJoCo Wasm module");
        }
        if (!mujocoInstance.FS) {
          throw new Error("MuJoCo instance missing FS (filesystem) module");
        }
        if (!mujocoInstance.MjModel) {
          throw new Error("MuJoCo instance missing MjModel class");
        }
        if (!mujocoInstance.MjData) {
          throw new Error("MuJoCo instance missing MjData class");
        }
        setMujoco(mujocoInstance);
        console.log("✓ MuJoCo Wasm module initialized.");

        // Fetch the model XML file
        console.log(`Fetching model from: ${MODEL_XML_URL}`);
        const response = await fetch(MODEL_XML_URL);
        if (!response.ok) {
          throw new Error(`Failed to fetch model: ${response.status} ${response.statusText}. Check that model.xml exists in the public directory.`);
        }
        const modelXML = await response.text();
        if (!modelXML || modelXML.trim().length === 0) {
          throw new Error("Model XML file is empty");
        }
        console.log("✓ Model XML fetched successfully.");

        // Set up the virtual filesystem (VFS) working directory
        // Create a working directory and mount MEMFS
        const workingDir = '/working';
        try {
          mujocoInstance.FS.mkdir(workingDir);
          console.log(`✓ Created working directory: ${workingDir}`);
        } catch (mkdirError: any) {
          // Directory might already exist, which is fine
          if (mkdirError && mkdirError.errno !== 17) { // 17 is EEXIST (directory exists)
            console.warn(`Warning creating working directory: ${mkdirError}`);
          }
        }

        // Mount MEMFS to the working directory
        try {
          mujocoInstance.FS.mount(mujocoInstance.MEMFS, { root: '.' }, workingDir);
          console.log("✓ Mounted MEMFS to working directory.");
        } catch (mountError: any) {
          // Mount might already exist, which is fine
          console.warn(`Warning mounting MEMFS: ${mountError}`);
        }

        // Write the model to the virtual filesystem (VFS)
        // Use absolute path in the working directory
        const vfsPath = `${workingDir}/model.xml`;
        console.log(`Writing model to virtual filesystem at: ${vfsPath}`);
        mujocoInstance.FS.writeFile(vfsPath, modelXML);
        console.log("✓ Model written to virtual filesystem.");

        // Verify the file was written
        try {
          const writtenContent = mujocoInstance.FS.readFile(vfsPath, { encoding: 'utf8' });
          if (!writtenContent || writtenContent.length === 0) {
            throw new Error("File written to VFS but appears empty");
          }
          console.log("✓ Verified model file in virtual filesystem.");
        } catch (verifyError) {
          throw new Error(`Failed to verify model file in VFS: ${verifyError}`);
        }

        // Load the model into the physics engine using MjModel.loadFromXML
        console.log("Loading model into physics engine...");
        const model = mujocoInstance.MjModel.loadFromXML(vfsPath);
        if (!model) {
          throw new Error("MjModel.loadFromXML returned null or undefined");
        }
        console.log("✓ Model loaded into physics engine.");
        
        // Initialize the simulation data structure using MjData constructor
        const data = new mujocoInstance.MjData(model);
        if (!data) {
          throw new Error("MjData constructor returned null or undefined");
        }
        console.log("✓ Simulation data initialized.");
        
        setPhysicsModel(model);
        setPhysicsData(data);
        
        console.log("%c✓ Physics simulation is ready!", "color: #00FF00; font-weight: bold;");

      } catch (error) {
        // Improved error logging - properly serialize error
        let errorMessage = 'Unknown error';
        let errorStack = undefined;
        let errorName = undefined;
        
        if (error instanceof Error) {
          errorMessage = error.message || 'Error without message';
          errorStack = error.stack;
          errorName = error.name;
        } else if (typeof error === 'string') {
          errorMessage = error;
        } else if (error && typeof error === 'object') {
          // Try to extract message from error object
          errorMessage = (error as any).message || (error as any).toString() || JSON.stringify(error);
        } else {
          errorMessage = String(error);
        }
        
        console.error("❌ Error initializing physics:");
        console.error("  Error Name:", errorName || 'N/A');
        console.error("  Error Message:", errorMessage);
        if (errorStack) {
          console.error("  Error Stack:", errorStack);
        }
        console.error("  Full Error Object:", error);
        
        // Also log to help with debugging
        console.error("Debug info:", {
          modelXmlUrl: MODEL_XML_URL,
          windowMujoco: !!(window as any).Mujoco,
          mujocoJsInstalled: true // We're using npm package now
        });
      }
    };

    initPhysics();

    // Cleanup function
    return () => {
      // Cleanup handled automatically
    };
  }, []); // Empty dependency array ensures this runs only once on mount

  // 2. Effect to handle simulation reset
  useEffect(() => {
    if (resetTrigger > 0 && mujoco && physicsModel && physicsData) {
      console.log("Resetting physics simulation state...");
      // MjData has a reset method
      if (physicsData.reset) {
        physicsData.reset();
      } else {
        // Fallback: create new data
        const newData = new mujoco.MjData(physicsModel);
        setPhysicsData(newData);
      }
    }
  }, [resetTrigger, mujoco, physicsModel, physicsData]); // Dependencies

  // 3. The Animation/Physics Loop
  useFrame(() => {
    // This hook is now safely inside the Canvas context
    if (isRunning && mujoco && physicsModel && physicsData && boxRef.current) {
      
      // --- PHYSICS ---
      // Use mj_step from the mujoco instance
      mujoco.mj_step(physicsModel, physicsData);

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