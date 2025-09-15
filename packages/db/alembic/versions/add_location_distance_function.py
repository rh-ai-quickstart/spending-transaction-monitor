"""add location distance calculation function

Revision ID: location_distance_func
Revises: 1b64d9695755
Create Date: 2025-09-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'location_distance_func'
down_revision = '1b64d9695755'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add PostgreSQL function for calculating distance between two points using Haversine formula"""
    
    # Create the distance calculation function
    op.execute("""
        CREATE OR REPLACE FUNCTION haversine_distance_km(
            lat1 DOUBLE PRECISION, 
            lon1 DOUBLE PRECISION, 
            lat2 DOUBLE PRECISION, 
            lon2 DOUBLE PRECISION
        )
        RETURNS DOUBLE PRECISION AS $$
        DECLARE
            dlat DOUBLE PRECISION;
            dlon DOUBLE PRECISION;
            a DOUBLE PRECISION;
            c DOUBLE PRECISION;
            r DOUBLE PRECISION := 6371; -- Earth radius in kilometers
        BEGIN
            -- Return NULL if any coordinate is NULL
            IF lat1 IS NULL OR lon1 IS NULL OR lat2 IS NULL OR lon2 IS NULL THEN
                RETURN NULL;
            END IF;
            
            -- Convert degrees to radians
            lat1 := lat1 * PI() / 180;
            lon1 := lon1 * PI() / 180;
            lat2 := lat2 * PI() / 180;
            lon2 := lon2 * PI() / 180;
            
            -- Haversine formula
            dlat := lat2 - lat1;
            dlon := lon2 - lon1;
            a := SIN(dlat/2) * SIN(dlat/2) + COS(lat1) * COS(lat2) * SIN(dlon/2) * SIN(dlon/2);
            c := 2 * ASIN(SQRT(a));
            
            RETURN r * c;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)
    
    # Create a helper view for location-based transaction analysis
    op.execute("""
        CREATE OR REPLACE VIEW transaction_location_analysis AS
        SELECT 
            t.id as transaction_id,
            t.user_id,
            t.merchant_name,
            t.merchant_city,
            t.merchant_state,
            t.transaction_date,
            t.amount,
            u.email as user_email,
            u.last_app_location_latitude as user_lat,
            u.last_app_location_longitude as user_lon,
            u.last_app_location_timestamp as user_location_timestamp,
            t.merchant_latitude as merchant_lat,
            t.merchant_longitude as merchant_lon,
            haversine_distance_km(
                u.last_app_location_latitude, 
                u.last_app_location_longitude,
                t.merchant_latitude, 
                t.merchant_longitude
            ) as distance_km,
            CASE 
                WHEN u.last_app_location_latitude IS NULL 
                     OR u.last_app_location_longitude IS NULL 
                     OR t.merchant_latitude IS NULL 
                     OR t.merchant_longitude IS NULL THEN 'NO_LOCATION_DATA'
                WHEN haversine_distance_km(
                    u.last_app_location_latitude, 
                    u.last_app_location_longitude,
                    t.merchant_latitude, 
                    t.merchant_longitude
                ) > 1000 THEN 'VERY_HIGH_RISK'
                WHEN haversine_distance_km(
                    u.last_app_location_latitude, 
                    u.last_app_location_longitude,
                    t.merchant_latitude, 
                    t.merchant_longitude
                ) > 500 THEN 'HIGH_RISK'
                WHEN haversine_distance_km(
                    u.last_app_location_latitude, 
                    u.last_app_location_longitude,
                    t.merchant_latitude, 
                    t.merchant_longitude
                ) > 100 THEN 'MEDIUM_RISK'
                WHEN haversine_distance_km(
                    u.last_app_location_latitude, 
                    u.last_app_location_longitude,
                    t.merchant_latitude, 
                    t.merchant_longitude
                ) > 25 THEN 'LOW_RISK'
                ELSE 'NORMAL'
            END as risk_level
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE u.location_consent_given = true;
    """)


def downgrade() -> None:
    """Remove the distance function and helper view"""
    op.execute("DROP VIEW IF EXISTS transaction_location_analysis;")
    op.execute("DROP FUNCTION IF EXISTS haversine_distance_km(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION);")
