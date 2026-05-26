"""
Pandoc Compiler Service
Subprocess wrapper for converting Markdown to EPUB/PDF with full error handling.
"""

import subprocess
import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import sys

from config import config


@dataclass
class CompilationResult:
    """Structured result from a pandoc compilation."""
    success: bool
    source_file: str
    output_file: Optional[str]
    format: str  # 'epub' or 'pdf'
    error_message: Optional[str]
    warning_messages: List[str]
    compilation_time_seconds: float
    timestamp: str


class PandocCompiler:
    """
    Encapsulates Pandoc subprocess execution for EPUB and PDF generation.
    Handles metadata injection, stylesheet configuration, and error recovery.
    """

    def __init__(self):
        self.pandoc_path = config.pandoc_path
        self.defaults_dir = config.pandoc_defaults_dir
        self.output_dir = config.content_output_dir
        self.log_dir = config.pipeline_log_dir
        self._validate_pandoc()

    def _validate_pandoc(self) -> None:
        """Verify pandoc is installed and accessible."""
        try:
            result = subprocess.run(
                [self.pandoc_path, "--version"],
                capture_output=True,
                timeout=5,
                check=True,
                text=True
            )
            version_line = result.stdout.split('\n')[0]
            print(f"✓ Pandoc available: {version_line}")
        except FileNotFoundError:
            raise RuntimeError(
                f"Pandoc not found at path: {self.pandoc_path}. "
                "Install pandoc from https://pandoc.org or update PANDOC_PATH."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Pandoc version check timed out.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Pandoc validation failed: {e.stderr}")

    def _load_defaults_file(self, format_type: str) -> Optional[str]:
        """
        Load pandoc defaults file for the specified format.
        Defaults files contain YAML configuration for metadata, styling, etc.
        """
        defaults_file = os.path.join(self.defaults_dir, f"{format_type}.yaml")
        
        if not os.path.exists(defaults_file):
            print(f"⚠ Defaults file not found: {defaults_file}. Using inline defaults.")
            return None
        
        try:
            with open(defaults_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✓ Loaded defaults from {defaults_file}")
                return defaults_file
        except Exception as e:
            print(f"✗ Error reading defaults file {defaults_file}: {e}")
            return None

    def _build_pandoc_command(
        self,
        source_file: str,
        output_file: str,
        format_type: str,
        metadata: Optional[Dict[str, str]] = None,
        defaults_file: Optional[str] = None
    ) -> List[str]:
        """
        Construct the full pandoc command with all arguments.
        
        Args:
            source_file: Path to Markdown source
            output_file: Path to output EPUB/PDF
            format_type: 'epub' or 'pdf'
            metadata: Optional key-value metadata to inject
            defaults_file: Optional defaults YAML file path
        
        Returns:
            List of command arguments ready for subprocess.run()
        """
        cmd = [self.pandoc_path]
        
        # Use defaults file if available
        if defaults_file:
            cmd.extend(["--defaults", defaults_file])
        
        # Add explicit format output
        cmd.extend(["-t", format_type])
        
        # Inject metadata
        if metadata:
            for key, value in metadata.items():
                cmd.extend(["-M", f"{key}={value}"])
        
        # Add common options
        cmd.extend([
            "--standalone",
            "--toc",
            "-f", "markdown+smart",
            source_file,
            "-o", output_file
        ])
        
        return cmd

    def compile_to_epub(
        self,
        source_file: str,
        output_filename: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> CompilationResult:
        """
        Compile Markdown to EPUB format.
        
        Args:
            source_file: Path to source markdown file
            output_filename: Output filename (optional; defaults to source basename)
            metadata: Optional dict of metadata to inject (title, author, etc.)
        
        Returns:
            CompilationResult with success/error details
        """
        return self._compile(
            source_file=source_file,
            format_type="epub",
            output_filename=output_filename,
            metadata=metadata
        )

    def compile_to_pdf(
        self,
        source_file: str,
        output_filename: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> CompilationResult:
        """
        Compile Markdown to PDF format.
        
        Args:
            source_file: Path to source markdown file
            output_filename: Output filename (optional; defaults to source basename)
            metadata: Optional dict of metadata to inject (title, author, etc.)
        
        Returns:
            CompilationResult with success/error details
        """
        return self._compile(
            source_file=source_file,
            format_type="pdf",
            output_filename=output_filename,
            metadata=metadata
        )

    def _compile(
        self,
        source_file: str,
        format_type: str,
        output_filename: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> CompilationResult:
        """
        Core compilation logic for both EPUB and PDF.
        Wraps all error handling and state logging.
        """
        import time
        start_time = time.time()
        
        # Validate source file
        if not os.path.exists(source_file):
            error_msg = f"Source file not found: {source_file}"
            print(f"✗ {error_msg}")
            return CompilationResult(
                success=False,
                source_file=source_file,
                output_file=None,
                format=format_type,
                error_message=error_msg,
                warning_messages=[],
                compilation_time_seconds=time.time() - start_time,
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Generate output filename
        if not output_filename:
            base_name = Path(source_file).stem
            output_filename = f"{base_name}.{format_type}"
        
        output_file = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load defaults file if available
        defaults_file = self._load_defaults_file(format_type)
        
        # Build pandoc command
        cmd = self._build_pandoc_command(
            source_file=source_file,
            output_file=output_file,
            format_type=format_type,
            metadata=metadata,
            defaults_file=defaults_file
        )
        
        print(f"→ Compiling {source_file} to {format_type.upper()}...")
        print(f"  Command: {' '.join(cmd)}")
        
        try:
            # Execute pandoc
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=config.request_timeout_seconds * 4,  # Generous timeout for compilation
                check=False,  # Don't raise on non-zero exit
                text=True
            )
            
            # Parse warnings from stderr
            warnings = [line.strip() for line in result.stderr.split('\n') if line.strip()]
            
            if result.returncode == 0:
                elapsed = time.time() - start_time
                print(f"✓ Successfully compiled to {output_file} ({elapsed:.2f}s)")
                
                return CompilationResult(
                    success=True,
                    source_file=source_file,
                    output_file=output_file,
                    format=format_type,
                    error_message=None,
                    warning_messages=warnings,
                    compilation_time_seconds=elapsed,
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                error_msg = f"Pandoc exited with code {result.returncode}"
                print(f"✗ {error_msg}")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:500]}")
                
                return CompilationResult(
                    success=False,
                    source_file=source_file,
                    output_file=None,
                    format=format_type,
                    error_message=f"{error_msg}: {result.stderr[:200]}",
                    warning_messages=warnings,
                    compilation_time_seconds=time.time() - start_time,
                    timestamp=datetime.utcnow().isoformat()
                )
        
        except subprocess.TimeoutExpired:
            error_msg = f"Compilation timeout (>{config.request_timeout_seconds * 4}s)"
            print(f"✗ {error_msg}")
            return CompilationResult(
                success=False,
                source_file=source_file,
                output_file=None,
                format=format_type,
                error_message=error_msg,
                warning_messages=[],
                compilation_time_seconds=time.time() - start_time,
                timestamp=datetime.utcnow().isoformat()
            )
        
        except Exception as e:
            error_msg = f"Unexpected error during compilation: {str(e)}"
            print(f"✗ {error_msg}")
            return CompilationResult(
                success=False,
                source_file=source_file,
                output_file=None,
                format=format_type,
                error_message=error_msg,
                warning_messages=[],
                compilation_time_seconds=time.time() - start_time,
                timestamp=datetime.utcnow().isoformat()
            )

    def compile_batch(
        self,
        source_files: List[str],
        format_types: List[str] = None,
        metadata_map: Optional[Dict[str, Dict[str, str]]] = None
    ) -> List[CompilationResult]:
        """
        Compile multiple source files to multiple formats.
        
        Args:
            source_files: List of markdown file paths
            format_types: List of formats (default: ['epub', 'pdf'])
            metadata_map: Dict mapping source_file -> metadata dict
        
        Returns:
            List of CompilationResult objects
        """
        if format_types is None:
            format_types = ["epub", "pdf"]
        
        if metadata_map is None:
            metadata_map = {}
        
        results = []
        
        for source_file in source_files:
            metadata = metadata_map.get(source_file, {})
            
            for format_type in format_types:
                if format_type == "epub":
                    result = self.compile_to_epub(source_file, metadata=metadata)
                elif format_type == "pdf":
                    result = self.compile_to_pdf(source_file, metadata=metadata)
                else:
                    print(f"⚠ Unsupported format: {format_type}")
                    continue
                
                results.append(result)
        
        return results

    def save_compilation_log(self, results: List[CompilationResult], log_filename: str = "compilation.json") -> str:
        """
        Save compilation results to a JSON log file for audit trails.
        
        Args:
            results: List of CompilationResult objects
            log_filename: Name of the log file
        
        Returns:
            Path to the saved log file
        """
        os.makedirs(self.log_dir, exist_ok=True)
        log_path = os.path.join(self.log_dir, log_filename)
        
        # Convert results to serializable dicts
        logs = []
        for result in results:
            logs.append({
                "success": result.success,
                "source_file": result.source_file,
                "output_file": result.output_file,
                "format": result.format,
                "error_message": result.error_message,
                "warning_messages": result.warning_messages,
                "compilation_time_seconds": result.compilation_time_seconds,
                "timestamp": result.timestamp
            })
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, default=str)
            print(f"✓ Compilation log saved to {log_path}")
            return log_path
        except Exception as e:
            print(f"✗ Failed to save compilation log: {e}")
            return ""
