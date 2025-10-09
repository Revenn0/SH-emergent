-- ==========================================
-- MIGRATION SCRIPT
-- Update existing "Heavy Impact" alerts to "Crash detect"
-- ==========================================

-- This script updates all existing tracker_alerts that have "Heavy Impact" 
-- in their alert_type to use the new "Crash detect" category

BEGIN;

-- Update all Heavy Impact alerts to Crash detect
UPDATE tracker_alerts 
SET alert_type = 'Crash detect' 
WHERE alert_type LIKE '%Heavy Impact%';

-- Verify the update
SELECT 
    'Heavy Impact alerts updated to Crash detect' as message,
    COUNT(*) as updated_count
FROM tracker_alerts 
WHERE alert_type = 'Crash detect';

COMMIT;

-- ==========================================
-- VERIFICATION QUERIES
-- ==========================================

-- Check if any Heavy Impact alerts remain
-- SELECT COUNT(*) as remaining_heavy_impact 
-- FROM tracker_alerts 
-- WHERE alert_type LIKE '%Heavy Impact%';

-- Show current distribution of alert types
-- SELECT alert_type, COUNT(*) as count 
-- FROM tracker_alerts 
-- GROUP BY alert_type 
-- ORDER BY count DESC;
