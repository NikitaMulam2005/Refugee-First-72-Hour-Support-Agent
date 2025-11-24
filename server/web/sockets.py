# backend/web/sockets.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import logging

from graph import create_graph

graph = create_graph()
logger = logging.getLogger("websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Web client connected → {session_id[:8]}")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        logger.info(f"Web client disconnected → {session_id[:8]}")

    async def send_text(self, message: str, session_id: str):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_text(message)


# Global manager instance
manager = ConnectionManager()


async def process_message(raw_message: str, session_id: str):
    """
    Core function: runs the LangGraph and streams final_response back
    Called from routes.py
    """
    try:
        async for event in graph.astream_events(
            input={"raw_message": raw_message, "session_id": session_id},
            version="v2",
        ):
            # Only send the final user-facing response
            if (
                event["event"] == "on_chain_end"
                and "final_response" in event["data"]["output"]
            ):
                response = event["data"]["output"]["final_response"]
                await manager.send_text(response, session_id)
                return

    except Exception as e:
        logger.error(f"Graph error for {session_id[:8]}: {e}")
        await manager.send_text("Sorry, something went wrong. Please try again.", session_id)