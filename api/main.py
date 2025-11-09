from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Literal, Optional
from core.parser import SpecParser  # make sure this import path is correct

import requests
import uuid
import json
import os
import re

#### import the core module files from core dir at some point
# Add parent directory to path to import core module
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#get; for getting information from server 
#post; for submit new information to the server 
#put; for updating a todo 
#delete for deleting a todo / info 

api = FastAPI()
load_dotenv()

xml_map = {
    "humanoid": "mujoco/mjspecs/humanoid.xml",
    "bug": "mujoco/mjspecs/bug.xml",
    "cheetah": "mujoco/mjspecs/cheetah.xml",
    "hopper": "mujoco/mjspecs/hopper.xml",
    "pusher": "mujoco/mjspecs/pusher.xml",
    "swimmer": "mujoco/mjspecs/swimmer.xml",
    "shoulder": "mujoco/mjspecs/shoulder.xml",
}

# Models:

class Prompt(BaseModel):
    prompt: str = Field(..., description="User prompt describing the desired simulation or edits")

class GenerateSimulationResponse(BaseModel):
    simulation_id: str = Field(..., description="Unique identifier for the simulation")
    model_xml: str = Field(..., description="Complete MuJoCo XML string for the chosen base model")

class EditInstruction(BaseModel):
    action: Literal["set_attribute"]
    element_type: Literal["body", "geom", "joint", "tendon", "motor"]
    element_name: str
    attribute_name: str
    attribute_value: str

class PlanEditsResponse(BaseModel):
    edits: List[EditInstruction]

class PlanEditsRequest(BaseModel):
    base_model: str = Field(..., description="Base model key, e.g. 'humanoid'")
    prompt: str = Field(..., description="User request describing how to modify the robot")

class ApplyEditsRequest(BaseModel):
    base_model: str = Field(..., description="Base model key, e.g. 'humanoid'")
    edits: List[EditInstruction] = Field(..., description="List of edit instructions")

class ApplyEditsResponse(BaseModel):
    simulation_id: str = Field(..., description="Unique identifier for the edited simulation")
    model_xml: str = Field(..., description="Edited MuJoCo XML string")

class ResponseConfirmation(BaseModel):
    status: bool

### first chat bot request at the beginning 
@api.post('/simulation/generate', response_model=GenerateSimulationResponse)
def generate_simulation(request: Prompt):
    try:
        # Generate a unique simulation ID
        simulation_id = f"sim_{uuid.uuid4().hex[:8]}" ## may or may not need this 
        
        #### Call the core module to generate MuJoCo XML from the prompt placeholder 
        model_xml_path = generate_mujoco_xml(request.prompt) 
        
        return GenerateSimulationResponse(
            simulation_id=simulation_id,
            model_xml=model_xml_path
        )
        
    
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating simulation: {str(e)}")
    

#request + prompt 
class RefineSimulationRequest(GenerateSimulationResponse):
    prompt : str = Field(..., description="user prompt for refinement")

    
#simualted model refine with the user prompt 
def llm_plan_edits(user_request: str, xml_path: str) -> dict:
    # Open and read the XML file
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

        Tips:
        - Changing the color requires changing all <geom> tags.
        - When increasing/decreasing size of the robot, you must also edit the positions of each XML tag accordingly
        - User will be vague: assume all changes are incremental unless written otherwise.

        Rules:
        - Only use names & attributes that actually exist in the provided XML.
        - Do NOT invent new top-level bodies/joints unless explicitly asked.
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

            # Check if the output is None
            if (data['choices'][0]['message']['content'].strip() == "NONE"):
                print("Request could not be honored.")
                return ""

            # Clean output
            cleaned = re.sub(r"^json\\n|```|^```json", "", raw_output).strip()
            cleaned = cleaned.replace("\\n", "\n")

            # 3. Now parse as JSON
            json_str_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group(0)
                plan = json.loads(json_str)
                print("✅ Parsed successfully!")
            else:
                print("❌ No JSON object found.")

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
                **humanoid**: A bipedal, human-like robot with arms and legs, suitable for walking, running, and manipulation. Use for any general bipedal task.
                **bug**: A quadrupedal (four-legged) insect-like robot, suitable for complex 3D motion on rough terrain.
                **cheetah**: A flexible 2D quadruped designed for high-speed running
                **hopper**: A singular 2D robot leg that only jumps and lands
                **pusher**: A simple planar robot tasked with pushing a block or object to a target location. Use for object manipulation tasks.
                **swimmer**: A multi-segmented robot designed for locomotion in a fluid environment (water), typically used in 3D.
                **shoulder**: A simplified arm or manipulator model focusing on rotational movement, often used for reaching or balancing tasks.
                
                **SELECTION RULES**
                
                1. Analyze the user's requests for keywords that may match with the descriptions above (e.g. \"four legs\", \"human\", \"arm movement\")
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
            return xml_map.get(data['choices'][0]['message']['content'].strip(), None)
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Request failed: {response.text}",)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving MuJoCo file: {str(e)}")
    
def apply_edits_to_xml(base_xml_path: str, edits: List[EditInstruction]) -> str:
    """
    Internal helper:
    Loads XML via SpecParser, applies edits, returns edited XML string.
    """
    if not os.path.exists(base_xml_path):
        raise RuntimeError(f"Base XML not found: {base_xml_path}")

    parser = SpecParser(base_xml_path)
    parser.load_file()

    for edit in edits:
        if edit.action != "set_attribute":
            # If you later add more actions, handle them here
            continue
        try:
            parser.set_attribute(
                edit.element_type,
                edit.element_name,
                edit.attribute_name,
                edit.attribute_value,
            )
        except Exception as e:
            # You can choose to raise instead, depending on how strict you want this
            print(f"Failed to set {edit.element_type}:{edit.element_name} {edit.attribute_name}={edit.attribute_value}: {e}")

    return parser.to_string(pretty_print=True)

# ---------- API Endpoints ----------

@api.post("/simulation/generate", response_model=GenerateSimulationResponse)
def simulation_generate(request: Prompt):
    """
    1) Uses LLM to pick a base template (humanoid, bug, etc.).
    2) Loads the corresponding XML.
    3) Returns simulation_id + XML string.
    """
    try:
        template = generate_mujoco_template(request.prompt)
        if not template or template not in xml_map:
            raise HTTPException(status_code=400, detail="No suitable template found for the prompt.")

        xml_path = xml_map[template]
        if not os.path.exists(xml_path):
            raise HTTPException(status_code=500, detail=f"Base XML file not found for template '{template}'.")

        with open(xml_path, "r") as f:
            xml_string = f.read()

        simulation_id = f"sim_{uuid.uuid4().hex[:8]}"

        return GenerateSimulationResponse(
            simulation_id=simulation_id,
            model_xml=xml_string,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating simulation: {e}")

@api.post("/simulation/plan_edits", response_model=PlanEditsResponse)
def simulation_plan_edits(request: PlanEditsRequest):
    """
    Calls LLM to create an edit plan for the specified base model.
    """
    base_xml_path = xml_map.get(request.base_model)
    if not base_xml_path:
        raise HTTPException(status_code=400, detail="Unknown base_model.")

    try:
        plan = llm_plan_edits(request.prompt, base_xml_path)
        # Validate into Pydantic model to ensure shape
        edits = [EditInstruction(**e) for e in plan.get("edits", [])]
        return PlanEditsResponse(edits=edits)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error planning edits: {e}")

@api.post("/simulation/apply_edits", response_model=ApplyEditsResponse)
def simulation_apply_edits(request: ApplyEditsRequest):
    """
    Applies a given list of edits to the chosen base model XML
    and returns a new simulation_id + edited XML.
    """
    base_xml_path = xml_map.get(request.base_model)
    if not base_xml_path:
        raise HTTPException(status_code=400, detail="Unknown base_model.")

    try:
        edited_xml = apply_edits_to_xml(base_xml_path, request.edits)
        simulation_id = f"sim_{uuid.uuid4().hex[:8]}"

        # Optional: persist edited XML on disk
        out_dir = os.path.dirname(base_xml_path)
        out_path = os.path.join(out_dir, f"{request.base_model}_{simulation_id}.xml")
        with open(out_path, "w") as f:
            f.write(edited_xml)

        return ApplyEditsResponse(
            simulation_id=simulation_id,
            model_xml=edited_xml,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying edits: {e}")

@api.post("/config/system_prompt", response_model=ResponseConfirmation)
def handle_prompt_config(request: Prompt):
    """
    Placeholder endpoint to accept/update a system prompt config.
    Right now: just acknowledges receipt.
    """
    # You could store request.prompt in memory/DB/config if needed.
    return ResponseConfirmation(status=True)