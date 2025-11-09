from fastapi import FastAPI, HTTPException 
from pydantic import BaseModel, Field 
from typing import List, Dict, Any
from core.parser import SpecParser
import requests
import uuid
import sys
import os

#### import the core module files from core dir at some point
# Add parent directory to path to import core module
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#get; for getting information from server 
#post; for submit new information to the server 
#put; for updating a todo 
#delete for deleting a todo / info 

api = FastAPI()

xml_map = {
    "humanoid": "mujoco/mjspecs/humanoid.xml",
    "bug": "mujoco/mjspecs/bug.xml",
    "cheetah": "mujoco/mjspecs/cheetah.xml",
    "hopper": "mujoco/mjspecs/hopper.xml",
    "pusher": "mujoco/mjspecs/pusher.xml",
    "swimmer": "mujoco/mjspecs/swimmer.xml",
    "shoulder": "mujoco/mjspecs/shoulder.xml",
}

# Request model for generating simulation / prompts 
class Prompt(BaseModel):
    prompt: str = Field(..., description="User prompt describing the desired simulation")


# Response model for simulation generation
class GenerateSimulationResponse(BaseModel):
    simulation_id: str = Field(..., description="Unique identifier for the simulation")
    model_spec: SpecParser = Field(..., description="Complete MuJoCo XML string for the simulation")


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
            model_xml=SpecParser(model_xml_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating simulation: {str(e)}")
    

# request + prompt 
class RefineSimulationRequest(GenerateSimulationResponse):
    prompt : str = Field(..., description="user prompt for refinement")

    
#simualted model refine with the user prompt 
@api.post('/simulation/refine', response_model=GenerateSimulationResponse)
def refine_simulation(request: RefineSimulationRequest):
    
    simulation_id = request.simulation_id
    current_model_xml = request.model_xml
    user_prompt = request.prompt
    
    #### return refine(simulation_id, current_model_xml, user_prompt) call refine fucntion form other file;

# response call for true/false confirmation of prompt
class responseConfirmation(BaseModel):
    status : bool  

# LLM chat bot function 
@api.post('/config/system_prompt', response_model = responseConfirmation)
def handlePrompt(request: Prompt):
    
    ### add function to querry the prompt for chat 
    success = bool ### add correct fucntion call here 
    return responseConfirmation(status = success)

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
            print(data)
            return xml_map.get(data['choices'][0]['message']['content'].strip(), None)
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Request failed: {response.text}",)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving MuJoCo file: {str(e)}")