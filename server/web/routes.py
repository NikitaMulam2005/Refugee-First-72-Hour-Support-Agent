# backend/web/routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .sockets import manager, process_message

router = APIRouter(tags=["web"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Fire and forget — processing happens in background
            import asyncio
            asyncio.create_task(process_message(data, session_id))
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        manager.disconnect(session_id)