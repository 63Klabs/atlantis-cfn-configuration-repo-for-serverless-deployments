# CLI Script CHANGELOG

To update your local cli scripts from GitHub repository:

```bash
./cli/update.py
```

- The scripts are still in BETA and features are still being added and tested.
- There may be several versions with small fixes released every few days until reaching v0.1.0.
- After v0.1.0 all v0.0.x version change information will be removed from the Changelog.
- Refer to [TODO](../TODO.md) for upcoming BETA fixes and features.
- Report any issues not covered in TODO via the [Issues page in the GitHub repository](https://github.com/63Klabs/atlantis-cfn-configuration-repo-for-serverless-deployments/issues)

## v0.0.5 (2025-06-07)

Mostly stable. Still in Beta.

- Fixed issue where update.py was not pulling latest changes from organization's SAM config repository.
- Fixed issue where CodeCommit and Repository tags being erroneously added to the tag prompts for the user even though they are automatically managed.
