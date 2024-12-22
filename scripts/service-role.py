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
script_name = sys.argv[0].lower()

# Check to make sure there is at least one argument else display message and exit.
if len(sys.argv) > 1:
    argPrefix = sys.argv[1].lower()
else:
    print("\n\nUsage: python "+script_name+" <Prefix>\n\n")
    sys.exit()

script_info = {
    "name": script_name,
    "args": argPrefix,
    "infra": script_name.split(".")[0]
}

# Default values - Set any of these defaults to your own in the defaults file
defaults = {
	"stack_parameters": {
		"Prefix": argPrefix,
		"S3BucketNameOrgPrefix": atlantis.prompts["S3BucketNameOrgPrefix"]["default"],
		"RolePath": atlantis.prompts["RolePath"]["default"],
		"PermissionsBoundaryArn": atlantis.prompts["PermissionsBoundaryArn"]["default"]
    },
    "globals": {
        "TemplateLocationBucketName": "",
        "TemplateLocationPrefix": "",
        "TemplateKeyFileName": "template-service-role.yml",
        "AwsRegion": atlantis.prompts["AwsRegion"]["default"],
        "DeployBucket": atlantis.prompts["DeployBucket"]["default"],
        "ConfirmChangeset": atlantis.prompts["ConfirmChangeset"]["default"]
	}
}

configEnv = "default" # would be arg 3

# =============================================================================
# Load Settings
# =============================================================================

settings = atlantis.loadSettings(script_info, defaults)

defaults = settings["defaults"]
custom_params = settings["custom_params"]
custom_tags = settings["custom_tags"]

# =============================================================================
# PROMPTS
# =============================================================================

print("")
tools.printCharStr("=", 80, bookend="!", text="INSTRUCTIONS")
tools.printCharStr(" ", 80, bookend="!", text="Enter parameter values to generate IAM Service Role configuration")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="The script will then generate a SAM TOML config file and CLI commands.")
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
        "key": "globals",
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

prompts["globals"]["TemplateLocationBucketName"] = atlantis.prompts["TemplateLocationBucketName"]
prompts["globals"]["TemplateLocationBucketName"]["default"] = defaults["globals"]["TemplateLocationBucketName"]

prompts["globals"]["TemplateLocationPrefix"] = atlantis.prompts["TemplateLocationPrefix"]
prompts["globals"]["TemplateLocationPrefix"]["default"] = defaults["globals"]["TemplateLocationPrefix"]

prompts["globals"]["TemplateKeyFileName"] = atlantis.prompts["TemplateKeyFileName"]
prompts["globals"]["TemplateKeyFileName"]["default"] = defaults["globals"]["TemplateKeyFileName"]

prompts["globals"]["AwsRegion"] = atlantis.prompts["AwsRegion"]
prompts["globals"]["AwsRegion"]["default"] = defaults["globals"]["AwsRegion"]

prompts["globals"]["DeployBucket"] = atlantis.prompts["DeployBucket"]
prompts["globals"]["DeployBucket"]["default"] = defaults["globals"]["DeployBucket"]

prompts["globals"]["ConfirmChangeset"] = atlantis.prompts["ConfirmChangeset"]
prompts["globals"]["ConfirmChangeset"]["default"] = defaults["globals"]["ConfirmChangeset"]

atlantis.getUserInput(prompts, parameters, promptSections)

# The user may have entered different values than the original arguments
script_info["args"] = parameters["stack_parameters"]["Prefix"]
# check if there is a ProjectId property in the parameters. Do same for StageId
if "ProjectId" in parameters["stack_parameters"]:
    script_info["args"] += f" {parameters["stack_parameters"]["ProjectId"]}"
if "StageId" in parameters["stack_parameters"]:
    script_info["args"] += f" {parameters["stack_parameters"]["StageId"]}"

# =============================================================================
# Save files
# =============================================================================

# we will progressively remove data as we save up the chain of files
# to do this we will list the data to remove in reverse order
removals = [
    { # defaults.json
        "stack_parameters": ["Prefix"]
    }
]

atlantis.saveSettings(parameters, removals, script_info)

# =============================================================================
# Generate
# =============================================================================

tools.printCharStr("-", 80)

deploy_globals = parameters["globals"]

deploy_globals["Capabilities"] = "CAPABILITY_IAM"
deploy_globals["ImageRepositories"] = "[]"

config_environments = {}

# Append custom_params to parameters["stack_parameters"]
parameters["stack_parameters"].update(custom_params)

# Add things that are not user editable

# Prepend {"Key": "Atlantis", "Value": "iam"} and {"Key": "atlantis:Prefix", "Value": prefix} to tags list
custom_tags.insert(0, {"Key": "Atlantis", "Value": "service-role"})
custom_tags.insert(1, {"Key": "atlantis:Prefix", "Value": parameters["stack_parameters"]["Prefix"]})


# If this were  Read in all deployment environment files, order dictionary by default, test*/t*, beta*/b*, stage*/s*, prod*/p*,
# Instead, since we just have the default environment we'll set it manually
config_environments[configEnv] = {
    "stack_parameters": parameters["stack_parameters"],
    "tags": custom_tags
}

sam_deploy_info = atlantis.generateTomlFile(deploy_globals, config_environments, script_info )

# =============================================================================
# CLI OUTPUT
# =============================================================================

output_dir = sam_deploy_info["output_dir"]
sam_deploy_commands = sam_deploy_info["sam_deploy_commands"][configEnv]

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
deploy_command.append(f"# 1. Navigate to the directory {output_dir}")
deploy_command.append("# 2. Execute the 'sam deploy' command listed below.")
deploy_command.append("#    (It has been saved as a comment in the toml file for later reference)")
deploy_command.append("")
deploy_command.append(f"cd {output_dir}")
deploy_command.append(f"{sam_deploy_commands}")

deployCmd = "\n".join(deploy_command)

print(deployCmd)
