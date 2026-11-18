"""Central GTEX AI gateway.

Application code calls ``GtexAiService`` instead of constructing its own OpenAI client.
The API key stays in server environment variables and is never returned by the admin API.
"""

from app.ai_gateway.service import GtexAiService

__all__ = ["GtexAiService"]
