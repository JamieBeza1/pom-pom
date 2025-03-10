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
            exclusions = plugin.findall(".//exclusions/exclusion",namespace)
            if exclusions:
                print(f"Skipping plugin '{plugin.find('artifactId', namespace).text}' due to exclusions.")
                continue
            
            a_id = plugin.find('artifactId', namespace).text if plugin.find('artifactId', namespace) is not None else "N/A"
            v = plugin.find('version', namespace).text if plugin.find('version', namespace) is not None else "N/A"
            
            v = self.resolve_placeholder(v, properties)
            a_id = self.resolve_placeholder(a_id, properties)

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
            exclusions = dep.findall(".//exclusions/exclusion",namespace)
            should_skip = False

            if exclusions:
                for exclusion in exclusions:
                    exclusion_group_id = exclusion.find('groupId', namespace).text if exclusion.find('groupId', namespace) is not None else "N/A"
                    exclusion_artifact_id = exclusion.find('artifactId', namespace).text if exclusion.find('artifactId', namespace) is not None else "N/A"

                    if exclusion_group_id == dep.find('groupId', namespace).text and exclusion_artifact_id == dep.find('artifactId', namespace).text:
                        print(f"Skipping dependency '{dep.find('artifactId', namespace).text}' due to exclusions.")
                        should_skip = True
                        break  

            if not should_skip:
                group_id = dep.find('groupId', namespace).text if dep.find('groupId', namespace) is not None else "N/A1"
                artifact_id = dep.find('artifactId', namespace).text if dep.find('artifactId', namespace) is not None else "N/A2"
                version = dep.find('version', namespace).text if dep.find('version', namespace) is not None else "N/A3"
                #scope = dep.find('scope', namespace).text if dep.find('scope', namespace) is not None else "N/A"

                artifact_id = self.resolve_placeholder(artifact_id, properties)
                version = self.resolve_placeholder(version, properties)

                self.deps.append({
                    'groupId': group_id,
                    'artifactId': artifact_id,
                    'version': version
                })

        for dep in self.deps:
            print(f"Dependency: {dep['artifactId']}, Version: {dep['version']}")


    def extract_properties(self, data):
        #tree = ET.parse(data)
        root = ET.fromstring(data)
        namespace = {'': 'http://maven.apache.org/POM/4.0.0'}
        properties_dict = {}

        project_version = self.extract_project_version(root)
        project_artifactId = self.extract_artifactId(root)

        if project_artifactId:
            properties_dict['project.artifactId'] = project_artifactId
            print(f"Project Artifact ID: {project_artifactId}")

        if project_version:
            properties_dict['project.version'] = project_version
            print(f"Project Version: {project_version}")

        properties = root.findall('.//properties', namespace)
        
        if properties:
            for prop in properties:
                if prop.tag == '{http://maven.apache.org/POM/4.0.0}properties':
                    for child in prop:
                        
                        tag_name = child.tag.split('}')[-1]
                        property_value = child.text.strip() if child.text else None

                        property_value = self.resolve_placeholder(property_value,properties_dict)
                        properties_dict[tag_name] = property_value
                        #print(f"Property: {tag_name}, Value: {property_value}")
        return properties_dict
    
    def extract_artifactId(self,root):
        namespace =  {'': 'http://maven.apache.org/POM/4.0.0'}
        artifact_id = root.find('artifactId', namespace)
        if artifact_id is not None:
            print(f"Artifact ID: {artifact_id.text.strip()}")
            return artifact_id.text.strip()
        return None

    def extract_project_version(self, root):
        namespace  = {'': 'http://maven.apache.org/POM/4.0.0'}
        version = root.find('version', namespace)

        if version is None:
            parent = root.find('parent', namespace)
            if parent is not None:
                version = parent.find('version', namespace)
        if version is not None:
            #print(f"Project Version11: {version.text.strip()}")
            return version.text.strip()
        return None
    
    
    def resolve_placeholder(self, value, properties):
        if value and isinstance(value, str):
            if '${' in value and '}' in value:
                while  '${' in value and '}' in value:
                    start_index = value.find('${') + 2
                    end_index = value.find('}', start_index)
                    placeholder = value[start_index:end_index]
                    resolved_value = properties.get(placeholder, None)
                    if resolved_value:
                        value = value.replace(f'${{{placeholder}}}', resolved_value)
                        print(f"Resolved placeholder: {placeholder} -> {resolved_value}")
                    else:
                        print(f"Warning: Placeholder '{placeholder}' not found in properties.")
                        break
        return value


if __name__ == "__main__":
    dl = Downloader()
    
    dl.download()
    
    content = dl.read_file(dl.filename)
    properties = dl.extract_properties(content)
    print(f"Properties: {properties}")
    dl.extract_plugins(content, properties)
    dl.extract_dependencies(content, properties)

    print(f"\nPlugins: {len(dl.plugins)}\nDependencies: {len(dl.deps)}\n\nSum: {int(len(dl.deps)) + int(len(dl.plugins))}")
