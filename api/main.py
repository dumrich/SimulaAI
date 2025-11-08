from fastapi import FastAPI, HTTPException 
from pydantic import BaseModel, Field 
from typing import List, Dict, Any
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


# Request model for generating simulation
class GenerateSimulationRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing the desired simulation")


# Response model for simulation generation
class GenerateSimulationResponse(BaseModel):
    simulation_id: str = Field(..., description="Unique identifier for the simulation")
    model_xml: str = Field(..., description="Complete MuJoCo XML string for the simulation")


@api.post('/simulation/generate', response_model=GenerateSimulationResponse)
def generate_simulation(request: GenerateSimulationRequest):
    try:
        # Generate a unique simulation ID
        simulation_id = f"sim_{uuid.uuid4().hex[:8]}" ## may or may not need this 
        
        #### Call the core module to generate MuJoCo XML from the prompt placeholder 
        model_xml = generate_mujoco_xml(request.prompt) 
        
        return GenerateSimulationResponse(
            simulation_id=simulation_id,
            model_xml=model_xml
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
    

    
    
