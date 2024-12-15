# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific language governing permissions 
# and limitations under the License.
#
# CLI Generator Variable and Function Library for Atlantis CI/CD CodePipeline CloudFormation Template
# Chad Leigh Kluck
# v2024.06.17 : lib/atlantis.py

import os
import shutil
import re
import sys


import tools
import yaml

hello = "Hello, World"

# =============================================================================
# Make sure that the directory structure is correct and that the files are present
# Copy over sample files

dirs = {
    "settings": {},
	"toml": {}
}

dirSettings = "./settings/"

dirs["settings"]["Iam"] = dirSettings+"iam/"
dirs["settings"]["Pipeline"] = dirSettings+"pipeline/"
dirs["settings"]["Storage"] = dirSettings+"storage/"
dirs["settings"]["Network"] = dirSettings+"network/"

dirs["iamServiceRole"] = "../iam-service-role-infrastructure/"
dirs["pipeline"] = "../pipeline-infrastructure/"
dirs["storage"] = "../storage-infrastructure/"
dirs["network"] = "../network-infrastructure/"

files = {
    "pipelineTemplate": {},
    "pipelineTemplateInput": {},
	"docsPipelineParamReadme": {}
}

dirs["docs"] = "../docs/"

files["pipelineTemplate"]["name"] = "template-pipeline.yml"
files["pipelineTemplate"]["path"] = dirs["pipeline"]+files["pipelineTemplate"]["name"]

files["docsPipelineParamReadme"]["name"] = "Pipeline-Parameters-Reference.md"
files["docsPipelineParamReadme"]["path"] = dirs["docs"]+files["docsPipelineParamReadme"]["name"]

dirsAndFiles = [
    {
        "dir": dirs["settings"]["Pipeline"],
        "files": [
            "sample.tags.json",
            "sample.params.json"
        ],
    },
    {
        "dir": dirs["settings"]["Iam"],
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

	# Application specific - pipeline-stack.py

	"application-Name": {
		"name": "Application Name",
		"required": True,
		"regex": "^[a-zA-Z0-9][a-zA-Z0-9_\\-\\/\\s]{0,62}[a-zA-Z0-9]$",
		"help": "2 to 64 characters. Alphanumeric, dashes, underscores, and spaces. Must start and end with a letter or number.",
		"description": "A descriptive name to identify the main application irregardless of the stage or branch. This is only used in the Tag Name and not visible anywhere else.",
		"examples": "Financial Transaction Processing, Financial Transaction Audit, acme-finance-app",
		"default": ""
	},

	"ServiceRoleARN": {
		"name": "Service Role ARN",
		"required": True,
		"regex": "^$|^arn:aws:iam::[0-9]{12}:role\\/[a-zA-Z0-9\\/_-]+$",
		"help": "Service Role ARN must be in the format: arn:aws:iam::{account_id}:role/{policy_name}",
		"description": "The Service Role gives CloudFormation permission to create, delete, and manage stacks on your behalf.",
		"examples": "arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role",
		"default": ""
	},

	# Template specific - pipeline-stack.py

	"pipeline_template_location-BucketName": {
		"name": "S3 Bucket Name for Pipeline Template",
		"required": True,
		"regex": "^[a-z0-9][a-z0-9-]*[a-z0-9]$|^$",
		"help": "S3 bucket name must be lowercase, start with a letter, and contain only letters, numbers, and dashes",
		"description": "Where is the pipeline template stored?",
		"examples": "63klabs, mybucket",
		"default": "63klabs"
	},

	"pipeline_template_location-BucketKey": {
		"name": "S3 Bucket Key for Pipeline Template",
		"required": True,
		"regex": "^\\/[a-zA-Z0-9\\/_-]+\\/$|^\\/$",
		"help": "S3 bucket key must be lowercase, start and end with a slash and contain only letters, numbers, dashes and underscores",
		"description": "Where is the pipeline template stored?",
		"examples": "/atlantis/v2/, /atlantis/v3/",
		"default": "/atlantis/v2/"
	},

	"pipeline_template_location-FileName": {
		"name": "Pipeline Template File Name",
		"required": True,
		"regex": "^[a-zA-Z0-9][a-zA-Z0-9-_]*[a-zA-Z0-9]\\.(yml|yaml|json)$",
		"help": "File name must be lowercase, start with a letter, and contain only letters, numbers, and dashes",
		"description": "What is the pipeline template file name?",
		"examples": "template-pipeline.yml, template-pipeline.yaml",
		"default": "template-pipeline.yml"
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
