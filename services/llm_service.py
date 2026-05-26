"""
Unified LLM Service
Handles both OpenAI and OpenRouter API calls with provider abstraction.
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import json

from config import config


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""
    success: bool
    provider: str
    model: str
    content: Optional[str]
    usage_tokens: Optional[Dict[str, int]]
    error_message: Optional[str]
    raw_response: Optional[Dict[str, Any]]


class LLMService:
    """
    Unified interface for OpenAI and OpenRouter models.
    Automatically routes requests and handles fallback logic.
    """

    def __init__(self):
        """Initialize LLM service with configured providers."""
        self.openai_available = bool(config.openai_api_key)
        self.openrouter_available = bool(config.openrouter_api_key)
        self.primary_provider = LLMProvider.OPENAI if self.openai_available else LLMProvider.OPENROUTER
        
        # Lazy-load OpenAI client only if available
        self._openai_client = None
        if self.openai_available:
            self._init_openai_client()

    def _init_openai_client(self) -> None:
        """Initialize OpenAI client with configured credentials."""
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url
            )
            print(f"✓ OpenAI client initialized (base_url: {config.openai_base_url})")
        except ImportError:
            print("✗ OpenAI library not installed. Install with: pip install openai")
            self.openai_available = False
        except Exception as e:
            print(f"✗ Failed to initialize OpenAI client: {e}")
            self.openai_available = False

    def _get_openrouter_client(self):
        """Get or create OpenRouter client (via OpenAI SDK with custom base URL)."""
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=config.openrouter_api_key,
                base_url=config.openrouter_base_url
            )
        except ImportError:
            raise ImportError("OpenAI library required for OpenRouter access. Install: pip install openai")

    def generate_creative_content(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        provider: Optional[LLMProvider] = None
    ) -> LLMResponse:
        """
        Generate creative writing content using the primary LLM.
        
        Args:
            prompt: The prompt for content generation
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            provider: Optional provider override
        
        Returns:
            LLMResponse with generated content
        """
        if provider is None:
            provider = self.primary_provider
        
        model = config.default_openai_model if provider == LLMProvider.OPENAI else config.default_openrouter_model
        
        return self._call_llm(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            provider=provider,
            max_tokens=max_tokens,
            temperature=temperature
        )

    def extract_structured_data(
        self,
        content: str,
        extraction_prompt: str,
        output_format: str = "json",
        provider: Optional[LLMProvider] = None
    ) -> LLMResponse:
        """
        Extract structured data from content using semantic analysis.
        Defaults to OpenRouter for specialized extraction models.
        
        Args:
            content: Text to extract data from
            extraction_prompt: Instructions for extraction
            output_format: 'json', 'yaml', or 'text'
            provider: Optional provider override
        
        Returns:
            LLMResponse with extracted data
        """
        if provider is None:
            provider = LLMProvider.OPENROUTER if self.openrouter_available else self.primary_provider
        
        model = config.default_openrouter_model if provider == LLMProvider.OPENROUTER else config.default_openai_model
        
        full_prompt = f"""Extract data from the following content using this format: {output_format}

Instructions: {extraction_prompt}

Content:
{content}

Respond only with valid {output_format}."""
        
        return self._call_llm(
            messages=[{"role": "user", "content": full_prompt}],
            model=model,
            provider=provider,
            max_tokens=1024,
            temperature=0.2  # Lower temp for structured extraction
        )

    def semantic_edit(
        self,
        original_text: str,
        editing_instruction: str,
        provider: Optional[LLMProvider] = None
    ) -> LLMResponse:
        """
        Semantically edit text using specialized models.
        Defaults to OpenRouter for fine-grained editing.
        
        Args:
            original_text: Text to edit
            editing_instruction: What to change
            provider: Optional provider override
        
        Returns:
            LLMResponse with edited text
        """
        if provider is None:
            provider = LLMProvider.OPENROUTER if self.openrouter_available else self.primary_provider
        
        model = config.default_openrouter_model if provider == LLMProvider.OPENROUTER else config.default_openai_model
        
        full_prompt = f"""Edit the following text according to the instruction. Return only the edited text, no explanations.

Instruction: {editing_instruction}

Original text:
{original_text}"""
        
        return self._call_llm(
            messages=[{"role": "user", "content": full_prompt}],
            model=model,
            provider=provider,
            max_tokens=2048,
            temperature=0.5
        )

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: LLMProvider,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        retries: int = 0
    ) -> LLMResponse:
        """
        Core LLM API call with error handling and retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            provider: LLMProvider enum value
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            retries: Current retry count
        
        Returns:
            LLMResponse with results or error details
        """
        try:
            if provider == LLMProvider.OPENAI:
                if not self.openai_available:
                    return LLMResponse(
                        success=False,
                        provider="openai",
                        model=model,
                        content=None,
                        usage_tokens=None,
                        error_message="OpenAI provider not available",
                        raw_response=None
                    )
                
                response = self._openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=config.request_timeout_seconds
                )
            
            elif provider == LLMProvider.OPENROUTER:
                if not self.openrouter_available:
                    return LLMResponse(
                        success=False,
                        provider="openrouter",
                        model=model,
                        content=None,
                        usage_tokens=None,
                        error_message="OpenRouter provider not available",
                        raw_response=None
                    )
                
                client = self._get_openrouter_client()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=config.request_timeout_seconds
                )
            
            else:
                return LLMResponse(
                    success=False,
                    provider=str(provider),
                    model=model,
                    content=None,
                    usage_tokens=None,
                    error_message=f"Unknown provider: {provider}",
                    raw_response=None
                )
            
            # Extract content
            content = response.choices[0].message.content if response.choices else None
            
            # Extract token usage
            usage_tokens = None
            if hasattr(response, 'usage') and response.usage:
                usage_tokens = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            print(f"✓ {provider.value.upper()} call successful ({model})")
            
            return LLMResponse(
                success=True,
                provider=provider.value,
                model=model,
                content=content,
                usage_tokens=usage_tokens,
                error_message=None,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
            )
        
        except Exception as e:
            error_msg = str(e)
            print(f"✗ {provider.value.upper()} API call failed: {error_msg}")
            
            # Retry logic
            if retries < config.max_retries:
                print(f"  Retrying ({retries + 1}/{config.max_retries})...")
                import time
                time.sleep(2 ** retries)  # Exponential backoff
                return self._call_llm(
                    messages=messages,
                    model=model,
                    provider=provider,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    retries=retries + 1
                )
            
            return LLMResponse(
                success=False,
                provider=provider.value,
                model=model,
                content=None,
                usage_tokens=None,
                error_message=error_msg,
                raw_response=None
            )

    def batch_generate(
        self,
        prompts: List[str],
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None
    ) -> List[LLMResponse]:
        """
        Generate responses for multiple prompts sequentially.
        
        Args:
            prompts: List of prompt strings
            model: Optional model override
            provider: Optional provider override
        
        Returns:
            List of LLMResponse objects
        """
        responses = []
        for i, prompt in enumerate(prompts):
            print(f"  Processing prompt {i + 1}/{len(prompts)}...")
            
            if provider is None:
                # Alternate between providers to balance load
                use_provider = self.primary_provider
            else:
                use_provider = provider
            
            if model is None:
                model_name = config.default_openai_model if use_provider == LLMProvider.OPENAI else config.default_openrouter_model
            else:
                model_name = model
            
            response = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                provider=use_provider
            )
            responses.append(response)
        
        return responses

    def get_provider_status(self) -> Dict[str, bool]:
        """
        Return availability status of all configured providers.
        
        Returns:
            Dict with provider names and availability boolean
        """
        return {
            "openai": self.openai_available,
            "openrouter": self.openrouter_available,
            "primary_provider": self.primary_provider.value
        }
