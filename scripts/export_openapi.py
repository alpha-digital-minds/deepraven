#!/usr/bin/env python3
"""Export the FastAPI OpenAPI spec to fern/openapi/openapi.json."""
import json
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def convert_31_to_30(obj):
    """Recursively convert OpenAPI 3.1 nullable patterns to 3.0 nullable:true."""
    if isinstance(obj, dict):
        # Convert anyOf: [{...}, {type: null}] → {..., nullable: true}
        if "anyOf" in obj:
            non_null = [s for s in obj["anyOf"] if s != {"type": "null"}]
            has_null = len(non_null) < len(obj["anyOf"])
            if has_null and len(non_null) == 1:
                result = {**non_null[0], "nullable": True}
                # Preserve other keys from the parent (e.g. title, description)
                for k, v in obj.items():
                    if k != "anyOf":
                        result[k] = v
                return convert_31_to_30(result)
        return {k: convert_31_to_30(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_31_to_30(item) for item in obj]
    return obj


output_path = Path(__file__).parent.parent / "fern" / "openapi" / "openapi.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

spec = app.openapi()

# Downgrade from 3.1.0 to 3.0.3 for broader tooling compatibility (Stainless, etc.)
spec["openapi"] = "3.0.3"

# Convert 3.1 nullable patterns to 3.0 nullable:true
spec = convert_31_to_30(spec)

# Add servers section (required by Stainless and many other SDK generators)
spec["servers"] = [
    {"url": "https://deepraven.ai", "description": "Production"},
    {"url": "http://localhost:5100", "description": "Local development"},
]

# Add security scheme for Bearer auth (API key + JWT)
spec.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
    "type": "http",
    "scheme": "bearer",
    "description": "API key (dr_...) or Supabase JWT (eyJ...)",
}

output_path.write_text(json.dumps(spec, indent=2))
print(f"Spec written to {output_path} ({len(spec['paths'])} paths)")
