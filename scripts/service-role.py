# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific language governing permissions 
# and limitations under the License.
# 
# README documentation goes through installation steps. 
# https://github.com/chadkluck/serverless-deploy-pipeline-atlantis/README.md
#

import os
import json
import sys

sys.path.append('./lib')
import tools
import atlantis

# Get the current working directory
cwd = os.getcwd()

print("")
tools.printCharStr("=", 80, bookend="|")
tools.printCharStr(" ", 80, bookend="|", text="Service Role Stack AWS SAM TOML Generator for Atlantis CI/CD")
tools.printCharStr(" ", 80, bookend="|", text="v2024.12.30 : service-role.py")
tools.printCharStr("-", 80, bookend="|")
tools.printCharStr(" ", 80, bookend="|", text="Chad Leigh Kluck")
tools.printCharStr(" ", 80, bookend="|", text="https://github.com/chadkluck/serverless-deploy-pipeline-atlantis")
tools.printCharStr("=", 80, bookend="|")
print("")

argPrefix = "acme"
argAcceptDefaults = False
scriptName = sys.argv[0]

# Check to make sure there is at least one argument else display message and exit.
if len(sys.argv) > 1:
    argPrefix = sys.argv[1]
else:
    print("\n\nUsage: python "+scriptName+" <Prefix>\n\n")
    sys.exit()

# Default values - Set any of these defaults to your own in the defaults file
defaults = {
	"stack_parameters": {
		"Prefix": argPrefix,
		"S3BucketNameOrgPrefix": atlantis.prompts["S3BucketNameOrgPrefix"]["default"],
		"RolePath": atlantis.prompts["RolePath"]["default"],
		"PermissionsBoundaryArn": atlantis.prompts["PermissionsBoundaryArn"]["default"]
    },
    "global": {
        "TemplateFile": "./templates/template-service-role.yml", # relative to generated toml file
        "AwsRegion": atlantis.prompts["AwsRegion"]["default"],
        "DeployBucket": atlantis.prompts["DeployBucket"]["default"],
        "ConfirmChangeset": atlantis.prompts["ConfirmChangeset"]["default"]
	}
}

# Read in defaults
    
print("[ Loading .default files... ]")

# Create a file location array - this is the hierarchy of files we will gather defaults from. The most recent file appended (lower on list) will overwrite previous values
fileLoc = []
fileLoc.append(atlantis.dirs["settings"]["Iam"]+"defaults.json")
fileLoc.append(atlantis.dirs["settings"]["Iam"]+"defaults-"+argPrefix.lower()+".json")

# iam defaults don't have keysections
# for i in range(len(fileLoc)):
# 	if os.path.isfile(fileLoc[i]):
# 		with open(fileLoc[i], "r") as f:
# 			temp = json.load(f)
# 			for key in temp.keys():
# 				defaults["stack_parameters"][key] = temp[key]
# 		print(" + Found "+fileLoc[i])
# 	else:
# 		print(" - Did not find "+fileLoc[i])

for i in range(len(fileLoc)):
    if os.path.isfile(fileLoc[i]):
        with open(fileLoc[i], "r") as f:
            temp = json.load(f)
            for sectionKey in temp.keys():
                # if keySection is a string and in defaultFromIamIndex then map (it came from IAM)
                # if type(temp[sectionKey]) is str and sectionKey in defaultsFromIamIndex:
                #     defaults[defaultsFromIamIndex[sectionKey]][sectionKey] = temp[sectionKey]
                # elif type(temp[sectionKey]) is dict:
                if type(temp[sectionKey]) is dict:
                    # otherwise loop through
                    for key in temp[sectionKey].keys():
                        defaults[sectionKey][key] = temp[sectionKey][key]
            print(" + Found "+fileLoc[i])
    else:
        print(" - Did not find "+fileLoc[i])

# Read in Custom Parameters
        
print("\n[ Loading params files... ]")

customStackParamsFileLoc = []
customStackParamsFileLoc.append(atlantis.dirs["settings"]["Iam"]+"params.json")
customStackParamsFileLoc.append(atlantis.dirs["settings"]["Iam"]+"params-"+argPrefix+".json")

# If params.json exists, read it in
customStackParams = {}

for i in range(len(customStackParamsFileLoc)):
    if os.path.isfile(customStackParamsFileLoc[i]):
        with open(customStackParamsFileLoc[i], "r") as f:
            customData = json.load(f)
            for key in customData.keys():
                customStackParams[key] = customData[key]
            print(" + Found "+customStackParamsFileLoc[i])
    else:
        print(" - Did not find "+customStackParamsFileLoc[i])

# print the defaults
# print(customStackParams)

# Read in Custom Stack Tags
        
print("\n[ Loading tags files... ]")

tagFileLoc = []
tagFileLoc.append(atlantis.dirs["settings"]["Iam"]+"tags.json")
tagFileLoc.append(atlantis.dirs["settings"]["Iam"]+"tags-"+argPrefix.lower()+".json")

# If tags.json exists, read it in
customSvcRoleTags = []

for i in range(len(tagFileLoc)):
    if os.path.isfile(tagFileLoc[i]):
        with open(tagFileLoc[i], "r") as f:
            tagData = json.load(f)
            # Both customSvcRoleTags and tagData are arrays with {Key: string, Value: string} elements
            # Loop through the elements in tagData
            #   1. Search customSvcRoleTags array for an element with Key == tagData[i].Key
            #   2. If it exists, replace it. Else, append
            for j in range(len(tagData)):
                found = False
                for k in range(len(customSvcRoleTags)):
                    if customSvcRoleTags[k]["Key"] == tagData[j]["Key"]:
                        customSvcRoleTags[k]["Value"] = tagData[j]["Value"]
                        found = True
                        break
                if not found:
                    customSvcRoleTags.append(tagData[j])
            

            print(" + Found "+tagFileLoc[i])
    else:
        print(" - Did not find "+tagFileLoc[i])

# print the customSvcRoleTags
# print(customSvcRoleTags)

# =============================================================================
# PROMPTS
# =============================================================================

print("")
tools.printCharStr("=", 80, bookend="!", text="INSTRUCTIONS")
tools.printCharStr(" ", 80, bookend="!", text="Enter parameter values to generate IAM Service Role and AWS CLI commands")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="The script will then generate a policy and CLI commands to create the role")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="Leave blank and press Enter/Return to accept default in square brackets []")
tools.printCharStr(" ", 80, bookend="!", text="Enter a dash '-' to clear default and leave optional responses blank.")
tools.printCharStr(" ", 80, bookend="!", text="Enter question mark '?' for help.")
tools.printCharStr(" ", 80, bookend="!", text="Enter carat '^' at any prompt to exit script.")
tools.printCharStr("=", 80, bookend="!")
print("")

promptSections = [
    {
        "key": "stack_parameters",
        "name": "Stack Parameters"
    },
    {
        "key": "global",
        "name": "Global Deploy Parameters"
    }
]

prompts = {}
parameters = {}
for item in promptSections:
    prompts[item["key"]] = {}
    parameters[item["key"]] = {}

prompts["stack_parameters"]["Prefix"] = atlantis.prompts["Prefix"]
prompts["stack_parameters"]["Prefix"]["default"] = defaults["stack_parameters"]["Prefix"]

prompts["stack_parameters"]["S3BucketNameOrgPrefix"] = atlantis.prompts["S3BucketNameOrgPrefix"]
prompts["stack_parameters"]["S3BucketNameOrgPrefix"]["default"] = defaults["stack_parameters"]["S3BucketNameOrgPrefix"]

prompts["stack_parameters"]["RolePath"] = atlantis.prompts["RolePath"]
prompts["stack_parameters"]["RolePath"]["default"] = defaults["stack_parameters"]["RolePath"]

prompts["stack_parameters"]["PermissionsBoundaryArn"] = atlantis.prompts["PermissionsBoundaryArn"]
prompts["stack_parameters"]["PermissionsBoundaryArn"]["default"] = defaults["stack_parameters"]["PermissionsBoundaryArn"]

prompts["global"]["AwsRegion"] = atlantis.prompts["AwsRegion"]
prompts["global"]["AwsRegion"]["default"] = defaults["global"]["AwsRegion"]

prompts["global"]["DeployBucket"] = atlantis.prompts["DeployBucket"]
prompts["global"]["DeployBucket"]["default"] = defaults["global"]["DeployBucket"]

prompts["global"]["ConfirmChangeset"] = atlantis.prompts["ConfirmChangeset"]
prompts["global"]["ConfirmChangeset"]["default"] = defaults["global"]["ConfirmChangeset"]

atlantis.getUserInput(prompts, parameters, promptSections)

# =============================================================================
# Save files
# =============================================================================

print("[ Saving .default files... ]")

tf = {
    "Prefix": parameters["stack_parameters"]["Prefix"],
}

# we list the files in reverse as we work up the normal read-in chain
iamInputsFiles = [
    atlantis.dirs["settings"]["Iam"]+"defaults-"+tf["Prefix"]+".json",
    atlantis.dirs["settings"]["Iam"]+"defaults.json"
]

# we will progressively remove data as we save up the chain of files
# to do this we will list the data to remove in reverse order
removals = [
    {
        "stack_parameters": ["Prefix"]
    }
]

data = []
data.append(json.dumps(parameters["stack_parameters"], indent=4))
limitedParam = json.dumps(parameters)

# loop through the removals array and remove the keys from the limitedParam array before appending to data
for removal in removals:
    d = json.loads(limitedParam)
    for key in removal.keys():
        for item in removal[key]:
            d[key].pop(item)
    limitedParam = json.dumps(d, indent=4)
    data.append(json.dumps(d["stack_parameters"], indent=4))

# go through each index of the cliInputFiles array and write out the corresponding data element and add the corresponding element at index in data
numFiles = len(iamInputsFiles)

for i in range(numFiles):
    file = iamInputsFiles[i]
    d = data[i]
    # create or overwrite file with d
    print(" * Saving "+file+"...")
    with open(file, "w") as f:
        f.write(d)
        f.close()

# =============================================================================
# Generate
# =============================================================================

tools.printCharStr("-", 80)

# Get the path to the generated directory
cli_output_dir = atlantis.dirs["iamServiceRole"]
suffix = "service-role"
scriptInfo = {
    "scriptName": scriptName,
    "args": argPrefix
}

# Append parameters["stack_parameters"] to customStackParams
customStackParams.update(parameters["stack_parameters"])

param_overrides_toml = ""
for key, value in customStackParams.items():
	param_overrides_toml += f"\\\"{key}\\\"=\\\"{value}\\\" "

param_overrides_toml = param_overrides_toml.rstrip()

# Prepend {"Key": "Atlantis", "Value": "iam"} and {"Key": "atlantis:Prefix", "Value": prefix} to tags list
customSvcRoleTags.insert(0, {"Key": "Atlantis", "Value": "iam"})
customSvcRoleTags.insert(1, {"Key": "atlantis:Prefix", "Value": parameters["stack_parameters"]["Prefix"]})

tags_toml = ""
for tag in customSvcRoleTags:
    key = tag["Key"]
    value = tag["Value"]
    tags_toml += f"\\\"{key}\\\"=\\\"{value}\\\" "

tags_toml = tags_toml.rstrip()

toml_defaultDeployParams["parameter_overrides"] = param_overrides_toml
toml_defaultDeployParams["tags"] = tags_toml



# Create a dictionary of replacements
replacements = {
    "$TEMPLATE_FILE$": toml_globalDeployParameters["template_file"],
    "$S3_BUCKET_FOR_DEPLOY_ARTIFACTS$": toml_globalDeployParameters["s3_bucket"],
    "$REGION$": toml_globalDeployParameters["region"],
    "$CAPABILITIES$": toml_globalDeployParameters["capabilities"],
	"$CONFIRM_CHANGESET$": toml_globalDeployParameters["confirm_changeset"],
	"$IMAGE_REPOSITORIES$": toml_globalDeployParameters["image_repositories"],
    "$SCRIPT_NAME$": toml_scriptInfo["scriptName"],
    "$SCRIPT_ARGS$": toml_scriptInfo["args"]
}

def generateTomlFile(replacements, deploy_environments, output_dir, suffix, ):

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Read in ./lib/templates/samconfig.toml.txt
    # Read the template file
    template_path = "./lib/templates/samconfig.toml.txt"
    with open(template_path, "r") as f:
        toml_template = f.read()

    toml_filename = "samconfig-"+parameters['stack_parameters']['Prefix'].upper()+"-service-role.toml"
    sam_deploy_command = f"sam deploy --profile default --config-file {toml_filename}"

    toml_globalDeployParameters = {
        "template_file": parameters["global"]["TemplateFile"],
        "s3_bucket": parameters["global"]["DeployBucket"],
        "region": parameters["global"]["AwsRegion"],
        "confirm_changeset": parameters["global"]["ConfirmChangeset"],
        "capabilities": "CAPABILITY_IAM",
        "image_repositories": "[]"
    }

    toml_defaultDeployParams = {
        "stack_name" : parameters["stack_parameters"]["Prefix"].upper()+"-service-role",
        "s3_prefix": parameters["stack_parameters"]["Prefix"].upper()+"-service-role",
        "parameter_overrides": "",
        "tags": ""
    }

    # Perform the replacements
    toml_content = toml_template
    for placeholder, value in replacements.items():
        toml_content = toml_content.replace(placeholder, str(value))

    # Add a [default.deploy.parameters] section to the content
    toml_content += "\n\n[default.deploy.parameters]\n"

    # Add a comment with the sam command to deploy
    toml_content += "# =====================================================\n"
    toml_content += "# Default Deployment Configuration\n"
    toml_content += "# Deploy command:\n"
    toml_content += f"# {sam_deploy_command} \n\n"

    # Add the toml_defaultDeployParams to the content
    for key, value in toml_defaultDeployParams.items():
        toml_content += f"{key} = \"{value}\"\n"

    # Write the processed TOML file
    output_toml_path = f"{cli_output_dir}samconfig-{parameters['stack_parameters']['Prefix'].upper()}-service-role.toml"
    with open(output_toml_path, "w") as f:
        f.write(toml_content)

print("")
tools.printCharStr("=", 80, bookend="!", text="CREATE ROLE INFRASTRUCTURE STACK")
tools.printCharStr(" ", 80, bookend="!", text="Make sure you are logged into AWS CLI with a user role holding permissions")
tools.printCharStr(" ", 80, bookend="!", text="to create the service role!")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="Ensure the --profile flag is correct")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="To update the role just re-run this script and then execute 'sam deploy'")
tools.printCharStr("=", 80, bookend="!")
print("")

# Print a message indicating the aws iam cli commands to create the role and policy and attach it to the role

deploy_command = []
deploy_command.append("# -----------------------------------------------------------------------------")
deploy_command.append(f"# 1. Navigate to the directory {cli_output_dir}")
deploy_command.append("# 2. Execute the 'sam deploy' command listed below.")
deploy_command.append("#    (It has been saved as a comment in the toml file for later reference)")
deploy_command.append("")
deploy_command.append(f"cd {cli_output_dir}")
deploy_command.append(f"{sam_deploy_command}")

deployCmd = "\n".join(deploy_command)

print(deployCmd)
