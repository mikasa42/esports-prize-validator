import asyncio
import unittest
from unittest.mock import Mock, patch

import pymysql

from src.database.initialization import inicializar_banco
from src.main import app, lifespan
from src.repositories.match_repository import BancoIndisponivel, conectar


class DatabaseInitializationTests(unittest.TestCase):
    @patch('src.repositories.match_repository.pymysql.connect')
    def test_connection_does_not_execute_schema(self, connect):
        connection = conectar()
        self.assertIs(connection, connect.return_value)
        connection.cursor.assert_not_called()

    @patch('src.database.initialization.conectar')
    def test_initialization_executes_schema_and_closes_connection(self, connect):
        connection = connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        inicializar_banco()
        self.assertEqual(cursor.execute.call_count, 5)
        connection.commit.assert_called_once()
        connection.close.assert_called_once()

    @patch('src.database.initialization.conectar')
    def test_schema_error_closes_connection(self, connect):
        connection = connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = pymysql.OperationalError('offline')
        with self.assertRaises(BancoIndisponivel):
            inicializar_banco()
        connection.commit.assert_not_called()
        connection.close.assert_called_once()

    @patch('src.main.inicializar_banco')
    def test_schema_initialized_once_per_application_start(self, initialize):
        async def run():
            async with lifespan(app):
                initialize.assert_called_once()
        asyncio.run(run())
        initialize.assert_called_once()

    @patch('src.main.inicializar_banco', side_effect=BancoIndisponivel('offline'))
    def test_failed_initialization_prevents_startup(self, initialize):
        entered = Mock()
        async def run():
            async with lifespan(app):
                entered()
        with self.assertRaises(BancoIndisponivel):
            asyncio.run(run())
        entered.assert_not_called()
