-- =====================================================================
-- CLIPPING AGENCY TRACKER - DATABASE SCHEMA (SUPABASE / POSTGRESQL)
-- =====================================================================
-- Run this entire script in Supabase's "SQL Editor" with 1 click.
-- It creates all required tables, indexes, and sets up public access.
-- =====================================================================

-- 1. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. CAMPAIGNS TABLE
CREATE TABLE IF NOT EXISTS public.campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    cpm NUMERIC(10, 2) NOT NULL DEFAULT 1.50, -- $ per 1,000 approved views
    platform TEXT NOT NULL DEFAULT 'all',      -- 'all', 'tiktok', 'youtube', 'instagram'
    budget_cap NUMERIC(12, 2) DEFAULT NULL,   -- Optional total budget
    tag_filter TEXT DEFAULT NULL,             -- Optional required hashtag (e.g. #brand)
    start_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active',    -- 'active', 'paused', 'completed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. CLIPPERS TABLE
CREATE TABLE IF NOT EXISTS public.clippers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    contact TEXT DEFAULT '',                  -- Discord / Telegram / Phone
    handles JSONB NOT NULL DEFAULT '[]'::jsonb, -- Array of objects: [{"platform": "tiktok", "handle": "@user"}, ...]
    assigned_campaign_ids JSONB DEFAULT '[]'::jsonb, -- Array of campaign UUIDs
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. VIDEOS TABLE (Automatically populated & updated every 30 mins)
CREATE TABLE IF NOT EXISTS public.videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES public.campaigns(id) ON DELETE CASCADE,
    clipper_id UUID REFERENCES public.clippers(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,                   -- 'tiktok', 'youtube', 'instagram'
    handle TEXT NOT NULL,                     -- e.g. '@viralclipz'
    video_url TEXT NOT NULL UNIQUE,           -- Unique video link / identifier
    video_id_str TEXT DEFAULT '',             -- Platform native video ID
    title TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    views BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',   -- 'approved', 'pending', 'rejected', 'unsubmitted'
    is_pre_campaign BOOLEAN NOT NULL DEFAULT FALSE, -- True if posted before campaign start date
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ DEFAULT NULL,
    last_scraped_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. SYNC LOGS TABLE (Tracks background cron runs)
CREATE TABLE IF NOT EXISTS public.sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'success',   -- 'success', 'error', 'partial'
    handles_scanned INT NOT NULL DEFAULT 0,
    new_videos_found INT NOT NULL DEFAULT 0,
    views_updated INT NOT NULL DEFAULT 0,
    log_message TEXT DEFAULT ''
);

-- 6. AUTOMATIC UPDATED_AT TRIGGER
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trg_campaigns_updated ON public.campaigns;
CREATE TRIGGER trg_campaigns_updated BEFORE UPDATE ON public.campaigns FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS trg_clippers_updated ON public.clippers;
CREATE TRIGGER trg_clippers_updated BEFORE UPDATE ON public.clippers FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS trg_videos_updated ON public.videos;
CREATE TRIGGER trg_videos_updated BEFORE UPDATE ON public.videos FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- 7. PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_videos_handle ON public.videos(handle);
CREATE INDEX IF NOT EXISTS idx_videos_campaign ON public.videos(campaign_id);
CREATE INDEX IF NOT EXISTS idx_videos_clipper ON public.videos(clipper_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON public.videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_url ON public.videos(video_url);

-- 8. ROW LEVEL SECURITY (RLS) - Permissive for quick single-page app access
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clippers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_logs ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read & write with Supabase anon public key
DROP POLICY IF EXISTS "Anon public access campaigns" ON public.campaigns;
CREATE POLICY "Anon public access campaigns" ON public.campaigns FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Anon public access clippers" ON public.clippers;
CREATE POLICY "Anon public access clippers" ON public.clippers FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Anon public access videos" ON public.videos;
CREATE POLICY "Anon public access videos" ON public.videos FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Anon public access sync_logs" ON public.sync_logs;
CREATE POLICY "Anon public access sync_logs" ON public.sync_logs FOR ALL USING (true) WITH CHECK (true);
