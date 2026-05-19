"""Local LLM Provider - Integration with local LLM models (Ollama, Llama, etc).

This module enables the Kabbalah system to use local LLM models for:
1. Error analysis and diagnosis
2. Automatic fix generation
3. Code review and optimization
4. Learning and adaptation
"""

import logging
import requests
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LocalLLMConfig:
    """Configuration for local LLM provider."""
    base_url: str = "http://localhost:11434"  # Ollama default
    model: str = "llama2"  # Default model
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    timeout: int = 300


class LocalLLMProvider:
    """Provider for local LLM models."""
    
    def __init__(self, config: Optional[LocalLLMConfig] = None):
        """Initialize local LLM provider.
        
        Args:
            config: Configuration for LLM provider
        """
        self.config = config or LocalLLMConfig()
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if local LLM is available."""
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Local LLM not available: {str(e)}")
            return False
    
    def analyze(self, prompt: str) -> str:
        """Analyze using local LLM.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            LLM response
        """
        if not self.available:
            logger.warning("Local LLM not available, returning empty response")
            return ""
        
        try:
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                    "stream": False,
                },
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error(f"LLM error: {response.status_code}")
                return ""
        
        except Exception as e:
            logger.error(f"Failed to call local LLM: {str(e)}")
            return ""
    
    def generate_fix(self, error_analysis: str) -> Dict[str, Any]:
        """Generate fix from error analysis.
        
        Args:
            error_analysis: Error analysis from LLM
            
        Returns:
            Fix proposal with changes
        """
        prompt = f"""Based on this error analysis, generate a fix:

{error_analysis}

Provide the fix in this JSON format:
{{
    "description": "Brief description of the fix",
    "changes": {{
        "file_path": "new_content"
    }},
    "confidence": 0.8,
    "reasoning": "Why this fix works"
}}
"""
        
        response = self.analyze(prompt)
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Failed to parse fix proposal: {str(e)}")
        
        return {
            "description": "Unable to generate fix",
            "changes": {},
            "confidence": 0.0,
            "reasoning": response,
        }
    
    def review_code(self, code: str, context: str = "") -> str:
        """Review code for improvements.
        
        Args:
            code: Code to review
            context: Additional context
            
        Returns:
            Code review
        """
        prompt = f"""Review this code for improvements:

{code}

Context: {context}

Provide:
1. Issues found
2. Suggested improvements
3. Performance optimizations
4. Security concerns
"""
        
        return self.analyze(prompt)
    
    def optimize_code(self, code: str) -> str:
        """Optimize code.
        
        Args:
            code: Code to optimize
            
        Returns:
            Optimized code
        """
        prompt = f"""Optimize this code for performance and readability:

{code}

Provide the optimized code with explanations.
"""
        
        return self.analyze(prompt)
    
    def explain_error(self, error_message: str, stack_trace: str = "") -> str:
        """Explain an error.
        
        Args:
            error_message: Error message
            stack_trace: Stack trace if available
            
        Returns:
            Error explanation
        """
        prompt = f"""Explain this error and suggest how to fix it:

Error: {error_message}

Stack Trace:
{stack_trace or 'N/A'}

Provide:
1. What caused this error
2. Why it happened
3. How to fix it
4. How to prevent it in the future
"""
        
        return self.analyze(prompt)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        try:
            response = requests.get(
                f"{self.config.base_url}/api/show",
                json={"name": self.config.model},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {str(e)}")
        
        return {}
    
    def list_models(self) -> list:
        """List available models."""
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
        
        return []
    
    def set_model(self, model_name: str) -> bool:
        """Set the model to use.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if model set successfully
        """
        available_models = self.list_models()
        model_names = [m.get("name") for m in available_models]
        
        if model_name in model_names:
            self.config.model = model_name
            logger.info(f"Model set to {model_name}")
            return True
        else:
            logger.error(f"Model {model_name} not available")
            return False
