# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific language governing permissions 
# and limitations under the License.
#
# CLI Generator Variable and Function Library for Atlantis CI/CD CodePipeline CloudFormation Template
# Chad Leigh Kluck
# v2024.12.30 : lib/atlantis.py

import os
import json
import shutil
import re
import sys


import tools
import yaml
import glob

hello = "Hello, World"

# =============================================================================
# Make sure that the directory structure is correct and that the files are present
# Copy over sample files

dirs = {
    "settings": "",
    "toml": {}
}

dirs["settings"] = "./settings/"

files = {
    "pipelineTemplate": {},
    "pipelineTemplateInput": {},
    "docsPipelineParamReadme": {}
}

dirs["docs"] = "../docs/"

files["pipelineTemplate"]["name"] = "template-pipeline.yml"
files["pipelineTemplate"]["path"] = "../pipeline-infrastructure/templates/"+files["pipelineTemplate"]["name"]

files["docsPipelineParamReadme"]["name"] = "Pipeline-Parameters-Reference.md"
files["docsPipelineParamReadme"]["path"] = dirs["docs"]+files["docsPipelineParamReadme"]["name"]

dirsAndFiles = [
    {
        "dir": f"{dirs["settings"]}network/",
        "files": [
            "sample.tags.json",
            "sample.params.json"
        ],
    },
    {
        "dir": f"{dirs["settings"]}storage/",
        "files": [
            "sample.tags.json",
            "sample.params.json"
        ],
    },
    {
        "dir": f"{dirs["settings"]}pipeline/",
        "files": [
            "sample.tags.json",
            "sample.params.json"
        ],
    },
    {
        "dir": f"{dirs["settings"]}service-role/",
        "files": [
            "sample.tags.json"
        ]
    },
    {
        "dir": dirs["docs"],
        "files": [
            files["docsPipelineParamReadme"]["name"]
        ]
    }
]

# loop through dirsAndFiles and check if each dir exists. If it doesn't, create it. 
# Then loop through the files and make sure they exist. If they don't, copy them
for dirAndFile in dirsAndFiles:
    if not os.path.isdir(dirAndFile["dir"]):
        os.makedirs(dirAndFile["dir"])

    for file in dirAndFile["files"]:
        if not os.path.isfile(dirAndFile["dir"]+file):
            shutil.copyfile("./lib/templates/"+file, dirAndFile["dir"]+file)
        else: # do it anyway to make sure the file is up to date - comment out if you don't want this
            shutil.copyfile("./lib/templates/"+file, dirAndFile["dir"]+file)

# =============================================================================
# Define prompts and their defaults
            
prompts = {
    "Prefix": {
        "name": "Prefix",
        "required": True,
        "examples": "acme, finc, ws",
    },

    "ProjectId": {
        "name": "Project Id",
        "required": True,
        "examples": "hello-world, finance-api, finance-audit, sales-api",
    },

    "StageId": {
        "name": "Stage Id",
        "required": True,
        "examples": "test, stage, beta, t-joe, prod, t95"
    },

    "S3BucketNameOrgPrefix": {
        "name": "S3 Bucket Name Org Prefix",
        "required": False,
        "examples": "xyzcompany, acme, b2b-solutions-inc",
        "default": ""
    },

    "RolePath": {
        "name": "Role Path",
        "required": True,
        "examples": "/, /acme-admin/, /acme-admin/dev/, /service-roles/, /application_roles/dev-ops/",
        "default": "/"
    },

    "DeployEnvironment": {
        "name": "Deploy Environment",
        "required": True,
        "regex": "^(DEV|TEST|PROD)$",
        "examples": "DEV, TEST, PROD",
        "default": "TEST"
    },

    "DeployBucket": {
        "name": "Deploy Bucket",
        "required": False,
        "examples": "cf-templates-hw8lsa-us-east-1",
        "default": ""
    },

    "ParameterStoreHierarchy": {
        "name": "Parameter Store Hierarchy",
        "required": True,
        "examples": "/, /Finance/, /Finance/ops/, /Finance/ops/dev/",
    },

    "AlarmNotificationEmail": {
        "name": "Alarm Notification Email",
        "required": True,
        "examples": "user@example.com, finance@example.com, xyzcompany@example.com",
        "default": ""
    },

    "PermissionsBoundaryArn": {
        "name": "Permissions Boundary ARN",
        "required": False,
        "examples": "arn:aws:iam::123456789012:policy/xyz-org-boundary-policy",
        "default": ""
    },

    "CodeCommitRepository": {
        "name": "CodeCommit Repository",
        "required": True,
        "examples": "acme-financial-application, acme-financial-api, acme",
        "default": ""
    },

    "CodeCommitBranch": {
        "name": "CodeCommit Branch",
        "required": True,
        "examples": "main, dev, beta, feature/acme-ui",
        "default": ""
    },

    # Application specific - pipeline.py

    "application-Name": {
        "name": "Application Name",
        "required": True,
        "regex": "^[a-zA-Z0-9][a-zA-Z0-9_\\-\\/\\s]{0,62}[a-zA-Z0-9]$",
        "help": "2 to 64 characters. Alphanumeric, dashes, underscores, and spaces. Must start and end with a letter or number.",
        "description": "A descriptive name to identify the main application irregardless of the stage or branch. This is only used in the Tag Name and not visible anywhere else.",
        "examples": "Financial Transaction Processing, Financial Transaction Audit, acme-finance-app",
        "default": ""
    },

    "ServiceRoleArn": {
        "name": "Service Role ARN",
        "required": True,
        "regex": "^$|^arn:aws:iam::[0-9]{12}:role\\/[a-zA-Z0-9\\/_-]+$",
        "help": "Service Role ARN must be in the format: arn:aws:iam::{account_id}:role/{policy_name}",
        "description": "The Service Role gives CloudFormation permission to create, delete, and manage stacks on your behalf.",
        "examples": "arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role",
        "default": ""
    },

    # Template specific - pipeline.py

    "TemplateLocationBucketName": {
        "name": "Template Location: S3 Bucket",
        "required": False,
        "regex": "^[a-z0-9][a-z0-9-]*[a-z0-9]$|^$",
        "help": "S3 bucket name must be lowercase, start with a letter, and contain only letters, numbers, and dashes. Leave blank if using a local template.",
        "description": "Where is the pipeline template stored?",
        "examples": "63klabs, mybucket",
        "default": "63klabs"
    },

    "TemplateLocationPrefix": {
        "name": "Template Location: S3 Prefix",
        "required": False,
        "regex": "^\\/[a-zA-Z0-9\\/_-]+\\/$|^\\/$",
        "help": "S3 bucket prefix must be lowercase, start and end with a slash and contain only letters, numbers, dashes and underscores. Leave blank if using a local template.",
        "description": "Where is the pipeline template stored?",
        "examples": "/atlantis/v2/, /atlantis/v3/",
        "default": "/" #/atlantis/v2/
    },

    "TemplateKeyFileName": {
        "name": "Template: Key of S3 Object or Local File Name",
        "required": True,
        "regex": "^[a-zA-Z0-9][a-zA-Z0-9-_]*[a-zA-Z0-9]\\.(yml|yaml|json)$",
        "help": "File name must be lowercase, start with a letter, and contain only letters, numbers, and dashes. If using a local template do not include path. Make sure local templates are stored in the /templates directory of the appropriate infrastructure.",
        "description": "What is the template file name?",
        "examples": "template-pipeline.yml, template-pipeline.yaml, template-storage.yml",
        "default": ""
    },

    "AwsAccountId": {
        "name": "AWS Account ID",
        "required": True,
        "regex": "^[0-9]{12}$",
        "help": "AWS Account ID must be 12 digits",
        "description": "AWS Account ID is a 12 digit number that identifies the AWS account.",
        "examples": "123456789012, 123456789013, 123456789014",
        "default": ""
    },
    
    "AwsRegion": {
        "name": "AWS Region",
        "required": True,
        "regex": "^[a-z]{2}-[a-z]+-[0-9]$",
        "help": "AWS Region must be lowercase and in the format: us-east-1",
        "description": "AWS Region is a string that identifies the AWS region. For example, the region 'us-east-1' is located in the United States.",
        "examples": "us-east-1, us-west-1, us-west-2, eu-west-1, ap-southeast-1",
        "default": "us-east-1"
    },

    "ConfirmChangeset": {
        "name": "Confirm Changeset",
        "required": True,
        "regex": "^(true|false)$",
        "help": "When deploying a changeset, does the user have the chance to review and confirm the changes?",
        "description": "When a user runs the sam deploy command, a changeset is generated with all changes listed. If set to true, the user is given the option to confirm executing the changeset.",
        "examples": "true, false",
        "default": "true"
    }
}

# =============================================================================
# Read in the CloudFormation template

# Read in CloudFormation template which is a YAML file
# parse the YAML file and update the prompts dictionary with the values from Parameters
with open(files["pipelineTemplate"]["path"], "r") as f:
    dataTemplate = yaml.load(f, Loader=yaml.BaseLoader)
    f.close()

    for key in dataTemplate["Parameters"]:
        param = dataTemplate["Parameters"][key]

        if "AllowedPattern" in param:
            prompts[key]["regex"] = param["AllowedPattern"].replace("\\\\", "\\")
        elif "AllowedValues" in param:
            prompts[key]["examples"] = ", ".join(i for i in param["AllowedValues"])

        if "Default" in param:
            prompts[key]["default"] = param["Default"]
        
        if "Description" in param:
            prompts[key]["description"] = param["Description"]

        if "ConstraintDescription" in param:
            prompts[key]["help"] = param["ConstraintDescription"]

        if "MinLength" in param:
            prompts[key]["MinLength"] = int(param["MinLength"])

        if "MaxLength" in param:
            prompts[key]["MaxLength"] = int(param["MaxLength"])

        if "MinValue" in param:
            prompts[key]["MinValue"] = int(param["MinValue"])

        if "MaxValue" in param:
            prompts[key]["MaxValue"] = int(param["MaxValue"])


# =============================================================================
# Update the Pipeline Parameter README with the pipeline parameters


# | Parameter | Required | Brief Description | Requirement | Examples | 
# | --------- | -------- | ----------------- | ----------- | -------- |

# Read in files["docsPipelineParamReadme"]["path"]
# loop through prompts and place each prompt in a row in the markdown table
# and write it to files["docsPipelineParamReadme"]["path"]
with open(files["docsPipelineParamReadme"]["path"], "a") as f:
    for key in prompts:
        f.write("| "+prompts[key]["name"]+" | "+str(prompts[key]["required"])+" | "+prompts[key]["description"]+" | "+prompts[key]["help"]+" | "+prompts[key]["examples"]+" |\n")
    f.close()


# =============================================================================
# Define Functions


def getUserInput(prompts, parameters, promptSections):
    #iterate through prompt sections
    for section in promptSections:
        sectionKey = section["key"]
        print("\n--- "+section["name"]+": ---\n")
        # loop through each parameter and prompt the user for it, then validate input based on requirement and regex
        for key in prompts[sectionKey]:
            prompt = prompts[sectionKey][key]
            req = " "
            if prompt["required"]:
                req = " (required)"
            
            # Loop until the user enters a valid value for the parameter
            while True:
                # Prompt the user for the parameter value
                pInput = input(prompt['name']+req+" ["+prompt["default"]+"] : ")

                # Allow user to enter ^ to exit script
                if pInput == "^":
                    sys.exit(0)

                # Allow user to enter ! for help and then go back to start of loop
                if pInput == "?":
                    tools.displayHelp(prompt, False)
                    continue

                # If the user left blank, use the default value, otherwise, If the user entered a dash, clear the parameter value
                if pInput == "":
                    pInput = prompt["default"]
                elif pInput == "-":
                    pInput = ""

                # Validate the input based on regex and re-prompt if invalid
                if prompt["regex"] != "":
                    if not re.match(prompt["regex"], pInput):
                        tools.displayHelp(prompt, True)
                        continue

                # if MinLength is set, check that the input is at least that long
                if "MinLength" in prompt:
                    if len(pInput) < prompt["MinLength"]:
                        tools.displayHelp(prompt, True)
                        continue

                # if MaxLength is set, check that the input is at most that long
                if "MaxLength" in prompt:
                    if len(pInput) > prompt["MaxLength"]:
                        tools.displayHelp(prompt, True)
                        continue

                # if MinValue is set, check that the input is at least that value
                if "MinValue" in prompt:
                    if int(pInput) < prompt["MinValue"]:
                        tools.displayHelp(prompt, True)
                        continue

                # if MaxValue is set, check that the input is at most that value
                if "MaxValue" in prompt:
                    if int(pInput) > prompt["MaxValue"]:
                        tools.displayHelp(prompt, True)
                        continue

                break

            parameters[sectionKey][key] = pInput

    tools.printCharStr("-", 80, newlines=True)	


def generateTomlFile(deploy_globals, config_environments, script_info ):

    infra_type = script_info["infra"]
    output_dir = f"../{infra_type}-infrastructure"

    Prefix = script_info["args"].split(" ")[0]
    ProjectId = ""
    if len(script_info["args"].split(" ")) > 1:
        ProjectId = script_info["args"].split(" ")[1]
    ProjectIdentifier = Prefix
    if ProjectId != "":
        ProjectIdentifier = Prefix + "-" + ProjectId

    toml_filename = f"samconfig-{ProjectIdentifier}-{infra_type}.toml"
    sam_deploy_commands = {}

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Read in ./lib/templates/samconfig.toml.txt
    # Read the template file
    template_path = "./lib/templates/samconfig.toml.txt"
    with open(template_path, "r") as f:
        toml_template = f.read()

    InfraTemplateFile = ""
    # If deploy_globals["TemplateLocationBucketName"] is not empty, then the template is in S3
    if deploy_globals["TemplateLocationBucketName"] != "":
        InfraTemplateFile = f"s3://{deploy_globals['TemplateLocationBucketName']}{deploy_globals['TemplateLocationPrefix']}{deploy_globals['TemplateKeyFileName']}"
    else:
        InfraTemplateFile = f"./{infra_type}/templates/{deploy_globals['TemplateKeyFileName']}"

    # Create a dictionary of replacements
    replacements = {
        "$TEMPLATE_FILE$": InfraTemplateFile,
        "$S3_BUCKET_FOR_DEPLOY_ARTIFACTS$": deploy_globals["DeployBucket"],
        "$REGION$": deploy_globals["AwsRegion"],
        "$CAPABILITIES$": deploy_globals["Capabilities"],
        "$CONFIRM_CHANGESET$": deploy_globals["ConfirmChangeset"],
        "$IMAGE_REPOSITORIES$": deploy_globals["ImageRepositories"],
        "$SCRIPT_NAME$": script_info["name"],
        "$SCRIPT_ARGS$": script_info["args"]
    }

    # Perform the replacements
    toml_content = toml_template
    for placeholder, value in replacements.items():
        toml_content = toml_content.replace(placeholder, str(value))

    # Add the individual deployment sections
    for dkey, dvalue in config_environments.items():

        sam_deploy_command = f"sam deploy --config-env {dkey} --config-file {toml_filename} --profile default"
        sam_deploy_commands[dkey] = sam_deploy_command

        parameter_overrides = ""
        dvalue["defaults"]["stack_parameters"].update(dvalue["custom_params"])
        for pkey, pvalue in dvalue["defaults"]["stack_parameters"].items():
            parameter_overrides += f"\\\"{pkey}\\\"=\\\"{pvalue}\\\" "

        parameter_overrides = parameter_overrides.rstrip()        

        # Generate automated tags
        dvalue["custom_tags"].append({"Key": "Atlantis", "Value": infra_type})
        dvalue["custom_tags"].append({"Key": "atlantis:Prefix", "Value": Prefix})
        dvalue["custom_tags"].append({"Key": "Provisioner", "Value": "CloudFormation"})
        dvalue["custom_tags"].append({"Key": "DeployedUsing", "Value": "AWS SAM CLI"})

        dvalue["custom_tags"].append({"Key": "atlantis:TemplateVer", "Value": "Atlantis.v2.0.0"})
        dvalue["custom_tags"].append({"Key": "atlantis:TemplateFile", "Value": deploy_globals['TemplateKeyFileName']})

        if ProjectId != "":
            dvalue["custom_tags"].append({"Key": "atlantis:Application", "Value": f"{Prefix}-{ProjectId}"})

        if dkey != "default":
            dvalue["custom_tags"].append({"Key": "atlantis:ApplicationDeploymentId", "Value": f"{Prefix}-{ProjectId}-{dkey}"})
            dvalue["custom_tags"].append({"Key": "Stage", "Value": dkey})
            dvalue["custom_tags"].append({"Key": "Environment", "Value": dvalue["defaults"]["stack_parameters"]["DeployEnvironment"]})

        if "AlarmNotificationEmail" in dvalue["defaults"]["stack_parameters"]:
            dvalue["custom_tags"].append({"Key": "AlarmNotificationEmail", "Value": dvalue["defaults"]["stack_parameters"]["AlarmNotificationEmail"]})
        
        if "application" in dvalue and "Name" in dvalue["application"]:
            dvalue["custom_tags"].append({"Key": "atlantis:Application", "Value": dvalue["application"]["Name"]})

        if "CodeCommitRepository" in dvalue["defaults"]["stack_parameters"]:
            repo = dvalue["defaults"]["stack_parameters"]["CodeCommitRepository"]
            dvalue["custom_tags"].append({"Key": "CodeCommitRepository", "Value": repo})
            if "CodeCommitBranch" in dvalue["defaults"]["stack_parameters"]:
                branch = dvalue["defaults"]["stack_parameters"]["CodeCommitBranch"]
                dvalue["custom_tags"].append({"Key": "CodeCommitBranch", "Value": f"{repo}:{branch}"})

        tags = ""
        for tag in dvalue["custom_tags"]:
            tkey = tag["Key"]
            tvalue = tag["Value"]
            tags += f"\\\"{tkey}\\\"=\\\"{tvalue}\\\" "

        tags = tags.rstrip()

        stack_identifier = ProjectIdentifier
        if dkey != "default":
            stack_identifier += "-"+dkey

        stack_name = f"{stack_identifier}-{infra_type}"

        toml_deployParameters = {
            "stack_name" : stack_name,
            "s3_prefix": stack_name,
            "parameter_overrides": parameter_overrides,
            "tags": tags
        }

        # Add a [*.deploy.parameters] section to the content
        toml_content += f"\n\n[{dkey}.deploy.parameters]\n"

        # Add a comment with the sam command to deploy
        toml_content += "# =====================================================\n"
        toml_content += f"# {dkey} Deployment Configuration\n"
        toml_content += "# Deploy command:\n"
        toml_content += f"# {sam_deploy_command} \n\n"

        # Add the toml_deployParameters to the content
        for pkey, pvalue in toml_deployParameters.items():
            toml_content += f"{pkey} = \"{pvalue}\"\n"

        toml_content += "\n"

    # Write the processed TOML file
    output_toml_path = f"{output_dir}/samconfig-{ProjectIdentifier}-{infra_type}.toml"
    with open(output_toml_path, "w") as f:
        f.write(toml_content)

    return { "output_dir": output_dir, "sam_deploy_commands": sam_deploy_commands }

def loadSettings(script_info, defaults):

    args = script_info["args"].split(" ")

    # Create a file location array - this is the hierarchy of files we will gather defaults from. The most recent file appended (lower on list) will overwrite previous values
    defaultsFileLoc = []
    defaultsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/defaults.json")
    defaultsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/defaults-{args[0]}.json")

    customParamsFileLoc = []
    customParamsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/params.json")
    customParamsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/params-{args[0]}.json")

    customTagsFileLoc = []
    customTagsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/tags.json")
    customTagsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/tags-{args[0]}.json")

    if len(args) > 1:
        defaultsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/defaults-{args[0]}-{args[1]}.json")
        customParamsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/params-{args[0]}-{args[1]}.json")
        customTagsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/tags-{args[0]}-{args[1]}.json")

    if len(args) > 2:
        defaultsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/defaults-{args[0]}-{args[1]}-{args[2]}.json")
        customParamsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/params-{args[0]}-{args[1]}-{args[2]}.json")
        customTagsFileLoc.append(f"{dirs["settings"]}{script_info["infra"]}/tags-{args[0]}-{args[1]}-{args[2]}.json")


    print("[ Loading default json files... ]")

    for i in range(len(defaultsFileLoc)):
        if os.path.isfile(defaultsFileLoc[i]):
            with open(defaultsFileLoc[i], "r") as f:
                temp = json.load(f)
                for sectionKey in temp.keys():
                    for key in temp[sectionKey].keys():
                        # if sectionKey is not in defaults, add it
                        if sectionKey not in defaults:
                            defaults[sectionKey] = {}
                        defaults[sectionKey][key] = temp[sectionKey][key]
                print(" + Found "+defaultsFileLoc[i])
        else:
            print(" - Did not find "+defaultsFileLoc[i])

    # Read in Custom Parameters
            
    print("\n[ Loading params files... ]")

    # If params.json exists, read it in
    custom_params = {}

    for i in range(len(customParamsFileLoc)):
        if os.path.isfile(customParamsFileLoc[i]):
            with open(customParamsFileLoc[i], "r") as f:
                customData = json.load(f)
                for key in customData.keys():
                    custom_params[key] = customData[key]
                print(" + Found "+customParamsFileLoc[i])
        else:
            print(" - Did not find "+customParamsFileLoc[i])

    # Read in Custom Stack Tags
            
    print("\n[ Loading tags files... ]")

    # If tags.json exists, read it in
    custom_tags = []

    for i in range(len(customTagsFileLoc)):
        if os.path.isfile(customTagsFileLoc[i]):
            with open(customTagsFileLoc[i], "r") as f:
                tagData = json.load(f)
                # Both custom_tags and tagData are arrays with {Key: string, Value: string} elements
                # Loop through the elements in tagData
                #   1. Search custom_tags array for an element with Key == tagData[i].Key
                #   2. If it exists, replace it. Else, append
                for j in range(len(tagData)):
                    found = False
                    for k in range(len(custom_tags)):
                        if custom_tags[k]["Key"] == tagData[j]["Key"]:
                            custom_tags[k]["Value"] = tagData[j]["Value"]
                            found = True
                            break
                    if not found:
                        custom_tags.append(tagData[j])
                
                print(" + Found "+customTagsFileLoc[i])
        else:
            print(" - Did not find "+customTagsFileLoc[i])

    return {"defaults": defaults, "custom_params": custom_params, "custom_tags": custom_tags}

def saveSettings(parameters, removals, script_info):

    InfraType = script_info["infra"]
    args = script_info["args"].split(" ")

    Prefix = parameters["stack_parameters"]["Prefix"]
    ProjectId = ""
    StageId = ""
    if "ProjectId" in parameters["stack_parameters"]:
        ProjectId = parameters["stack_parameters"]["ProjectId"]
    if "StageId" in parameters["stack_parameters"]:
        StageId = parameters["stack_parameters"]["StageId"]

    # we list the files in reverse as we work up the normal read-in chain
    settingsFiles = [
        f"{dirs["settings"]}{InfraType}/defaults-{Prefix}.json",
        f"{dirs["settings"]}{InfraType}/defaults.json"
    ]

    if ProjectId != "":
        settingsFiles.insert(0, f"{dirs["settings"]}{script_info["infra"]}/defaults-{Prefix}-{ProjectId}.json")

    if StageId != "":
        settingsFiles.insert(0, f"{dirs["settings"]}{script_info["infra"]}/defaults-{Prefix}-{ProjectId}-{StageId}.json")

    print("[ Saving default json files... ]")

    data = []
    data.append(json.dumps(parameters, indent=4))
    limitedParam = json.dumps(parameters)

    # loop through the removals array and remove the keys from the limitedParam array before appending to data
    i = 0
    for removal in removals:
        d = json.loads(limitedParam)
        #remove tags property and i == 0
        if "tags" in d and i == 0:
            d.pop("tags")
        for key in removal.keys():
            for item in removal[key]:
                d[key].pop(item)
        limitedParam = json.dumps(d, indent=4)
        data.append(limitedParam)

    # go through each index of the cliInputFiles array and write out the corresponding data element and add the corresponding element at index in data
    numFiles = len(settingsFiles)

    for i in range(numFiles):
        file = settingsFiles[i]
        d = data[i]
        # create or overwrite file with d
        print(" * Saving "+file+"...")
        with open(file, "w") as f:
            f.write(d)
            f.close()

def getConfigEnvironments(script_info):
    # Read in all deployment environment files, order dictionary by default, test*/t*, beta*/b*, stage*/s*, prod*/p*,
    # Instead, since we just have the default environment we'll set it manually
    config_environments = {}
    
    infra_type = script_info["infra"]
    args = script_info["args"].split(" ")
    Prefix = args[0]
    ProjectId = ""
    StageId = ""
    if len(args) > 1:
        ProjectId = args[1]
    if len(args) > 2:
        StageId = args[2]

    if StageId != "":
        stages = ["t", "b", "s", "p"] # test, beta, stage, prod
        # loop through stages
        for stage in stages:
            # find all files that match the pattern defaults-{Prefix}-{stage*}.json
            # if there are any, read them in and add them to the config_environments dictionary
            # if there are none, skip
            # if there is only one, add it to the config_environments dictionary with the key {stage}
            # if there are multiple, add them to the config_environments dictionary with the key {stage}{i}
            # where i is the index of the file in the list of files
            files = glob.glob(f"{dirs["settings"]}{infra_type}/defaults-{Prefix}-{ProjectId}-{stage}*")

            if len(files) > 0:
                for i in range(len(files)):
                    # go through all the files and parse out the stage from the filename
                    # add the stage to the config_environments dictionary
                    # read in the file and add it to the config_environments dictionary
                    s = files[i].split("-")[-1].split(".")[0]
                    config_environments[s] = {}

        # Now that we know what stages exist, we can loop through config_environments and use loadSettings to read in the files
        for stage in config_environments.keys():
            temp_script_info = script_info
            temp_script_info["args"] = f"{Prefix} {ProjectId} {stage}"
            config_environments[stage] = loadSettings(temp_script_info, {})

    else:
        config_environments["default"] = loadSettings(script_info, {})

    #print(config_environments)
    return config_environments