"""WebSocket endpoints for real-time updates"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter()


# Store active connections by user_id
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}
        self.max_connections_per_user = 3  # Limit connections per user

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        # If user already has too many connections, close the oldest
        if (
            user_id in self.active_connections
            and len(self.active_connections[user_id]) >= self.max_connections_per_user
        ):
            logger.warning(f'User {user_id} has too many connections, closing oldest')
            oldest_connection = next(iter(self.active_connections[user_id]))
            try:
                await oldest_connection.close()
            except Exception as e:
                logger.error(f'Error closing old connection: {e}')
            self.active_connections[user_id].discard(oldest_connection)

        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(
            f'WebSocket connected for user {user_id} '
            f'(total: {len(self.active_connections[user_id])})'
        )

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f'WebSocket disconnected for user {user_id}')

    async def send_personal_message(self, message: dict, user_id: str) -> None:
        if user_id in self.active_connections:
            # Create a copy of the set to avoid modification during iteration
            connections = self.active_connections[user_id].copy()
            for connection in connections:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f'Error sending message to user {user_id}: {e}')
                    self.active_connections[user_id].discard(connection)

    async def broadcast(self, message: dict) -> None:
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)


manager = ConnectionManager()


@router.websocket('/ws/recommendations/{user_id}')
async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep the connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Log received data but don't echo back (client expects only JSON messages)
            logger.debug(f'Received WebSocket message from user {user_id}: {data}')
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f'WebSocket error for user {user_id}: {e}')
        manager.disconnect(websocket, user_id)


async def notify_recommendations_ready(user_id: str, recommendations: dict) -> None:
    """Notify a user when their personalized recommendations are ready"""

    logger.info(f'Notifying user {user_id} that recommendations are ready')
    message = {
        'type': 'recommendations_ready',
        'user_id': user_id,
        'recommendations': recommendations,
        'timestamp': recommendations.get('generated_at'),
    }
    await manager.send_personal_message(message, user_id)
