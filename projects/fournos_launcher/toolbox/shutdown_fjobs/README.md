# FournosJob Shutdown Toolbox

This toolbox provides graceful shutdown functionality for FournosJobs by setting `spec.shutdown=Stop`.

## Features

- **Graceful Shutdown**: Uses `spec.shutdown=Stop` for clean job termination
- **Flexible Targeting**: Shutdown jobs by CI label, specific job name, or all jobs
- **Auto-detection**: Automatically generates CI labels from environment variables
- **Safety Checks**: Validation and confirmation for dangerous operations
- **Status Capture**: Saves job status after shutdown for debugging

## Usage

### Basic Usage (Auto-detect CI label)

```bash
# Shutdown jobs for current CI run (uses PULL_NUMBER and BUILD_ID from env)
./main.py
```

### Advanced Usage

```bash
# Shutdown jobs for specific CI run
./main.py --ci-label pr123_b456

# Shutdown specific job
./main.py --job-name forge-llm-d-20241203-143022

# Shutdown ALL jobs in namespace (use with caution!)
./main.py --all-jobs

# Use different namespace
./main.py --namespace my-fournos-jobs
```

## How It Works

1. **Target Selection**: Identifies which FournosJobs to shutdown based on provided criteria
2. **Validation**: Ensures valid inputs and confirms dangerous operations
3. **Graceful Shutdown**: Sets `spec.shutdown=Stop` for each target job
4. **Status Capture**: Saves final job status to artifacts directory for review

## Signal Handler Integration

The FOURNOS launcher automatically sets up signal handlers that call this shutdown functionality when the process is interrupted:

- **SIGINT (Ctrl+C)**: Triggers graceful shutdown of current CI run's jobs
- **SIGTERM**: Triggers graceful shutdown of current CI run's jobs

## Environment Variables

- `PULL_NUMBER`: Used to generate CI label (format: `pr{PULL_NUMBER}`)
- `BUILD_ID`: Combined with PULL_NUMBER (format: `pr{PULL_NUMBER}_b{BUILD_ID}`)

## Output

The toolbox creates artifacts in the `artifacts/` directory:
- `{job-name}-shutdown-status.yaml`: Final status of each shutdown job

## Safety Features

- **Input validation**: Prevents invalid parameter combinations
- **Confirmation logging**: Shows which jobs will be shutdown before proceeding
- **Error handling**: Continues shutdown process even if individual jobs fail
- **Status reporting**: Provides summary of successful vs failed shutdowns

## Comparison: shutdown vs aborted

- **`spec.shutdown=Stop`**: Graceful shutdown - allows jobs to clean up properly
- **`spec.aborted=true`**: Immediate cancellation - forces jobs to stop abruptly

This toolbox uses the graceful shutdown approach for better resource cleanup.
