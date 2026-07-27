"""
Tests para TelegramAdapter y NotificationDispatcher (tests/test_telegram_adapter.py)
====================================================================================
Verifica que el adaptador de Telegram procesa los comandos correctamente llamando a
BotService, y que NotificationDispatcher despacha alertas multi-canal.
"""

import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from services.bot_service import BotService
from services.telegram_adapter import TelegramAdapter
from services.notification_dispatcher import NotificationDispatcher

class TestTelegramAdapter(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.bot_service = BotService()
        self.adapter = TelegramAdapter(bot_service=self.bot_service)
        self.adapter.token = "TEST_TOKEN"
        self.adapter.authorized_chat_id = "12345"

    def _create_mock_session(self):
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="{}")
        
        # Async Context Manager mock for session.post
        mock_post = MagicMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post.return_value = mock_post
        return mock_session, mock_post

    async def test_cmd_status(self):
        mock_session, mock_post = self._create_mock_session()
        await self.adapter._cmd_status(mock_session, 12345)
        
        self.assertTrue(mock_session.post.called)
        json_sent = mock_session.post.call_args[1]["json"]
        self.assertEqual(json_sent["chat_id"], 12345)
        self.assertIn("LastEdge — Estado del Bot", json_sent["text"])

    async def test_cmd_positions(self):
        mock_session, mock_post = self._create_mock_session()
        await self.adapter._cmd_positions(mock_session, 12345)
        
        self.assertTrue(mock_session.post.called)
        json_sent = mock_session.post.call_args[1]["json"]
        self.assertIn("posiciones abiertas", json_sent["text"])

    async def test_cmd_equity(self):
        mock_session, mock_post = self._create_mock_session()
        await self.adapter._cmd_equity(mock_session, 12345)
        
        self.assertTrue(mock_session.post.called)
        json_sent = mock_session.post.call_args[1]["json"]
        self.assertIn("Balance", json_sent["text"])

    async def test_cmd_risk(self):
        mock_session, mock_post = self._create_mock_session()
        await self.adapter._cmd_risk(mock_session, 12345)
        
        self.assertTrue(mock_session.post.called)
        json_sent = mock_session.post.call_args[1]["json"]
        self.assertIn("Risk Engine v2", json_sent["text"])

    async def test_cmd_research(self):
        mock_session, mock_post = self._create_mock_session()
        await self.adapter._cmd_research(mock_session, 12345)
        
        self.assertTrue(mock_session.post.called)
        json_sent = mock_session.post.call_args[1]["json"]
        self.assertIn("Research Database", json_sent["text"])

    async def test_notification_dispatcher_broadcast(self):
        dispatcher = NotificationDispatcher()
        discord_received = []

        async def dummy_discord(msg):
            discord_received.append(msg)

        dispatcher.register_discord_handler(dummy_discord)
        
        res = await dispatcher.broadcast_message("Prueba de alerta simultánea", title="Alerta de Riesgo", level="WARNING")
        self.assertTrue(res["discord"])
        self.assertEqual(len(discord_received), 1)
        self.assertIn("Alerta de Riesgo", discord_received[0])


if __name__ == '__main__':
    unittest.main()
