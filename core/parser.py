import xml.etree.ElementTree as ET

class SpecParser:
    def __init__(self, filename):
        self.filename = f'../{filename}'
        self.et = None

    def load_file(self):
        self.et = ET.parse(self.filename)

    # Create hashmap for different parameters (height, rgb1, rgb2, width, size, friction)

    # View kinematic tree

    # Modify positions

            
            
