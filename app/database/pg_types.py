ENUM_PATRON_STATUS = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT * FROM pg_type WHERE typname = 'patron_status'
        ) THEN
            CREATE TYPE patron_status AS ENUM  (
                'no', 'declined', 'yes'
            );
        END IF;
    END;
    $$"""

ALL_TYPES = [ENUM_PATRON_STATUS]
