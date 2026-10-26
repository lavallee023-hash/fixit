import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fixit import agent

def test_knows_supabase_oct30_grant_change():
    s = agent.SYSTEM
    assert "42501" in s and "Oct 30, 2026" in s and "grant select, insert, update, delete on public.X to authenticated" in s
    assert "PGRST200" in s and "AuthSessionMissingError" in s

def test_grant_advice_not_flagged_unsafe_but_disabling_rls_is():
    assert not agent.UNSAFE.search("Run: grant select, insert, update, delete on public.todos to authenticated; keep RLS enabled.")
    assert agent.UNSAFE.search("Just disable row level security on the table for now")
