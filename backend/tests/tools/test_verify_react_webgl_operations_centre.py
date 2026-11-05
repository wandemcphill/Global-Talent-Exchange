"""Unit and contract tests for the dedicated React WebGL & GLB asset verification tool."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from tools.verify_react_webgl_operations_centre import (
    EXPECTED_DESTINATIONS,
    EXPECTED_GLBS,
    ConsoleSPARequestHandler,
)


class VerifyReactWebglOperationsCentreTests(unittest.TestCase):
    def test_destination_keys_and_glb_mapping_integrity(self) -> None:
        """Verify all six operational wings have valid GLB asset paths in public directory."""
        self.assertEqual(len(EXPECTED_DESTINATIONS), 6)
        self.assertEqual(len(EXPECTED_GLBS), 6)
        for dest in EXPECTED_DESTINATIONS:
            self.assertIn(dest, EXPECTED_GLBS)
            glb_path = EXPECTED_GLBS[dest]
            self.assertTrue(glb_path.startswith("/models/campus/"))
            self.assertTrue(glb_path.endswith(".glb"))

    def test_spa_handler_glb_mime_type(self) -> None:
        """Verify that GLB models are served with the correct model/gltf-binary MIME type."""
        handler = MagicMock(spec=ConsoleSPARequestHandler)
        mime = ConsoleSPARequestHandler.guess_type(handler, "stadium_main.glb")
        self.assertEqual(mime, "model/gltf-binary")

    def test_spa_handler_translate_path(self) -> None:
        """Verify that paths prefixed with /console/ strip the prefix properly for SPA routing."""
        handler = MagicMock(spec=ConsoleSPARequestHandler)
        # Call unbound method
        p1 = ConsoleSPARequestHandler.translate_path(handler, "/console/models/campus/club_hq.glb")
        self.assertTrue(p1.replace("\\", "/").endswith("models/campus/club_hq.glb"))

        p2 = ConsoleSPARequestHandler.translate_path(handler, "/console/app")
        self.assertTrue(p2.replace("\\", "/").endswith("index.html"))
