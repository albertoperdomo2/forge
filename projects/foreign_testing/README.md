# Foreign Testing Project

The Foreign Testing project enables testing of external GitHub
repositories within the **FORGE** test harness framework. This allows
you to integrate and test projects from other repositories as if they
were native FORGE projects.

## Overview

Foreign Testing extends FORGE's capabilities to:

- **Clone External Repositories**: Fetch code from any GitHub repository during CI
- **Import External Projects**: Copy specific project directories into FORGE's project structure
- **Run Foreign Tests**: Execute tests from external repositories using FOURNOS CI infrastructure
- **Maintain Isolation**: Keep foreign code separate while enabling FORGE integration

This enables testing scenarios where you need to validate external
projects, integrate third-party tools, or run tests against specific
commit SHAs from other repositories.

## How It Works

1. **Configuration**: Define foreign repository mappings in `config.yaml`
2. **Preparation**: Clone the external repository and copy specified project directories
3. **Execution**: Run tests using FOURNOS CI infrastructure with the foreign projects integrated

## Configuration

Configure foreign repositories in your project's `config.yaml`:

```yaml
foreign_testing:
  my_external_repo:
    repository:
      owner: "external-org"
      name: "external-repo"
    project_mappings:
      # Map external paths to FORGE project names
      "external/project/path": "imported_project_name"
      "another/path": "another_project"
```

## Environment Variables

Set these environment variables to control the foreign testing behavior:

- **`PSAP_FORGE_FOREIGN_TESTING`**: Points to the config section (e.g., `"my_external_repo"`)
- **`REPO_OWNER`**: GitHub repository owner (automatically set in CI)
- **`REPO_NAME`**: GitHub repository name (automatically set in CI)
- **`PULL_PULL_SHA`**: Specific commit SHA to fetch and test

## Quick Start

### 1. Configure Foreign Repository

Create or update `config.yaml`:

```yaml
foreign_testing:
  openshift-psap/fournos:
    project_mappings:
      "benchmarks/performance": "llm_performance"
      "tests/integration": "llm_integration"
```

### 2. Set Environment Variables

```bash
export PSAP_FORGE_FOREIGN_TESTING="openshift-psap/fournos"
export REPO_OWNER="openshift-psap"
export REPO_NAME="fournos"
export PULL_PULL_SHA="abc123def456789"
```

### 3. Run Foreign Testing

```bash
# Prepare: Clone and import foreign projects
./run_ci foreign_testing ci submit

# This will:
# 1. Clone the specified repository
# 2. Fetch the specific commit SHA
# 3. Copy configured project directories to FORGE
# 4. Launch FOURNOS CI to run the tests
```

## Project Structure

```
foreign_testing/
├── orchestration/
│   ├── ci.py                    # Main CI script
│   ├── foreign_testing.py       # Core foreign testing logic
│   └── config.yaml              # Project configuration
└── README.md                    # This documentation
```

## Commands

### Submit Command

The main command for foreign testing:

```bash
./run_ci foreign_testing ci submit
```

This command:
1. **Validates** that `PSAP_FORGE_FOREIGN_TESTING` is set
2. **Clones** the specified external repository to `/tmp`
3. **Fetches** the specific commit SHA
4. **Copies** configured project directories to `$FORGE_HOME/projects`
5. **Submits** a FOURNOS job to execute the foreign tests

## Integration Flow

1. **External Repository**: Contains the projects you want to test
   ```
   external-repo/
   ├── project-a/           # External project to test
   └── project-b/           # Another external project
   ```

2. **FORGE Configuration**: Maps external paths to FORGE project names
   ```yaml
   foreign_testing:
     external_tests:
       project_mappings:
         "project_a": "local/path/to/project_a"
         "project_b": "local/path/to/project_b"
   ```

3. **Result**: External projects become available as FORGE projects
   ```
   $FORGE_HOME/projects/
   ├── project_a/  # Copied from external-repo/project-a/
   ├── project_b/  # Copied from external-repo/project-b/
   └── foreign_testing/     # This project
   ```

## Configuration Reference

### Repository Configuration

```yaml
foreign_testing:
  config_name:                    # Identifier for this foreign repo config
    project_mappings:             # Map external paths to FORGE projects
      "external/path": "forge_project_name"
      "another/path": "another_forge_project"
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PSAP_FORGE_FOREIGN_TESTING` | Points to config section | `"my_repo_config"` |
| `REPO_OWNER` | GitHub repository owner | `"openshift-psap"` |
| `REPO_NAME` | GitHub repository name | `"llm-benchmarks"` |
| `PULL_PULL_SHA` | Specific commit SHA to fetch | `"abc123def456"` |

## Error Handling

The foreign testing system validates:

- ✅ **Environment Variables**: All required variables are set
- ✅ **Configuration**: Foreign testing config exists and is valid
- ✅ **Repository Access**: Can clone the specified repository
- ✅ **Project Paths**: Configured paths exist in the external repository
- ✅ **Permissions**: Can write to FORGE projects directory

Common error scenarios:

```bash
# Missing environment variable
❌ ERROR: PSAP_FORGE_FOREIGN_TESTING must be set

# Invalid configuration
❌ ERROR: PSAP_FORGE_FOREIGN_TESTING must point to `foreign_testing.config_name` field

# Missing external project
❌ ERROR: Foreign project source not found: /tmp/repo/missing/path
```
