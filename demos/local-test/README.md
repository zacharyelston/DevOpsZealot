# DevOpsZealot Local Test with Transcribe-Demo

This directory contains configuration and scripts for testing DevOpsZealot locally using Docker with the transcribe-demo repository.

## Setup

1. Create a `.env` file based on `.env.example` with your API keys:
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file to add your OpenAI API key, Anthropic API key, and/or GitHub token.

2. Set logging level if desired in your `.env` file:
   ```bash
   # Debug level logging
   LOG_LEVEL=DEBUG
   ```

## Running the Demo

Run the local test with the transcribe-demo repository:

```bash
./run-local-test.sh -d
```

This will:
1. Build a Docker image for DevOpsZealot
2. Mount the transcribe-demo repository
3. Run the DevOpsZealot container with the context file
4. Modify the transcribe-demo repository based on the requirements in the context file

## Test Configuration

The test uses the following files:

- `context.json`: Defines the task for DevOpsZealot to perform
- `.env`: Contains API keys and configuration options
- `run-local-test.sh`: Script to run the test

## Transcribe-Demo Repository

The transcribe-demo repository (`/Users/zacelston/AlZacAI/transcribe-demo`) contains:

- Shell scripts for transcribing video to text using Whisper
- Configuration files for customizing the transcription process
- Utilities for audio extraction and processing

## Testing With Other Repositories

To test with a different repository:

```bash
./run-local-test.sh -r /path/to/your/repository
```

You can also customize the context file:

```bash
./run-local-test.sh -r /path/to/your/repository -c /path/to/custom/context.json
```

## Development and Testing Mode

For testing and development purposes:

```bash
# In your .env file
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
```

This provides more detailed logs during execution.
