#!/usr/bin/env python3
"""Export the FastAPI OpenAPI spec to fern/openapi/openapi.json."""
import json
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

output_path = Path(__file__).parent.parent / "fern" / "openapi" / "openapi.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

spec = app.openapi()
output_path.write_text(json.dumps(spec, indent=2))
print(f"Spec written to {output_path} ({len(spec['paths'])} paths)")
