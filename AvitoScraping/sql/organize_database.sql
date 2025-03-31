-- SQL script to organize the Neon database structure
-- Creates schemas for "Knowledge DB" and "Avito Scraping"
-- Moves tables to their respective schemas

-- Create schemas if they don't exist
CREATE SCHEMA IF NOT EXISTS knowledge_db;
CREATE SCHEMA IF NOT EXISTS avito_scraping;

-- Get a list of all tables in the public schema
DO $$
DECLARE
    table_rec RECORD;
BEGIN
    -- Move knowledge base tables to knowledge_db schema
    FOR table_rec IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (
            tablename LIKE 'truck_%' OR 
            tablename LIKE 'faq%' OR 
            tablename LIKE 'company_%' OR 
            tablename LIKE 'contact_%' OR 
            tablename LIKE 'testimonial%' OR 
            tablename LIKE 'industry_%' OR 
            tablename LIKE 'objection_%' OR 
            tablename LIKE 'technical_%' OR 
            tablename LIKE 'knowledge_%' OR
            tablename LIKE 'financing_%' OR
            tablename = 'leads'
        )
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(table_rec.tablename) || ' SET SCHEMA knowledge_db';
        RAISE NOTICE 'Moved table % to knowledge_db schema', table_rec.tablename;
    END LOOP;
    
    -- Move Avito Scraping tables to avito_scraping schema
    FOR table_rec IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (
            tablename IN (
                'kamaz_54901', 'gazel_nn', 'kamaz_6520', 'shaanxi_x3000', 'faw_j6',
                'sitrak_c7h_max', 'dongfeng_gx', 'jac_n_series', 'kamaz_65115', 'foton_auman',
                'kamaz_5490_neo', 'isuzu_elf', 'sitrak_c7h', 'maz_5440', 'howo_t5g',
                'jac_s_series', 'dongfeng_captain_t', 'changan_m9', 'shacman_x3000', 'jac_x200',
                'avito_scraping_metadata'
            )
        )
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(table_rec.tablename) || ' SET SCHEMA avito_scraping';
        RAISE NOTICE 'Moved table % to avito_scraping schema', table_rec.tablename;
    END LOOP;
END $$;

-- Create a view in public schema to list all schemas and their tables
CREATE OR REPLACE VIEW public.database_structure AS
SELECT 
    n.nspname AS schema_name,
    c.relname AS table_name,
    CASE 
        WHEN c.relkind = 'r' THEN 'table'
        WHEN c.relkind = 'v' THEN 'view'
        WHEN c.relkind = 'm' THEN 'materialized view'
        WHEN c.relkind = 'i' THEN 'index'
        WHEN c.relkind = 'S' THEN 'sequence'
        WHEN c.relkind = 'f' THEN 'foreign table'
        ELSE c.relkind::text
    END AS object_type,
    pg_catalog.obj_description(c.oid, 'pg_class') AS description
FROM pg_catalog.pg_class c
LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE 
    c.relkind IN ('r', 'v', 'm') AND
    n.nspname NOT IN ('pg_catalog', 'information_schema') AND
    n.nspname IN ('public', 'knowledge_db', 'avito_scraping')
ORDER BY 1, 2;

-- Add comments to schemas
COMMENT ON SCHEMA knowledge_db IS 'Schema for Business Trucks knowledge base tables used by the AI agent';
COMMENT ON SCHEMA avito_scraping IS 'Schema for Avito Scraping project tables containing commercial transport data';

-- Add comments to the view
COMMENT ON VIEW public.database_structure IS 'View showing all tables and views in the main schemas';
