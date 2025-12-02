import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketMessage, UseWebSocketOptions } from '../schemas/websocket';

// DOM types for browser environment
type EventTargetType = {
  addEventListener(type: string, listener: (event: EventType) => void): void;
  removeEventListener(type: string, listener: (event: EventType) => void): void;
  dispatchEvent(event: EventType): boolean;
};

// DOM event types for browser environment
type EventType = {
  readonly type: string;
  readonly target: EventTargetType | null;
  readonly currentTarget: EventTargetType | null;
  preventDefault(): void;
  stopPropagation(): void;
};

type MessageEventType = EventType & {
  readonly data: string;
  readonly origin: string;
  readonly lastEventId: string;
};

type CloseEventType = EventType & {
  readonly code: number;
  readonly reason: string;
  readonly wasClean: boolean;
};

// WebSocket type for browser environment
type WebSocketType = {
  new (url: string): WebSocketType;
  readonly readyState: number;
  readonly OPEN: number;
  readonly CONNECTING: number;
  readonly CLOSING: number;
  readonly CLOSED: number;
  onopen: ((event: EventType) => void) | null;
  onmessage: ((event: MessageEventType) => void) | null;
  onclose: ((event: CloseEventType) => void) | null;
  onerror: ((event: EventType) => void) | null;
  send(data: string): void;
  close(): void;
};

declare const WebSocket: WebSocketType;

export function useWebSocket({
  userId,
  onMessage,
  onRecommendationsReady,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocketType | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const isConnecting = useRef(false);
  const connectionCooldown = useRef(0);
  const heartbeatInterval = useRef<number | null>(null);
  const connectRef = useRef<(() => void) | undefined>(undefined);
  const disconnectRef = useRef<(() => void) | undefined>(undefined);

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnecting.current || ws.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // Implement connection cooldown to prevent rapid reconnections
    const now = Date.now();
    if (now < connectionCooldown.current) {
      const remainingTime = connectionCooldown.current - now;
      console.log(`Connection cooldown active, waiting ${remainingTime}ms`);
      return;
    }

    // Clean up existing connection before creating new one
    if (ws.current) {
      if (ws.current.readyState === WebSocket.OPEN) {
        ws.current.close();
      }
      ws.current = null;
    }

    isConnecting.current = true;
    connectionCooldown.current = now + 2000; // 2 second cooldown

    try {
      // Use relative URL that works with Vite proxy
      // In development, this will be proxied to the API server
      // In production, this will be served from the same domain
      // Use wss:// for HTTPS pages, ws:// for HTTP pages
      // WebSocket endpoint is under /api to use the same OpenShift route
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws/recommendations/${userId}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        isConnecting.current = false;

        // Start heartbeat to keep connection alive
        heartbeatInterval.current = window.setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000); // Send ping every 30 seconds
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          if (
            message.type === 'recommendations_ready' &&
            onRecommendationsReady &&
            message.recommendations
          ) {
            onRecommendationsReady(message.recommendations);
          }

          if (onMessage) {
            onMessage(message);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
        });
        setIsConnected(false);
        isConnecting.current = false;

        // Clear heartbeat interval
        if (heartbeatInterval.current) {
          clearInterval(heartbeatInterval.current);
          heartbeatInterval.current = null;
        }

        // Only attempt to reconnect if we haven't exceeded max attempts
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000;
          reconnectAttempts.current++;

          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log(
              `Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})...`,
            );
            connect();
          }, delay);
        } else {
          setError('Failed to reconnect to server');
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
        isConnecting.current = false;
      };
    } catch (err) {
      console.error('Error creating WebSocket connection:', err);
      setError('Failed to create WebSocket connection');
      isConnecting.current = false;
    }
  }, [userId, onMessage, onRecommendationsReady]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
      heartbeatInterval.current = null;
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    setIsConnected(false);
    isConnecting.current = false;
  }, []);

  // Update refs when functions change
  connectRef.current = connect;
  disconnectRef.current = disconnect;

  useEffect(() => {
    if (userId) {
      // Add a small delay to prevent rapid reconnections
      const timeoutId = setTimeout(() => {
        connectRef.current?.();
      }, 100);

      return () => {
        clearTimeout(timeoutId);
        disconnectRef.current?.();
      };
    }

    return () => {
      disconnectRef.current?.();
    };
  }, [userId]); // Intentionally exclude connect/disconnect to prevent reconnection loops

  return {
    isConnected,
    error,
    connect,
    disconnect,
  };
}
