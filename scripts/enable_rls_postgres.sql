-- PostgreSQL Row Level Security (RLS) Implementation for BlockShelf
-- This script enables RLS on user-owned tables to ensure data isolation
--
-- IMPORTANT: Run this script as a PostgreSQL superuser
-- Apply after all migrations are complete

-- ============================================================================
-- Enable Row Level Security on User-Owned Tables
-- ============================================================================

-- Enable RLS on inventory items
ALTER TABLE inventory_inventoryitem ENABLE ROW LEVEL SECURITY;

-- Enable RLS on notes
ALTER TABLE inventory_note ENABLE ROW LEVEL SECURITY;

-- Enable RLS on inventory shares
ALTER TABLE inventory_inventoryshare ENABLE ROW LEVEL SECURITY;

-- Enable RLS on collaborations
ALTER TABLE inventory_inventorycollab ENABLE ROW LEVEL SECURITY;

-- Enable RLS on login attempts (admin-only access)
ALTER TABLE inventory_loginattempt ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Create Policies for InventoryItem
-- ============================================================================

-- Users can SELECT their own inventory items
CREATE POLICY inventory_item_select_policy ON inventory_inventoryitem
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::integer);

-- Users can INSERT their own inventory items
CREATE POLICY inventory_item_insert_policy ON inventory_inventoryitem
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id')::integer);

-- Users can UPDATE their own inventory items
CREATE POLICY inventory_item_update_policy ON inventory_inventoryitem
    FOR UPDATE
    USING (user_id = current_setting('app.current_user_id')::integer);

-- Users can DELETE their own inventory items
CREATE POLICY inventory_item_delete_policy ON inventory_inventoryitem
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id')::integer);

-- ============================================================================
-- Create Policies for Note
-- ============================================================================

-- Users can SELECT their own notes
CREATE POLICY note_select_policy ON inventory_note
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::integer);

-- Users can INSERT their own notes
CREATE POLICY note_insert_policy ON inventory_note
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id')::integer);

-- Users can UPDATE their own notes
CREATE POLICY note_update_policy ON inventory_note
    FOR UPDATE
    USING (user_id = current_setting('app.current_user_id')::integer);

-- Users can DELETE their own notes
CREATE POLICY note_delete_policy ON inventory_note
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id')::integer);

-- ============================================================================
-- Create Policies for InventoryShare
-- ============================================================================

-- Users can SELECT their own shares
CREATE POLICY inventory_share_select_policy ON inventory_inventoryshare
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::integer);

-- Users can INSERT their own shares
CREATE POLICY inventory_share_insert_policy ON inventory_inventoryshare
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id')::integer);

-- Users can UPDATE their own shares
CREATE POLICY inventory_share_update_policy ON inventory_inventoryshare
    FOR UPDATE
    USING (user_id = current_setting('app.current_user_id')::integer);

-- Users can DELETE their own shares
CREATE POLICY inventory_share_delete_policy ON inventory_inventoryshare
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id')::integer);

-- ============================================================================
-- Create Policies for InventoryCollab
-- ============================================================================

-- Users can SELECT collaborations where they are owner or collaborator
CREATE POLICY inventory_collab_select_policy ON inventory_inventorycollab
    FOR SELECT
    USING (
        owner_id = current_setting('app.current_user_id')::integer
        OR collaborator_id = current_setting('app.current_user_id')::integer
    );

-- Only owners can INSERT collaborations
CREATE POLICY inventory_collab_insert_policy ON inventory_inventorycollab
    FOR INSERT
    WITH CHECK (owner_id = current_setting('app.current_user_id')::integer);

-- Only owners can UPDATE collaborations
CREATE POLICY inventory_collab_update_policy ON inventory_inventorycollab
    FOR UPDATE
    USING (owner_id = current_setting('app.current_user_id')::integer);

-- Only owners can DELETE collaborations
CREATE POLICY inventory_collab_delete_policy ON inventory_inventorycollab
    FOR DELETE
    USING (owner_id = current_setting('app.current_user_id')::integer);

-- ============================================================================
-- Create Policies for LoginAttempt (Admin Only)
-- ============================================================================

-- Only superusers/admins can SELECT login attempts
-- This requires checking if user is a superuser in Django before setting the session var
CREATE POLICY login_attempt_select_policy ON inventory_loginattempt
    FOR SELECT
    USING (current_setting('app.is_superuser', true)::boolean = true);

-- No INSERT policy needed (Django creates records)
-- No UPDATE/DELETE policies (records should not be modified)

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check if RLS is enabled on tables
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'inventory_%'
ORDER BY tablename;

-- List all policies
SELECT schemaname, tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename LIKE 'inventory_%'
ORDER BY tablename, cmd;

-- ============================================================================
-- Testing RLS (Run these queries to verify)
-- ============================================================================

-- Set a test user ID
-- SET LOCAL app.current_user_id = '1';
-- SET LOCAL app.is_superuser = 'false';

-- Try to query inventory items (should only see user 1's items)
-- SELECT * FROM inventory_inventoryitem;

-- Try to insert an item with a different user_id (should fail)
-- INSERT INTO inventory_inventoryitem (user_id, name, part_id, color, quantity_total, quantity_used)
-- VALUES (999, 'Test Item', 'TEST123', 'Red', 10, 0);

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================

-- To disable RLS on a table:
-- ALTER TABLE inventory_inventoryitem DISABLE ROW LEVEL SECURITY;

-- To drop a policy:
-- DROP POLICY IF EXISTS inventory_item_select_policy ON inventory_inventoryitem;

-- ============================================================================
-- Notes for Django Integration
-- ============================================================================

-- You need to create Django middleware to set the session variables:
--
-- In your Django middleware:
--
-- from django.db import connection
--
-- class RowLevelSecurityMiddleware:
--     def __init__(self, get_response):
--         self.get_response = get_response
--
--     def __call__(self, request):
--         if request.user.is_authenticated:
--             with connection.cursor() as cursor:
--                 cursor.execute(
--                     "SET LOCAL app.current_user_id = %s",
--                     [request.user.id]
--                 )
--                 cursor.execute(
--                     "SET LOCAL app.is_superuser = %s",
--                     [str(request.user.is_superuser).lower()]
--                 )
--         response = self.get_response(request)
--         return response
--
-- Add this middleware to MIDDLEWARE in settings.py after AuthenticationMiddleware
