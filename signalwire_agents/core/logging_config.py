"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
Central logging configuration for SignalWire Agents SDK

This module provides a single point of control for all logging across the SDK
and applications built with it. All components should use get_logger() instead
of direct logging module usage or print() statements.

The StructuredLoggerWrapper provides backward compatibility with existing 
structured logging calls (e.g., log.info("message", key=value)) while using
standard Python logging underneath. This allows the entire codebase to work
without changes while providing centralized logging control.
"""

import logging
import os
import sys
from typing import Optional, Any, Dict

# Global flag to ensure configuration only happens once
_logging_configured = False


class StructuredLoggerWrapper:
    """
    A wrapper that provides structured logging interface while using standard Python logging
    
    This allows existing structured logging calls to work without changes while
    giving us centralized control over logging behavior.
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _format_structured_message(self, message: str, **kwargs) -> str:
        """Format a message with structured keyword arguments"""
        if not kwargs:
            return message
            
        # Convert kwargs to readable string format
        parts = []
        for key, value in kwargs.items():
            # Handle different value types appropriately
            if isinstance(value, str):
                parts.append(f"{key}={value}")
            elif isinstance(value, (list, dict)):
                parts.append(f"{key}={str(value)}")
            else:
                parts.append(f"{key}={value}")
        
        if parts:
            return f"{message} ({', '.join(parts)})"
        else:
            return message
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional structured data"""
        formatted = self._format_structured_message(message, **kwargs)
        self._logger.debug(formatted)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional structured data"""
        formatted = self._format_structured_message(message, **kwargs)
        self._logger.info(formatted)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional structured data"""
        formatted = self._format_structured_message(message, **kwargs)
        self._logger.warning(formatted)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with optional structured data"""
        formatted = self._format_structured_message(message, **kwargs)
        self._logger.error(formatted)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with optional structured data"""
        formatted = self._format_structured_message(message, **kwargs)
        self._logger.critical(formatted)
    
    # Also support the 'warn' alias
    warn = warning
    
    def bind(self, **kwargs) -> 'StructuredLoggerWrapper':
        """
        Create a new logger instance with bound context data
        
        This maintains compatibility with structlog's bind() method.
        The bound data will be included in all subsequent log messages.
        """
        # Create a new wrapper that includes the bound context
        return BoundStructuredLoggerWrapper(self._logger, kwargs)
    
    # Support direct access to underlying logger attributes if needed
    def __getattr__(self, name: str) -> Any:
        """Delegate any unknown attributes to the underlying logger"""
        return getattr(self._logger, name)


class BoundStructuredLoggerWrapper(StructuredLoggerWrapper):
    """
    A structured logger wrapper that includes bound context data in all messages
    """
    
    def __init__(self, logger: logging.Logger, bound_data: Dict[str, Any]):
        super().__init__(logger)
        self._bound_data = bound_data
    
    def _format_structured_message(self, message: str, **kwargs) -> str:
        """Format a message with both bound data and additional keyword arguments"""
        # Combine bound data with additional kwargs
        all_kwargs = {**self._bound_data, **kwargs}
        return super()._format_structured_message(message, **all_kwargs)
    
    def bind(self, **kwargs) -> 'BoundStructuredLoggerWrapper':
        """Create a new logger with additional bound context"""
        # Combine existing bound data with new data
        new_bound_data = {**self._bound_data, **kwargs}
        return BoundStructuredLoggerWrapper(self._logger, new_bound_data)


def get_execution_mode():
    """
    Determine the execution mode based on environment variables
    
    Returns:
        str: 'server', 'cgi', 'lambda', 'google_cloud_function', 'azure_function', or 'unknown'
    """
    # Check for CGI environment
    if os.getenv('GATEWAY_INTERFACE'):
        return 'cgi'
    
    # Check for AWS Lambda environment
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME') or os.getenv('LAMBDA_TASK_ROOT'):
        return 'lambda'
    
    # Check for Google Cloud Functions environment
    if (os.getenv('FUNCTION_TARGET') or 
        os.getenv('K_SERVICE') or 
        os.getenv('GOOGLE_CLOUD_PROJECT')):
        return 'google_cloud_function'
    
    # Check for Azure Functions environment
    if (os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or 
        os.getenv('FUNCTIONS_WORKER_RUNTIME') or
        os.getenv('AzureWebJobsStorage')):
        return 'azure_function'
    
    # Default to server mode
    return 'server'


def reset_logging_configuration():
    """
    Reset the logging configuration flag to allow reconfiguration
    
    This is useful when environment variables change after initial configuration.
    """
    global _logging_configured
    _logging_configured = False


def configure_logging():
    """
    Configure logging system once, globally, based on environment variables
    
    Environment Variables:
        SIGNALWIRE_LOG_MODE: off, stderr, default, auto
        SIGNALWIRE_LOG_LEVEL: debug, info, warning, error, critical
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    # Get configuration from environment
    log_mode = os.getenv('SIGNALWIRE_LOG_MODE', '').lower()
    log_level = os.getenv('SIGNALWIRE_LOG_LEVEL', 'info').lower()
    
    # Determine log mode if auto or not specified
    if not log_mode or log_mode == 'auto':
        execution_mode = get_execution_mode()
        if execution_mode == 'cgi':
            log_mode = 'off'
        else:
            log_mode = 'default'
    
    # Configure based on mode
    if log_mode == 'off':
        _configure_off_mode()
    elif log_mode == 'stderr':
        _configure_stderr_mode(log_level)
    else:  # default mode
        _configure_default_mode(log_level)
    
    _logging_configured = True


def _configure_off_mode():
    """Suppress all logging output"""
    # Redirect to devnull
    null_file = open(os.devnull, 'w')
    
    # Clear existing handlers and configure to devnull
    logging.getLogger().handlers.clear()
    logging.basicConfig(
        stream=null_file,
        level=logging.CRITICAL,
        format=''
    )
    
    # Set all known loggers to CRITICAL to prevent any output
    logger_names = [
        '', 'signalwire_agents', 'skill_registry', 'swml_service', 
        'agent_base', 'AgentServer', 'uvicorn', 'fastapi'
    ]
    for name in logger_names:
        logging.getLogger(name).setLevel(logging.CRITICAL)
    
    # Configure structlog if available
    try:
        import structlog
        structlog.configure(
            processors=[],
            wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
            logger_factory=structlog.PrintLoggerFactory(file=null_file),
            cache_logger_on_first_use=True,
        )
    except ImportError:
        pass


def _configure_stderr_mode(log_level: str):
    """Configure logging to stderr with colored formatting"""
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Convert log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create handler with colored formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColoredFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)


def _configure_default_mode(log_level: str):
    """Configure standard logging behavior with colored formatting"""
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Convert log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create handler with colored formatter
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)


def get_logger(name: str) -> StructuredLoggerWrapper:
    """
    Get a logger instance for the specified name with structured logging support
    
    This is the single entry point for all logging in the SDK.
    All modules should use this instead of direct logging module usage.
    
    Args:
        name: Logger name, typically __name__
        
    Returns:
        StructuredLoggerWrapper that supports both regular and structured logging
    """
    # Ensure logging is configured
    configure_logging()
    
    # Get the standard Python logger
    python_logger = logging.getLogger(name)
    
    # Wrap it with our structured logging interface
    return StructuredLoggerWrapper(python_logger)


class ColoredFormatter(logging.Formatter):
    """
    A beautiful colored logging formatter that makes logs easy to read and visually appealing
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green  
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
        'BOLD': '\033[1m',       # Bold
        'DIM': '\033[2m',        # Dim
        'WHITE': '\033[37m',     # White
        'BLUE': '\033[34m',      # Blue
        'BLACK': '\033[30m',     # Black (for brackets)
    }
    
    def __init__(self):
        super().__init__()
    
    def format(self, record):
        # Check if we should use colors (not in raw mode, and stdout is a tty)
        use_colors = (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            os.getenv('SIGNALWIRE_LOG_MODE') != 'off' and
            '--raw' not in sys.argv and '--dump-swml' not in sys.argv
        )
        
        if use_colors:
            # Get colors
            level_color = self.COLORS.get(record.levelname, self.COLORS['WHITE'])
            reset = self.COLORS['RESET']
            dim = self.COLORS['DIM']
            bold = self.COLORS['BOLD']
            blue = self.COLORS['BLUE']
            black = self.COLORS['BLACK']
            
            # Format timestamp in a compact, readable way
            timestamp = self.formatTime(record, '%H:%M:%S')
            
            # Format level with appropriate color and consistent width
            level_name = f"{level_color}{record.levelname:<8}{reset}"
            
            # Format logger name - keep it short and readable
            logger_name = record.name
            if len(logger_name) > 15:
                # Truncate long logger names but keep the end (most specific part)
                logger_name = "..." + logger_name[-12:]
            
            # Get function and line info if available
            func_info = ""
            if hasattr(record, 'funcName') and hasattr(record, 'lineno'):
                func_name = getattr(record, 'funcName', '')
                line_no = getattr(record, 'lineno', 0)
                if func_name and func_name != '<module>':
                    func_info = f" {dim}({func_name}:{line_no}){reset}"
            
            # Format the message
            message = record.getMessage()
            
            # Create the final formatted message with a clean, readable layout
            formatted = (
                f"{black}[{reset}{dim}{timestamp}{reset}{black}]{reset} "
                f"{level_name} "
                f"{blue}{logger_name:<15}{reset}"
                f"{func_info} "
                f"{message}"
            )
            
            return formatted
        else:
            # Non-colored format (fallback for files, pipes, etc.)
            timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
            return f"{timestamp} {record.levelname:<8} {record.name} {record.getMessage()}" 