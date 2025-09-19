# Location-Based Fraud Detection - Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant F as Frontend App
    participant A as API Server
    participant AUTH as Auth Middleware
    participant LM as Location Middleware
    participant DB as PostgreSQL Database
    participant TS as Transaction Service
    participant ARS as Alert Rule Service
    participant ALG as Alert LLM Graph
    participant NS as Notification Service

    Note over U,NS: 1. User Location Capture Flow

    U->>F: Opens app/logs in
    F->>F: useLocation() hook captures GPS
    F->>F: createLocationHeaders() adds X-User-Latitude, X-User-Longitude
    F->>A: API request with location headers
    A->>AUTH: JWT validation + user extraction
    AUTH->>LM: update_user_location_on_login()
    LM->>LM: validate_coordinates()
    LM->>DB: Update user.last_app_location_*
    DB-->>LM: Location saved
    LM-->>AUTH: Success
    AUTH-->>A: User authenticated with location

    Note over U,NS: 2. Transaction Processing Flow

    participant TXN as Transaction Source
    TXN->>A: POST /transactions (new transaction with merchant lat/lon)
    A->>TS: create_transaction()
    TS->>DB: INSERT INTO transactions
    DB->>DB: transaction_location_analysis VIEW calculates distance
    Note over DB: haversine_distance_km(user_lat, user_lon, merchant_lat, merchant_lon)
    DB-->>TS: Transaction created with location data
    TS-->>A: Transaction response

    Note over U,NS: 3. Alert Rule Evaluation Flow

    A->>ARS: Check active alert rules for user
    ARS->>DB: SELECT alert_rules WHERE user_id = ? AND is_active = true
    DB-->>ARS: Active alert rules
    
    loop For each location-based alert rule
        ARS->>ALG: trigger_alert_rule(rule, transaction)
        ALG->>ALG: parse_alert_to_sql_with_context()
        Note over ALG: Generates SQL: "SELECT * FROM transactions t JOIN users u ON t.user_id = u.id WHERE haversine_distance_km(...) > threshold"
        ALG->>DB: Execute generated SQL query
        DB-->>ALG: Query results
        ALG->>ALG: validate_sql() - check if alert triggered
        
        alt Alert Triggered (distance > threshold)
            ALG->>ALG: generate_alert_message()
            Note over ALG: Creates human-readable alert message
            ALG-->>ARS: Alert triggered with message
            ARS->>DB: INSERT AlertNotification
            ARS->>DB: UPDATE AlertRule.trigger_count++
            ARS->>NS: Send notification (email/SMS)
            NS-->>U: Alert notification sent
        else No Alert
            ALG-->>ARS: Alert not triggered
        end
    end

    Note over U,NS: 4. Risk Assessment Components

    rect rgb(255, 245, 235)
        Note over DB: Database Functions Available:
        Note over DB: • haversine_distance_km(lat1, lon1, lat2, lon2)
        Note over DB: • transaction_location_analysis VIEW
        Note over DB: • Risk levels: NORMAL, LOW_RISK, MEDIUM_RISK, HIGH_RISK, VERY_HIGH_RISK
    end

    rect rgb(240, 248, 255)
        Note over ALG: Python Risk Calculation:
        Note over ALG: • calculate_location_risk_score()
        Note over ALG: • Distance thresholds: 25km, 100km, 500km, 1000km
        Note over ALG: • Exponential risk scoring (0.0 to 1.0)
    end

    Note over U,NS: 5. Alert Types and Natural Language Processing

    rect rgb(245, 255, 245)
        Note over ALG: LLM Alert Classification:
        Note over ALG: • "spending" → AMOUNT_THRESHOLD
        Note over ALG: • "location" → LOCATION_BASED  
        Note over ALG: • "merchant" → MERCHANT_CATEGORY
        Note over ALG: • "pattern" → PATTERN_BASED
    end

    Note over U,NS: Example Location Alert Queries:
    Note over ALG: "Alert me if I spend more than $100 outside my home state"
    Note over ALG: "Notify me of transactions over 500km from my last location"
    Note over ALG: "Alert for any spending outside New York City"
```

## Key Components & Flow Summary

### 1. **Location Capture**
- Browser's Geolocation API captures user's current location
- Location headers (`X-User-Latitude`, `X-User-Longitude`) sent with API requests
- Auth middleware automatically captures and updates user location in database

### 2. **Transaction Processing**
- Transactions include merchant location (latitude/longitude)
- Database calculates distance using Haversine formula via SQL function
- `transaction_location_analysis` VIEW provides real-time risk assessment

### 3. **Alert Rule System**
- Users create natural language alert rules (e.g., "Alert me for spending over $100 more than 500km away")
- LLM parses natural language into SQL queries
- SQL queries use `haversine_distance_km()` function for location-based conditions

### 4. **Risk Scoring**
- **Distance Thresholds:** 25km (LOW), 100km (MEDIUM), 500km (HIGH), 1000km+ (VERY HIGH)
- **Risk Score:** Exponential function from 0.0 (no risk) to 1.0 (maximum risk)
- **Real-time Evaluation:** Every transaction is evaluated against active alert rules

### 5. **Notification System**
- Triggered alerts create `AlertNotification` records
- Notifications sent via email/SMS through configured channels
- Alert rules track trigger count and last triggered time

## Technical Features

- **Offline Geocoding:** Built-in city coordinates lookup for 150+ major cities
- **PostGIS Compatible:** Can use PostGIS ST_Distance for enhanced geospatial operations
- **Privacy Controls:** User consent management for location data
- **Development Mode:** Mock location data for testing without GPS access
- **Haversine Formula:** Accurate great-circle distance calculations

