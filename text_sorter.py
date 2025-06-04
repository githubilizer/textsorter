#!/usr/bin/env python3
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import customtkinter as ctk
import ollama
import subprocess
import json

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Default file path
DEFAULT_FILE_PATH = "/home/j/Desktop/joined.vhd"

# List of available models (alphabetically sorted)
AVAILABLE_MODELS = [
    "deepcoder:1.5b",
    "deepseek-r1:1.5b",
    "deepseek-r1:8b",
    "deepseek-r1:latest",
    "gemma3:1b",
    "gemma3:latest",
    "llama3.1:8b",
    "llama3.1:latest",
    "llama3.2:3b",
    "llama3.2:latest",
    "mistral-small3.1:latest",
    "openchat:7b-v3.5-0106",
    "phi3.5:latest",
    "phi4-mini-reasoning:latest",
    "phi4-mini:latest",
    "phi4:latest",
    "qwen2.5-coder:0.5b",
    "qwen2.5-coder:1.5b",
    "qwen2.5vl:3b",
    "qwen3:0.6b",
    "qwen3:1.7b",
    "qwen3:14b",
    "qwen3:30b",
    "qwen3:32b",
    "qwen3:4b",
    "qwen3:8b",
    "qwen3:latest",
    "smollm2:latest"
]

# Tag prefixes that should be ignored when making segment decisions
TAG_PREFIXES = [
    '--', 
    'http', 
    'Timestamp:', 
    'Map view:', 
    'Source:', 
    'jj-', 'JJ-', 
    'cc-', 'CC-', 
    'mm-', 'MM-', 
    '@'
]

# Regular expression for tag detection
TAG_PATTERN = re.compile(r'^(--|https?://|Timestamp:|Map view:|Source:|\w\w-|@)')

class ContextMenuText(scrolledtext.ScrolledText):
    """Text widget with a context menu"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_context_menu()
        
    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_text)
        self.context_menu.add_command(label="Paste", command=self.paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self.select_all_text)
        self.context_menu.add_command(label="Copy All", command=self.copy_all_text)
        
        # Bind right-click to show context menu
        self.bind("<Button-3>", self.show_context_menu)
        
    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)
        
    def copy_text(self):
        self.event_generate("<<Copy>>")
        
    def paste_text(self):
        self.event_generate("<<Paste>>")
        
    def select_all_text(self):
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, "1.0")
        self.see(tk.INSERT)
        
    def copy_all_text(self):
        self.select_all_text()
        self.copy_text()

class AutoScrollText(ContextMenuText):
    """Text widget with context menu and autoscroll toggle"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autoscroll = True
        
        # Add autoscroll toggle to context menu
        self.context_menu.add_separator()
        self.autoscroll_var = tk.BooleanVar(value=True)
        self.context_menu.add_checkbutton(
            label="Autoscroll", 
            variable=self.autoscroll_var,
            command=self.toggle_autoscroll
        )
        
    def toggle_autoscroll(self):
        self.autoscroll = self.autoscroll_var.get()
        
    def see_end_if_autoscroll(self):
        if self.autoscroll:
            self.see(tk.END)

class TextSorterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Text Segment Sorter")
        self.geometry("900x700")  # Increased size for progress display
        self.minsize(800, 600)
        
        # Initialize variables
        self.input_file_path = ""
        self.output_file_path = ""
        self.processed = False
        self.selected_model = ctk.StringVar(value="qwen3:0.6b")  # Default model
        self.auto_process = ctk.BooleanVar(value=True)  # Auto process by default
        
        # Segment processing variables
        self.segments = []
        self.current_segment_index = 0
        self.processed_segments = []
        self.processing_active = False
        
        # Topic counter variables
        self.baseline_topic_count = 0
        self.current_topic_count = 0
        self.different_topics_count = 0
        self.same_topics_count = 0
        
        # Create UI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # App title
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="Text Segment Sorter", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(0, 20))
        
        # Top section frame (model selection, options)
        self.top_section = ctk.CTkFrame(self.main_frame)
        self.top_section.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Model selection frame
        self.model_frame = ctk.CTkFrame(self.top_section)
        self.model_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.model_label = ctk.CTkLabel(
            self.model_frame,
            text="Select Model:",
            anchor="w"
        )
        self.model_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.model_dropdown = ctk.CTkOptionMenu(
            self.model_frame,
            values=AVAILABLE_MODELS,
            variable=self.selected_model,
            width=200
        )
        self.model_dropdown.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Advanced options frame
        self.options_frame = ctk.CTkFrame(self.top_section)
        self.options_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.same_topic_var = ctk.BooleanVar(value=True)
        self.same_topic_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Keep same topic content",
            variable=self.same_topic_var
        )
        self.same_topic_checkbox.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.preserve_tags_var = ctk.BooleanVar(value=True)
        self.preserve_tags_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Preserve tagged groups",
            variable=self.preserve_tags_var
        )
        self.preserve_tags_checkbox.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.auto_process_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Auto-process (no confirmation)",
            variable=self.auto_process,
            command=self.toggle_decision_buttons_visibility
        )
        self.auto_process_checkbox.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # File selection buttons frame
        self.file_buttons_frame = ctk.CTkFrame(self.main_frame)
        self.file_buttons_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Select file button
        self.select_button = ctk.CTkButton(
            self.file_buttons_frame,
            text="Select File",
            command=self.browse_file
        )
        self.select_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Load default file button
        self.default_file_button = ctk.CTkButton(
            self.file_buttons_frame,
            text="Load Default File",
            command=self.load_default_file,
            fg_color="#4d8a3d",  # Green color to distinguish from other buttons
            hover_color="#3b6b2f"
        )
        self.default_file_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Start processing button
        self.process_button = ctk.CTkButton(
            self.file_buttons_frame, 
            text="Start Processing",
            command=self.start_processing,
            state="disabled"
        )
        self.process_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Open result button
        self.open_button = ctk.CTkButton(
            self.file_buttons_frame, 
            text="Open Result",
            command=self.open_result_file,
            state="disabled"
        )
        self.open_button.pack(side=tk.RIGHT, padx=5, pady=10)
        
        # Progress information frame
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Progress: Not started",
            anchor="w",
            font=ctk.CTkFont(size=14)
        )
        self.progress_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # File info
        self.file_info = ctk.CTkLabel(
            self.progress_frame, 
            text="No file selected",
            anchor="e"
        )
        self.file_info.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Topic counter frame
        self.topic_counter_frame = ctk.CTkFrame(self.main_frame)
        self.topic_counter_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Topic counters
        self.baseline_label = ctk.CTkLabel(
            self.topic_counter_frame,
            text="Original Segments: 0",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.baseline_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.current_topics_label = ctk.CTkLabel(
            self.topic_counter_frame,
            text="Final Segments: 0",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.current_topics_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.different_topics_label = ctk.CTkLabel(
            self.topic_counter_frame,
            text="Kept Separate: 0",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffcc00"  # Highlighted color
        )
        self.different_topics_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.merged_topics_label = ctk.CTkLabel(
            self.topic_counter_frame,
            text="Merged: 0",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4d8a3d"  # Green color
        )
        self.merged_topics_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Log display
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        # Create a header frame for log title and autoscroll toggle
        self.log_header_frame = ctk.CTkFrame(self.log_frame)
        self.log_header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.log_title = ctk.CTkLabel(
            self.log_header_frame,
            text="Processing Log",
            anchor="w",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.log_title.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=5)
        
        # Add autoscroll toggle switch
        self.autoscroll_var = ctk.BooleanVar(value=True)
        self.autoscroll_label = ctk.CTkLabel(
            self.log_header_frame,
            text="Autoscroll:",
            anchor="e"
        )
        self.autoscroll_label.pack(side=tk.RIGHT, padx=(10, 5), pady=5)
        
        self.autoscroll_switch = ctk.CTkSwitch(
            self.log_header_frame,
            text="",
            variable=self.autoscroll_var,
            command=self.toggle_autoscroll,
            onvalue=True,
            offvalue=False
        )
        self.autoscroll_switch.pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.log_text = AutoScrollText(
            self.log_frame,
            wrap=tk.WORD,
            height=15,
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure log text highlighting with different colors
        self.log_text.tag_configure("highlight", foreground="#ffcc00")  # Yellow for important messages
        self.log_text.tag_configure("error", foreground="#ff4444")     # Red for errors
        self.log_text.tag_configure("success", foreground="#44ff44")   # Green for success
        self.log_text.tag_configure("info", foreground="#44aaff")      # Blue for info
        self.log_text.tag_configure("warning", foreground="#ffaa44")   # Orange for warnings
        
        # Add initial log message
        self.after(100, lambda: self.add_to_log("Application started. Select a file to begin processing.", "info"))
        
        # Segment decision buttons
        self.decision_frame = ctk.CTkFrame(self.main_frame)
        # Only pack if auto-process is disabled
        if not self.auto_process.get():
            self.decision_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Add explanation label for clarity
        self.explanation_label = ctk.CTkLabel(
            self.decision_frame,
            text="Do these two segments (with different titles) belong to the same topic or story?",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.explanation_label.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.same_topic_button = ctk.CTkButton(
            self.decision_frame,
            text="Yes - Group Together",
            command=self.mark_same_topic,
            fg_color="#4d8a3d",  # Green
            hover_color="#3b6b2f",
            state="disabled"
        )
        self.same_topic_button.pack(side=tk.LEFT, padx=10, pady=10, expand=True, fill=tk.X)
        
        self.different_topic_button = ctk.CTkButton(
            self.decision_frame,
            text="No - Keep Separate",
            command=self.mark_different_topic,
            fg_color="#a83232",  # Red
            hover_color="#7a2525",
            state="disabled"
        )
        self.different_topic_button.pack(side=tk.RIGHT, padx=10, pady=10, expand=True, fill=tk.X)
    
    def browse_file(self, event=None):
        file_path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[("Text files", "*.txt"), ("VHD files", "*.vhd"), ("All files", "*.*")]
        )
        
        if file_path:
            self.input_file_path = file_path
            self.update_file_info()
            self.process_button.configure(state="normal")
            filename = os.path.basename(file_path)
            self.add_to_log(f"Selected file: {filename}")
    
    def load_default_file(self):
        """Load the default file path"""
        if os.path.exists(DEFAULT_FILE_PATH):
            self.input_file_path = DEFAULT_FILE_PATH
            self.update_file_info()
            self.process_button.configure(state="normal")
            self.progress_label.configure(text=f"Status: Loaded default file")
            filename = os.path.basename(DEFAULT_FILE_PATH)
            self.add_to_log(f"Loaded default file: {filename}", "highlight")
            
            # Automatically start processing
            self.after(100, self.start_processing)
        else:
            # Try to load joined.vhd instead if default file not found
            alternate_path = os.path.join(os.path.dirname(DEFAULT_FILE_PATH), "joined.vhd")
            if os.path.exists(alternate_path):
                self.input_file_path = alternate_path
                self.update_file_info()
                self.process_button.configure(state="normal")
                self.progress_label.configure(text=f"Status: Loaded alternate file")
                filename = os.path.basename(alternate_path)
                self.add_to_log(f"Default file not found. Loaded alternate file: {filename}", "warning")
                
                # Automatically start processing
                self.after(100, self.start_processing)
            else:
                messagebox.showerror("Error", f"Default file not found at: {DEFAULT_FILE_PATH}")
                self.add_to_log(f"Error: Default file not found at: {DEFAULT_FILE_PATH}", "error")
    
    def update_file_info(self):
        filename = os.path.basename(self.input_file_path)
        self.file_info.configure(text=f"Selected: {filename}")
    
    def start_processing(self):
        if not self.input_file_path:
            messagebox.showerror("Error", "No file selected")
            return
        
        if self.processing_active:
            messagebox.showinfo("Processing Active", "Processing is already in progress")
            return
        
        # Get the selected model
        model = self.selected_model.get()
        
        # Log start of processing
        self.add_to_log(f"Started processing with model: {model}", "highlight")
        
        # Disable start button during processing
        self.process_button.configure(state="disabled")
        self.progress_label.configure(text=f"Status: Preparing file...")
        
        # Enable decision buttons only if manual processing is enabled
        if not self.auto_process.get():
            self.same_topic_button.configure(state="normal")
            self.different_topic_button.configure(state="normal")
        
        # Run initial processing in a separate thread to prevent UI freezing
        threading.Thread(
            target=self._prepare_segments,
            args=(model,),
            daemon=True
        ).start()
    
    def _prepare_segments(self, model):
        try:
            # Set processing flag
            self.processing_active = True
            
            # Get file base name and create output path
            input_basename = os.path.basename(self.input_file_path)
            file_name, file_ext = os.path.splitext(input_basename)
            
            # Add timestamp to the output filename
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file_path = os.path.join(
                os.path.dirname(self.input_file_path),
                f"{file_name}_sorted_{timestamp}{file_ext}"
            )
            
            # Read input file content
            with open(self.input_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            self.add_to_log(f"Reading file content...", "info")
            
            # Store the original content for exact formatting preservation
            self.original_content = content
            
            # Improved segment pattern to better identify proper title segments
            # Look for "Title:" pattern at the beginning of a line or after a newline
            segment_pattern = r'((?:^|\n)\s*"Title:[^"]+")(.+?)(?=(?:^|\n)\s*"Title:|$)'
            
            # Find positions of each segment to preserve exact text
            matches = list(re.finditer(segment_pattern, content, re.DOTALL | re.MULTILINE))
            
            # Extract segments with their exact original text
            self.segments = []
            for match in matches:
                title = match.group(1).strip()
                segment_content = match.group(2)
                # Get the exact original text for this segment
                original_text = match.group(0)
                # Store the tuple (title, content, original_text)
                self.segments.append((title, segment_content, original_text))
            
            self.current_segment_index = 0
            self.processed_segments = []
            
            # Set initial counters
            self.baseline_topic_count = len(self.segments)
            self.current_topic_count = 0  # Start with 0, will increment as we process
            self.different_topics_count = 0
            self.same_topics_count = 0
            
            # Extract all metadata (timestamps, URLs, images, comments) by segments
            self.segment_metadata = []
            for title, content, original_text in self.segments:
                metadata = []
                for line in original_text.splitlines():
                    # Check if line is metadata
                    if (line.startswith('--') or 
                        line.startswith('http') or 
                        line.startswith('Timestamp:') or 
                        line.startswith('Map view:') or 
                        line.startswith('Source:') or 
                        line.startswith('cc-') or 
                        line.startswith('@') or
                        re.match(r'^[A-Za-z]{2}-', line)):
                        metadata.append(line)
                self.segment_metadata.append(metadata)
            
            # Update counter displays
            self.update_topic_counters()
            
            # Update UI with segment count
            self.progress_label.configure(
                text=f"Status: Found {len(self.segments)} segments. Starting analysis..."
            )
            self.add_to_log(f"Found {len(self.segments)} segments in the file", "highlight")
            
            # Start processing the first segment
            if self.segments:
                # Use after with delay to prevent recursion
                self.after(100, lambda: self._process_next_segment(model))
            else:
                # No segments found
                messagebox.showinfo("No Segments", "No segments found in the file")
                self.progress_label.configure(text="Status: No segments found")
                self.process_button.configure(state="normal")
                self.add_to_log("Error: No segments found in the file", "error")
                self.processing_active = False
                
        except Exception as e:
            messagebox.showerror("Error", f"Preparation failed: {str(e)}")
            self.progress_label.configure(text="Status: Error in preparation")
            self.process_button.configure(state="normal")
            self.add_to_log(f"Error during preparation: {str(e)}", "error")
            self.processing_active = False
    
    def _process_next_segment(self, model):
        try:
            if self.current_segment_index >= len(self.segments):
                # All segments processed, save the file
                self._save_processed_file()
                return
            
            # Get current segment
            title, content, original_text = self.segments[self.current_segment_index]
            
            # Update the log first (direct call)
            self.add_to_log(f"Processing: Segment #{self.current_segment_index + 1}/{len(self.segments)} - {title.strip()}", "info")
            
            # Update the progress display
            progress_text = f"Processing segment {self.current_segment_index + 1} of {len(self.segments)}"
            self.progress_label.configure(text=progress_text)
            
            # If auto-process is enabled, use AI to decide
            if self.auto_process.get():
                # Get AI analysis
                self.add_to_log(f"Analyzing with {model}...", "info")
                
                ai_result, reasoning, raw_response, contains_multiple_stories, number_of_stories, sub_topics, split_points = self.analyze_segment_with_ollama(
                    title, 
                    content, 
                    model, 
                    self.same_topic_var.get()
                )
                
                # Add debug log entry with raw response
                self.add_to_log(f"Raw AI response: {raw_response}", "info")
                
                # Check if segment contains multiple stories
                if contains_multiple_stories and number_of_stories > 1:
                    self.add_to_log(f"AI found {number_of_stories} distinct stories within segment #{self.current_segment_index + 1}!", "highlight")
                    
                    # Log topic titles if available
                    if sub_topics:
                        topic_str = ", ".join(sub_topics)
                        self.add_to_log(f"Story topics: {topic_str}", "info")
                    
                    # Log split points if available
                    if split_points:
                        splits_str = ", ".join([str(p) for p in split_points])
                        self.add_to_log(f"Split after line/paragraph: {splits_str}", "info")
                    
                    # Split the segment
                    if self._split_segment(title, content, original_text, split_points, sub_topics):
                        return
                    # If splitting failed, fall through to normal processing
                
                # Process based on AI result for comparison with next segment
                try:
                    # Check if AI suggests different topics
                    if ai_result:
                        self.add_to_log(f"AI decision: Different topics", "highlight")
                        self.add_to_log(f"Reasoning: {reasoning}", "info")
                        # Use after with a delay to prevent recursion
                        self.after(100, self.mark_different_topic)
                    else:
                        self.add_to_log(f"AI decision: Same topic", "highlight")
                        self.add_to_log(f"Reasoning: {reasoning}", "info")
                        # Use after with a delay to prevent recursion
                        self.after(100, self.mark_same_topic)
                except Exception as e:
                    # Default to same topic on error
                    self.add_to_log(f"Error parsing AI result: {e}. Defaulting to same topic.", "error")
                    # Use after with a delay to prevent recursion
                    self.after(100, self.mark_same_topic)
            
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
            self.progress_label.configure(text="Status: Error in processing")
            self.process_button.configure(state="normal")
            self.add_to_log(f"Error during processing: {str(e)}", "error")
            self.processing_active = False
    
    def _update_current_segment(self, title, content):
        """This method is no longer needed as we removed the current segment display"""
        pass

    def _update_next_segment(self, title, content):
        """This method is no longer needed as we removed the next segment display"""
        pass
    
    def mark_same_topic(self):
        # Add the current segment to processed segments
        if self.current_segment_index < len(self.segments):
            title, content, original_text = self.segments[self.current_segment_index]
            
            # Get metadata for current segment
            current_metadata = self.segment_metadata[self.current_segment_index]
            
            # Add to processed segments
            if not self.processed_segments:
                # First segment - just use the original text as is
                self.processed_segments.append(original_text)
                self.current_topic_count = 1  # Start with the first topic
                self.add_to_log(f"Added first segment #{self.current_segment_index + 1}: {title.strip()}", "success")
            else:
                # For merging, we need to combine with the previous segment
                # Ensure there's a newline between segments if needed
                if not self.processed_segments[-1].endswith('\n'):
                    self.processed_segments[-1] += '\n'
                
                # Remove the title part from the original text (just for merging)
                content_only = re.sub(
                    pattern=r'^\s*"Title:[^"]+"\s*', 
                    repl='', 
                    string=original_text, 
                    count=1, 
                    flags=re.MULTILINE
                )
                
                # Add content without the title
                content_lines = content_only.strip().splitlines()
                
                # Add the non-metadata content lines
                content_to_add = []
                for line in content_lines:
                    # Skip lines that are already in metadata
                    if not (line.startswith('--') or 
                            line.startswith('http') or 
                            line.startswith('Timestamp:') or 
                            line.startswith('Map view:') or 
                            line.startswith('Source:') or 
                            line.startswith('cc-') or 
                            line.startswith('@') or
                            re.match(r'^[A-Za-z]{2}-', line)):
                        content_to_add.append(line)
                
                # Add the content lines followed by metadata
                if content_to_add:
                    self.processed_segments[-1] += '\n' + '\n'.join(content_to_add)
                
                # Add metadata if not already present in the last segment
                for meta_line in current_metadata:
                    if meta_line not in self.processed_segments[-1]:
                        self.processed_segments[-1] += '\n' + meta_line
                
                self.same_topics_count += 1  # Count when segments are merged
                self.add_to_log(f"Merged segment #{self.current_segment_index + 1} with metadata: {title.strip()}", "success")
            
            # Update counters
            self.update_topic_counters()
            
            # Move to next segment
            self.current_segment_index += 1
            
            # Get the selected model
            model = self.selected_model.get()
            
            # Process the next segment
            if self.current_segment_index < len(self.segments):
                # Use after with a delay to prevent recursion
                self.after(100, lambda: self._process_next_segment(model))
            else:
                # All segments processed
                self._save_processed_file()
    
    def mark_different_topic(self):
        # Add the current segment as a separate segment
        if self.current_segment_index < len(self.segments):
            title, content, original_text = self.segments[self.current_segment_index]
            
            # Get metadata for current segment
            current_metadata = self.segment_metadata[self.current_segment_index]
            
            # Process the segment to ensure it has all its metadata
            # Split into lines and filter out empty lines
            segment_lines = [line for line in original_text.splitlines() if line.strip()]
            
            # Make sure all metadata is included
            for meta_line in current_metadata:
                if meta_line not in segment_lines:
                    segment_lines.append(meta_line)
            
            # Reconstruct the segment with all metadata
            processed_segment = "\n".join(segment_lines)
            
            # Add to processed segments as a separate segment with all metadata
            self.processed_segments.append(processed_segment)
            
            # Increment counters
            if self.current_segment_index == 0:
                # First segment is always a topic
                self.current_topic_count = 1
                self.add_to_log(f"Added first segment #{self.current_segment_index + 1}: {title.strip()}", "success")
            else:
                # New different topic found
                self.different_topics_count += 1
                self.current_topic_count += 1
                self.add_to_log(f"Added segment #{self.current_segment_index + 1} as separate segment: {title.strip()}", "success")
            
            self.update_topic_counters()
            
            # Move to next segment
            self.current_segment_index += 1
            
            # Get the selected model
            model = self.selected_model.get()
            
            # Process the next segment
            if self.current_segment_index < len(self.segments):
                # Use after with a delay to prevent recursion
                self.after(100, lambda: self._process_next_segment(model))
            else:
                # All segments processed
                self._save_processed_file()
    
    def _save_processed_file(self):
        try:
            # Check if we have any processed segments
            if not self.processed_segments:
                messagebox.showinfo("No Content", "No content to save.")
                self.progress_label.configure(text="Status: No content to save")
                self.process_button.configure(state="normal")
                self.processing_active = False
                return
            
            # Create the output directory if it doesn't exist
            output_dir = os.path.dirname(self.output_file_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Use the base filename without the timestamp for the output
            input_basename = os.path.basename(self.input_file_path)
            file_name, file_ext = os.path.splitext(input_basename)
            
            # Create the output path without timestamp
            self.output_file_path = os.path.join(
                os.path.dirname(self.input_file_path),
                f"{file_name}_shouldbe{file_ext}"
            )
            
            # Combine all processed segments 
            final_content = ""
            
            for i, segment in enumerate(self.processed_segments):
                # If not the first segment, ensure there's proper spacing between segments
                if i > 0:
                    # Always add two newlines between segments for consistency
                    if final_content.endswith('\n\n'):
                        pass  # Already has correct spacing
                    elif final_content.endswith('\n'):
                        final_content += '\n'
                    else:
                        final_content += '\n\n'
                
                # Clean up any empty lines at the beginning of the segment
                cleaned_segment = segment.lstrip()
                if not cleaned_segment:
                    continue  # Skip completely empty segments
                
                # Make sure segment has all the metadata it needs
                if i < len(self.segment_metadata):
                    segment_lines = cleaned_segment.splitlines()
                    for meta_line in self.segment_metadata[i]:
                        if meta_line not in segment_lines:
                            cleaned_segment += '\n' + meta_line
                
                # Add the segment (which now includes all metadata)
                final_content += cleaned_segment
            
            # Write to output file
            with open(self.output_file_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            self.processed = True
            
            # Update UI
            save_message = f"Status: Processing complete! File saved to: {os.path.basename(self.output_file_path)}"
            try:
                self.progress_label.configure(text=save_message)
                self.open_button.configure(state="normal")
                self.process_button.configure(state="normal")
                self.same_topic_button.configure(state="disabled")
                self.different_topic_button.configure(state="disabled")
            except Exception as ui_error:
                # UI may have been destroyed, continue with the function
                print(f"UI update error (non-critical): {ui_error}")
            
            # Count the actual number of title markers in the final content
            title_count = len(re.findall(r'"Title:', final_content))
            
            # Make sure our counts are accurate
            self.current_topic_count = len(self.processed_segments)
            
            # Verify the kept separate count
            processed_segments_count = len(self.processed_segments)
            expected_different_count = processed_segments_count - 1
            
            # If there's a mismatch, fix the different count
            if self.different_topics_count != expected_different_count:
                self.add_to_log(f"Adjusting different topics count from {self.different_topics_count} to {expected_different_count} to match processed segments", "warning")
                self.different_topics_count = expected_different_count
            
            # Update counters
            try:
                self.update_topic_counters()
            except Exception as ui_error:
                # UI may have been destroyed, continue with the function
                print(f"Counter update error (non-critical): {ui_error}")
            
            # Calculate topics reduction
            topics_reduction = self.baseline_topic_count - self.current_topic_count
            reduction_percentage = (topics_reduction / self.baseline_topic_count * 100) if self.baseline_topic_count > 0 else 0
            
            # Log completion
            self.add_to_log(
                f"Processing complete! Condensed {len(self.segments)} segments into {len(self.processed_segments)} groups with {title_count} titles", 
                "success"
            )
            self.add_to_log(f"Saved to: {self.output_file_path}", "info")
            
            # Add detailed summary
            if self.same_topics_count > 0:
                self.add_to_log(
                    f"Final topic count: {self.current_topic_count} (reduced from {self.baseline_topic_count} by {topics_reduction} segments, {reduction_percentage:.1f}%)",
                    "highlight"
                )
            else:
                self.add_to_log(
                    f"Final topic count: {self.current_topic_count} (no reduction from original {self.baseline_topic_count} segments)",
                    "highlight"
                )
                
            self.add_to_log(
                f"Segments kept separate: {self.different_topics_count}, Segments merged: {self.same_topics_count}",
                "highlight"
            )
            
            # Add a clear explanation of what happened
            first_segment_text = "1 first segment + "
            if self.same_topics_count == 0 and self.different_topics_count == self.baseline_topic_count - 1:
                self.add_to_log(
                    f"Summary: All segments were kept separate. No merging occurred.",
                    "highlight"
                )
            else:
                self.add_to_log(
                    f"Summary: {first_segment_text}{self.different_topics_count} separate segments + {self.same_topics_count} merged segments = {self.baseline_topic_count} total original segments",
                    "highlight"
                )
            
            # Reset processing flag
            self.processing_active = False
            
            # Show completion message in a try-except block to handle potential UI destruction
            try:
                messagebox.showinfo(
                    "Processing Complete", 
                    f"All {len(self.segments)} segments have been processed and saved to:\n{self.output_file_path}"
                )
            except Exception as dialog_error:
                print(f"Dialog error (non-critical): {dialog_error}")
                # Print to console instead
                print(f"Processing Complete: All {len(self.segments)} segments have been processed and saved to: {self.output_file_path}")
            
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            try:
                messagebox.showerror("Error", f"Saving failed: {str(e)}")
                self.progress_label.configure(text="Status: Error saving file")
                self.process_button.configure(state="normal")
                self.add_to_log(f"Error saving file: {str(e)}", "error")
            except Exception:
                # UI may have been destroyed, just print the error
                print(f"Critical error saving file: {str(e)}")
            self.processing_active = False
    
    def analyze_segment_with_ollama(self, title, content, model, keep_same_topic):
        try:
            # Define the prompt for Ollama
            prompt = f"""
            Analyze these two consecutive text segments:
            
            SEGMENT 1 (Current):
            {title}
            {content}
            
            SEGMENT 2 (Next):
            {self.segments[self.current_segment_index + 1][0] if self.current_segment_index + 1 < len(self.segments) else "None"}
            {self.segments[self.current_segment_index + 1][1] if self.current_segment_index + 1 < len(self.segments) else "No more segments"}
            
            First, analyze if SEGMENT 1 itself contains multiple distinct news stories or topics.
            If it does, identify the following:
            1. How many distinct stories or topics are in SEGMENT 1 (give a number)
            2. For each sub-topic, provide a SINGLE WORD that best describes the content (e.g., "Politics", "Military", "Economy")
            3. Identify specific line/paragraph numbers where the content should be split
            
            Then, determine if SEGMENT 1 and SEGMENT 2 are about DIFFERENT topics (not the same topic).
            
            {"Look for SIGNIFICANTLY different topics, not just different aspects of the same story or news item. If the content is discussing the same main topic or event, consider them the same topic." if keep_same_topic else ""}
            
            IMPORTANT: DO NOT consider them different topics if they're discussing different aspects of the same news story or event.
            
            IMPORTANT: Ignore all of these tag line types when making decisions - they should NOT cause a segment split:
            - Lines starting with '--' (media references)
            - URLs starting with 'http' or 'https'
            - Lines starting with 'Timestamp:'
            - Lines starting with 'Map view:'
            - Lines starting with 'Source:'
            - Lines starting with '@' (mentions)
            - Comment tags starting with two letters and a dash (e.g., "cc-", "jj-", "mm-", "CC-", "JJ-", "MM-")
            
            Format your response exactly like this:
            CONTAINS_MULTIPLE_STORIES: YES/NO
            NUMBER_OF_STORIES: [if YES, provide a number]
            SUB_TOPICS: [if YES, provide a comma-separated list of SINGLE WORDS]
            SPLIT_AFTER: [if YES, provide line/paragraph numbers where to split, e.g., "1,3,5"]
            DIFFERENT: YES/NO
            REASONING: Your explanation here
            """
            
            # Update status to show which model is being used
            self.progress_label.configure(text=f"Status: Analyzing with {model}...")
            
            # Call Ollama API with the selected model
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response['message']['content'].strip()
            
            # Default values
            is_different = False
            reasoning = "No clear reasoning provided"
            contains_multiple_stories = False
            number_of_stories = 1
            sub_topics = []
            split_points = []
            
            # Try to parse the response with more reliable pattern matching
            # Check if segment contains multiple stories
            multiple_stories_match = re.search(r'CONTAINS_MULTIPLE_STORIES:\s*(YES|NO)', response_text, re.IGNORECASE)
            if multiple_stories_match:
                contains_multiple_stories = multiple_stories_match.group(1).upper() == "YES"
            
            # Get number of stories if provided
            if contains_multiple_stories:
                number_match = re.search(r'NUMBER_OF_STORIES:\s*(\d+)', response_text, re.IGNORECASE)
                if number_match:
                    try:
                        number_of_stories = int(number_match.group(1))
                    except ValueError:
                        number_of_stories = 2  # Default to 2 if parsing fails
                
                # Get sub-topics if provided
                topics_match = re.search(r'SUB_TOPICS:\s*(.*?)(?=$|\n)', response_text, re.IGNORECASE | re.DOTALL)
                if topics_match:
                    topics_text = topics_match.group(1).strip()
                    # Parse the topics, handling various formats
                    if '[' in topics_text and ']' in topics_text:
                        # Handle array format
                        topics_text = topics_text.replace('[', '').replace(']', '')
                    
                    # Split by commas, handling quotes
                    sub_topics = []
                    for topic in re.findall(r'(?:"([^"]+)"|([^,]+))', topics_text):
                        topic_text = topic[0] if topic[0] else topic[1]
                        if topic_text and topic_text.strip():
                            # Extract just the first word if multiple words are provided
                            first_word = topic_text.strip().split()[0]
                            sub_topics.append(first_word)
                
                # Get split points if provided
                split_match = re.search(r'SPLIT_AFTER:\s*(.*?)(?=$|\n)', response_text, re.IGNORECASE | re.DOTALL)
                if split_match:
                    split_text = split_match.group(1).strip()
                    # Parse the split points, handling various formats
                    if '[' in split_text and ']' in split_text:
                        # Handle array format
                        split_text = split_text.replace('[', '').replace(']', '')
                    
                    # Try to extract numbers
                    for point in re.findall(r'\d+', split_text):
                        try:
                            split_points.append(int(point))
                        except ValueError:
                            continue
            
            # Check if segments are different topics
            different_match = re.search(r'DIFFERENT:\s*(YES|NO)', response_text, re.IGNORECASE)
            if different_match:
                is_different = different_match.group(1).upper() == "YES"
            
            # Extract reasoning if available
            reasoning_match = re.search(r'REASONING:\s*(.*?)(?=$|\n\n)', response_text, re.IGNORECASE | re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            return is_different, reasoning, response_text, contains_multiple_stories, number_of_stories, sub_topics, split_points
                
        except Exception as e:
            print(f"Ollama analysis error: {str(e)}")
            return False, f"Error occurred during analysis: {str(e)}", str(e), False, 1, [], []
    
    def open_result_file(self):
        if not self.output_file_path or not os.path.exists(self.output_file_path):
            messagebox.showerror("Error", "Output file not found")
            return
        
        try:
            # Use the appropriate command to open the file based on OS
            if os.name == 'nt':  # Windows
                os.startfile(self.output_file_path)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.run(['xdg-open', self.output_file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def toggle_decision_buttons_visibility(self):
        """Toggle visibility of the decision buttons based on auto-process setting"""
        if self.auto_process.get():
            self.decision_frame.pack_forget()
        else:
            self.decision_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

    def add_to_log(self, message, message_type="normal"):
        """Add a message to the log with timestamp and color coding"""
        import datetime
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        log_message = f"{timestamp} {message}\n"
        
        # Insert the message at the end of the log
        self.log_text.insert(tk.END, log_message)
        
        # Apply color based on message type
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if message_type == "highlight":
            self.log_text.tag_add("highlight", f"{line_count-1}.0", f"{line_count}.0")
        elif message_type == "error":
            self.log_text.tag_add("error", f"{line_count-1}.0", f"{line_count}.0")
        elif message_type == "success":
            self.log_text.tag_add("success", f"{line_count-1}.0", f"{line_count}.0")
        elif message_type == "info":
            self.log_text.tag_add("info", f"{line_count-1}.0", f"{line_count}.0")
        elif message_type == "warning":
            self.log_text.tag_add("warning", f"{line_count-1}.0", f"{line_count}.0")
        
        # Scroll to the end if autoscroll is enabled
        self.log_text.see_end_if_autoscroll()
        
        # Update the UI
        self.update()

    def toggle_autoscroll(self):
        """Toggle the autoscroll feature for the log text"""
        autoscroll_enabled = self.autoscroll_var.get()
        self.log_text.autoscroll = autoscroll_enabled
        self.log_text.autoscroll_var.set(autoscroll_enabled)
        self.add_to_log(f"Autoscroll {'enabled' if autoscroll_enabled else 'disabled'}")

    def update_topic_counters(self):
        """Update the topic counter displays"""
        self.baseline_label.configure(text=f"Original Segments: {self.baseline_topic_count}")
        self.current_topics_label.configure(text=f"Final Segments: {self.current_topic_count}")
        self.different_topics_label.configure(text=f"Kept Separate: {self.different_topics_count}")
        self.merged_topics_label.configure(text=f"Merged: {self.same_topics_count}")

    def _split_segment(self, original_title, content, original_text, split_points, sub_topics):
        """Split a segment into multiple segments based on AI analysis"""
        if not split_points or not sub_topics:
            self.add_to_log(f"Can't split segment - missing split points or topic titles", "warning")
            return False
        
        # Clean the title format from the original title
        title_format = original_title.strip()
        # Extract the basic structure (usually "Title:something")
        title_base = re.search(r'("Title:[^"]+")', title_format)
        if title_base:
            title_format = title_base.group(1)
            # Replace the content part with a placeholder
            title_format = re.sub(r':.*?"', ':{title}"', title_format)
        else:
            # Fallback if we can't parse the title format
            title_format = '"Title:{title}"'
        
        # Split the content into lines to handle paragraph-based splitting
        lines = content.splitlines()
        
        # Ensure we have enough titles for all sub-segments
        while len(sub_topics) < len(split_points) + 1:
            sub_topics.append(f"Part{len(sub_topics)+1}")
        
        # Sort split points in ascending order
        split_points.sort()
        
        # Extract metadata (timestamps, URLs, images, comments) from the original text
        metadata_lines = []
        for line in original_text.splitlines():
            # Check if line is metadata
            if (line.startswith('--') or 
                line.startswith('http') or 
                line.startswith('Timestamp:') or 
                line.startswith('Map view:') or 
                line.startswith('Source:') or 
                line.startswith('cc-') or 
                line.startswith('@') or
                re.match(r'^[A-Za-z]{2}-', line)):
                metadata_lines.append(line)
            
        # Create an array to hold the split segments
        segments = []
        
        # Add sub-segments based on split points
        start_idx = 0
        for i, split_point in enumerate(split_points):
            # Adjust split point to ensure it's within bounds
            split_point = min(split_point, len(lines) - 1)
            split_point = max(split_point, 0)
            
            # Get content for this sub-segment
            if split_point >= len(lines):
                # If split point is beyond the end, just take all remaining lines
                segment_content = "\n".join(lines[start_idx:])
            else:
                # Take lines from start to split point (inclusive)
                segment_content = "\n".join(lines[start_idx:split_point+1])
            
            # Create title for this sub-segment - ensure it's a single word
            topic_word = sub_topics[i].strip().split()[0]  # Take just the first word
            segment_title = title_format.format(title=topic_word)
            
            # Create a new segment with metadata preserved
            # Start with the title
            new_segment = segment_title + "\n" + segment_content
            
            # Include all metadata for every segment
            for line in metadata_lines:
                new_segment += "\n" + line
            
            # Add to segments list
            segments.append(new_segment)
            
            # Update start index for next segment
            start_idx = split_point + 1
        
        # Add the final segment (from last split point to end)
        if start_idx < len(lines):
            final_content = "\n".join(lines[start_idx:])
            # Ensure the final title is a single word
            final_topic = sub_topics[-1].strip().split()[0]  # Take just the first word
            final_title = title_format.format(title=final_topic)
            
            # Create a new segment with metadata preserved
            new_segment = final_title + "\n" + final_content
            
            # Include all metadata for this segment too
            for line in metadata_lines:
                new_segment += "\n" + line
            
            segments.append(new_segment)
        
        # Log what we're doing
        self.add_to_log(f"Splitting segment #{self.current_segment_index + 1} into {len(segments)} sub-segments", "highlight")
        
        # Add the segments to processed segments
        for i, segment_text in enumerate(segments):
            if i == 0 and not self.processed_segments:
                # First segment of the whole file
                self.processed_segments.append(segment_text)
                self.current_topic_count = 1
                self.add_to_log(f"Added first sub-segment", "success")
            else:
                # Additional segment - ensure proper spacing
                if self.processed_segments and not self.processed_segments[-1].endswith('\n'):
                    self.processed_segments[-1] += '\n'
                
                self.processed_segments.append(segment_text)
                self.current_topic_count += 1
                self.different_topics_count += 1
                self.add_to_log(f"Added sub-segment", "success")
        
        # Update counters
        self.update_topic_counters()
        
        # Adjust baseline count since we've added segments
        self.baseline_topic_count += len(segments) - 1
        
        # Move to next segment
        self.current_segment_index += 1
        
        # Get the selected model
        model = self.selected_model.get()
        
        # Process the next segment
        if self.current_segment_index < len(self.segments):
            # Use after with a delay to prevent recursion
            self.after(100, lambda: self._process_next_segment(model))
        else:
            # All segments processed
            self._save_processed_file()
        
        return True

if __name__ == "__main__":
    app = TextSorterApp()
    app.mainloop() 