import requests
import json
import xml.etree.ElementTree as ET


class Downloader:
    def __init__(self):
        self.pom = "https://repo1.maven.org/maven2/org/apache/flink/flink-parent/1.20.1/flink-parent-1.20.1.pom"
        self.filename = "/home/jamie/Documents/maven scripts/flink-parent-1.20.1.pom"
        self.deps = []
        self.plugins = []

    def download(self):
        print(self.pom)
        try:
            response = requests.get(self.pom, allow_redirects=True)
            self.write_output(self.filename, response.content)
            #open("pom","wb").write(response.content)
            print("success")
        except BaseException as be:
            print(f"Something went wrong while downloading: {self.pom}\nThe following exception was raised: {be}")
            exit(1)
    
    def write_output(self,filename, output):
        with open(filename, "wb") as file:
            file.write(output)
        
    def read_file(self, filename):
        with open(filename, "r", encoding='utf-8') as file:
            return file.read()

    def extract_plugins(self, data, properties):
        root = ET.fromstring(data)
        namespace = {'': 'http://maven.apache.org/POM/4.0.0'}
        plugins = root.findall(".//plugin",namespace)

        for plugin in plugins:
            a_id = plugin.find('artifactId', namespace).text if plugin.find('artifactId', namespace) is not None else "N/A"
            v = plugin.find('version', namespace).text if plugin.find('version', namespace) is not None else "N/A"
            
            v = self.resolve_placeholder(v, properties)
            
            
            self.plugins.append({
                'artifactId':a_id,
                'version':v
            })
        
        for plugin in self.plugins:
            print(f"Plugin: {plugin['artifactId']}, Version: {plugin['version']}")
        
    def extract_dependencies(self, data, properties):
        root = ET.fromstring(data)
        namespace = {'': 'http://maven.apache.org/POM/4.0.0'}
        dependencies = root.findall(".//dependency", namespace)

        for dep in dependencies:
            group_id = dep.find('groupId', namespace).text if dep.find('groupId', namespace) is not None else "N/A"
            artifact_id = dep.find('artifactId', namespace).text if dep.find('artifactId', namespace) is not None else "N/A"
            version = dep.find('version', namespace).text if dep.find('version', namespace) is not None else "N/A"
            scope = dep.find('scope', namespace).text if dep.find('scope', namespace) is not None else "N/A"


            version = self.resolve_placeholder(version, properties)

            self.deps.append({
                'groupId': group_id,
                'artifactId': artifact_id,
                'version': version,
                'scope': scope
            })
                
        for dep in self.deps:
            print(f"Dependency: {dep['groupId']}:{dep['artifactId']}, Version: {dep['version']}, Scope: {dep['scope']}")


    def extract_properties(self, data):
        properties = {}
        root = ET.fromstring(data)
        namespace = {'': 'http://maven.apache.org/POM/4.0.0'}
        properties_section = root.find(".//properties", namespace)

        if properties_section is not None:
            for prop in properties_section:
                prop_name = prop.tag
                prop_value = prop.text
                properties[prop_name] = prop_value
        print(f"Properties: {properties}")
        return properties
    
    def resolve_placeholder(self,value, properties):
        if value.startswith("${") and value.endswith("}"):
            property_name = value[2:-1]
            #print(value)
            #print(property_name)
            print(f"Value: {value}, Property Name: {property_name}, resolved to: {properties.get(property_name)}")
            #return properties.get(property_name, "UNKNOWN")
        #return value
       

if __name__ == "__main__":
    dl = Downloader()
    dl.download()
    
    content = dl.read_file(dl.filename)
    properties = dl.extract_properties(content)

    dl.extract_plugins(content, properties)
    dl.extract_dependencies(content, properties)

    print(f"\nPlugins: {len(dl.plugins)}\nDependencies: {len(dl.deps)}\n\nSum: {int(len(dl.deps)) + int(len(dl.plugins))}")
