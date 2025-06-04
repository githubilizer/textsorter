# Text Segment Sorter

A dark mode Python application that helps you process text files containing segmented data. The app uses Ollama to analyze text segments and separate them into more organized segments.

## Features

- Dark mode UI for comfortable viewing
- Simple file selection interface for .txt and .vhd files
- Direct loading of default file with a single click
- Model selection from multiple Ollama models
- Interactive segment-by-segment processing with live progress display
- Visual decision-making for determining if segments are related
- Auto-processing option with AI-assisted decisions
- Intelligent content processing with customizable options:
  - Keep same-topic content together
  - Preserve tagged content groups
- Creates a new file with the processed content
- Button to open the processed file

## Requirements

- Python 3.6+
- Ollama installed with at least one of the supported models
- Required Python packages (install with pip):
  - customtkinter
  - ollama
  - requests

## Installation

1. Create a virtual environment:
   ```
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   - On Linux/Mac:
     ```
     source venv/bin/activate
     ```
   - On Windows:
     ```
     venv\Scripts\activate
     ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Make sure Ollama is installed and at least one model is available:
   ```
   ollama pull qwen3:0.6b
   ```

## Usage

1. Run the application:
   ```
   python text_sorter.py
   ```

2. Select a model from the dropdown menu (default is qwen3:0.6b)

3. Configure processing options:
   - **Keep same topic content**: When checked, the app will suggest keeping content discussing the same topic or news story together
   - **Preserve tagged groups**: When checked, the app will keep all related tagged content together
   - **Auto-process**: When checked, the app will automatically process all segments using AI without requiring manual confirmation

4. Either:
   - Click the "Select File" button to browse for a .txt or .vhd file, OR
   - Click the "Load Default File" button to directly load `/home/j/Desktop/joined_sorted.vhd`

5. Click the "Start Processing" button to begin segment analysis.

6. For each segment:
   - Review the current segment in the "Current Segment" tab
   - Preview the next segment in the "Next Segment" tab
   - Decide if they are about the same topic or different topics:
     - Click "Same Topic (Keep Together)" to combine the segments
     - Click "Different Topic (Separate)" to keep them as separate segments
   - The progress indicator will show which segment is currently being processed

7. Once all segments are processed, click the "Open Result" button to view the processed file.

## Interactive Processing

The application now processes segments one at a time, allowing you to:

1. View the current segment and the next segment side by side
2. Make informed decisions about whether segments are related
3. See your progress through the file in real-time
4. Enable auto-processing to let the AI make decisions automatically

Tagged lines (like timestamps, URLs, etc.) are highlighted in yellow for better visibility.

## Default File

The application includes a dedicated button to directly load the file at `/home/j/Desktop/joined_sorted.vhd`. This provides a convenient way to quickly load a frequently used file without having to navigate through the file browser each time.

## Supported Models

The application supports various models, including:
- Various qwen models (0.6b to 32b)
- deepseek-r1 models
- llama models
- phi models
- gemma models
- and more

If you have additional models installed in Ollama, you may need to update the model list in the code.

## File Format

The application expects files with segments formatted as:

```
"Title:SomeWord"
Content line 1
Content line 2
...
"Title:AnotherWord"
More content
...
```

The app will analyze each segment and allow you to decide whether to keep consecutive segments together or separate them.

### Tagged Content Recognition

The application recognizes and highlights these special content tags (these lines are also ignored when making segmentation decisions):

- Lines starting with `--` (media references)
- URLs starting with `http` or `https`
- Lines starting with `Timestamp:`
- Lines starting with `Map view:`
- Lines starting with `Source:`
- Lines starting with `@` (mentions)
- Comment tags starting with two letters and a dash (case insensitive):
  - `cc-` or `CC-`
  - `mm-` or `MM-`
  - `jj-` or `JJ-`
  - and other similar prefixes

## Note

This application requires an active Ollama server running locally with at least one of the supported models available. 