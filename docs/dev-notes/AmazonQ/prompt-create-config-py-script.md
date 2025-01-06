1. Reads in the current samconfig file (based on infrastructure type and naming convention - if exists)
2. If --check-stack is true then it checks the existing stack (user needs to have valid credentials and may need to use --profile)
3. If exisitng stack configuration differs from samconfig then the user is notified. The script will display the differences. The user will then be allowed to continue with either the local or deployed settings, or cancel.
4. If it is an existing stack with tag "atlantis:TemplateFile", or existing samconfig with template_file, read in that file and grab the CloudFormation parameters. The template_file may point to an S3 location (s3://) or local file (such as template-pipeline.yml). If local, then the template is located in the infrastructure's template directory. (Full path is not listed for local files in the tag)
5. If no stack and no samconfig exists, then the script will allow user to choose from a list of templates discovered in the templates directory for that infrastructure type. Default global values will be read in from default.json files specific to Prefix and/or ProjectId.
6. After the script examines the template file, the user will be prompted for global deploy parameters (s3_bucket, template_file, region, confirm_changeset, and role (if pipeline)). (s3_bucket, region, and role may be pre-set in a settings/defaults.json file)
7. Next, the user will be prompted to enter values for each parameter. Existing or default values will be presented in square brackets. This value will be used if the user accepts it by leaving the prompt blank and hitting enter. (if the user types in -, ?, or ^ and presses enter the script will clear out the default value, provide help information, or exit script respectively. The entries should be validated based on the template's parameter definitions.
8. The script will then save the TOML file. If a StageId was provided as a script argument then that will be the sam deployment environment. Otherwise (for service-role and storage which do not have stages) default will be used.

I'll help you create a Python script that implements this CloudFormation/SAM configuration management workflow. Here's a structured implementation:

import boto3
import toml
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
import click
from botocore.exceptions import ClientError

class ConfigManager:
    def __init__(self, infra_type: str, project_id: str, stage_id: Optional[str] = None):
        self.infra_type = infra_type
        self.project_id = project_id
        self.stage_id = stage_id or 'default'
        self.cfn_client = boto3.client('cloudformation')
        self.templates_dir = Path(f"infrastructure/{infra_type}/templates")
        self.settings_dir = Path("settings")
        
    def read_samconfig(self) -> Optional[Dict]:
        """Read existing samconfig.toml if it exists"""
        samconfig_path = Path(f"samconfig.toml")
        if samconfig_path.exists():
            return toml.load(samconfig_path)
        return None

    def get_stack_config(self, stack_name: str) -> Optional[Dict]:
        """Get configuration from existing CloudFormation stack"""
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            # Get template file from tags
            template_file = None
            for tag in stack.get('Tags', []):
                if tag['Key'] == 'atlantis:TemplateFile':
                    template_file = tag['Value']
                    
            return {
                'parameters': {p['ParameterKey']: p['ParameterValue'] 
                             for p in stack.get('Parameters', [])},
                'template_file': template_file
            }
        except ClientError:
            return None

    def compare_configurations(self, local_config: Dict, stack_config: Dict) -> Dict:
        """Compare local and deployed configurations"""
        differences = {}
        
        for key, local_value in local_config.items():
            stack_value = stack_config.get(key)
            if stack_value != local_value:
                differences[key] = {
                    'local': local_value,
                    'deployed': stack_value
                }
        return differences

    def get_template_parameters(self, template_path: str) -> Dict:
        """Get parameters from CloudFormation template"""
        if template_path.startswith('s3://'):
            # Handle S3 template
            pass
        else:
            # Handle local template
            template_path = self.templates_dir / template_path
            with open(template_path) as f:
                template = json.load(f)
                return template.get('Parameters', {})

    def discover_templates(self) -> List[str]:
        """Discover available templates in the infrastructure type directory"""
        return [f.name for f in self.templates_dir.glob('*.yml')]

    def load_defaults(self) -> Dict:
        """Load default values from settings files"""
        defaults = {}
        
        # Load project defaults
        project_defaults = self.settings_dir / f"{self.project_id}_defaults.json"
        if project_defaults.exists():
            with open(project_defaults) as f:
                defaults.update(json.load(f))
                
        return defaults

    def prompt_for_parameters(self, parameters: Dict, defaults: Dict) -> Dict:
        """Prompt user for parameter values"""
        values = {}
        
        for param_name, param_def in parameters.items():
            default_value = defaults.get(param_name, param_def.get('Default', ''))
            
            while True:
                value = click.prompt(
                    f"{param_name} [{default_value}]",
                    default=default_value,
                    show_default=False
                )
                
                if value == '?':
                    click.echo(param_def.get('Description', 'No description available'))
                    continue
                elif value == '^':
                    raise click.Abort()
                elif value == '-':
                    value = ''
                
                # Validate parameter
                if self.validate_parameter(value, param_def):
                    values[param_name] = value
                    break
                else:
                    click.echo(f"Invalid value for {param_name}")
                    
        return values

    def validate_parameter(self, value: str, param_def: Dict) -> bool:
        """Validate parameter value against CloudFormation parameter definition"""
        # Implement parameter validation based on AllowedPattern, AllowedValues, etc.
        return True

    def save_config(self, config: Dict):
        """Save configuration to samconfig.toml"""
        with open('samconfig.toml', 'w') as f:
            toml.dump(config, f)

@click.command()
@click.option('--check-stack', is_flag=True, help='Check existing stack configuration')
@click.option('--profile', help='AWS profile name')
@click.argument('infra_type')
@click.argument('project_id')
@click.argument('stage_id', required=False)
def main(check_stack: bool, profile: str, infra_type: str, project_id: str, stage_id: str):
    if profile:
        boto3.setup_default_session(profile_name=profile)
        
    config_manager = ConfigManager(infra_type, project_id, stage_id)
    
    # Read existing configuration
    local_config = config_manager.read_samconfig()
    
    if check_stack:
        stack_name = f"{project_id}-{stage_id}"
        stack_config = config_manager.get_stack_config(stack_name)
        
        if stack_config and local_config:
            differences = config_manager.compare_configurations(local_config, stack_config)
            if differences:
                click.echo("Differences found between local and deployed configuration:")
                click.echo(json.dumps(differences, indent=2))
                
                choice = click.prompt(
                    "Choose configuration to use (local/deployed/cancel)",
                    type=click.Choice(['local', 'deployed', 'cancel'])
                )
                
                if choice == 'cancel':
                    raise click.Abort()
                elif choice == 'deployed':
                    local_config = stack_config

    # Handle template selection and parameter configuration
    if not local_config:
        templates = config_manager.discover_templates()
        template_file = click.prompt(
            "Select template",
            type=click.Choice(templates)
        )
    else:
        template_file = local_config['template_file']

    parameters = config_manager.get_template_parameters(template_file)
    defaults = config_manager.load_defaults()
    
    # Prompt for parameters
    parameter_values = config_manager.prompt_for_parameters(parameters, defaults)
    
    # Save configuration
    config = {
        'default': {
            'deploy': {
                'parameters': parameter_values,
                'template_file': template_file
            }
        }
    }
    config_manager.save_config(config)

if __name__ == '__main__':
    main()

Copy

Insert at cursor
python
This implementation provides:

A ConfigManager class that handles all configuration-related operations

Support for reading existing samconfig.toml files

Stack configuration checking and comparison

Template discovery and parameter processing

Default value handling from settings files

Interactive parameter prompting with validation

Configuration saving in TOML format

The script uses Click for CLI argument handling and provides a user-friendly interface for parameter input. It handles both local and S3-hosted templates, supports AWS profiles for authentication, and implements the specified special input handling ( -, ?, ^).

You would need to install the required dependencies:

pip install boto3 toml click

Copy

Insert at cursor
bash
The script could be enhanced with:

More robust parameter validation

Better error handling

Support for additional CloudFormation template formats

More detailed logging

Support for additional parameter sources

Template validation before deployment

Would you like me to elaborate on any particular aspect of the implementation?

> So this was a starting point. From there I ran the script, walked through the code and suggested changes to futher develop it such as updating file locations, naming conventions, and refining my requirements.

> Q did a pretty good job, but still had issues with the samconfig.toml file. Whenever I've worked with Q on samconfig files, it seems to forget how AWS formats them. For example, placing the version number at top. And then the way parameter_overrides and tags need to be a single string. And then, how to properly format the quotes in the string. Usually placing extra escape characters, and "forgetting" that the toml dump will put them in automatically.

> We need to save the samconfig.toml file as a valid samconfig file for use with AWS SAM deploy

Here's how we can save the parameters to a valid samconfig.toml file format: [1]

def save_sam_config(self, template_file: str, parameter_values: Dict) -> None:
    """Save parameters to samconfig.toml file"""
    config = {
        'default': {
            'deploy': {
                'template_file': template_file,
                'parameters': parameter_values
            }
        }
    }
    
    # Convert the config to TOML format
    try:
        import toml
        
        # Create the samconfig.toml file
        with open('samconfig.toml', 'w') as f:
            # Write the template file setting
            f.write(f'[default.deploy]\ntemplate_file = "{template_file}"\n\n')
            
            # Write the parameters section
            f.write('[default.deploy.parameters]\n')
            for key, value in parameter_values.items():
                # Handle empty strings
                if value == '':
                    value = '""'
                f.write(f'{key} = "{value}"\n')
            
        logging.info("Configuration saved to samconfig.toml")
        
    except ImportError:
        logging.error("toml package not installed. Run: pip install toml")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        sys.exit(1)

Copy

Insert at cursor
python
You'll need to add this import at the top of your file:

import sys

Copy

Insert at cursor
python
And install the toml package:

pip install toml

Copy

Insert at cursor
bash
Then call this method after getting the parameter values:

# In your main function or wherever you're handling the parameters
parameter_values = config_manager.prompt_for_parameters(parameters, defaults)
config_manager.save_sam_config(template_file, parameter_values)

Copy

Insert at cursor
python
This will create a samconfig.toml file that looks like:

[default.deploy]
template_file = "template-storage-cache-data.yml"

[default.deploy.parameters]
Prefix = "acme"
ProjectId = "myproj"
StageId = "dev"

Copy

Insert at cursor
toml
This format is compatible with the AWS SAM CLI and can be used directly with sam deploy. The file will be created in the current directory, and any existing samconfig.toml file will be overwritten.

> Because I had the same issue with Q improperly generating the parameter_overrides in previous dealings I quickly saw an issue

> Don't parameters for templates need to be set as parameter_overrides = "" in samconfig.toml files?

Yes, you're absolutely right! For SAM templates, the parameters need to be formatted as a single parameter_overrides string. Here's the corrected version:

def save_sam_config(self, template_file: str, parameter_values: Dict) -> None:
    """Save parameters to samconfig.toml file"""
    try:
        # Create the parameter_overrides string
        # Format: "Key1=Value1 Key2=Value2 Key3=Value3"
        parameter_overrides = " ".join([
            f'{key}=\\"{value}\\"' for key, value in parameter_values.items()
        ])
        
        # Create the samconfig.toml file
        with open('samconfig.toml', 'w') as f:
            # Write the template file setting
            f.write(f'[default.deploy]\ntemplate_file = "{template_file}"\n\n')
            
            # Write the parameters section with parameter_overrides
            f.write('[default.deploy.parameters]\n')
            f.write(f'parameter_overrides = "{parameter_overrides}"\n')
            
        logging.info("Configuration saved to samconfig.toml")
        
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        sys.exit(1)

Copy

Insert at cursor
python
This will create a samconfig.toml file that looks like:

[default.deploy]
template_file = "template-storage-cache-data.yml"

[default.deploy.parameters]
parameter_overrides = "Prefix=\"acme\" ProjectId=\"myproj\" StageId=\"dev\""

Copy

Insert at cursor
toml
This format is the correct one for AWS SAM CLI to use with sam deploy. The double escaping of quotes ( \") is necessary for the SAM CLI to properly parse the parameter values.

> now, when parameter_overrides is written, there are extra back slashes.

Yes, we need to adjust the escaping in the parameter_overrides string. Here's the corrected version:

def save_config(self, config: Dict) -> None:
    """Save configuration to samconfig.toml file"""
    try:
        # Get the parameter values from the config
        parameter_values = config.get('default', {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {})
        
        # Convert parameter_values dict to parameter_overrides string
        if isinstance(parameter_values, dict):
            parameter_overrides = " ".join([
                f'{key}=\\\"{value}\\\"' for key, value in parameter_values.items()
            ])
            
            # Update the config with the string version
            config['default']['deploy']['parameters']['parameter_overrides'] = parameter_overrides
        
        # Write the config to samconfig.toml
        import toml
        with open('samconfig.toml', 'w') as f:
            toml.dump(config, f)
            
        logging.info("Configuration saved to samconfig.toml")
        
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        sys.exit(1)

Copy

Insert at cursor
python
The key change is in the string formatting:

f'{key}=\\\"{value}\\\"'  # Three backslashes for proper escaping

Copy

Insert at cursor
python
This will produce the correct format in samconfig.toml:

[globals.deploy.parameters]
template_file = "template-storage-cache-data.yml"

[default.deploy.parameters]
parameter_overrides = "Prefix=\"acme\" ProjectId=\"myproj\" StageId=\"dev\""

Copy

Insert at cursor
toml
Now the parameter_overrides string will have the correct number of backslashes when written to the file.

> The toml file is still showing three backslashes

Let's modify the escaping approach. Since TOML's dump function is adding its own escaping, we need to adjust our string formatting: [1]

def save_config(self, config: Dict) -> None:
    """Save configuration to samconfig.toml file"""
    try:
        # Get the parameter values from the config
        parameter_values = config.get('default', {}).get('deploy', {}).get('parameters', {}).get('parameter_overrides', {})
        
        # Convert parameter_values dict to parameter_overrides string
        if isinstance(parameter_values, dict):
            parameter_overrides = " ".join([
                f'{key}="{value}"' for key, value in parameter_values.items()
            ])
            
            # Update the config with the string version
            config['default']['deploy']['parameters']['parameter_overrides'] = parameter_overrides
        
        # Write the config to samconfig.toml
        import toml
        with open('samconfig.toml', 'w') as f:
            toml.dump(config, f)
            
        logging.info("Configuration saved to samconfig.toml")
        
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        sys.exit(1)

Copy

Insert at cursor
python
The key change is simplifying the string formatting to:

f'{key}="{value}"'  # Simple quotes, let toml.dump handle the escaping

Copy

Insert at cursor
python
This should now produce the correct format in samconfig.toml:

[globals.deploy.parameters]
template_file = "template-storage-cache-data.yml"

[default.deploy.parameters]
parameter_overrides = "Prefix=\"acme\" ProjectId=\"myproj\" StageId=\"dev\""


> Parsing the Template files to get the parameter section was a back and forth. First, it had written the code to bring in a template file from json format. I gave it the error message and it was able to add in yaml parsing (it opted to allow either YAML or JSON formatted files. I don't write my templates in JSON so I haven't tested it.)

> I do like how I can just paste in error messages and Q will work on fixing it. If I look at an error message and can't figure it out on my own in 30 seconds, I hand it over to Q. Though this is a valid one that required some work to overcome, I do feel like a pesky junior constantly asking my senior to see why I get a syntax error. With Q I don't mind saving a few minutes of debugging on my own and just handing it over.

> Traceback (most recent call last):
File "/home/devuser/Projects/personal/aws/63k-release/serverless-deploy-pipeline-atlantis/scripts/config.py", line 264, in <module>
main()
File "/usr/lib/python3/dist-packages/click/core.py", line 1157, in call
return self.main(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3/dist-packages/click/core.py", line 1078, in main
rv = self.invoke(ctx)
^^^^^^^^^^^^^^^^
File "/usr/lib/python3/dist-packages/click/core.py", line 1434, in invoke
return ctx.invoke(self.callback, **ctx.params)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3/dist-packages/click/core.py", line 783, in invoke
return __callback(*args, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/devuser/Projects/personal/aws/63k-release/serverless-deploy-pipeline-atlantis/scripts/config.py", line 246, in main
parameters = config_manager.get_template_parameters(template_file)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/devuser/Projects/personal/aws/63k-release/serverless-deploy-pipeline-atlantis/scripts/config.py", line 90, in get_template_parameters
template = json.load(f)
^^^^^^^^^^^^
File "/usr/lib/python3.12/json/init.py", line 293, in load
return loads(fp.read(),
^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/json/init.py", line 346, in loads
return _default_decoder.decode(s)
^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/json/decoder.py", line 337, in decode
obj, end = self.raw_decode(s, idx=_w(s, 0).end())
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/lib/python3.12/json/decoder.py", line 355, in raw_decode
raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

The error occurs because we're trying to parse a file as JSON but it's likely a YAML file (based on the .yml extension in the discover_templates method). Let's modify the get_template_parameters method to handle both JSON and YAML files:

import yaml  # Add this import at the top of the file

def get_template_parameters(self, template_path: str) -> Dict:
    """Get parameters from CloudFormation template"""
    if template_path.startswith('s3://'):
        # Handle S3 template
        pass
    else:
        # Handle local template
        template_path = self.templates_dir / template_path
        with open(template_path) as f:
            content = f.read()
            try:
                # Try parsing as JSON first
                template = json.loads(content)
            except json.JSONDecodeError:
                try:
                    # If JSON fails, try parsing as YAML
                    template = yaml.safe_load(content)
                except yaml.YAMLError as e:
                    logging.error(f"Error parsing template file {template_path}: {e}")
                    return {}
            
            return template.get('Parameters', {})

Copy

Insert at cursor
python
This updated version:

Attempts to parse the file as JSON first

If JSON parsing fails, tries to parse it as YAML

Returns an empty dict if both parsing attempts fail

Uses yaml.safe_load() which is the recommended secure way to parse YAML files

You'll need to install the PyYAML package if you haven't already:

pip install pyyaml

Copy

Insert at cursor
bash
This should resolve the JSONDecodeError and handle both JSON and YAML CloudFormation templates.

> ERROR:root:Error parsing template file ../storage-infrastructure/templates/template-storage-cache-data.yml: could not determine a constructor for the tag '!Not'
in "<unicode string>", line 111, column 29:
UseS3BucketNameOrgPrefix: !Not [!Equals [!Ref S3BucketName ...

Can we parse just the parameters section?

Yes, we can modify the YAML parsing to ignore CloudFormation-specific tags like !Not, !Equals, etc., by using a custom YAML loader that treats these tags as strings. Here's the updated version:

def get_template_parameters(self, template_path: str) -> Dict:
    """Get parameters from CloudFormation template"""
    if template_path.startswith('s3://'):
        # Handle S3 template
        pass
    else:
        # Handle local template
        template_path = self.templates_dir / template_path
        
        # Create a custom loader that ignores CloudFormation tags
        class IgnoreTagsLoader(yaml.SafeLoader):
            def ignore_unknown(self, node):
                return node.tag
        
        # Register all common CloudFormation tags to be ignored
        tags_to_ignore = [
            'Ref', 'Condition', 'Not', 'And', 'Or', 'If', 'Equals',
            'Join', 'Sub', 'GetAtt', 'ImportValue', 'Select'
        ]
        for tag in tags_to_ignore:
            yaml.add_constructor(f'!{tag}', IgnoreTagsLoader.ignore_unknown, Loader=IgnoreTagsLoader)
        
        with open(template_path) as f:
            content = f.read()
            try:
                # Try parsing as JSON first
                template = json.loads(content)
            except json.JSONDecodeError:
                try:
                    # If JSON fails, try parsing as YAML with custom loader
                    template = yaml.load(content, Loader=IgnoreTagsLoader)
                except yaml.YAMLError as e:
                    logging.error(f"Error parsing template file {template_path}: {e}")
                    return {}
            
            return template.get('Parameters', {})

Copy

Insert at cursor
python
This solution:

Creates a custom YAML loader that ignores CloudFormation intrinsic functions and their tags

Registers common CloudFormation tags to be ignored during parsing

Uses this custom loader when parsing the YAML file

Still maintains security by inheriting from SafeLoader

This should allow you to parse the Parameters section of the template without being affected by CloudFormation-specific tags in other sections of the template.

> Here, Q's solution was way to intense, and even for future development I don't plan on parsing out the entire template. I just need the Parameters so that I can prompt the user and validate. So I gave a suggestion as I would to a junior developer in case I wasn't clear before:

> can we just load in the parameters section of the yaml file?

Yes, we can use PyYAML's ability to load specific sections of a YAML file. Here's the modified version: [1]

def get_template_parameters(self, template_path: str) -> Dict:
    """Get parameters from CloudFormation template"""
    if template_path.startswith('s3://'):
        # Handle S3 template
        pass
    else:
        # Handle local template
        template_path = self.templates_dir / template_path
        
        try:
            # Read the file content
            with open(template_path) as f:
                # Look for the Parameters section
                parameters_section = ""
                in_parameters = False
                
                for line in f:
                    if line.startswith('Parameters:'):
                        in_parameters = True
                        parameters_section = line
                    elif in_parameters:
                        # Check if we've moved to a new top-level section
                        if line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                            break
                        parameters_section += line
                
                # Parse just the Parameters section
                if parameters_section:
                    # Add a dummy root to ensure valid YAML
                    yaml_content = yaml.safe_load(parameters_section)
                    return yaml_content.get('Parameters', {})
                return {}
                
        except Exception as e:
            logging.error(f"Error parsing template file {template_path}: {e}")
            return {}

Copy

Insert at cursor
python
This approach:

Reads the file line by line

Captures only the Parameters section and its contents

Stops when it encounters the next top-level section (any line that doesn't start with a space and ends with a colon)

Parses only the Parameters section using yaml.safe_load

Returns an empty dict if no Parameters section is found or if there's an error

This should avoid any issues with CloudFormation intrinsic functions and tags since we're not parsing those sections of the template.

> At this point I want to do something that is beyond my Python coding to improve the UI

> for select template, can we have a numbered list and have the user enter a number instead of the whole template name?

Yes, we can modify the template selection to show a numbered list and accept numeric input. Here's how:

def select_template(self, templates: List[str]) -> str:
    """Display numbered list of templates and let user select by number"""
    if not templates:
        logging.error("No templates found")
        sys.exit(1)
    
    # Sort templates for consistent ordering
    templates.sort()
    
    # Display numbered list
    print("\nAvailable templates:")
    for idx, template in enumerate(templates, 1):
        print(f"{idx}. {template}")
    
    while True:
        try:
            choice = input("\nEnter template number: ")
            # Check if input is a number
            template_idx = int(choice) - 1
            
            # Validate the index is within range
            if 0 <= template_idx < len(templates):
                return templates[template_idx]
            else:
                print(f"Please enter a number between 1 and {len(templates)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nTemplate selection cancelled")
            sys.exit(1)

Copy

Insert at cursor
python
This implementation:

Sorts the templates for consistent ordering

Displays a numbered list starting from 1

Prompts for numeric input

Validates the input is:

A valid number

Within the range of available templates

Keeps prompting until a valid selection is made

Handles keyboard interrupts gracefully

Returns the selected template name

Example output would look like:

Available templates:
1. template-storage-cache-data.yml
2. template-storage-cache.yml
3. template-storage-data.yml
4. template-storage.yml

Enter template number: 

Copy

Insert at cursor
text
The user can then just enter a number (like "2") instead of typing the full template name.

> Awesome! But... I was still new to the way it was doing the prompting, so I had to follow up. I had a general idea of where the new function should be called so I selected some code.

> How do I update selected code to use the new select_template function?

Looking at the highlighted code from your open file, you can update it like this:

    # Handle template selection and parameter configuration
    if not local_config:
        templates = config_manager.discover_templates()
        template_file = config_manager.select_template(templates)

Copy

Insert at cursor
python
This replaces the original click.prompt() with our new select_template() method. The functionality remains the same, but now provides a numbered list interface instead of requiring the user to type the full template name.

The change is minimal since we're just replacing the template selection mechanism while keeping the rest of the logic intact. The template_file variable will still contain the selected template name, just like before, so no other changes are needed in the surrounding code.

In the end I was able to create the script in just over one weekend. I probably wrote 50% of the code, but did 10% of the work. Q started me off with a 90% finished product with wonderful structure, libraries, etc. (Don't forget, the final 10% of a project always takes the longest!) It would have taken me weeks to start from scratch. Even with novice experience of developing in Python and Q's start with libraries I wasn't familiar with, I was able to start coding and making changes on my own within an hour.
