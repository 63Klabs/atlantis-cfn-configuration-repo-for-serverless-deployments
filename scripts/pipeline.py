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
import re

sys.path.append('./lib')
import tools
import atlantis

# Get the current working directory
cwd = os.getcwd()

print("")
tools.printCharStr("=", 80, bookend="|")
tools.printCharStr(" ", 80, bookend="|", text="Pipeline Stack AWS SAM TOML Generator for Atlantis CI/CD")
tools.printCharStr(" ", 80, bookend="|", text="v2024.12.30 : pipeline.py")
tools.printCharStr("-", 80, bookend="|")
tools.printCharStr(" ", 80, bookend="|", text="Chad Leigh Kluck")
tools.printCharStr(" ", 80, bookend="|", text="https://github.com/chadkluck/serverless-deploy-pipeline-atlantis")
tools.printCharStr("=", 80, bookend="|")
print("")

constraint = {
    "maxLenPrefixProjId": 28,
    "maxLenStage": 6
}

argPrefix = "acme"
argProjectId = "myproject"
argStageId = "test"
argAcceptDefaults = False
script_name = sys.argv[0].lower()

# Check to make sure there are at least three arguments. If there are not 3 arguments then display message and exit. If there are 3 arguments set Prefix, ProjectId, and Stage
if len(sys.argv) > 3:
    argPrefix = sys.argv[1].lower()
    argProjectId = sys.argv[2].lower()
    argStageId = sys.argv[3].lower()
else:
    print("\n\nUsage: python "+script_name+" <Prefix> <ProjectId> <StageId>\n\n")
    sys.exit()

script_info = {
    "name": script_name,
    "args": argPrefix,
    "infra": script_name.split(".")[0]
}

# Check to make sure Prefix + ProjectId is less than or equal to maxLenPrefixProjId
if len(argPrefix+argProjectId) > constraint["maxLenPrefixProjId"]:
    print("\n\nError: Prefix + ProjectId is greater than "+str(constraint["maxLenPrefixProjId"])+" characters.")
    print("Because some resources have a maximum length of 63 and require additional descriptors in their name, Prefix + ProjectId is restricted to "+str(constraint["maxLenPrefixProjId"])+" characters.\n\n")
    sys.exit()

# Check to make sure Prefix + ProjectId + Stage is less than or equal to maxLenStage + maxLenPrefixProjId
if len(argPrefix+argProjectId+argStageId) > constraint["maxLenStage"] + constraint["maxLenPrefixProjId"]:
    print("\n\nError: Prefix + ProjectId + Stage is greater than "+str(constraint["maxLenStage"] + constraint["maxLenPrefixProjId"])+" characters.")
    print("Because some resources have a maximum length of 63 and require additional descriptors in their name, Prefix + ProjectId + Stage is restricted to "+str(constraint["maxLenStage"] + constraint["maxLenPrefixProjId"])+" characters.\n\n")
    sys.exit()

# Default values - Set any of these defaults to your own in the defaults file
defaults = {
    # "template_location": {
    #     "BucketName": "63klabs",
    #     "BucketKey": "/atlantis/v2/",
    #     "FileName": atlantis.files["cfnPipelineTemplate"]["name"]
    # },
    "application": {
        # "AwsAccountId": "XXXXXXXXXXXX",
        # "AwsRegion": "us-east-1",
        "ServiceRoleARN": "",
        "Name": argPrefix+"-"+argProjectId
    },
    "stack_parameters": {
        "Prefix": argPrefix,
        "ProjectId": argProjectId,
        "StageId": argStageId,
        "S3BucketNameOrgPrefix": atlantis.prompts["S3BucketNameOrgPrefix"]["default"],
        "RolePath": atlantis.prompts["RolePath"]["default"],
        "DeployEnvironment": atlantis.prompts["DeployEnvironment"]["default"],
        "DeployBucket": atlantis.prompts["DeployBucket"]["default"],
        "ParameterStoreHierarchy": atlantis.prompts["ParameterStoreHierarchy"]["default"],
        "AlarmNotificationEmail": "",
        "PermissionsBoundaryArn": "",
        "CodeCommitRepository": "",
        "CodeCommitBranch": atlantis.prompts["CodeCommitBranch"]["default"]
    },
    "globals": {
        "TemplateLocationBucketName": "",
        "TemplateLocationPrefix": "/",
        "TemplateKeyFileName": "template-pipeline.yml",
        "AwsRegion": atlantis.prompts["AwsRegion"]["default"],
        "DeployBucket": atlantis.prompts["DeployBucket"]["default"],
        "ConfirmChangeset": atlantis.prompts["ConfirmChangeset"]["default"]
	}
}

# if stage begins with dev then set DeployEnvironment to DEV, test to TEST, and prod, beta, stage to PROD
if re.match("^dev", argStageId):
    defaults["stack_parameters"]["DeployEnvironment"] = "DEV"

if re.match("^test", argStageId):
    defaults["stack_parameters"]["DeployEnvironment"] = "TEST"

if re.match("^prod|^beta|^stage", argStageId):
    defaults["stack_parameters"]["DeployEnvironment"] = "PROD"

# if stage begins with prod then set CodeCommitBranch to main, otherwise set CodeCommitBranch to the stageId
if re.match("^prod", argStageId):
    defaults["stack_parameters"]["CodeCommitBranch"] = "main"
else:
    defaults["stack_parameters"]["CodeCommitBranch"] = argStageId

configEnv = argStageId

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
tools.printCharStr(" ", 80, bookend="!", text="Enter parameter values to generate the Code Pipeline configuration")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="The script will then generate a SAM TOML config file and CLI commands")
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
        "key": "application",
        "name": "Application"
    },
    {
        "key": "globals",
        "name": "Globals"
    }
]

prompts = {}
parameters = {}
for item in promptSections:
    prompts[item["key"]] = {}
    parameters[item["key"]] = {}

prompts["stack_parameters"]["Prefix"] = atlantis.prompts["Prefix"]
prompts["stack_parameters"]["Prefix"]["default"] = defaults["stack_parameters"]["Prefix"]

prompts["stack_parameters"]["ProjectId"] = atlantis.prompts["ProjectId"]
prompts["stack_parameters"]["ProjectId"]["default"] = defaults["stack_parameters"]["ProjectId"]

prompts["stack_parameters"]["StageId"] = atlantis.prompts["StageId"]
prompts["stack_parameters"]["StageId"]["default"] = defaults["stack_parameters"]["StageId"]

prompts["stack_parameters"]["S3BucketNameOrgPrefix"] = atlantis.prompts["S3BucketNameOrgPrefix"]
prompts["stack_parameters"]["S3BucketNameOrgPrefix"]["default"] = defaults["stack_parameters"]["S3BucketNameOrgPrefix"]

prompts["stack_parameters"]["RolePath"] = atlantis.prompts["RolePath"]
prompts["stack_parameters"]["RolePath"]["default"] = defaults["stack_parameters"]["RolePath"]

prompts["stack_parameters"]["DeployEnvironment"] = atlantis.prompts["DeployEnvironment"]
prompts["stack_parameters"]["DeployEnvironment"]["default"] = defaults["stack_parameters"]["DeployEnvironment"]

prompts["stack_parameters"]["DeployBucket"] = atlantis.prompts["DeployBucket"]
prompts["stack_parameters"]["DeployBucket"]["default"] = defaults["stack_parameters"]["DeployBucket"]

prompts["stack_parameters"]["ParameterStoreHierarchy"] = atlantis.prompts["ParameterStoreHierarchy"]
prompts["stack_parameters"]["ParameterStoreHierarchy"]["default"] = defaults["stack_parameters"]["ParameterStoreHierarchy"]

prompts["stack_parameters"]["AlarmNotificationEmail"] = atlantis.prompts["AlarmNotificationEmail"]
prompts["stack_parameters"]["AlarmNotificationEmail"]["default"] = defaults["stack_parameters"]["AlarmNotificationEmail"]

prompts["stack_parameters"]["PermissionsBoundaryArn"] = atlantis.prompts["PermissionsBoundaryArn"]
prompts["stack_parameters"]["PermissionsBoundaryArn"]["default"] = defaults["stack_parameters"]["PermissionsBoundaryArn"]

prompts["stack_parameters"]["CodeCommitRepository"] = atlantis.prompts["CodeCommitRepository"]
prompts["stack_parameters"]["CodeCommitRepository"]["default"] = defaults["stack_parameters"]["CodeCommitRepository"]

prompts["stack_parameters"]["CodeCommitBranch"] = atlantis.prompts["CodeCommitBranch"]
prompts["stack_parameters"]["CodeCommitBranch"]["default"] = defaults["stack_parameters"]["CodeCommitBranch"]

prompts["application"]["Name"] = atlantis.prompts["application-Name"]
prompts["application"]["Name"]["default"] = defaults["application"]["Name"]

prompts["application"]["ServiceRoleARN"] = atlantis.prompts["ServiceRoleARN"]
prompts["application"]["ServiceRoleARN"]["default"] = defaults["application"]["ServiceRoleARN"]

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
    {
        "stack_parameters": [
            "StageId", "CodeCommitBranch", "DeployEnvironment"
        ]
    },
    {
        "stack_parameters": [
            "ProjectId", "CodeCommitRepository"
        ],
        "application": [
            "Name"
        ]
    },
    {
        "stack_parameters": [
            "Prefix"
        ],
        "application": [
            "ServiceRoleARN"
        ]
    }
]

atlantis.saveSettings(parameters, removals, script_info)

# =============================================================================
# Generate
# =============================================================================

tools.printCharStr("-", 80)

deploy_globals = parameters["globals"]

deploy_globals["Capabilities"] = "CAPABILITY_IAM" # NAMED_IAM
deploy_globals["ImageRepositories"] = "[]"

config_environments = {}

# Append custom_params to parameters["stack_parameters"]
parameters["stack_parameters"].update(custom_params)

# Add things that are not user editable

# Prepend {"Key": "Atlantis", "Value": "iam"} and {"Key": "atlantis:Prefix", "Value": prefix} to tags list
custom_tags.insert(0, {"Key": "Atlantis", "Value": "pipeline"})
custom_tags.insert(1, {"Key": "atlantis:Prefix", "Value": parameters["stack_parameters"]["Prefix"]})

config_environments = atlantis.getConfigEnvironments(script_info)
print(config_environments)

sam_deploy_info = atlantis.generateTomlFile(deploy_globals, config_environments, script_info )

# =============================================================================
# CLI OUTPUT
# =============================================================================

output_dir = sam_deploy_info["output_dir"]
sam_deploy_commands = sam_deploy_info["sam_deploy_commands"][configEnv]

print("")
tools.printCharStr("=", 80, bookend="!", text="CREATE PIPELINE INFRASTRUCTURE STACK")
tools.printCharStr(" ", 80, bookend="!", text="Make sure you are logged into AWS CLI with a user role holding permissions")
tools.printCharStr(" ", 80, bookend="!", text="to create the pipeline stack!")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="Ensure the --profile flag is correct")
tools.printCharStr(" ", 80, bookend="!", text="Ensure the --deployConfig flag is correct")
tools.printCharStr("-", 80, bookend="!")
tools.printCharStr(" ", 80, bookend="!", text="To update the pipeline just re-run this script and then execute 'sam deploy'")
tools.printCharStr("=", 80, bookend="!")
print("")

# Print a message indicating the aws sam cli commands to create the stack

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
