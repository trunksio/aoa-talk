"""
Agent Self-Registration Module
-------------------------------
Handles automatic registration of Agentic Units (AUs) with the Registry service
on startup by reading capability manifests from YAML files.
"""

import os
import sys
import time
import yaml
import requests
from typing import Optional
from datetime import datetime

# Handle both package import and standalone script usage
try:
    from .manifest import AgentManifest, Agent, Capability, Embedding
except ImportError:
    from manifest import AgentManifest, Agent, Capability, Embedding


def load_manifest_from_yaml(manifest_path: str) -> AgentManifest:
    """
    Load agent manifest from YAML file.

    Args:
        manifest_path: Path to manifest YAML file

    Returns:
        AgentManifest: Parsed manifest object

    Raises:
        FileNotFoundError: If manifest file doesn't exist
        ValueError: If manifest format is invalid
    """
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    with open(manifest_path, "r") as f:
        manifest_data = yaml.safe_load(f)

    if not manifest_data:
        raise ValueError(f"Empty manifest file: {manifest_path}")

    # Parse capabilities
    capabilities = []
    for cap_data in manifest_data.get("agent", {}).get("capabilities", []):
        capability = Capability(
            name=cap_data.get("name"),
            description=cap_data.get("description"),
            input_types=cap_data.get("input_types", []),
            output_types=cap_data.get("output_types", []),
            parameters=cap_data.get("parameters", {}),
            metadata=cap_data.get("metadata", {}),
        )
        capabilities.append(capability)

    # Parse embedding if provided
    embedding = None
    if "embedding" in manifest_data.get("agent", {}):
        emb_data = manifest_data["agent"]["embedding"]
        embedding = Embedding(
            vector=emb_data.get("vector", []),
            model=emb_data.get("model", "all-MiniLM-L6-v2"),
            dimension=emb_data.get("dimension", 384),
        )

    # Parse agent
    agent_data = manifest_data.get("agent", {})
    agent = Agent(
        agent_id=agent_data.get("agent_id"),
        name=agent_data.get("name"),
        description=agent_data.get("description"),
        agent_type=agent_data.get("agent_type"),
        capabilities=capabilities,
        embedding=embedding,
        metadata=agent_data.get("metadata", {}),
        version=agent_data.get("version", "1.0.0"),
        status=agent_data.get("status", "active"),
    )

    # Create manifest
    manifest = AgentManifest(agent=agent, registration_timestamp=datetime.utcnow())

    return manifest


def register_agent_from_manifest(
    manifest_path: str,
    registry_url: Optional[str] = None,
    max_retries: int = 5,
    retry_delay: int = 5,
) -> bool:
    """
    Register agent with Registry service using manifest file.

    Args:
        manifest_path: Path to manifest YAML file
        registry_url: Registry service URL (default: from REGISTRY_URL env var)
        max_retries: Maximum number of registration attempts
        retry_delay: Delay between retries in seconds

    Returns:
        bool: True if registration successful, False otherwise
    """
    # Get registry URL from environment or use default
    if registry_url is None:
        registry_url = os.getenv("REGISTRY_URL", "http://registry:8000")

    # Ensure URL doesn't have trailing slash
    registry_url = registry_url.rstrip("/")
    registration_endpoint = f"{registry_url}/register"

    print(f"[INFO] Loading manifest from: {manifest_path}")

    try:
        # Load manifest
        manifest = load_manifest_from_yaml(manifest_path)
        print(
            f"[INFO] Loaded manifest for agent: {manifest.agent.name} "
            f"(ID: {manifest.agent.agent_id})"
        )

        # Retry registration with exponential backoff
        for attempt in range(1, max_retries + 1):
            try:
                print(
                    f"[INFO] Registering with Registry service "
                    f"(attempt {attempt}/{max_retries})..."
                )

                # Send registration request
                response = requests.post(
                    registration_endpoint,
                    json=manifest.model_dump(mode="json"),
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

                if response.status_code == 200:
                    result = response.json()
                    print(
                        f"[SUCCESS] Agent registered successfully: "
                        f"{result.get('message', 'OK')}"
                    )
                    print(f"[INFO] Agent ID: {result.get('agent_id')}")
                    print(f"[INFO] Action: {result.get('action', 'unknown')}")
                    return True
                else:
                    print(
                        f"[WARNING] Registration failed with status "
                        f"{response.status_code}: {response.text}"
                    )

            except requests.exceptions.ConnectionError as e:
                print(
                    f"[WARNING] Connection error (attempt {attempt}/{max_retries}): {e}"
                )
            except requests.exceptions.Timeout as e:
                print(
                    f"[WARNING] Request timeout (attempt {attempt}/{max_retries}): {e}"
                )
            except Exception as e:
                print(
                    f"[WARNING] Registration error (attempt {attempt}/{max_retries}): {e}"
                )

            # Wait before retry (except on last attempt)
            if attempt < max_retries:
                print(f"[INFO] Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)

        print(
            f"[ERROR] Registration failed after {max_retries} attempts. "
            "Agent will start without registration."
        )
        return False

    except FileNotFoundError as e:
        print(f"[ERROR] Manifest file not found: {e}")
        return False
    except ValueError as e:
        print(f"[ERROR] Invalid manifest format: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during registration: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """
    Main entry point for standalone registration script.

    Usage:
        python register_on_start.py [manifest_path]

    Environment variables:
        MANIFEST_PATH: Path to manifest YAML file (default: ./manifest.yaml)
        REGISTRY_URL: Registry service URL (default: http://registry:8000)
    """
    # Get manifest path from command line or environment
    if len(sys.argv) > 1:
        manifest_path = sys.argv[1]
    else:
        manifest_path = os.getenv("MANIFEST_PATH", "./manifest.yaml")

    print("[INFO] Agent Self-Registration Script")
    print(f"[INFO] Manifest path: {manifest_path}")

    # Register agent
    success = register_agent_from_manifest(manifest_path)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
