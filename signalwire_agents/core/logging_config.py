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
    
    # Support direct access to underlying logger attributes if needed
    def __getattr__(self, name: str) -> Any:
        """Delegate any unknown attributes to the underlying logger"""
        return getattr(self._logger, name)


def get_execution_mode() -> str:
    """
    Determine the execution mode based on environment variables
    
    Returns:
        'cgi' if running in CGI mode
        'lambda' if running in AWS Lambda 
        'server' for normal server mode
    """
    if os.getenv('GATEWAY_INTERFACE'):
        return 'cgi'
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME') or os.getenv('LAMBDA_TASK_ROOT'):
        return 'lambda'
    return 'server'


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
    """Configure logging to stderr"""
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Convert log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure to stderr
    logging.basicConfig(
        stream=sys.stderr,
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def _configure_default_mode(log_level: str):
    """Configure standard logging behavior"""
    # Convert log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


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