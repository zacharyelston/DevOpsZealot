#!/bin/bash
#
# whisper_transcribe.sh
#
# Simple script to extract audio from an MP4 file and transcribe it using Whisper CLI
# Dependencies: ffmpeg, Whisper CLI
#
set -e

# Function to print colored messages
print_message() {
  local color=$1
  local message=$2
  
  case "$color" in
    "red") echo -e "\033[0;31m$message\033[0m" ;;
    "green") echo -e "\033[0;32m$message\033[0m" ;;
    "yellow") echo -e "\033[0;33m$message\033[0m" ;;
    "blue") echo -e "\033[0;34m$message\033[0m" ;;
    *) echo "$message" ;;
  esac
}

# Function to check if a command exists
check_command() {
  local cmd=$1
  local package=$2
  
  if ! command -v "$cmd" &>/dev/null; then
    print_message "red" "Error: '$cmd' not found."
    if [ -n "$package" ]; then
      print_message "yellow" "Please install it using: $package"
    fi
    return 1
  fi
  
  return 0
}

# Display usage information
usage() {
  print_message "blue" "Whisper MP4 Transcription Tool"
  echo
  echo "Usage: $0 <input_mp4_file> [output_dir] [whisper_model]"
  echo "Environment variables:"
  echo "  WHISPER_CLI_PATH : Optional. Set path to whisper CLI executable (default: whisper)"
  echo
  echo "Arguments:"
  echo "  input_mp4_file  : Path to MP4 video file to transcribe"
  echo "  output_dir      : Optional. Directory to save outputs (default: ./output)"
  echo "  whisper_model   : Optional. Whisper model to use (default: base)"
  echo
  echo "Examples:"
  echo "  $0 lecture.mp4"
  echo "  $0 interview.mp4 ./transcripts medium"
  echo
  echo "Dependencies:"
  echo "  - ffmpeg (for audio extraction)"
  echo "  - Whisper CLI (for transcription)"
  echo "      Install with: pip install -U openai-whisper setuptools-rust"
  exit 1
}

# Main function
main() {
  # Process arguments
  if [ $# -lt 1 ]; then
    usage
  fi
  
  local input_file="$1"
  local output_dir="${2:-./output}"
  local whisper_model="${3:-base}"
  
  # Check if input file exists
  if [ ! -f "$input_file" ]; then
    print_message "red" "Error: Input file not found: $input_file"
    exit 1
  fi
  
  # Check dependencies
  print_message "blue" "Checking dependencies..."
  check_command "ffmpeg" "brew install ffmpeg" || exit 1
  
  # Define whisper CLI path
  WHISPER_CLI_PATH="${WHISPER_CLI_PATH:-whisper}"
  
  # Check if Whisper CLI exists in PATH or at custom location
  if ! command -v "$WHISPER_CLI_PATH" &>/dev/null; then
    print_message "yellow" "Whisper CLI not found at: $WHISPER_CLI_PATH"
    print_message "yellow" "Installation instructions:"
    print_message "yellow" "  1. pip install -U openai-whisper"
    print_message "yellow" "  2. pip install setuptools-rust"
    print_message "yellow" "  3. Or set WHISPER_CLI_PATH to point to your Whisper executable"
    exit 1
  fi
  
  print_message "green" "Found Whisper CLI at: $(command -v "$WHISPER_CLI_PATH")"
  
  # Create output directory if it doesn't exist
  if [ ! -d "$output_dir" ]; then
    mkdir -p "$output_dir"
    print_message "green" "Created output directory: $output_dir"
  fi
  
  # Get base filename without extension
  local basename=$(basename "$input_file" .mp4)
  local audio_file="$output_dir/${basename}.wav"
  local transcript_file="$output_dir/${basename}.txt"
  
  # Extract audio using ffmpeg
  print_message "blue" "Extracting audio from $input_file..."
  ffmpeg -i "$input_file" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$audio_file" -y
  
  # Check if audio extraction was successful
  if [ ! -f "$audio_file" ]; then
    print_message "red" "Error: Failed to extract audio."
    exit 1
  fi
  print_message "green" "Audio extracted successfully: $audio_file"
  
  # Transcribe using Whisper CLI
  print_message "blue" "Transcribing audio with Whisper CLI (model: $whisper_model)..."
  "$WHISPER_CLI_PATH" "$audio_file" --model "$whisper_model" --output_dir "$output_dir"
  
  # Check if transcription was successful
  if [ -f "$output_dir/${basename}.txt" ]; then
    print_message "green" "Transcription completed successfully!"
    print_message "green" "Transcript saved to: $output_dir/${basename}.txt"
  else
    print_message "red" "Error: Failed to generate transcript."
    exit 1
  fi
}

# Run the main function
main "$@"
