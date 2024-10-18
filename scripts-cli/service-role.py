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
tools.printCharStr(" ", 80, bookend="|", text="Service Role AWS CLI Generator for Atlantis CI/CD")
tools.printCharStr(" ", 80, bookend="|", text="v2024.10.18 : service-role.py")
tools.printCharStr("-", 80, bookend="|")
tools.printCharStr(" ", 80, bookend="|", text="Chad Leigh Kluck")
tools.printCharStr(" ", 80, bookend="|", text="https://github.com/chadkluck/serverless-deploy-pipeline-atlantis")
tools.printCharStr("=", 80, bookend="|")
print("")

argPrefix = "atlantis"
argAcceptDefaults = False
scriptName = sys.argv[0]

# Check to make sure there are at least three arguments. If there are not 3 arguments then display message and exit. If there are 3 arguments set Prefix, ProjectId, and Stage
if len(sys.argv) > 1:
    argPrefix = sys.argv[1]
else:
    print("\n\nUsage: python "+scriptName+" <Prefix>\n\n")
    sys.exit()

# Default values - Set any of these defaults to your own in the defaults file
defaults = {
	"general": {
		"Prefix": argPrefix,
		"S3BucketNameOrgPrefix": atlantis.prompts["S3BucketNameOrgPrefix"]["default"],
		"AwsAccountId": atlantis.prompts["AwsAccountId"]["default"],
		"AwsRegion": atlantis.prompts["AwsRegion"]["default"],
		"RolePath": atlantis.prompts["RolePath"]["default"],
		"PermissionsBoundaryArn": atlantis.prompts["PermissionsBoundaryArn"]["default"],
		"ServiceRoleARN": ""
	}
}

# Read in defaults
    
print("[ Loading .default files... ]")

# Create a file location array - this is the hierarchy of files we will gather defaults from. The most recent file appended (lower on list) will overwrite previous values
fileLoc = []
fileLoc.append(atlantis.dirs["settings"]["Iam"]+"defaults.json")
fileLoc.append(atlantis.dirs["settings"]["Iam"]+"defaults-"+argPrefix+".json")

# iam defaults don't have keysections
for i in range(len(fileLoc)):
	if os.path.isfile(fileLoc[i]):
		with open(fileLoc[i], "r") as f:
			temp = json.load(f)
			for key in temp.keys():
				defaults["general"][key] = temp[key]
		print(" + Found "+fileLoc[i])
	else:
		print(" - Did not find "+fileLoc[i])

# Read in Custom Stack Tags
        
print("\n[ Loading tags files... ]")

tagFileLoc = []
tagFileLoc.append(atlantis.dirs["settings"]["Iam"]+"tags.json")
tagFileLoc.append(atlantis.dirs["settings"]["Iam"]+"tags-"+argPrefix+".json")

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
        "key": "general",
        "name": "General Information"
    }
]

prompts = {}
parameters = {}
for item in promptSections:
    prompts[item["key"]] = {}
    parameters[item["key"]] = {}

prompts["general"]["Prefix"] = atlantis.prompts["Prefix"]
prompts["general"]["Prefix"]["default"] = defaults["general"]["Prefix"]

prompts["general"]["S3BucketNameOrgPrefix"] = atlantis.prompts["S3BucketNameOrgPrefix"]
prompts["general"]["S3BucketNameOrgPrefix"]["default"] = defaults["general"]["S3BucketNameOrgPrefix"]

prompts["general"]["RolePath"] = atlantis.prompts["RolePath"]
prompts["general"]["RolePath"]["default"] = defaults["general"]["RolePath"]

prompts["general"]["PermissionsBoundaryArn"] = atlantis.prompts["PermissionsBoundaryArn"]
prompts["general"]["PermissionsBoundaryArn"]["default"] = defaults["general"]["PermissionsBoundaryArn"]

prompts["general"]["AwsAccountId"] = atlantis.prompts["AwsAccountId"]
prompts["general"]["AwsAccountId"]["default"] = defaults["general"]["AwsAccountId"]

prompts["general"]["AwsRegion"] = atlantis.prompts["AwsRegion"]
prompts["general"]["AwsRegion"]["default"] = defaults["general"]["AwsRegion"]

atlantis.getUserInput(prompts, parameters, promptSections)

# =============================================================================
# Set Values
# =============================================================================

parameters["general"]["ServiceRoleARN"] = "arn:aws:iam::"+parameters["general"]["AwsAccountId"]+":role"+parameters["general"]["RolePath"]+parameters["general"]["Prefix"].upper()+"-CloudFormation-Service-Role"

permissions_boundary_conditional = ""
permissions_boundary_cli = ""

if parameters["general"]["PermissionsBoundaryArn"]:
	permissions_boundary_conditional = """,
			"Condition": {
				"StringLike": {
					"iam:PermissionsBoundary": "$PERMISSIONS_BOUNDARY_ARN$"
				}
			}"""
	permissions_boundary_cli = " --permissions-boundary "+parameters["general"]["PermissionsBoundaryArn"]+" \\\n\t"

# =============================================================================
# Save files
# =============================================================================

print("[ Saving .default files... ]")

tf = {
    "Prefix": parameters["general"]["Prefix"],
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
        "general": [
            "Prefix", "ServiceRoleARN"
        ]
    }
]

data = []
data.append(json.dumps(parameters["general"], indent=4))
limitedParam = json.dumps(parameters)

# loop through the removals array and remove the keys from the limitedParam array before appending to data
for removal in removals:
    d = json.loads(limitedParam)
    for key in removal.keys():
        for item in removal[key]:
            d[key].pop(item)
    limitedParam = json.dumps(d, indent=4)
    data.append(json.dumps(d["general"], indent=4))

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
cli_output_dir = atlantis.dirs["cli"]["Iam"]+parameters["general"]["Prefix"]+"/"
if not os.path.isdir(cli_output_dir):
	os.makedirs(cli_output_dir)
        
# Open the sample-ATLANTIS-CloudFormationServicePolicy.json file
with open(
	os.path.join(cwd, atlantis.files["iamServicePolicy"]["path"]), "r"
) as f:
	# Read the contents of the file
	contents = f.read()
	# Replace the placeholders with the values from the command line
	contents = contents.replace("$PREFIX$", parameters["general"]["Prefix"])
	contents = contents.replace("$PREFIX_UPPER$", parameters["general"]["Prefix"].upper())
	contents = contents.replace("$ROLE_PATH$", parameters["general"]["RolePath"])
	contents = contents.replace("$AWS_ACCOUNT$", parameters["general"]["AwsAccountId"])
	contents = contents.replace("$AWS_REGION$", parameters["general"]["AwsRegion"])

	# Replace permissions boundary placeholder which is complex:
	contents = contents.replace(",\"Condition\": \"$PERMISSIONS_BOUNDARY_CONDITIONAL$\"", permissions_boundary_conditional)
	contents = contents.replace("$PERMISSIONS_BOUNDARY_ARN$", parameters["general"]["PermissionsBoundaryArn"])

	# if s3_bucket_prefix is provided, replace the placeholder with the value from the command line followed by a hyphen, else replace with blank
	if not parameters["general"]["S3BucketNameOrgPrefix"]:
		contents = contents.replace("$S3_ORG_PREFIX$", "")
	else:
		contents = contents.replace("$S3_ORG_PREFIX$", parameters["general"]["S3BucketNameOrgPrefix"] + "-")

	# Write the updated contents to a new file in the generated directory
	new_file_name = parameters["general"]["Prefix"].upper()+"-CloudFormationServicePolicy.json"
	with open(os.path.join(cli_output_dir, new_file_name), "w") as g:
		g.write(contents)
		g.close()
		f.close()

		# Print a message indicating that the file has been copied
		print("File copied and updated successfully!")
		print(os.path.join(cli_output_dir, new_file_name))

		# Prepend {"Key": "Atlantis", "Value": "iam"} and {"Key": "atlantis:Prefix", "Value": prefix} to tags list
		customSvcRoleTags.insert(0, {"Key": "Atlantis", "Value": "iam"})
		customSvcRoleTags.insert(1, {"Key": "atlantis:Prefix", "Value": parameters["general"]["Prefix"]})

		tags_cli = "--tags "
		for tag in customSvcRoleTags:
			tags_cli += "'{\"Key\": \""+tag["Key"]+"\", \"Value\": \""+tag["Value"]+"\"}' "

		tags_cli = tags_cli.rstrip()

		print("")
		tools.printCharStr("=", 80, bookend="!", text="CREATE ROLE INSTRUCTIONS")
		tools.printCharStr(" ", 80, bookend="!", text="Execute the following AWS CLI commands in order to create the role.")
		tools.printCharStr(" ", 80, bookend="!", text="A copy of the commands have been saved to inputs/ for later use.")
		tools.printCharStr("-", 80, bookend="!")
		tools.printCharStr(" ", 80, bookend="!", text="Make sure you are logged into AWS CLI with a user role holding permissions")
		tools.printCharStr(" ", 80, bookend="!", text="to create the service role!")
		tools.printCharStr("-", 80, bookend="!")
		tools.printCharStr(" ", 80, bookend="!", text="Alternately, you can create the role manually via the AWS Web Console using")
		tools.printCharStr(" ", 80, bookend="!", text="the CloudFormationServicePolicy found in cli/iam/")
		tools.printCharStr("=", 80, bookend="!")
		print("")
            
		win_cmd = []
		msgForWinCLI_1 = "# NOTE FOR BASH ON WINDOWS USERS: When using Bash on Windows you may need to execute the following export command first if you receive the following error:"
		msgForWinCLI_2 = "# ValidationError when calling the CreateRole operation: The specified value for path is invalid."
		win_cmd.append(tools.breakLines(msgForWinCLI_1, tools.indent(4, '#')))
		win_cmd.append(tools.breakLines(msgForWinCLI_2, tools.indent(4, '#')))
		win_cmd.append("")
		win_cmd.append("export MSYS_NO_PATHCONV=1")
            
		stringWinCmd = "\n".join(win_cmd)
    
		# detect if user is on windows and print a message to export MSYS_NO_PATHCONV variable
		if os.name == "nt":
			print(stringWinCmd)

		ROOT_CLI_DIR_IAM = cli_output_dir
		IAM_TRUST_POLICY = "../../"+atlantis.files["iamTrustPolicy"]["name"]
		IAM_SERVICE_POLICY = new_file_name
        
		# Print a message indicating the aws iam cli commands to create the role and policy and attach it to the role

		create_role_comment = []
		create_role_comment.append("# -----------------------------------------------------------------------------")
		create_role_comment.append("# Run iam create-role command from the /iam-cloudformation-service-role/roles/"+parameters["general"]["Prefix"]+" directory (or adjust path as needed)")
		create_role_comment.append("")
		create_role_comment.append("cd "+ROOT_CLI_DIR_IAM)

		stringCliRoleComment = "\n".join(create_role_comment)
        
		# Generate the CLI command for create-role
		create_role = []
		create_role.append("aws iam create-role --path "+parameters["general"]["RolePath"])
		create_role.append("--role-name "+parameters["general"]["Prefix"].upper()+"-CloudFormation-Service-Role")
		create_role.append("--description 'Service Role for CloudFormation Service to create and manage pipelines under the "+parameters["general"]["Prefix"]+" prefix'")
		create_role.append("--assume-role-policy-document file://$IAM_TRUST_POLICY$")
		if parameters["general"]["PermissionsBoundaryArn"]:
			create_role.append("--permissions-boundary "+parameters["general"]["PermissionsBoundaryArn"])
		create_role.append(tags_cli)

		stringCliRole = " \\\n\t".join(create_role)
            
		put_policy = []
		put_policy.append("aws iam put-role-policy --role-name "+parameters["general"]["Prefix"].upper()+"-CloudFormation-Service-Role")
		put_policy.append("--policy-name "+parameters["general"]["Prefix"].upper()+"-CloudFormationServicePolicy")
		put_policy.append("--policy-document file://$IAM_SERVICE_POLICY$")
		
		stringCliPolicy = " \\\n\t".join(put_policy)
        
		cliCommands = stringCliRoleComment + "\n\n" + stringCliRole + "\n\n" + stringCliPolicy + "\n"
		cliCommands = cliCommands.replace("$IAM_TRUST_POLICY$", IAM_TRUST_POLICY)
		cliCommands = cliCommands.replace("$IAM_SERVICE_POLICY$", IAM_SERVICE_POLICY)
            
		# save cliCommands to cli-<Prefix>.txt
		cliCommandsFilename = cli_output_dir+"cli-"+parameters["general"]["Prefix"]+".txt"
		myFile = open(cliCommandsFilename, "w")
		n = myFile.write(stringWinCmd+"\n\n"+cliCommands)

		print(cliCommands)
