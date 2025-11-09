import xml.etree.ElementTree as ET
import os
import copy

class SpecParser:
    def __init__(self, filename):
        if filename.startswith('../'):
            self.filename = filename
        else:
            self.filename = f'../mjspecs/{filename}'
        self.et = None
        self.root = None
        self.worldbody = None
        self.original_root = None  # Store original state for reset

    def load_file(self):
        """Load and parse the XML file"""
        if not os.path.exists(self.filename):
            raise FileNotFoundError(f"XML file not found: {self.filename}")

        self.et = ET.parse(self.filename)
        self.root = self.et.getroot()
        self.worldbody = self.root.find('worldbody')

        if self.worldbody is None:
            raise ValueError("No worldbody found in XML file")

        # Store original state for reset functionality
        self.original_root = copy.deepcopy(self.root)

    def _extract_element_attributes(self, element):
        """Extract all attributes from an element as a dictionary"""
        attrs = dict(element.attrib)

        # Add element text if it exists and is not just whitespace
        if element.text and element.text.strip():
            attrs['text'] = element.text.strip()

        return attrs

    def _find_elements_in_worldbody_children(self, parent, tag_name):
        """Find elements with given tag name only in direct children of worldbody"""
        elements = {}

        # Find direct children of worldbody
        for element in parent.findall(tag_name):
            name = element.get('name', f"{tag_name}_{len(elements)}")
            elements[name] = self._extract_element_attributes(element)

        # Find elements in direct body children of worldbody only (no nested bodies)
        for body in parent.findall('body'):
            for element in body.findall(tag_name):
                name = element.get('name', f"{tag_name}_{len(elements)}")
                elements[name] = self._extract_element_attributes(element)

        return elements

    def get_bodies_hashmap(self):
        """Generate hashmap for body elements that are direct children of worldbody"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        bodies = {}

        # Find only direct body children of worldbody
        for body in self.worldbody.findall('body'):
            name = body.get('name', f"body_{len(bodies)}")
            bodies[name] = self._extract_element_attributes(body)

        return bodies

    def get_geoms_hashmap(self):
        """Generate hashmap for all geom elements under worldbody"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        return self._find_elements_in_worldbody_children(self.worldbody, 'geom')

    def get_joints_hashmap(self):
        """Generate hashmap for all joint elements under worldbody"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        return self._find_elements_in_worldbody_children(self.worldbody, 'joint')

    def get_tendons_hashmap(self):
        """Generate hashmap for all tendon elements under worldbody"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        return self._find_elements_in_worldbody_children(self.worldbody, 'tendon')

    def get_motors_hashmap(self):
        """Generate hashmap for all motor elements under worldbody"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        return self._find_elements_in_worldbody_children(self.worldbody, 'motor')

    def get_all_hashmaps(self):
        """Generate hashmaps for all supported elements (bodies, geoms, joints, tendons, motors)"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        return {
            'bodies': self.get_bodies_hashmap(),
            'geoms': self.get_geoms_hashmap(),
            'joints': self.get_joints_hashmap(),
            'tendons': self.get_tendons_hashmap(),
            'motors': self.get_motors_hashmap()
        }

    def print_summary(self):
        """Print a summary of all elements found"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        hashmaps = self.get_all_hashmaps()

        print(f"XML Spec Parser Summary for: {self.filename}")
        print("=" * 50)

        for element_type, hashmap in hashmaps.items():
            print(f"{element_type.capitalize()}: {len(hashmap)} found")
            if hashmap:
                for name in list(hashmap.keys())[:3]:  # Show first 3 names
                    print(f"  - {name}")
                if len(hashmap) > 3:
                    print(f"  ... and {len(hashmap) - 3} more")
            print()

    def _find_element_by_name(self, element_type, element_name):
        """Find specific element by type and name in the XML tree"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        # Search in worldbody and all its descendants
        for element in self.worldbody.iter(element_type):
            if element.get('name') == element_name:
                return element

        return None

    def set_attribute(self, element_type, element_name, attribute_name, attribute_value):
        """Set an attribute value for a specific element"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        element = self._find_element_by_name(element_type, element_name)
        if element is None:
            raise ValueError(f"{element_type} '{element_name}' not found")

        element.set(attribute_name, str(attribute_value))

        # Update worldbody reference if we modified the root
        self.worldbody = self.root.find('worldbody')

    def get_attribute(self, element_type, element_name, attribute_name):
        """Get an attribute value from a specific element"""
        if self.worldbody is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        element = self._find_element_by_name(element_type, element_name)
        if element is None:
            raise ValueError(f"{element_type} '{element_name}' not found")

        return element.get(attribute_name)

    def set_body_attribute(self, body_name, attribute_name, attribute_value):
        """Set an attribute for a body element"""
        return self.set_attribute('body', body_name, attribute_name, attribute_value)

    def set_geom_attribute(self, geom_name, attribute_name, attribute_value):
        """Set an attribute for a geom element"""
        return self.set_attribute('geom', geom_name, attribute_name, attribute_value)

    def set_joint_attribute(self, joint_name, attribute_name, attribute_value):
        """Set an attribute for a joint element"""
        return self.set_attribute('joint', joint_name, attribute_name, attribute_value)

    def set_tendon_attribute(self, tendon_name, attribute_name, attribute_value):
        """Set an attribute for a tendon element"""
        return self.set_attribute('tendon', tendon_name, attribute_name, attribute_value)

    def set_motor_attribute(self, motor_name, attribute_name, attribute_value):
        """Set an attribute for a motor element"""
        return self.set_attribute('motor', motor_name, attribute_name, attribute_value)

    def reset_to_original(self):
        """Reset the XML tree to its original state"""
        if self.original_root is None:
            raise ValueError("No original state found. Make sure load_file() was called.")

        self.root = copy.deepcopy(self.original_root)
        self.worldbody = self.root.find('worldbody')

    def to_string(self, pretty_print=True):
        """Convert the current XML tree to a string"""
        if self.root is None:
            raise ValueError("XML file not loaded. Call load_file() first.")

        if pretty_print:
            # Format the XML with proper indentation
            self._indent_xml(self.root)

        return ET.tostring(self.root, encoding='unicode', method='xml')

    def _indent_xml(self, elem, level=0):
        """Add indentation to XML for pretty printing"""
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent


# Example usage
if __name__ == "__main__":
    parser = SpecParser("ant.xml")
    parser.load_file()

    # Get individual hashmaps
    bodies = parser.get_bodies_hashmap()
    geoms = parser.get_geoms_hashmap()
    joints = parser.get_joints_hashmap()

    # Print summary
    parser.print_summary()

    # Example: Access specific element
    if 'torso' in bodies:
        print("Original torso body attributes:", bodies['torso'])

    # Example editing functionality
    print("\n=== Editing Demo ===")

    # Modify torso position
    print("Original torso pos:", parser.get_attribute('body', 'torso', 'pos'))
    parser.set_body_attribute('torso', 'pos', '0 0 1.0')
    print("Modified torso pos:", parser.get_attribute('body', 'torso', 'pos'))

    # Modify a joint attribute
    if 'hip_1' in joints:
        print("Original hip_1 range:", parser.get_attribute('joint', 'hip_1', 'range'))
        parser.set_joint_attribute('hip_1', 'range', '-45 45')
        print("Modified hip_1 range:", parser.get_attribute('joint', 'hip_1', 'range'))

    # Get XML string
    print("\n=== XML Output (first 500 chars) ===")
    xml_string = parser.to_string()
    print(xml_string[:500] + "...")

    # Reset to original and verify
    parser.reset_to_original()
    print("\nAfter reset - torso pos:", parser.get_attribute('body', 'torso', 'pos'))