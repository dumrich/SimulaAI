import mujoco
import mujoco.viewer
import numpy as np
import time

# We need a path to the XML file. We can get it from the 
# gymnasium library, since we know it's there.
try:
    from importlib import resources
    xml_path = '../mjspecs/humanoid.xml'
except ImportError:
    print("Error: Please install gymnasium to locate the XML file:")
    print("pip install gymnasium")
    exit()

# 1. Load the model and create data
model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

print(f"Loaded '{xml_path}'")
print(f"Number of actuators (controls): {model.nu}")

# 2. Launch the passive viewer
# 'launch_passive' is the easiest way to open a window
# and run a simulation.
with mujoco.viewer.launch_passive(model, data) as viewer:
    
    start_time = time.time()
    
    # 3. Run the simulation loop
    while viewer.is_running():
        step_start_time = time.time()
        
        # --- Your Custom Logic Goes Here ---
        
        # Apply random controls to the actuators
        # model.nu is the number of actuators
        ctrl = np.random.randn(model.nu)
        data.ctrl[:] = ctrl
        
        # ----------------------------------
        
        # Step the physics simulation
        mujoco.mj_step(model, data)
        
        # Sync the viewer to show the new state
        # This renders the scene
        viewer.sync()
        
        # Optional: Slow down the simulation to real-time
        # MuJoCo's default timestep (model.opt.timestep) is 0.005s
        time_until_next_step = model.opt.timestep - (time.time() - step_start_time)
        if time_until_next_step > 0:
            time.sleep(time_until_next_step)

print("Viewer closed.")
