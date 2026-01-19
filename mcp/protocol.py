"""JSON-RPC 2.0 protocol implementation for MCP."""
from typing import Any, Dict, Optional, Union
from enum import Enum
import json


class JSONRPCErrorCode(Enum):
    """JSON-RPC 2.0 error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Custom error codes
    RESOURCE_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002


class JSONRPCError(Exception):
    """JSON-RPC 2.0 error."""
    
    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to JSON-RPC error object."""
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            error["data"] = self.data
        return error


class JSONRPCRequest:
    """JSON-RPC 2.0 request."""
    
    def __init__(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], list]] = None,
        request_id: Optional[Union[str, int]] = None
    ):
        self.jsonrpc = "2.0"
        self.method = method
        self.params = params or {}
        self.id = request_id
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCRequest":
        """Create request from dictionary."""
        if data.get("jsonrpc") != "2.0":
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST.value,
                "Invalid JSON-RPC version"
            )
        
        if "method" not in data:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST.value,
                "Method is required"
            )
        
        return cls(
            method=data["method"],
            params=data.get("params"),
            request_id=data.get("id")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "JSONRPCRequest":
        """Create request from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise JSONRPCError(
                JSONRPCErrorCode.PARSE_ERROR.value,
                f"Parse error: {str(e)}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method
        }
        if self.params:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class JSONRPCResponse:
    """JSON-RPC 2.0 response."""
    
    def __init__(
        self,
        result: Optional[Any] = None,
        error: Optional[JSONRPCError] = None,
        request_id: Optional[Union[str, int]] = None
    ):
        self.jsonrpc = "2.0"
        self.result = result
        self.error = error
        self.id = request_id
        
        if result is not None and error is not None:
            raise ValueError("Response cannot have both result and error")
    
    @classmethod
    def success(cls, result: Any, request_id: Optional[Union[str, int]] = None) -> "JSONRPCResponse":
        """Create success response."""
        return cls(result=result, request_id=request_id)
    
    @classmethod
    def error(
        cls,
        error: JSONRPCError,
        request_id: Optional[Union[str, int]] = None
    ) -> "JSONRPCResponse":
        """Create error response."""
        return cls(error=error, request_id=request_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "jsonrpc": self.jsonrpc
        }
        
        if self.error:
            result["error"] = self.error.to_dict()
        else:
            result["result"] = self.result
        
        if self.id is not None:
            result["id"] = self.id
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
