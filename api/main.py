from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Literal, Optional, Dict
from core.parser import SpecParser
from core.train import train # <-- IMPORT THE REAL TRAIN FUNCTION

from fastapi.middleware.cors import CORSMiddleware
import asyncio 

import requests
import uuid
import json
import os
import re
import sys 

# Add the parent directory ('SimulaAI') to the path
# This allows 'core.parser' and 'core.train' to be found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

api = FastAPI()
load_dotenv()

# This will store the path to the XML file for each simulation
# NOTE: This is in-memory and will reset when the server restarts.
simulation_db: Dict[str, str] = {}


origins = ["*"]
api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set the base directory for the XML files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUJOCO_SPECS_DIR = os.path.join(BASE_DIR, "..", "mujoco", "mjspecs")


xml_map = {
    "humanoid": os.path.join(MUJOCO_SPECS_DIR, "humanoid.xml"),
    "bug": os.path.join(MUJOCO_SPECS_DIR, "bug.xml"),
    "cheetah": os.path.join(MUJOCO_SPECS_DIR, "cheetah.xml"),
    "hopper": os.path.join(MUJOCO_SPECS_DIR, "hopper.xml"),
    "pusher": os.path.join(MUJOCO_SPECS_DIR, "pusher.xml"),
    "swimmer": os.path.join(MUJOCO_SPECS_DIR, "swimmer.xml"),
    "shoulder": os.path.join(MUJOCO_SPECS_DIR, "shoulder.xml"),
}

# --- Pydantic Models ---
class Prompt(BaseModel):
    prompt: str = Field(..., description="User prompt describing the desired simulation or edits")

class GenerateSimulationResponse(BaseModel):
    simulation_id: str = Field(..., description="Unique identifier for the simulation")
    model_xml: str = Field(..., description="Complete MuJoCo XML string for the chosen base model")
    xml_key: str = Field(..., description="The key of the base model, e.g. 'humanoid'")

class EditInstruction(BaseModel):
    action: Literal["set_attribute"]
    element_type: Literal["body", "geom", "joint", "tendon", "motor"]
    element_name: str
    attribute_name: str
    attribute_value: str

class PlanEditsResponse(BaseModel):
    edits: List[EditInstruction]

class PlanEditsRequest(BaseModel):
    xml_key: str = Field(..., description="Base model key, e.g. 'humanoid'")
    prompt: str = Field(..., description="User request describing how to modify the robot")

class ApplyEditsRequest(BaseModel):
    xml_key: str = Field(..., description="Base model key, e.g. 'humanoid'")
    edits: List[EditInstruction] = Field(..., description="List of edit instructions")

class ApplyEditsResponse(BaseModel):
    simulation_id: str = Field(..., description="Unique identifier for the edited simulation")
    model_xml: str = Field(..., description="Edited MuJoCo XML string")

class ResponseConfirmation(BaseModel):
    status: bool

# --- Helper Functions ---

def llm_plan_edits(user_request: str, xml_path: str) -> dict:
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"XML file not found at path: {xml_path}")
    with open(xml_path, "r") as f:
        xml_string = f.read()

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    system_prompt = """
        You are a MuJoCo XML editing assistant.
        You receive:
        1) The current MuJoCo XML.
        2) A natural language request about how to modify the robot.
        You MUST respond ONLY as a JSON object with this schema:
        {
            "edits": [
                {
                    "action": "set_attribute",
                    "element_type": "body" | "geom" | "joint" | "tendon" | "motor",
                    "element_name": "string (name attribute in XML)",
                    "attribute_name": "string",
                    "attribute_value": "string"
                }
            ]
        }
        Rules:
        - Only use names & attributes that actually exist in the provided XML.
        - Do NOT include any explanation, only include the changes
        - If you physically cannot honor the user's request, output \"NONE\""""
    
    user_prompt = f"Here are the relevant XML details: {xml_string} Here is the user's request: {user_request}"
    body = {
        "model": "openai/gpt-4o",
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": user_prompt }
        ]
    }

    try:
        response = requests.post(url="https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            raw_output = data['choices'][0]['message']['content'].strip()

            if (raw_output == "NONE"):
                print("Request could not be honored.")
                return {"edits": []} 

            cleaned = re.sub(r"^json\\n|```|^```json", "", raw_output).strip()
            cleaned = cleaned.replace("\\n", "\n")
            json_str_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            
            if json_str_match:
                json_str = json_str_match.group(0)
                plan = json.loads(json_str)
                print("✅ Parsed successfully!")
            else:
                print("❌ No JSON object found.")
                raise ValueError("LLM did not return a valid JSON object.")
            return plan
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Request failed: {response.text}",)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving refinement params: {str(e)}")

def generate_mujoco_xml(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "openai/gpt-4o",
        "messages": [
            {
                "role": "system", 
                "content": """The user will ask for their desired specifications of the robot, and you need to choose a base model to use from this list:
                
                **TEMPLATE LIST (INDEX)**
                **humanoid**: A bipedal, human-like robot.
                **bug**: A quadrupedal (four-legged) insect-like robot.
                **cheetah**: A flexible 2D quadruped designed for high-speed running
                **hopper**: A singular 2D robot leg that only jumps and lands
                **pusher**: A simple planar robot tasked with pushing a block.
                **swimmer**: A multi-segmented robot for fluid locomotion.
                **shoulder**: A simplified arm or manipulator model.
                
                **SELECTION RULES**
                
                1. Analyze the user's requests for keywords (e.g. \"four legs\", \"human\", \"arm movement\")
                2. Your final output MUST be ONLY the exact template name from the INDEX list. Do not use any other words or explanation.
                3. If no template is suitable, output \"NONE\""""
            },
            {
                "role": "user", 
                "content": f"Match the correct template for the following prompt: {prompt}"
            }
        ]
    }

    try:
        response = requests.post(url="https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            template_key = data['choices'][0]['message']['content'].strip()
            if template_key not in xml_map:
                return None
            return template_key
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Request failed: {response.text}",)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving MuJoCo file: {str(e)}")
    
def apply_edits_to_xml(base_xml_path: str, edits: List[EditInstruction]) -> str:
    # Your SpecParser's __init__ logic seems to handle the path logic
    # We pass it the *base* path, e.g., "../mujoco/mjspecs/humanoid.xml"
    if not os.path.exists(base_xml_path):
        raise RuntimeError(f"Base XML not found: {base_xml_path} (Resolved: {os.path.abspath(base_xml_path)})")

    parser = SpecParser(base_xml_path)
    parser.load_file()

    for edit in edits:
        if edit.action != "set_attribute":
            continue
        try:
            parser.set_attribute(
                edit.element_type,
                edit.element_name,
                edit.attribute_name,
                edit.attribute_value,
            )
        except Exception as e:
            print(f"Failed to set {edit.element_type}:{edit.element_name} {edit.attribute_name}={edit.attribute_value}: {e}")

    return parser.to_string(pretty_print=True)

# ---------- API Endpoints (Updated) ----------

@api.post("/simulation/generate", response_model=GenerateSimulationResponse)
def simulation_generate(request: Prompt):
    try:
        template_key = generate_mujoco_xml(request.prompt)
        if not template_key or template_key not in xml_map:
            raise HTTPException(status_code=400, detail="No suitable template found for the prompt.")
        
        print(f"Base template selected: {template_key}")
        xml_path = xml_map[template_key]

        print(f"Planning edits for prompt: {request.prompt}")
        plan = llm_plan_edits(request.prompt, xml_path)
        edits = [EditInstruction(**e) for e in plan.get("edits", [])]
        
        model_xml = ""
        out_path = "" 

        if edits:
            print(f"Applying {len(edits)} edits...")
            model_xml = apply_edits_to_xml(xml_path, edits)
            
            simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
            out_dir = MUJOCO_SPECS_DIR
            base_name = os.path.splitext(os.path.basename(xml_path))[0]
            out_path = os.path.join(out_dir, f"{base_name}_{simulation_id}.xml")

            os.makedirs(out_dir, exist_ok=True)
            with open(out_path, "w") as f:
                f.write(model_xml)
            print(f"✅ Edited XML saved to: {out_path}")

        else:
            print("No edits planned. Using base model.")
            if not os.path.exists(xml_path):
                raise HTTPException(status_code=500, detail=f"Base XML file not found.")
            with open(xml_path, "r") as f:
                model_xml = f.read()
            
            simulation_id = f"sim_base_{uuid.uuid4().hex[:8]}"
            out_path = xml_path 

        simulation_db[simulation_id] = out_path
        print(f"Simulation {simulation_id} mapped to {out_path}")

        return GenerateSimulationResponse(
            simulation_id=simulation_id,
            model_xml=model_xml,
            xml_key=template_key 
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating simulation: {e}")

@api.post("/simulation/plan_edits", response_model=PlanEditsResponse)
def simulation_plan_edits(request: PlanEditsRequest):
    try:
        if request.xml_key not in xml_map:
             raise HTTPException(status_code=404, detail=f"XML key '{request.xml_key}' not found.")
        
        xml_path = xml_map[request.xml_key]
        plan = llm_plan_edits(request.prompt, xml_path)
        
        edits = [EditInstruction(**e) for e in plan.get("edits", [])]
        return PlanEditsResponse(edits=edits)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error planning edits: {e}")

@api.post("/simulation/apply_edits", response_model=ApplyEditsResponse)
def simulation_apply_edits(request: ApplyEditsRequest):
    try:
        if request.xml_key not in xml_map:
             raise HTTPException(status_code=404, detail=f"XML key '{request.xml_key}' not found.")
        
        xml_path = xml_map[request.xml_key]
        edited_xml = apply_edits_to_xml(xml_path, request.edits)
        simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
        out_dir = MUJOCO_SPECS_DIR
        base_name = os.path.splitext(os.path.basename(xml_path))[0]
        out_path = os.path.join(out_dir, f"{base_name}_{simulation_id}.xml")

        os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(edited_xml)
        print(f"✅ Edited XML saved to: {out_path}")
        
        simulation_db[simulation_id] = out_path
        print(f"Simulation {simulation_id} mapped to {out_path}")

        return ApplyEditsResponse(
            simulation_id=simulation_id,
            model_xml=edited_xml,
        )
    except Exception as e:
        import traceback
        print("=== APPLY EDITS FAILED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error applying edits: {str(e)}")

@api.post("/config/system_prompt", response_model=ResponseConfirmation)
def handle_prompt_config(request: Prompt):
    print(f"System prompt updated: {request.prompt}")
    return ResponseConfirmation(status=True)


# *** UPDATED WEBSOCKET ENDPOINT ***
@api.websocket("/ws/train/{simulation_id}")
async def websocket_training_endpoint(websocket: WebSocket, simulation_id: str):
    await websocket.accept()
    print(f"WebSocket connection established for sim: {simulation_id}")
    
    # 1. Find the XML path from our in-memory DB
    xml_path = simulation_db.get(simulation_id)
    if not xml_path:
        print(f"Error: No XML path found for sim_id {simulation_id}")
        await websocket.send_json({"error": "Simulation ID not found. The server may have restarted."})
        await websocket.close(code=1011, reason="Simulation ID not found")
        return
    
    # Ensure the path is absolute for the training script
    if not os.path.isabs(xml_path):
        xml_path = os.path.join(BASE_DIR, xml_path)
        
    print(f"Found XML path: {xml_path}")
    
    # 2. Create an asyncio Queue to get data from the training thread
    data_queue = asyncio.Queue()
    is_running = asyncio.Event()
    is_running.set() # Start in a "running" state
    reset_event = asyncio.Event()
    
    # 3. Create a task that listens to the queue and sends to the WebSocket
    async def sender_task(ws: WebSocket, queue: asyncio.Queue):
        try:
            while True:
                data = await queue.get()
                await ws.send_json(data)
                queue.task_done()
                if data.get("status") == "complete" or data.get("error"):
                    break 
        except asyncio.CancelledError:
            print("Sender task cancelled.")
        except WebSocketDisconnect:
            print("Client disconnected, stopping sender task.")

    send_task = asyncio.create_task(sender_task(websocket, data_queue))

    # 4. Create a task that listens for commands from the WebSocket
    async def receiver_task(ws: WebSocket):
        try:
            while True:
                message = await ws.receive_text()
                data = json.loads(message)
                if data.get("command") == "pause":
                    is_running.clear() # Clears the flag, train() will see it
                    print("Training pause requested")
                elif data.get("command") == "run":
                    is_running.set() # Sets the flag
                    print("Training run requested")
                elif data.get("command") == "reset":
                    reset_event.set() # Set the reset flag
                    print("Training reset requested")
        except WebSocketDisconnect:
            print(f"Client for sim {simulation_id} disconnected (receiver).")
        except json.JSONDecodeError:
            print("Received malformed JSON")
        except Exception as e:
            print(f"Error in receiver task: {e}")
        finally:
            if not send_task.done():
                send_task.cancel() # Stop the sender if receiver fails

    recv_task = asyncio.create_task(receiver_task(websocket))

    # 5. Start the blocking training function in a separate thread
    try:
        await asyncio.to_thread(
            train,
            xml_path=xml_path,
            data_queue=data_queue,
            total_timesteps=1_000_000, # Shortened for demo
            # Pass the asyncio events (they are thread-safe)
            run_event=is_running,
            reset_event=reset_event 
        )
        
        await data_queue.join()

    except Exception as e:
        print(f"Error starting training thread: {e}")
        await data_queue.put({"error": str(e)})
    finally:
        if not send_task.done():
            send_task.cancel()
        if not recv_task.done():
            recv_task.cancel()
        if websocket.client_state != 3: 
             await websocket.close(code=1000)
        print(f"Training session for {simulation_id} finished.")