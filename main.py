import requests
import os
import json
import xml.etree.ElementTree as ET

class Downloader:
    def __init__(self):
        self.pom = "https://repo1.maven.org/maven2/org/apache/flink/flink-parent/1.20.1/flink-parent-1.20.1.pom"
        self.filename = "/home/beza/Downloads/pom-pom-main/flink-parent-1.20.1.pom"
        self.deps = []
        self.plugins = []
        self.base = "https://repo1.maven.org/maven2/"
        self.download_location = "/home/beza/Downloads/pom-pom-main/pkg/"

    def download(self):
        print(self.pom)
        try:
            response = requests.get(self.pom, allow_redirects=True)
            self.write_output(self.filename, response.content)
            print("success")
        except BaseException as be:
            print(f"Something went wrong while downloading: {self.pom}\nThe following exception was raised: {be}")
            exit(1)
    
    def write_output(self, filename, output):
        with open(filename, "wb") as file:
            file.write(output)
        
    def read_file(self, filename):
        with open(filename, "r", encoding='utf-8') as file:
            return file.read()

    def extract_plugins(self, data, properties):
        root = ET.fromstring(data)
        namespace = {'': 'http://maven.apache.org/POM/4.0.0'}

        plugin_elements = root.findall(".//build/pluginManagement/plugins/plugin", namespace) + root.findall(".//build/plugins/plugin", namespace)

        for plugin in plugin_elements:
            artifact_id = plugin.find('artifactId', namespace).text if plugin.find('artifactId', namespace) is not None else "N/A"
            version = plugin.find('version', namespace).text if plugin.find('version', namespace) is not None else "N/A"

            if version == "N/A":
                parent_version = plugin.find('parent/version', namespace)
                if parent_version is not None:
                    version = parent_version.text

            artifact_id = self.resolve_placeholder(artifact_id, properties)
            version = self.resolve_placeholder(version, properties)

            exclusions = plugin.findall(".//exclusions/exclusion", namespace)
            if exclusions:
                print(f"Skipping plugin '{artifact_id}' due to exclusions.")
                continue

            plugin_info = {
                'artifactId': artifact_id,
                'version': version
            }

            if plugin_info not in self.plugins:
                self.plugins.append(plugin_info)

        for plugin in self.plugins:
            print(f"Plugin: {plugin['artifactId']}, Version: {plugin['version']}")



    def extract_dependencies(self, data, properties):
        root = ET.fromstring(data)
        namespace = {'': 'http://maven.apache.org/POM/4.0.0'}
        dependencies = root.findall(".//dependency", namespace)
        excluded_deps = []

        for dep in dependencies:
            exclusions = dep.findall(".//exclusions/exclusion", namespace)
            should_skip = False

            if exclusions:
                for exclusion in exclusions:
                    exclusion_group_id = exclusion.find('groupId', namespace).text if exclusion.find('groupId', namespace) is not None else "N/A"
                    exclusion_artifact_id = exclusion.find('artifactId', namespace).text if exclusion.find('artifactId', namespace) is not None else "N/A"
                    
                    excluded_deps.append({
                        'groupId': exclusion_group_id,
                        'artifactId': exclusion_artifact_id,
                        'message': f"Excluded: {exclusion_artifact_id} from {dep.find('artifactId', namespace).text}"
                    })
                    
                    should_skip = True
                    break

            if not should_skip:
                group_id = dep.find('groupId', namespace).text if dep.find('groupId', namespace) is not None else None
                artifact_id = dep.find('artifactId', namespace).text if dep.find('artifactId', namespace) is not None else None
                version = dep.find('version', namespace).text if dep.find('version', namespace) is not None else None

                if not group_id or not artifact_id or not version:
                    print(f"Missing information for dependency: groupId={group_id}, artifactId={artifact_id}, version={version}")
                    continue

                artifact_id = self.resolve_placeholder(artifact_id, properties)
                version = self.resolve_placeholder(version, properties)

                self.deps.append({
                    'groupId': group_id,
                    'artifactId': artifact_id,
                    'version': version
                })

        for excluded in excluded_deps:
            print(f"Excluded Dependency: {excluded['artifactId']} (Group: {excluded['groupId']}) - {excluded['message']}")

        for dep in self.deps:
            print(f"Dependency: {dep['artifactId']}, Version: {dep['version']}")

    def extract_properties(self, data):
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

                        property_value = self.resolve_placeholder(property_value, properties_dict)
                        properties_dict[tag_name] = property_value
        return properties_dict
    
    def extract_artifactId(self, root):
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
    
    def write_files(self, file, content_to_write):
        with open(file, "wb") as f:
            f.write(content_to_write)
    
    
    def download_files(self, download_location, dependencies):
        if not os.path.exists(download_location):
            os.makedirs(download_location)
            print(f"Download Location Created: {download_location}")
        
        for dep in dependencies:
            g_id = dep['groupId']
            g_id_clean = g_id.replace(".", "/")
            a_id = dep['artifactId']
            version = dep['version']
            
            repo = f"https://repo1.maven.org/maven2/{g_id_clean}/{a_id}/{version}/{a_id}-{version}"
            
            filetypes = ["pom", "jar", "aar", "module"]

            for filetype in filetypes:
                filenm = repo+"."+filetype
                response = requests.get(filenm, allow_redirects=True)
                if response.status_code == 200:
                    filename = filenm.split("https://repo1.maven.org/maven2/")[-1]
                    file_path = os.path.join(download_location, filename)
                    print(file_path)
                    
                    self.write_files(file_path, response.content)
                else:
                    print(f"Error getting file: {filenm}")       
              
    
if __name__ == "__main__":
    dl = Downloader()
    
    dl.download()
    
    content = dl.read_file(dl.filename)
    properties = dl.extract_properties(content)
    print(f"Properties: {properties}")
    dl.extract_plugins(content, properties)
    dl.extract_dependencies(content, properties)

    print(f"\nPlugins: {len(dl.plugins)}\nDependencies: {len(dl.deps)}\n\nSum: {int(len(dl.deps)) + int(len(dl.plugins))}")
    
    print("===============\nLinks\n")
    dl.download_files(dl.download_location, dl.deps)