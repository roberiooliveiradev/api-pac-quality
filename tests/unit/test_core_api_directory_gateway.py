from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.infrastructure.gateways.core_api_directory_gateway import CoreApiDirectoryGateway


def test_search_assignable_users_returns_items():
    gateway = CoreApiDirectoryGateway()
    with patch.object(gateway, "configured", return_value=True), patch(
        "app.infrastructure.gateways.core_api_directory_gateway.httpx.Client"
    ) as client_cls:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "items": [{"id": "u1", "name": "Ana", "email": "a***@delpi.com"}],
        }
        client_cls.return_value.__enter__.return_value.get.return_value = response

        items = gateway.search_assignable_users(query="ana", limit=5)

    assert len(items) == 1
    assert items[0]["id"] == "u1"
