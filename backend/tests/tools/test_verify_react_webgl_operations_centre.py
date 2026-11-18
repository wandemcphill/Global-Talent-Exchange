"""Unit and contract tests for the dedicated React WebGL & GLB asset verification tool."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from tools.verify_react_webgl_operations_centre import (
    EXPECTED_DESTINATIONS,
    EXPECTED_GLBS,
    PROCEDURAL_DESTINATIONS,
    REALTIME_SOCKET_GLOB,
    ConsoleSPARequestHandler,
    hold_realtime_off_production,
)


class VerifyReactWebglOperationsCentreTests(unittest.TestCase):
    def test_destination_keys_and_glb_mapping_integrity(self) -> None:
        """Fetched campus models plus procedural offices cover all six wings."""
        self.assertEqual(len(EXPECTED_DESTINATIONS), 6)
        self.assertEqual(len(EXPECTED_GLBS), 3)
        self.assertEqual(len(PROCEDURAL_DESTINATIONS), 3)
        for dest, glb_path in EXPECTED_GLBS.items():
            self.assertIn(dest, EXPECTED_DESTINATIONS)
            self.assertTrue(glb_path.startswith("/models/campus/"))
            self.assertTrue(glb_path.endswith(".glb"))
        for dest in PROCEDURAL_DESTINATIONS:
            self.assertIn(dest, EXPECTED_DESTINATIONS)
            self.assertNotIn(dest, EXPECTED_GLBS)
        self.assertEqual(
            set(EXPECTED_GLBS) | set(PROCEDURAL_DESTINATIONS),
            set(EXPECTED_DESTINATIONS),
        )

    def test_asset_test_does_not_open_the_production_realtime_socket(self) -> None:
        page = MagicMock()
        hold_realtime_off_production(page)
        page.route_web_socket.assert_called_once_with(REALTIME_SOCKET_GLOB, unittest.mock.ANY)
        handler = page.route_web_socket.call_args.args[1]
        socket = MagicMock()
        handler(socket)
        socket.connect_to_server.assert_not_called()

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

    def test_fallback_wireframe_naming_and_destination_keys(self) -> None:
        """Verify fallback wireframe object naming contract and destination keys."""
        for dest in EXPECTED_DESTINATIONS:
            expected_name = f"fallback-wireframe-{dest}"
            self.assertTrue(expected_name.startswith("fallback-wireframe-"))
            self.assertEqual(expected_name.split("fallback-wireframe-")[1], dest)
